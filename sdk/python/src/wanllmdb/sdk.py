"""
Core SDK functions for run management and metric logging.
"""

import os
import time
from typing import Any, Dict, List, Optional

import wanllmdb
from wanllmdb.run import Run
from wanllmdb.config import Config
from wanllmdb.api_client import APIClient
from wanllmdb.errors import WanLLMDBError


def init(
    project: Optional[str] = None,
    name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    monitor_system: bool = True,
    monitor_interval: int = 30,
    git_tracking: bool = True,
    capture_logs: bool = True,
    reinit: bool = False,
) -> Run:
    """
    Initialize a new run.

    Args:
        project: Project name (required, or set via env var WANLLMDB_PROJECT)
        name: Run name (optional, auto-generated if not provided)
        config: Configuration dictionary (hyperparameters)
        tags: List of tags for organizing runs
        notes: Description/notes for the run
        monitor_system: Enable system metrics collection
        monitor_interval: System metrics collection interval in seconds
        git_tracking: Enable automatic git information capture
        capture_logs: Enable automatic log capture (stdout/stderr)
        reinit: Allow reinitializing if a run is already active

    Returns:
        Run: The initialized run object

    Raises:
        WanLLMDBError: If project is not provided or run already exists

    Example:
        >>> import wanllmdb as wandb
        >>> run = wandb.init(
        ...     project="my-project",
        ...     config={"lr": 0.001, "batch_size": 32},
        ...     tags=["baseline"]
        ... )
    """
    # Check for existing run
    if wanllmdb._run is not None and not reinit:
        raise WanLLMDBError(
            "A run is already initialized. Call wandb.finish() first or use reinit=True."
        )

    # Get configuration
    global_config = wanllmdb.get_config()

    # Determine project
    if project is None:
        project = os.environ.get("WANLLMDB_PROJECT") or global_config.project
    if project is None:
        raise WanLLMDBError(
            "Project name is required. Provide via project= argument, "
            "WANLLMDB_PROJECT environment variable, or config file."
        )

    # Create API client
    api_client = APIClient(
        api_url=global_config.api_url,
        metric_url=global_config.metric_url,
        username=global_config.username,
        password=global_config.password,
        api_key=global_config.api_key,
    )

    # Authenticate
    api_client.login()

    # Get or create project
    try:
        project_data = api_client.get_project_by_name(project)
        project_id = project_data["id"]
    except Exception:
        # Create project if it doesn't exist
        project_data = api_client.create_project({"name": project})
        project_id = project_data["id"]

    # Create run
    run = Run(
        api_client=api_client,
        project_id=project_id,
        name=name,
        config=config or {},
        tags=tags or [],
        notes=notes,
        monitor_system=monitor_system,
        monitor_interval=monitor_interval,
        git_tracking=git_tracking,
        capture_logs=capture_logs,
    )

    # Start the run
    run.start()

    # Set as active run
    wanllmdb.set_run(run)

    return run


def log(
    metrics: Dict[str, Any],
    step: Optional[int] = None,
    commit: bool = True,
) -> None:
    """
    Log metrics for the current run.

    Args:
        metrics: Dictionary of metric name-value pairs
        step: Step number (auto-increments if not provided)
        commit: Immediately send metrics to server (default: True)

    Raises:
        WanLLMDBError: If no run is initialized

    Example:
        >>> wandb.log({"loss": 0.5, "accuracy": 0.95})
        >>> wandb.log({"loss": 0.4}, step=100)
    """
    run = wanllmdb.get_run()
    if run is None:
        raise WanLLMDBError(
            "No run is initialized. Call wandb.init() first."
        )

    run.log(metrics, step=step, commit=commit)


def finish(exit_code: int = 0) -> None:
    """
    Finish the current run.

    Args:
        exit_code: Exit code (0=success, non-zero=failure)

    Example:
        >>> wandb.finish()
        >>> wandb.finish(exit_code=1)  # Mark as failed
    """
    run = wanllmdb.get_run()
    if run is not None:
        run.finish(exit_code=exit_code)
        wanllmdb.set_run(None)


def save(
    glob_str: str,
    base_path: Optional[str] = None,
    policy: str = "live"
) -> None:
    """
    Save files to the current run.

    This function uploads files to be associated with the run. Unlike artifacts,
    these files are directly tied to a specific run and are not versioned.

    Args:
        glob_str: File path or glob pattern (e.g., "*.txt", "data/**/*.csv")
        base_path: Base path for computing relative paths. If None, uses cwd
        policy: Upload policy - "live" (immediate), "end" (at run end), "now" (same as live)

    Raises:
        WanLLMDBError: If no run is initialized

    Example:
        >>> wandb.save("model.pkl")  # Save single file
        >>> wandb.save("logs/*.txt")  # Save all txt files in logs/
        >>> wandb.save("data/**/*.csv")  # Save all csv files recursively
    """
    run = wanllmdb.get_run()
    if run is None:
        raise WanLLMDBError(
            "No run is initialized. Call wandb.init() first."
        )

    run.save(glob_str, base_path=base_path, policy=policy)


# Convenience properties for accessing run attributes
class _RunProxy:
    """Proxy object for accessing run attributes."""

    @property
    def config(self):
        """Access run configuration."""
        run = wanllmdb.get_run()
        if run is None:
            raise WanLLMDBError("No run is initialized.")
        return run.config

    @property
    def summary(self):
        """Access run summary."""
        run = wanllmdb.get_run()
        if run is None:
            raise WanLLMDBError("No run is initialized.")
        return run.summary

    @property
    def tags(self):
        """Access run tags."""
        run = wanllmdb.get_run()
        if run is None:
            raise WanLLMDBError("No run is initialized.")
        return run.tags

    @property
    def id(self):
        """Get run ID."""
        run = wanllmdb.get_run()
        if run is None:
            raise WanLLMDBError("No run is initialized.")
        return run.id

    @property
    def name(self):
        """Get run name."""
        run = wanllmdb.get_run()
        if run is None:
            raise WanLLMDBError("No run is initialized.")
        return run.name


# Create proxy instance
run = _RunProxy()
