"""Repository for run log operations."""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.models.run_log import RunLog
from app.schemas.run_log import RunLogCreate, RunLogFilter


class RunLogRepository:
    """Repository for managing run logs."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, run_id: UUID, log_data: RunLogCreate) -> RunLog:
        """Create a new run log.

        Args:
            run_id: ID of the run
            log_data: Log data

        Returns:
            Created run log
        """
        # Get next line number if not provided
        if log_data.line_number is None:
            max_line = (
                self.db.query(func.max(RunLog.line_number))
                .filter(RunLog.run_id == run_id)
                .scalar()
            )
            line_number = (max_line or 0) + 1
        else:
            line_number = log_data.line_number

        run_log = RunLog(
            run_id=run_id,
            level=log_data.level,
            message=log_data.message,
            timestamp=log_data.timestamp,
            source=log_data.source,
            line_number=line_number,
        )
        self.db.add(run_log)
        self.db.commit()
        self.db.refresh(run_log)
        return run_log

    def create_batch(self, run_id: UUID, logs: List[RunLogCreate]) -> List[RunLog]:
        """Batch create run logs.

        Args:
            run_id: ID of the run
            logs: List of log data

        Returns:
            List of created run logs
        """
        if not logs:
            return []

        # Get next line number
        max_line = (
            self.db.query(func.max(RunLog.line_number))
            .filter(RunLog.run_id == run_id)
            .scalar()
        )
        next_line = (max_line or 0) + 1

        run_logs = []
        for i, log_data in enumerate(logs):
            line_number = log_data.line_number if log_data.line_number else next_line + i
            run_log = RunLog(
                run_id=run_id,
                level=log_data.level,
                message=log_data.message,
                timestamp=log_data.timestamp,
                source=log_data.source,
                line_number=line_number,
            )
            run_logs.append(run_log)

        self.db.bulk_save_objects(run_logs, return_defaults=True)
        self.db.commit()
        return run_logs

    def get(self, log_id: UUID) -> Optional[RunLog]:
        """Get a run log by ID.

        Args:
            log_id: Log ID

        Returns:
            Run log if found, None otherwise
        """
        return self.db.query(RunLog).filter(RunLog.id == log_id).first()

    def list_by_run(
        self,
        run_id: UUID,
        filter_params: Optional[RunLogFilter] = None,
        skip: int = 0,
        limit: int = 1000
    ) -> Tuple[List[RunLog], int]:
        """List logs for a run with optional filtering.

        Args:
            run_id: Run ID
            filter_params: Filter parameters
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of logs, total count)
        """
        query = self.db.query(RunLog).filter(RunLog.run_id == run_id)

        # Apply filters
        if filter_params:
            if filter_params.level:
                query = query.filter(RunLog.level == filter_params.level)

            if filter_params.source:
                query = query.filter(RunLog.source == filter_params.source)

            if filter_params.search:
                search_pattern = f"%{filter_params.search}%"
                query = query.filter(RunLog.message.ilike(search_pattern))

            if filter_params.start_time:
                query = query.filter(RunLog.timestamp >= filter_params.start_time)

            if filter_params.end_time:
                query = query.filter(RunLog.timestamp <= filter_params.end_time)

        total = query.count()

        logs = (
            query
            .order_by(RunLog.timestamp.asc(), RunLog.line_number.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return logs, total

    def get_latest_logs(
        self,
        run_id: UUID,
        limit: int = 100
    ) -> List[RunLog]:
        """Get latest logs for a run.

        Args:
            run_id: Run ID
            limit: Maximum number of logs to return

        Returns:
            List of latest logs
        """
        logs = (
            self.db.query(RunLog)
            .filter(RunLog.run_id == run_id)
            .order_by(RunLog.timestamp.desc(), RunLog.line_number.desc())
            .limit(limit)
            .all()
        )
        # Reverse to get chronological order
        return list(reversed(logs))

    def delete_by_run(self, run_id: UUID) -> int:
        """Delete all logs for a run.

        Args:
            run_id: Run ID

        Returns:
            Number of logs deleted
        """
        count = self.db.query(RunLog).filter(RunLog.run_id == run_id).delete()
        self.db.commit()
        return count

    def get_log_count_by_run(self, run_id: UUID) -> int:
        """Get count of logs for a run.

        Args:
            run_id: Run ID

        Returns:
            Number of logs
        """
        return self.db.query(RunLog).filter(RunLog.run_id == run_id).count()

    def get_log_levels_summary(self, run_id: UUID) -> dict:
        """Get summary of log levels for a run.

        Args:
            run_id: Run ID

        Returns:
            Dictionary with counts per level
        """
        results = (
            self.db.query(RunLog.level, func.count(RunLog.id))
            .filter(RunLog.run_id == run_id)
            .group_by(RunLog.level)
            .all()
        )
        return {level: count for level, count in results}
