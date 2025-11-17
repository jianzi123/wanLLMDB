"""
Common types for scheduling module.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Resources:
    """Resource requirements/allocation."""
    cpu: float = 0.0  # CPU cores
    memory: float = 0.0  # Memory in GB
    gpu: int = 0  # GPU cards

    def __add__(self, other: 'Resources') -> 'Resources':
        """Add two resource sets."""
        return Resources(
            cpu=self.cpu + other.cpu,
            memory=self.memory + other.memory,
            gpu=self.gpu + other.gpu
        )

    def __sub__(self, other: 'Resources') -> 'Resources':
        """Subtract resources."""
        return Resources(
            cpu=max(0, self.cpu - other.cpu),
            memory=max(0, self.memory - other.memory),
            gpu=max(0, self.gpu - other.gpu)
        )

    def __le__(self, other: 'Resources') -> bool:
        """Check if resources are less than or equal to other."""
        return (
            self.cpu <= other.cpu and
            self.memory <= other.memory and
            self.gpu <= other.gpu
        )

    def is_zero(self) -> bool:
        """Check if all resources are zero."""
        return self.cpu == 0 and self.memory == 0 and self.gpu == 0


@dataclass
class QuotaInfo:
    """Quota information."""
    limits: Resources
    used: Resources

    @property
    def available(self) -> Resources:
        """Get available resources."""
        return self.limits - self.used

    def has_capacity(self, requested: Resources) -> bool:
        """Check if quota has capacity for requested resources."""
        return requested <= self.available

    def usage_percentage(self) -> dict:
        """Get usage percentage for each resource."""
        return {
            "cpu": (self.used.cpu / self.limits.cpu * 100) if self.limits.cpu > 0 else 0,
            "memory": (self.used.memory / self.limits.memory * 100) if self.limits.memory > 0 else 0,
            "gpu": (self.used.gpu / self.limits.gpu * 100) if self.limits.gpu > 0 else 0,
        }
