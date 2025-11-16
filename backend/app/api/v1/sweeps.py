"""
Sweep API endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.sweep_repository import SweepRepository
from app.services.optuna_service import optuna_service
from app.schemas.sweep import (
    Sweep,
    SweepCreate,
    SweepUpdate,
    SweepList,
    SweepSuggestRequest,
    SweepSuggestResponse,
    SweepStats,
    ParallelCoordinatesData,
    SweepWithStats,
)

router = APIRouter()


@router.post("", response_model=Sweep, status_code=status.HTTP_201_CREATED)
def create_sweep(
    sweep_in: SweepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new hyperparameter sweep."""
    repo = SweepRepository(db)
    sweep = repo.create(sweep_in, current_user.id)

    # Initialize Optuna study if using Bayesian optimization
    if sweep.method == "bayes":
        try:
            optuna_service.create_study(sweep)
        except Exception as e:
            print(f"Warning: Failed to create Optuna study: {e}")

    return sweep


@router.get("", response_model=SweepList)
def list_sweeps(
    project_id: Optional[UUID] = None,
    state: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sweeps with filters and pagination."""
    repo = SweepRepository(db)

    skip = (page - 1) * page_size
    sweeps, total = repo.list(
        project_id=project_id,
        state=state,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": sweeps,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
    }


@router.get("/{sweep_id}", response_model=SweepWithStats)
def get_sweep(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a sweep by ID with statistics."""
    repo = SweepRepository(db)
    sweep = repo.get(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )

    # Get statistics
    stats = repo.get_sweep_stats(sweep_id)

    # Get parameter importance if available
    try:
        importance = optuna_service.get_parameter_importance(sweep)
        if importance:
            stats["parameter_importance"] = importance
    except Exception as e:
        print(f"Error getting parameter importance: {e}")

    return {
        **sweep.__dict__,
        "stats": stats,
    }


@router.put("/{sweep_id}", response_model=Sweep)
def update_sweep(
    sweep_id: UUID,
    sweep_in: SweepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a sweep."""
    repo = SweepRepository(db)
    sweep = repo.update(sweep_id, sweep_in)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )
    return sweep


@router.delete("/{sweep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sweep(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a sweep."""
    repo = SweepRepository(db)
    success = repo.delete(sweep_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )


# Sweep control endpoints
@router.post("/{sweep_id}/start", response_model=Sweep)
def start_sweep(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a sweep."""
    repo = SweepRepository(db)
    sweep = repo.start_sweep(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )
    return sweep


@router.post("/{sweep_id}/pause", response_model=Sweep)
def pause_sweep(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause a sweep."""
    repo = SweepRepository(db)
    sweep = repo.pause_sweep(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )
    return sweep


@router.post("/{sweep_id}/resume", response_model=Sweep)
def resume_sweep(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused sweep."""
    repo = SweepRepository(db)
    sweep = repo.resume_sweep(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )
    return sweep


@router.post("/{sweep_id}/finish", response_model=Sweep)
def finish_sweep(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a sweep as finished."""
    repo = SweepRepository(db)
    sweep = repo.finish_sweep(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )
    return sweep


# Parameter suggestion endpoint
@router.post("/{sweep_id}/suggest", response_model=SweepSuggestResponse)
def suggest_parameters(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Suggest next set of hyperparameters.

    This endpoint is called by agents to get the next set of parameters to try.
    """
    repo = SweepRepository(db)
    sweep = repo.get(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )

    # Check if sweep is at capacity
    if sweep.run_cap and sweep.run_count >= sweep.run_cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sweep has reached maximum number of runs",
        )

    # Check if sweep is running
    if sweep.state not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sweep is {sweep.state}, cannot suggest parameters",
        )

    try:
        # Get suggestion from optimization service
        if sweep.method == "bayes":
            result = optuna_service.suggest_parameters(sweep)
            return {
                "suggested_params": result["suggested_params"],
                "trial_number": result["trial_number"],
            }
        else:
            # For random and grid search, implement simple suggestion
            import random

            suggested_params = {}
            for param_name, param_config in sweep.config.items():
                if "values" in param_config:
                    suggested_params[param_name] = random.choice(param_config["values"])
                elif "distribution" in param_config:
                    dist = param_config["distribution"]
                    min_val = param_config.get("min", 0)
                    max_val = param_config.get("max", 1)

                    if dist == "uniform":
                        suggested_params[param_name] = random.uniform(min_val, max_val)
                    elif dist == "log_uniform":
                        import math
                        log_min = math.log(min_val)
                        log_max = math.log(max_val)
                        suggested_params[param_name] = math.exp(random.uniform(log_min, log_max))
                    elif dist == "int_uniform":
                        suggested_params[param_name] = random.randint(int(min_val), int(max_val))

            return {
                "suggested_params": suggested_params,
                "trial_number": sweep.run_count,
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suggest parameters: {str(e)}",
        )


# Statistics and visualization endpoints
@router.get("/{sweep_id}/stats", response_model=SweepStats)
def get_sweep_stats(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get statistics for a sweep."""
    repo = SweepRepository(db)
    sweep = repo.get(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )

    stats = repo.get_sweep_stats(sweep_id)

    # Try to get parameter importance
    try:
        importance = optuna_service.get_parameter_importance(sweep)
        if importance:
            stats["parameter_importance"] = importance
    except Exception:
        pass

    return stats


@router.get("/{sweep_id}/parallel-coordinates", response_model=ParallelCoordinatesData)
def get_parallel_coordinates_data(
    sweep_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get data for parallel coordinates visualization."""
    repo = SweepRepository(db)
    sweep = repo.get(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )

    data = repo.get_parallel_coordinates_data(sweep_id)
    return data


# Sweep runs endpoints
@router.get("/{sweep_id}/runs")
def list_sweep_runs(
    sweep_id: UUID,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all runs for a sweep."""
    repo = SweepRepository(db)
    sweep = repo.get(sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sweep not found",
        )

    skip = (page - 1) * page_size
    sweep_runs, total = repo.list_sweep_runs(sweep_id, skip, page_size)

    # Enrich with run data
    from app.repositories.run_repository import RunRepository
    run_repo = RunRepository(db)

    enriched_runs = []
    for sweep_run in sweep_runs:
        run = run_repo.get_run(sweep_run.run_id)
        enriched_runs.append({
            **sweep_run.__dict__,
            "run": run.__dict__ if run else None,
        })

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": enriched_runs,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
    }
