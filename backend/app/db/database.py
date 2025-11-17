from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# Main database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Import models so that Base.metadata is populated, then create tables on startup.
# This is primarily for local/docker development; in real deployments Alembic migrations
# should be used instead.
from app.db import base as _models  # noqa: F401

# Create all tables (ignore errors for existing tables/indexes)
# We create tables and indexes separately to handle errors gracefully
from sqlalchemy import inspect as sqlalchemy_inspect, text

try:
    inspector = sqlalchemy_inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    # Clean up orphaned indexes (indexes without their tables)
    with engine.begin() as conn:
        # Get all indexes that reference non-existent tables
        result = conn.execute(text("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            AND tablename NOT IN (SELECT tablename FROM information_schema.tables WHERE table_schema = 'public')
        """))
        for row in result:
            index_name, table_name = row[0], row[1]
            try:
                conn.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
                print(f"Dropped orphaned index: {index_name} (table {table_name} does not exist)")
            except Exception as e:
                print(f"Note: Could not drop orphaned index {index_name}: {e}")
    
    # Get updated list after dropping orphaned indexes
    existing_tables = set(inspector.get_table_names())
    
    # Create tables that don't exist (retry logic for dependencies)
    # We retry because tables with foreign keys need their referenced tables to exist first
    max_rounds = 10
    for round_num in range(max_rounds):
        created_any = False
        # Refresh inspector to get latest table list
        inspector = sqlalchemy_inspect(engine)
        current_tables = set(inspector.get_table_names())
        existing_tables.update(current_tables)
        
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                try:
                    # Create table (this will also create indexes, but we'll handle errors)
                    table.create(bind=engine, checkfirst=True)
                    print(f"Created table: {table_name}")
                    existing_tables.add(table_name)
                    created_any = True
                except Exception as e:
                    error_msg = str(e).lower()
                    # If it's an index error but table might have been created, check
                    if "index" in error_msg and ("already exists" in error_msg or "duplicate" in error_msg):
                        # Table might have been created despite index error
                        if table_name in inspector.get_table_names():
                            existing_tables.add(table_name)
                            created_any = True
                            print(f"Table {table_name} exists (index error ignored)")
                    # Ignore "already exists" errors for tables
                    elif "already exists" in error_msg or "duplicate" in error_msg:
                        existing_tables.add(table_name)
                        created_any = True
                    # For dependency errors, we'll retry in next round
                    elif "does not exist" in error_msg or "undefined" in error_msg:
                        # Dependency not ready yet, will retry
                        pass
                    # For other errors on first round, log it
                    elif round_num == 0:
                        print(f"Note: Could not create table {table_name} (will retry): {error_msg[:100]}")
        
        if not created_any:
            break  # No more tables to create
    
    print("Table creation completed")
        
except Exception as e:
    # Log but don't fail - tables/indexes may already exist
    # Some errors are expected (e.g., duplicate indexes)
    error_msg = str(e)
    if "already exists" not in error_msg.lower() and "duplicate" not in error_msg.lower():
        print(f"Note: Error during table creation: {e}")


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
