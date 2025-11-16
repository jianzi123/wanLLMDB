"""
System metrics monitoring (CPU, GPU, memory, disk, network).
"""

import platform
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

from wanllmdb.api_client import APIClient


class SystemMonitor:
    """Monitor system metrics and send to metric service."""

    def __init__(
        self,
        api_client: APIClient,
        run_id: str,
        interval: int = 30,
    ):
        """
        Initialize system monitor.

        Args:
            api_client: API client instance
            run_id: Run ID
            interval: Monitoring interval in seconds
        """
        self.api_client = api_client
        self.run_id = run_id
        self.interval = interval

        # Check GPU availability
        self._has_gpu = self._check_gpu()

    def _check_gpu(self) -> bool:
        """Check if GPU is available."""
        try:
            import GPUtil
            return len(GPUtil.getGPUs()) > 0
        except ImportError:
            return False

    def collect_metrics(self) -> List[Dict[str, Any]]:
        """
        Collect system metrics.

        Returns:
            List of metric dictionaries
        """
        metrics = []
        timestamp = datetime.now().isoformat()

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append({
            "run_id": self.run_id,
            "metric_type": "cpu",
            "value": cpu_percent,
            "time": timestamp,
            "metadata": {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
            },
        })

        # CPU per-core metrics
        cpu_percents = psutil.cpu_percent(interval=1, percpu=True)
        for i, percent in enumerate(cpu_percents):
            metrics.append({
                "run_id": self.run_id,
                "metric_type": "cpu_core",
                "value": percent,
                "time": timestamp,
                "metadata": {"core": i},
            })

        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.append({
            "run_id": self.run_id,
            "metric_type": "memory",
            "value": memory.percent,
            "time": timestamp,
            "metadata": {
                "total_mb": memory.total / (1024 * 1024),
                "used_mb": memory.used / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
            },
        })

        # Disk metrics
        disk = psutil.disk_usage("/")
        metrics.append({
            "run_id": self.run_id,
            "metric_type": "disk",
            "value": disk.percent,
            "time": timestamp,
            "metadata": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
            },
        })

        # Network metrics
        net_io = psutil.net_io_counters()
        metrics.append({
            "run_id": self.run_id,
            "metric_type": "network_sent",
            "value": net_io.bytes_sent / (1024**2),  # MB
            "time": timestamp,
        })
        metrics.append({
            "run_id": self.run_id,
            "metric_type": "network_recv",
            "value": net_io.bytes_recv / (1024**2),  # MB
            "time": timestamp,
        })

        # GPU metrics (if available)
        if self._has_gpu:
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                for i, gpu in enumerate(gpus):
                    metrics.append({
                        "run_id": self.run_id,
                        "metric_type": "gpu_util",
                        "value": gpu.load * 100,
                        "time": timestamp,
                        "metadata": {
                            "gpu_id": i,
                            "gpu_name": gpu.name,
                            "memory_used_mb": gpu.memoryUsed,
                            "memory_total_mb": gpu.memoryTotal,
                            "memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                            "temperature": gpu.temperature,
                        },
                    })
                    metrics.append({
                        "run_id": self.run_id,
                        "metric_type": "gpu_memory",
                        "value": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                        "time": timestamp,
                        "metadata": {
                            "gpu_id": i,
                            "gpu_name": gpu.name,
                        },
                    })
            except Exception as e:
                print(f"Warning: Failed to collect GPU metrics: {e}")

        return metrics

    def collect_and_send(self) -> None:
        """Collect metrics and send to server."""
        try:
            metrics = self.collect_metrics()
            self.api_client.batch_write_system_metrics(metrics)
        except Exception as e:
            print(f"Warning: Failed to send system metrics: {e}")
