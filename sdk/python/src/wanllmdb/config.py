"""
Configuration management for wanLLMDB SDK.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration for wanLLMDB SDK."""

    api_url: str = "http://localhost:8000/api/v1"
    metric_url: str = "http://localhost:8001/api/v1"
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    project: Optional[str] = None
    monitor_system: bool = True
    monitor_interval: int = 30

    @classmethod
    def load(cls) -> "Config":
        """
        Load configuration from environment variables and config file.

        Priority (highest to lowest):
        1. Environment variables
        2. Config file (.wanllmdb/config.yaml)
        3. Default values
        """
        # Load .env file if it exists
        load_dotenv()

        # Try to load config file
        config_data = {}
        config_file = cls._find_config_file()
        if config_file and config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}

        # Merge with environment variables (env vars take precedence)
        return cls(
            api_url=os.environ.get("WANLLMDB_API_URL") or config_data.get("api_url", cls.api_url),
            metric_url=os.environ.get("WANLLMDB_METRIC_URL") or config_data.get("metric_url", cls.metric_url),
            username=os.environ.get("WANLLMDB_USERNAME") or config_data.get("username"),
            password=os.environ.get("WANLLMDB_PASSWORD") or config_data.get("password"),
            api_key=os.environ.get("WANLLMDB_API_KEY") or config_data.get("api_key"),
            project=os.environ.get("WANLLMDB_PROJECT") or config_data.get("project"),
            monitor_system=cls._parse_bool(
                os.environ.get("WANLLMDB_MONITOR_SYSTEM") or config_data.get("monitor_system", True)
            ),
            monitor_interval=int(
                os.environ.get("WANLLMDB_MONITOR_INTERVAL") or config_data.get("monitor_interval", 30)
            ),
        )

    @staticmethod
    def _find_config_file() -> Optional[Path]:
        """Find configuration file."""
        # Check current directory
        local_config = Path.cwd() / ".wanllmdb" / "config.yaml"
        if local_config.exists():
            return local_config

        # Check home directory
        home_config = Path.home() / ".wanllmdb" / "config.yaml"
        if home_config.exists():
            return home_config

        return None

    @staticmethod
    def _parse_bool(value: any) -> bool:
        """Parse boolean value from string."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            path: Path to save config file (default: ~/.wanllmdb/config.yaml)
        """
        if path is None:
            path = Path.home() / ".wanllmdb" / "config.yaml"

        path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            "api_url": self.api_url,
            "metric_url": self.metric_url,
            "username": self.username,
            "password": self.password,
            "api_key": self.api_key,
            "project": self.project,
            "monitor_system": self.monitor_system,
            "monitor_interval": self.monitor_interval,
        }

        # Remove None values
        config_data = {k: v for k, v in config_data.items() if v is not None}

        with open(path, "w") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False)

        print(f"Configuration saved to {path}")
