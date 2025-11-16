"""
Run class for managing experiment runs.
"""

import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from threading import Thread, Event

from wanllmdb.api_client import APIClient
from wanllmdb.metrics_buffer import MetricsBuffer
from wanllmdb.system_monitor import SystemMonitor
from wanllmdb.git_info import GitInfo
from wanllmdb.errors import WanLLMDBError
from wanllmdb.artifact import Artifact


class ConfigDict(dict):
    """Configuration dictionary with attribute access."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"Config has no attribute '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Update configuration."""
        super().update(*args, **kwargs)
        # TODO: Send config update to server


class SummaryDict(dict):
    """Summary dictionary for best/final metrics."""

    def __setitem__(self, key: str, value: Any) -> None:
        """Set summary value."""
        super().__setitem__(key, value)
        # TODO: Send summary update to server


class Run:
    """
    Represents a single experiment run.

    Attributes:
        id: Run ID
        name: Run name
        project_id: Project ID
        state: Run state (running, finished, crashed, killed)
        config: Configuration dictionary
        summary: Summary metrics dictionary
        tags: List of tags
    """

    def __init__(
        self,
        api_client: APIClient,
        project_id: str,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        monitor_system: bool = True,
        monitor_interval: int = 30,
        git_tracking: bool = True,
    ):
        """
        Initialize a Run.

        Args:
            api_client: API client instance
            project_id: Project ID
            name: Run name (auto-generated if not provided)
            config: Configuration dictionary
            tags: List of tags
            notes: Run description
            monitor_system: Enable system metrics collection
            monitor_interval: System metrics interval in seconds
            git_tracking: Enable git tracking
        """
        self.api_client = api_client
        self.project_id = project_id
        self.name = name or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self._config = ConfigDict(config or {})
        self._summary = SummaryDict()
        self.tags = list(tags or [])
        self.notes = notes

        # Run state
        self.id: Optional[str] = None
        self.state = "running"
        self._step = 0
        self._started_at: Optional[datetime] = None

        # Metrics buffer
        self._metrics_buffer = MetricsBuffer(
            api_client=api_client,
            flush_interval=5.0,
            max_buffer_size=1000,
        )

        # System monitoring
        self._monitor_system = monitor_system
        self._monitor_interval = monitor_interval
        self._system_monitor: Optional[SystemMonitor] = None
        self._monitor_thread: Optional[Thread] = None
        self._stop_monitor = Event()

        # Git tracking
        self._git_tracking = git_tracking
        self._git_info: Optional[Dict[str, str]] = None

        # Heartbeat
        self._heartbeat_thread: Optional[Thread] = None
        self._stop_heartbeat = Event()

    @property
    def config(self) -> ConfigDict:
        """Get configuration dictionary."""
        return self._config

    @property
    def summary(self) -> SummaryDict:
        """Get summary dictionary."""
        return self._summary

    def start(self) -> None:
        """Start the run."""
        # Capture git information
        if self._git_tracking:
            try:
                git_info = GitInfo.get_info()
                self._git_info = git_info
            except Exception as e:
                print(f"Warning: Failed to capture git info: {e}")

        # Create run on server
        run_data = {
            "name": self.name,
            "project_id": self.project_id,
            "config": dict(self._config),
            "tags": self.tags,
            "notes": self.notes,
        }

        # Add git info if available
        if self._git_info:
            run_data.update({
                "git_commit": self._git_info.get("commit"),
                "git_branch": self._git_info.get("branch"),
                "git_remote": self._git_info.get("remote"),
            })

        try:
            response = self.api_client.create_run(run_data)
            self.id = response["id"]
            self._started_at = datetime.now()
            print(f"Run started: {self.name} (ID: {self.id})")
        except Exception as e:
            raise WanLLMDBError(f"Failed to start run: {e}")

        # Start metrics buffer
        self._metrics_buffer.set_run_id(self.id)
        self._metrics_buffer.start()

        # Start system monitoring
        if self._monitor_system:
            self._start_system_monitor()

        # Start heartbeat
        self._start_heartbeat()

    def log(
        self,
        metrics: Dict[str, Any],
        step: Optional[int] = None,
        commit: bool = True,
    ) -> None:
        """
        Log metrics.

        Args:
            metrics: Dictionary of metric name-value pairs
            step: Step number (auto-increments if not provided)
            commit: Immediately flush metrics to server
        """
        if self.id is None:
            raise WanLLMDBError("Run not started")

        # Use provided step or auto-increment
        if step is None:
            step = self._step
            self._step += 1
        else:
            self._step = max(self._step, step + 1)

        # Add metrics to buffer
        timestamp = datetime.now().isoformat()
        for name, value in metrics.items():
            if not isinstance(value, (int, float)):
                print(f"Warning: Skipping non-numeric metric '{name}': {value}")
                continue

            self._metrics_buffer.add_metric(
                metric_name=name,
                value=float(value),
                step=step,
                timestamp=timestamp,
            )

        # Flush if requested
        if commit:
            self._metrics_buffer.flush()

    def finish(self, exit_code: int = 0) -> None:
        """
        Finish the run.

        Args:
            exit_code: Exit code (0=success, non-zero=failure)
        """
        if self.id is None:
            return

        print(f"Finishing run: {self.name}")

        # Stop system monitoring
        if self._system_monitor:
            self._stop_monitor.set()
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)

        # Stop heartbeat
        self._stop_heartbeat.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)

        # Flush remaining metrics
        self._metrics_buffer.flush()
        self._metrics_buffer.stop()

        # Update run state on server
        try:
            self.api_client.finish_run(
                run_id=self.id,
                exit_code=exit_code,
                summary=dict(self._summary),
            )
            self.state = "finished" if exit_code == 0 else "crashed"
            print(f"Run finished: {self.state}")
        except Exception as e:
            print(f"Warning: Failed to finish run: {e}")

    def log_artifact(
        self,
        artifact: Artifact,
        aliases: Optional[List[str]] = None
    ) -> Artifact:
        """Log an artifact.

        Args:
            artifact: Artifact object to log
            aliases: List of aliases for this artifact version (e.g., ['latest', 'best'])

        Returns:
            The logged artifact with version information

        Raises:
            RuntimeError: If run hasn't been started
            WanLLMDBError: If artifact logging fails
        """
        if self.id is None:
            raise RuntimeError("Run not started. Call start() first.")

        print(f"Logging artifact '{artifact.name}' ({artifact.type})...")

        try:
            # 1. Create or get artifact
            artifact_data = {
                'name': artifact.name,
                'type': artifact.type,
                'project_id': self.project_id,
                'description': artifact.description,
                'metadata': artifact.metadata,
            }

            # Try to get existing artifact
            try:
                artifact_response = self.api_client.get(
                    f'/artifacts?project_id={self.project_id}&name={artifact.name}'
                )
                if artifact_response['items']:
                    artifact_obj = artifact_response['items'][0]
                    artifact._artifact_id = artifact_obj['id']
                    print(f"  Using existing artifact: {artifact_obj['id']}")
                else:
                    raise Exception("Not found")
            except:
                # Create new artifact
                artifact_response = self.api_client.post('/artifacts', data=artifact_data)
                artifact._artifact_id = artifact_response['id']
                print(f"  Created new artifact: {artifact._artifact_id}")

            # 2. Create new version
            version_data = {
                'artifact_id': artifact._artifact_id,
                'description': f"Logged from run {self.name}",
                'metadata': {},
                'run_id': self.id,
            }

            version_response = self.api_client.post(
                f'/artifacts/{artifact._artifact_id}/versions',
                data=version_data
            )
            version_id = version_response['id']
            artifact._version = version_response['version']
            artifact._version_id = version_id
            artifact._project_id = self.project_id

            print(f"  Created version: {artifact._version}")

            # 3. Upload files
            if artifact._files:
                print(f"  Uploading {len(artifact._files)} file(s)...")
                for artifact_file in artifact._files:
                    # Compute hashes
                    artifact_file.compute_hashes()

                    # Get upload URL
                    upload_request = {
                        'path': artifact_file.artifact_path,
                        'name': os.path.basename(artifact_file.artifact_path),
                        'size': artifact_file.size,
                        'md5_hash': artifact_file.md5_hash,
                        'sha256_hash': artifact_file.sha256_hash,
                    }

                    upload_response = self.api_client.post(
                        f'/artifacts/versions/{version_id}/files/upload-url',
                        data=upload_request
                    )

                    # Upload to MinIO
                    upload_url = upload_response['upload_url']
                    self.api_client.upload_file(artifact_file.local_path, upload_url)

                    # Register file
                    file_data = {
                        'path': artifact_file.artifact_path,
                        'name': os.path.basename(artifact_file.artifact_path),
                        'size': artifact_file.size,
                        'storage_key': upload_response['storage_key'],
                        'md5_hash': artifact_file.md5_hash,
                        'sha256_hash': artifact_file.sha256_hash,
                    }

                    self.api_client.post(
                        f'/artifacts/versions/{version_id}/files',
                        data=file_data
                    )

                    print(f"    ✓ {artifact_file.artifact_path}")

            # 4. Finalize version
            self.api_client.post(f'/artifacts/versions/{version_id}/finalize')
            print(f"  ✓ Artifact logged successfully")

            # 5. Add aliases (if backend supports it)
            # TODO: Implement alias support in backend

            return artifact

        except Exception as e:
            raise WanLLMDBError(f"Failed to log artifact: {e}")

    def use_artifact(
        self,
        artifact_or_name: str,
        type: Optional[str] = None,
        version: Optional[str] = None,
        alias: Optional[str] = None
    ) -> Artifact:
        """Use an artifact.

        Args:
            artifact_or_name: Artifact name or "name:version" or "name:alias"
            type: Artifact type filter
            version: Specific version to use (optional if using alias)
            alias: Alias to use (e.g., 'latest', 'best')

        Returns:
            Artifact object ready for download

        Raises:
            WanLLMDBError: If artifact not found or access fails
        """
        # Parse artifact name and version
        if ':' in artifact_or_name:
            name, version_or_alias = artifact_or_name.split(':', 1)
            if version is None and alias is None:
                # Try to determine if it's a version or alias
                # For now, assume it's a version
                version = version_or_alias
        else:
            name = artifact_or_name

        print(f"Using artifact '{name}'...")

        try:
            # Get artifact
            artifact_response = self.api_client.get(
                f'/artifacts?project_id={self.project_id}&name={name}'
            )

            if not artifact_response['items']:
                raise WanLLMDBError(f"Artifact '{name}' not found")

            artifact_data = artifact_response['items'][0]
            artifact_id = artifact_data['id']

            # Get version
            if version:
                # Get specific version
                versions_response = self.api_client.get(
                    f'/artifacts/{artifact_id}/versions'
                )
                version_data = None
                for v in versions_response['items']:
                    if v['version'] == version:
                        version_data = v
                        break

                if not version_data:
                    raise WanLLMDBError(f"Version '{version}' not found")
            else:
                # Get latest version
                versions_response = self.api_client.get(
                    f'/artifacts/{artifact_id}/versions?limit=1'
                )
                if not versions_response['items']:
                    raise WanLLMDBError(f"No versions found for artifact '{name}'")
                version_data = versions_response['items'][0]

            # Create Artifact object
            artifact = Artifact(
                name=artifact_data['name'],
                type=artifact_data['type'],
                description=artifact_data.get('description'),
                metadata=artifact_data.get('metadata', {})
            )

            artifact._artifact_id = artifact_id
            artifact._version = version_data['version']
            artifact._version_id = version_data['id']
            artifact._project_id = self.project_id

            print(f"  ✓ Artifact '{name}:{artifact._version}' ready")

            return artifact

        except Exception as e:
            if isinstance(e, WanLLMDBError):
                raise
            raise WanLLMDBError(f"Failed to use artifact: {e}")

    def save(
        self,
        glob_str: str,
        base_path: Optional[str] = None,
        policy: str = "live"
    ) -> None:
        """Save files to the run.

        This method uploads files to be associated with the run. Unlike artifacts,
        these files are directly tied to a specific run and are not versioned.

        Args:
            glob_str: File path or glob pattern (e.g., "*.txt", "data/**/*.csv")
            base_path: Base path for computing relative paths. If None, uses cwd
            policy: Upload policy - "live" (immediate), "end" (at run end), "now" (same as live)

        Example:
            >>> run.save("model.pkl")  # Save single file
            >>> run.save("logs/*.txt")  # Save all txt files in logs/
            >>> run.save("data/**/*.csv")  # Save all csv files recursively
        """
        import glob as glob_module
        import hashlib

        if self.id is None:
            raise WanLLMDBError("Cannot save files to a run that hasn't been created")

        # TODO: Implement policy="end" to defer upload until run.finish()
        if policy not in ["live", "now"]:
            print(f"Warning: Policy '{policy}' not yet implemented, using 'live'")

        # Resolve base path
        if base_path is None:
            base_path = os.getcwd()
        base_path = os.path.abspath(base_path)

        # Find files matching glob pattern
        glob_path = os.path.join(base_path, glob_str)
        files = glob_module.glob(glob_path, recursive=True)

        # Filter out directories
        files = [f for f in files if os.path.isfile(f)]

        if not files:
            print(f"Warning: No files found matching pattern: {glob_str}")
            return

        print(f"Saving {len(files)} file(s)...")

        for file_path in files:
            try:
                # Get file info
                file_path = os.path.abspath(file_path)
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # Compute relative path
                try:
                    rel_path = os.path.relpath(file_path, base_path)
                except ValueError:
                    # Different drives on Windows
                    rel_path = file_name

                # Normalize path separators
                rel_path = rel_path.replace(os.sep, '/')

                # Compute hashes
                md5_hash = hashlib.md5()
                sha256_hash = hashlib.sha256()

                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        md5_hash.update(chunk)
                        sha256_hash.update(chunk)

                md5 = md5_hash.hexdigest()
                sha256 = sha256_hash.hexdigest()

                # Detect content type
                content_type = None
                ext = os.path.splitext(file_name)[1].lower()
                content_type_map = {
                    '.txt': 'text/plain',
                    '.json': 'application/json',
                    '.csv': 'text/csv',
                    '.pkl': 'application/octet-stream',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.pdf': 'application/pdf',
                }
                content_type = content_type_map.get(ext)

                # Get upload URL
                upload_request = {
                    'name': file_name,
                    'path': rel_path,
                    'size': file_size,
                    'content_type': content_type,
                }

                upload_response = self.api_client.post(
                    f'/runs/{self.id}/files/upload-url',
                    data=upload_request
                )

                # Upload file to storage
                upload_url = upload_response['upload_url']
                self.api_client.upload_file(file_path, upload_url)

                # Register file in database
                file_data = {
                    'name': file_name,
                    'path': rel_path,
                    'size': file_size,
                    'content_type': content_type,
                    'storage_key': upload_response['storage_key'],
                    'md5_hash': md5,
                    'sha256_hash': sha256,
                }

                self.api_client.post(f'/runs/{self.id}/files', data=file_data)

                print(f"  ✓ {rel_path} ({file_size / 1024:.1f} KB)")

            except Exception as e:
                print(f"  ✗ Failed to save {file_path}: {e}")

    def _start_system_monitor(self) -> None:
        """Start system metrics monitoring."""
        self._system_monitor = SystemMonitor(
            api_client=self.api_client,
            run_id=self.id,
            interval=self._monitor_interval,
        )

        def monitor_loop():
            while not self._stop_monitor.is_set():
                try:
                    self._system_monitor.collect_and_send()
                except Exception as e:
                    print(f"Warning: System monitor error: {e}")
                self._stop_monitor.wait(self._monitor_interval)

        self._monitor_thread = Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _start_heartbeat(self) -> None:
        """Start heartbeat thread."""
        def heartbeat_loop():
            while not self._stop_heartbeat.is_set():
                try:
                    self.api_client.heartbeat_run(self.id)
                except Exception as e:
                    print(f"Warning: Heartbeat failed: {e}")
                self._stop_heartbeat.wait(30)  # Heartbeat every 30 seconds

        self._heartbeat_thread = Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        exit_code = 0 if exc_type is None else 1
        self.finish(exit_code=exit_code)
        return False

    def __repr__(self) -> str:
        return f"Run(id={self.id}, name={self.name}, state={self.state})"
