# wanLLMDB Backend

This is the backend API for wanLLMDB, built with FastAPI and Python 3.11.

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.11
- **Database**: PostgreSQL + TimescaleDB
- **ORM**: SQLAlchemy
- **Migration**: Alembic
- **Authentication**: JWT (python-jose)
- **Password Hashing**: Passlib with bcrypt
- **Cache**: Redis

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Install dependencies
poetry install

# or with pip
pip install -r requirements.txt
```

### Environment Setup

Copy `.env.example` to `.env` and configure your environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your configuration.

### Database Setup

```bash
# Run migrations
poetry run alembic upgrade head
```

### Development

```bash
# Run development server
poetry run python -m app.main

# or
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) will be at `http://localhost:8000/docs`

### Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
poetry run black app

# Lint code
poetry run ruff check app

# Type checking
poetry run mypy app
```

## Project Structure

```
app/
├── api/
│   └── v1/            # API version 1
│       ├── auth.py    # Authentication endpoints
│       ├── projects.py
│       └── runs.py
├── core/              # Core functionality
│   ├── config.py      # Configuration
│   └── security.py    # Security utilities
├── db/                # Database
│   ├── database.py    # Database connection
│   └── base.py        # Base model imports
├── models/            # SQLAlchemy models
│   ├── user.py
│   ├── project.py
│   └── run.py
├── schemas/           # Pydantic schemas
│   ├── user.py
│   ├── project.py
│   └── run.py
├── services/          # Business logic
├── repositories/      # Data access layer
└── main.py            # Application entry point

alembic/               # Database migrations
tests/                 # Test files
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user

### Projects (Coming soon)
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Runs (Coming soon)
- `GET /api/v1/projects/{id}/runs` - List runs
- `POST /api/v1/projects/{id}/runs` - Create run
- `GET /api/v1/runs/{id}` - Get run
- `PATCH /api/v1/runs/{id}` - Update run
- `DELETE /api/v1/runs/{id}` - Delete run

## Database Migrations

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Run migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# Show current revision
poetry run alembic current

# Show migration history
poetry run alembic history
```

## Development Tips

1. Always use dependency injection for database sessions and authentication
2. Follow the repository pattern for data access
3. Keep business logic in services, not in API endpoints
4. Write tests for all new features
5. Use Pydantic schemas for request/response validation
