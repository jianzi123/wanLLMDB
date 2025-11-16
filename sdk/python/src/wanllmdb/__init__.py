"""
wanLLMDB Python SDK

A powerful Python SDK for ML experiment management.
"""

__version__ = "0.1.0"

from wanllmdb.sdk import init, finish, log
from wanllmdb.run import Run
from wanllmdb.config import Config
from wanllmdb.sweep import sweep, agent, SweepController
from wanllmdb import errors

# Global state
_run: Run | None = None
_config: Config | None = None


def get_run() -> Run | None:
    """Get the current active run."""
    return _run


def set_run(run: Run | None) -> None:
    """Set the current active run."""
    global _run
    _run = run


def get_config() -> Config:
    """Get the global configuration."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


# Convenience attributes
@property
def run() -> Run | None:
    """Current active run."""
    return get_run()


@property
def config() -> Config:
    """Global configuration."""
    return get_config()


__all__ = [
    "__version__",
    "init",
    "finish",
    "log",
    "Run",
    "Config",
    "sweep",
    "agent",
    "SweepController",
    "errors",
    "run",
    "config",
]
