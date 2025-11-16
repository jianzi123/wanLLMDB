"""
Metrics buffering and batching for efficient sending.
"""

import time
from datetime import datetime
from threading import Thread, Lock, Event
from typing import Any, Dict, List, Optional

from wanllmdb.api_client import APIClient


class MetricsBuffer:
    """
    Buffer metrics and send them in batches to the metric service.

    This improves performance by reducing the number of API calls.
    """

    def __init__(
        self,
        api_client: APIClient,
        flush_interval: float = 5.0,
        max_buffer_size: int = 1000,
    ):
        """
        Initialize metrics buffer.

        Args:
            api_client: API client instance
            flush_interval: Interval in seconds to flush buffer
            max_buffer_size: Maximum buffer size before auto-flush
        """
        self.api_client = api_client
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size

        self._buffer: List[Dict[str, Any]] = []
        self._lock = Lock()
        self._flush_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._run_id: Optional[str] = None

    def set_run_id(self, run_id: str) -> None:
        """Set the run ID for metrics."""
        self._run_id = run_id

    def start(self) -> None:
        """Start the auto-flush thread."""
        if self._flush_thread is not None:
            return

        self._stop_event.clear()
        self._flush_thread = Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def stop(self) -> None:
        """Stop the auto-flush thread."""
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=10)
            self._flush_thread = None

    def add_metric(
        self,
        metric_name: str,
        value: float,
        step: Optional[int] = None,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a metric to the buffer.

        Args:
            metric_name: Name of the metric
            value: Metric value
            step: Step number
            timestamp: Timestamp (ISO format)
            metadata: Additional metadata
        """
        if self._run_id is None:
            raise ValueError("Run ID not set")

        metric = {
            "run_id": self._run_id,
            "metric_name": metric_name,
            "value": value,
            "time": timestamp or datetime.now().isoformat(),
        }

        if step is not None:
            metric["step"] = step

        if metadata:
            metric["metadata"] = metadata

        with self._lock:
            self._buffer.append(metric)

            # Auto-flush if buffer is full
            if len(self._buffer) >= self.max_buffer_size:
                self._flush()

    def flush(self) -> None:
        """Flush all buffered metrics immediately."""
        with self._lock:
            self._flush()

    def _flush(self) -> None:
        """Internal flush implementation (assumes lock is held)."""
        if not self._buffer:
            return

        metrics_to_send = self._buffer[:]
        self._buffer.clear()

        # Send metrics (release lock while sending)
        try:
            self.api_client.batch_write_metrics(metrics_to_send)
        except Exception as e:
            print(f"Warning: Failed to send metrics: {e}")
            # Put metrics back in buffer on failure
            self._buffer.extend(metrics_to_send)

    def _flush_loop(self) -> None:
        """Background thread for periodic flushing."""
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            with self._lock:
                self._flush()
