"""
Repository for Sweep operations.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.sweep import Sweep, SweepRun, SweepState
from app.models.run import Run
from app.schemas.sweep import SweepCreate, SweepUpdate, SweepRunCreate


class SweepRepository:
    """Repository for sweep database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, sweep_in: SweepCreate, user_id: UUID) -> Sweep:
        """Create a new sweep."""
        sweep = Sweep(
            **sweep_in.model_dump(),
            created_by=user_id,
        )
        self.db.add(sweep)
        self.db.commit()
        self.db.refresh(sweep)
        return sweep

    def get(self, sweep_id: UUID) -> Optional[Sweep]:
        """Get a sweep by ID."""
        return self.db.query(Sweep).filter(Sweep.id == sweep_id).first()

    def list(
        self,
        project_id: Optional[UUID] = None,
        state: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Sweep], int]:
        """List sweeps with filters and pagination."""
        query = self.db.query(Sweep)

        # Apply filters
        if project_id:
            query = query.filter(Sweep.project_id == project_id)
        if state:
            query = query.filter(Sweep.state == state)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        sweeps = query.order_by(desc(Sweep.created_at)).offset(skip).limit(limit).all()

        return sweeps, total

    def update(self, sweep_id: UUID, sweep_in: SweepUpdate) -> Optional[Sweep]:
        """Update a sweep."""
        sweep = self.get(sweep_id)
        if not sweep:
            return None

        update_data = sweep_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sweep, field, value)

        self.db.commit()
        self.db.refresh(sweep)
        return sweep

    def delete(self, sweep_id: UUID) -> bool:
        """Delete a sweep."""
        sweep = self.get(sweep_id)
        if not sweep:
            return False

        self.db.delete(sweep)
        self.db.commit()
        return True

    def start_sweep(self, sweep_id: UUID) -> Optional[Sweep]:
        """Mark a sweep as started."""
        sweep = self.get(sweep_id)
        if not sweep:
            return None

        sweep.state = SweepState.RUNNING
        sweep.started_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(sweep)
        return sweep

    def finish_sweep(self, sweep_id: UUID) -> Optional[Sweep]:
        """Mark a sweep as finished."""
        sweep = self.get(sweep_id)
        if not sweep:
            return None

        sweep.state = SweepState.FINISHED
        sweep.finished_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(sweep)
        return sweep

    def pause_sweep(self, sweep_id: UUID) -> Optional[Sweep]:
        """Pause a sweep."""
        sweep = self.get(sweep_id)
        if not sweep:
            return None

        sweep.state = SweepState.PAUSED
        self.db.commit()
        self.db.refresh(sweep)
        return sweep

    def resume_sweep(self, sweep_id: UUID) -> Optional[Sweep]:
        """Resume a paused sweep."""
        sweep = self.get(sweep_id)
        if not sweep:
            return None

        sweep.state = SweepState.RUNNING
        self.db.commit()
        self.db.refresh(sweep)
        return sweep

    # Sweep Run operations
    def create_sweep_run(self, sweep_run_in: SweepRunCreate) -> SweepRun:
        """Create a sweep run association."""
        sweep_run = SweepRun(**sweep_run_in.model_dump())
        self.db.add(sweep_run)

        # Increment run count on sweep
        sweep = self.get(sweep_run_in.sweep_id)
        if sweep:
            sweep.run_count += 1

        self.db.commit()
        self.db.refresh(sweep_run)
        return sweep_run

    def get_sweep_run(self, sweep_run_id: UUID) -> Optional[SweepRun]:
        """Get a sweep run by ID."""
        return self.db.query(SweepRun).filter(SweepRun.id == sweep_run_id).first()

    def get_sweep_run_by_run_id(self, run_id: UUID) -> Optional[SweepRun]:
        """Get a sweep run by run ID."""
        return self.db.query(SweepRun).filter(SweepRun.run_id == run_id).first()

    def list_sweep_runs(
        self,
        sweep_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[SweepRun], int]:
        """List all runs for a sweep."""
        query = self.db.query(SweepRun).filter(SweepRun.sweep_id == sweep_id)

        total = query.count()
        sweep_runs = query.order_by(SweepRun.created_at).offset(skip).limit(limit).all()

        return sweep_runs, total

    def update_sweep_run_result(
        self,
        sweep_run_id: UUID,
        metric_value: float,
    ) -> Optional[SweepRun]:
        """Update sweep run with evaluation result."""
        sweep_run = self.get_sweep_run(sweep_run_id)
        if not sweep_run:
            return None

        sweep_run.metric_value = metric_value
        sweep_run.evaluated_at = datetime.utcnow()

        # Check if this is the best run for the sweep
        sweep = self.get(sweep_run.sweep_id)
        if sweep:
            is_better = False
            if sweep.best_value is None:
                is_better = True
            elif sweep.metric_goal.value == "maximize":
                is_better = metric_value > sweep.best_value
            else:  # minimize
                is_better = metric_value < sweep.best_value

            if is_better:
                # Mark previous best as not best
                if sweep.best_run_id:
                    prev_best = self.get_sweep_run_by_run_id(sweep.best_run_id)
                    if prev_best:
                        prev_best.is_best = False

                # Update sweep with new best
                sweep.best_value = metric_value
                sweep.best_run_id = sweep_run.run_id
                sweep_run.is_best = True
            else:
                sweep_run.is_best = False

        self.db.commit()
        self.db.refresh(sweep_run)
        return sweep_run

    def get_sweep_stats(self, sweep_id: UUID) -> dict:
        """Get statistics for a sweep."""
        sweep = self.get(sweep_id)
        if not sweep:
            return {}

        # Get run statistics
        sweep_runs = self.db.query(SweepRun).filter(SweepRun.sweep_id == sweep_id).all()
        run_ids = [sr.run_id for sr in sweep_runs]

        runs = self.db.query(Run).filter(Run.id.in_(run_ids)).all() if run_ids else []

        completed_runs = len([r for r in runs if r.state.value == "finished"])
        running_runs = len([r for r in runs if r.state.value == "running"])
        failed_runs = len([r for r in runs if r.state.value in ["crashed", "failed"]])

        # Get best run params
        best_params = None
        if sweep.best_run_id:
            best_sweep_run = self.get_sweep_run_by_run_id(sweep.best_run_id)
            if best_sweep_run:
                best_params = best_sweep_run.suggested_params

        return {
            "sweep_id": sweep_id,
            "total_runs": len(runs),
            "completed_runs": completed_runs,
            "running_runs": running_runs,
            "failed_runs": failed_runs,
            "best_value": sweep.best_value,
            "best_run_id": sweep.best_run_id,
            "best_params": best_params,
        }

    def get_parallel_coordinates_data(self, sweep_id: UUID) -> dict:
        """Get data for parallel coordinates visualization."""
        sweep = self.get(sweep_id)
        if not sweep:
            return {}

        # Get all sweep runs with their run data
        sweep_runs = self.db.query(SweepRun).filter(
            SweepRun.sweep_id == sweep_id,
            SweepRun.metric_value.isnot(None)
        ).all()

        if not sweep_runs:
            return {
                "sweep_id": sweep_id,
                "dimensions": [],
                "data": [],
                "best_index": None,
            }

        # Extract parameter names from config
        param_names = list(sweep.config.keys())
        dimensions = param_names + [sweep.metric_name]

        # Build data array
        data = []
        best_index = None

        for idx, sweep_run in enumerate(sweep_runs):
            row = {}

            # Add parameter values
            if sweep_run.suggested_params:
                for param_name in param_names:
                    value = sweep_run.suggested_params.get(param_name)
                    # Convert to float for visualization
                    if isinstance(value, (int, float)):
                        row[param_name] = float(value)
                    elif isinstance(value, str):
                        # For categorical, we'll need to map to numbers
                        # This should be handled in the frontend
                        row[param_name] = value
                    else:
                        row[param_name] = value

            # Add metric value
            row[sweep.metric_name] = sweep_run.metric_value

            # Track best run
            if sweep_run.is_best:
                best_index = idx

            data.append(row)

        return {
            "sweep_id": sweep_id,
            "dimensions": dimensions,
            "data": data,
            "best_index": best_index,
        }
