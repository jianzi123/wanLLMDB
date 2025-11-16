"""Repository for run file operations."""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.run_file import RunFile
from app.schemas.run_file import RunFileCreate, RunFileUpdate


class RunFileRepository:
    """Repository for managing run files."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, run_id: UUID, file_data: RunFileCreate) -> RunFile:
        """Create a new run file.

        Args:
            run_id: ID of the run
            file_data: File data

        Returns:
            Created run file
        """
        run_file = RunFile(
            run_id=run_id,
            name=file_data.name,
            path=file_data.path,
            size=file_data.size,
            content_type=file_data.content_type,
            storage_key=file_data.storage_key,
            md5_hash=file_data.md5_hash,
            sha256_hash=file_data.sha256_hash,
            description=file_data.description,
        )
        self.db.add(run_file)
        self.db.commit()
        self.db.refresh(run_file)
        return run_file

    def get(self, file_id: UUID) -> Optional[RunFile]:
        """Get a run file by ID.

        Args:
            file_id: File ID

        Returns:
            Run file if found, None otherwise
        """
        return self.db.query(RunFile).filter(RunFile.id == file_id).first()

    def get_by_run_and_path(self, run_id: UUID, path: str) -> Optional[RunFile]:
        """Get a run file by run ID and path.

        Args:
            run_id: Run ID
            path: File path

        Returns:
            Run file if found, None otherwise
        """
        return (
            self.db.query(RunFile)
            .filter(RunFile.run_id == run_id, RunFile.path == path)
            .first()
        )

    def list_by_run(
        self,
        run_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[RunFile], int]:
        """List files for a run with pagination.

        Args:
            run_id: Run ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of files, total count)
        """
        query = self.db.query(RunFile).filter(RunFile.run_id == run_id)

        total = query.count()

        files = (
            query
            .order_by(RunFile.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return files, total

    def update(self, file_id: UUID, file_data: RunFileUpdate) -> Optional[RunFile]:
        """Update a run file.

        Args:
            file_id: File ID
            file_data: Updated file data

        Returns:
            Updated run file if found, None otherwise
        """
        run_file = self.get(file_id)
        if not run_file:
            return None

        for field, value in file_data.model_dump(exclude_unset=True).items():
            setattr(run_file, field, value)

        self.db.commit()
        self.db.refresh(run_file)
        return run_file

    def delete(self, file_id: UUID) -> bool:
        """Delete a run file.

        Args:
            file_id: File ID

        Returns:
            True if deleted, False if not found
        """
        run_file = self.get(file_id)
        if not run_file:
            return False

        self.db.delete(run_file)
        self.db.commit()
        return True

    def get_total_size_by_run(self, run_id: UUID) -> int:
        """Get total size of all files for a run.

        Args:
            run_id: Run ID

        Returns:
            Total size in bytes
        """
        result = (
            self.db.query(func.coalesce(func.sum(RunFile.size), 0))
            .filter(RunFile.run_id == run_id)
            .scalar()
        )
        return int(result)

    def get_file_count_by_run(self, run_id: UUID) -> int:
        """Get count of files for a run.

        Args:
            run_id: Run ID

        Returns:
            Number of files
        """
        return self.db.query(RunFile).filter(RunFile.run_id == run_id).count()
