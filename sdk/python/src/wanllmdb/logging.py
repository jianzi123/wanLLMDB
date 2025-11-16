"""Log capture for stdout/stderr."""

import sys
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, TextIO, Optional
from threading import Thread, Event
import time


class StreamCapture:
    """Wrapper for stdout/stderr that captures output."""

    def __init__(self, stream: TextIO, source: str, capture: 'LogCapture'):
        """Initialize stream wrapper.

        Args:
            stream: Original stream to wrap
            source: Source identifier ('stdout' or 'stderr')
            capture: Parent LogCapture instance
        """
        self.stream = stream
        self.source = source
        self.capture = capture

    def write(self, text: str) -> int:
        """Write text to both original stream and capture buffer.

        Args:
            text: Text to write

        Returns:
            Number of characters written
        """
        # Write to original stream first
        result = self.stream.write(text)

        # Capture for logging (if enabled)
        if self.capture.enabled and text.strip():
            self.capture._add_log(text, self.source)

        return result

    def flush(self):
        """Flush the stream."""
        self.stream.flush()

    def __getattr__(self, name: str):
        """Delegate other attributes to original stream."""
        return getattr(self.stream, name)


class LogCapture:
    """Capture stdout/stderr and send to backend.

    This class intercepts stdout and stderr output and buffers it for
    batch upload to the backend logging API.
    """

    def __init__(self, run, buffer_size: int = 100, flush_interval: float = 5.0):
        """Initialize log capture.

        Args:
            run: Run instance
            buffer_size: Number of log lines to buffer before flushing
            flush_interval: Interval in seconds to flush logs
        """
        self.run = run
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self.buffer: List[Dict[str, Any]] = []
        self.enabled = True
        self.line_number = 0

        # Background flushing
        self._stop_event = Event()
        self._flush_thread: Optional[Thread] = None

    def start(self):
        """Start capturing logs."""
        # Wrap stdout and stderr
        sys.stdout = StreamCapture(self.original_stdout, 'stdout', self)
        sys.stderr = StreamCapture(self.original_stderr, 'stderr', self)

        # Start background flush thread
        self._stop_event.clear()
        self._flush_thread = Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def stop(self):
        """Stop capturing logs."""
        # Restore original streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        # Stop flush thread
        if self._flush_thread and self._flush_thread.is_alive():
            self._stop_event.set()
            self._flush_thread.join(timeout=2.0)

        # Final flush
        self._flush()

    def _add_log(self, text: str, source: str):
        """Add log entry to buffer.

        Args:
            text: Log message
            source: Source of log ('stdout' or 'stderr')
        """
        # Split multi-line messages
        lines = text.split('\n')

        for line in lines:
            if line.strip():
                self.line_number += 1
                self.buffer.append({
                    'level': 'ERROR' if source == 'stderr' else 'INFO',
                    'message': line.rstrip(),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': source,
                    'line_number': self.line_number,
                })

        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            self._flush()

    def _flush(self):
        """Flush logs to backend."""
        if not self.buffer:
            return

        try:
            # Copy buffer and clear it
            logs_to_send = self.buffer.copy()
            self.buffer.clear()

            # Send to backend
            self.run._upload_logs(logs_to_send)

        except Exception as e:
            # Restore buffer on error (but limit size to prevent memory issues)
            if len(self.buffer) < self.buffer_size * 2:
                self.buffer = logs_to_send + self.buffer
            print(f"Warning: Failed to upload logs: {e}")

    def _flush_loop(self):
        """Background thread to periodically flush logs."""
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            if self.buffer:
                self._flush()


class LogHandler(logging.Handler):
    """Logging handler that sends logs to run."""

    def __init__(self, run):
        """Initialize log handler.

        Args:
            run: Run instance
        """
        super().__init__()
        self.run = run
        self.line_number = 0

    def emit(self, record: logging.LogRecord):
        """Emit a log record.

        Args:
            record: Log record
        """
        try:
            self.line_number += 1
            log_entry = {
                'level': record.levelname,
                'message': self.format(record),
                'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                'source': 'sdk',
                'line_number': self.line_number,
            }

            # Add to run's log buffer
            if hasattr(self.run, '_log_capture') and self.run._log_capture:
                self.run._log_capture.buffer.append(log_entry)
            else:
                # Fallback: upload immediately
                self.run._upload_logs([log_entry])

        except Exception:
            self.handleError(record)
