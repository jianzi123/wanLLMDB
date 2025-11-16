"""Local cache management for downloaded artifacts."""

import os
import json
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime


class ArtifactCache:
    """Manages local cache of downloaded artifacts.

    The cache stores artifacts in a local directory to avoid re-downloading.
    It supports automatic cleanup based on size limits and age.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the artifact cache.

        Args:
            cache_dir: Directory to store cached artifacts.
                      If None, uses ~/.wanllmdb/artifacts
        """
        if cache_dir is None:
            cache_dir = os.path.expanduser('~/.wanllmdb/artifacts')

        self.cache_dir = cache_dir
        self.metadata_file = os.path.join(cache_dir, '.cache_metadata.json')

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Load metadata
        self.metadata = self._load_metadata()

    def get(self, artifact_id: str, version: str) -> Optional[str]:
        """Get the path to a cached artifact.

        Args:
            artifact_id: Artifact ID
            version: Artifact version

        Returns:
            Path to cached artifact directory, or None if not cached
        """
        cache_key = f"{artifact_id}:{version}"

        if cache_key in self.metadata:
            cache_path = self.metadata[cache_key]['path']

            # Verify the path still exists
            if os.path.exists(cache_path):
                # Update last access time
                self.metadata[cache_key]['last_accessed'] = time.time()
                self._save_metadata()
                return cache_path
            else:
                # Remove stale entry
                del self.metadata[cache_key]
                self._save_metadata()

        return None

    def put(self, artifact_id: str, version: str, path: str) -> None:
        """Add an artifact to the cache.

        Args:
            artifact_id: Artifact ID
            version: Artifact version
            path: Path to the artifact directory
        """
        cache_key = f"{artifact_id}:{version}"

        # Calculate size
        size = self._get_directory_size(path)

        self.metadata[cache_key] = {
            'path': path,
            'artifact_id': artifact_id,
            'version': version,
            'size': size,
            'cached_at': time.time(),
            'last_accessed': time.time()
        }

        self._save_metadata()

    def cleanup(self, max_size_gb: float = 10.0, max_age_days: int = 30) -> None:
        """Clean up old or large artifacts from the cache.

        Args:
            max_size_gb: Maximum total cache size in GB
            max_age_days: Maximum age of cached artifacts in days
        """
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        # Calculate total size and remove old artifacts
        total_size = 0
        to_remove = []

        for cache_key, entry in self.metadata.items():
            # Check age
            age = current_time - entry.get('cached_at', current_time)
            if age > max_age_seconds:
                to_remove.append(cache_key)
                continue

            total_size += entry.get('size', 0)

        # Remove old artifacts
        for cache_key in to_remove:
            self._remove_cache_entry(cache_key)

        # If still over size limit, remove least recently used
        max_size_bytes = max_size_gb * 1024 * 1024 * 1024

        if total_size > max_size_bytes:
            # Sort by last accessed time (oldest first)
            sorted_entries = sorted(
                self.metadata.items(),
                key=lambda x: x[1].get('last_accessed', 0)
            )

            for cache_key, entry in sorted_entries:
                if total_size <= max_size_bytes:
                    break

                self._remove_cache_entry(cache_key)
                total_size -= entry.get('size', 0)

        self._save_metadata()

    def clear(self) -> None:
        """Clear all cached artifacts."""
        for cache_key in list(self.metadata.keys()):
            self._remove_cache_entry(cache_key)

        self._save_metadata()

    def list(self) -> List[Dict[str, any]]:
        """List all cached artifacts.

        Returns:
            List of cache entries with metadata
        """
        result = []
        for cache_key, entry in self.metadata.items():
            result.append({
                'key': cache_key,
                'artifact_id': entry.get('artifact_id'),
                'version': entry.get('version'),
                'path': entry.get('path'),
                'size_mb': entry.get('size', 0) / (1024 * 1024),
                'cached_at': datetime.fromtimestamp(
                    entry.get('cached_at', 0)
                ).isoformat(),
                'last_accessed': datetime.fromtimestamp(
                    entry.get('last_accessed', 0)
                ).isoformat(),
            })
        return result

    def get_total_size(self) -> int:
        """Get total size of all cached artifacts in bytes.

        Returns:
            Total cache size in bytes
        """
        return sum(entry.get('size', 0) for entry in self.metadata.values())

    def _load_metadata(self) -> Dict:
        """Load cache metadata from disk."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to save cache metadata: {e}")

    def _remove_cache_entry(self, cache_key: str) -> None:
        """Remove a cache entry and its files.

        Args:
            cache_key: Cache key to remove
        """
        if cache_key not in self.metadata:
            return

        entry = self.metadata[cache_key]
        cache_path = entry.get('path')

        # Remove directory if it exists
        if cache_path and os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
            except OSError as e:
                print(f"Warning: Failed to remove cache directory {cache_path}: {e}")

        # Remove metadata entry
        del self.metadata[cache_key]

    @staticmethod
    def _get_directory_size(path: str) -> int:
        """Calculate total size of a directory.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
