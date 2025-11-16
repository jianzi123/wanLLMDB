"""Artifact management for versioning datasets, models, and files."""

import os
import hashlib
import glob as glob_module
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import time


class ArtifactFile:
    """Represents a file in an artifact."""

    def __init__(
        self,
        local_path: str,
        artifact_path: str,
        size: int,
        is_reference: bool = False,
        reference_uri: Optional[str] = None
    ):
        """Initialize artifact file.

        Args:
            local_path: Local file system path (or URI for references)
            artifact_path: Path within the artifact
            size: File size in bytes
            is_reference: True if this is an external reference
            reference_uri: External URI (s3://, gs://, etc.) for references
        """
        self.local_path = local_path
        self.artifact_path = artifact_path
        self.size = size
        self.is_reference = is_reference
        self.reference_uri = reference_uri
        self.md5_hash: Optional[str] = None
        self.sha256_hash: Optional[str] = None

    def compute_hashes(self) -> None:
        """Compute MD5 and SHA256 hashes of the file.

        Only works for local files, not external references.
        """
        if self.is_reference:
            # Cannot compute hashes for external references
            return

        md5 = hashlib.md5()
        sha256 = hashlib.sha256()

        with open(self.local_path, 'rb') as f:
            while chunk := f.read(8192):
                md5.update(chunk)
                sha256.update(chunk)

        self.md5_hash = md5.hexdigest()
        self.sha256_hash = sha256.hexdigest()


class Artifact:
    """Artifact for versioning datasets, models, and files.

    An artifact is a versioned collection of files. Artifacts can be logged
    to track datasets, models, or any other files produced or consumed by runs.

    Example:
        >>> artifact = wandb.Artifact('my-dataset', type='dataset')
        >>> artifact.add_file('data.csv')
        >>> artifact.add_dir('images/')
        >>> run.log_artifact(artifact)
    """

    def __init__(
        self,
        name: str,
        type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize an artifact.

        Args:
            name: A human-readable name for this artifact
            type: The type of artifact (e.g., 'dataset', 'model', 'file', 'code')
            description: A description of the artifact
            metadata: Additional metadata to store with the artifact
        """
        self.name = name
        self.type = type
        self.description = description or ""
        self.metadata = metadata or {}

        # Internal state
        self._files: List[ArtifactFile] = []
        self._manifest: Dict[str, Any] = {}
        self._artifact_id: Optional[str] = None
        self._version: Optional[str] = None
        self._version_id: Optional[str] = None
        self._project_id: Optional[str] = None

    def add_file(
        self,
        local_path: str,
        name: Optional[str] = None,
        is_tmp: bool = False
    ) -> ArtifactFile:
        """Add a file to the artifact.

        Args:
            local_path: Path to the file on the local filesystem
            name: Name for the file within the artifact. If None, uses basename
            is_tmp: If True, the file will be copied (useful for temp files)

        Returns:
            ArtifactFile object

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        local_path = os.path.abspath(local_path)

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")

        if not os.path.isfile(local_path):
            raise ValueError(f"Path is not a file: {local_path}")

        # Determine artifact path
        if name is None:
            name = os.path.basename(local_path)

        # Get file size
        size = os.path.getsize(local_path)

        # Create artifact file
        artifact_file = ArtifactFile(local_path, name, size)
        self._files.append(artifact_file)

        return artifact_file

    def add_dir(
        self,
        local_path: str,
        name: Optional[str] = None,
        skip_empty_dirs: bool = True
    ) -> None:
        """Add a directory recursively to the artifact.

        Args:
            local_path: Path to the directory
            name: Prefix name for files in the artifact. If None, uses directory name
            skip_empty_dirs: If True, skip empty directories

        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        local_path = os.path.abspath(local_path)

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Directory not found: {local_path}")

        if not os.path.isdir(local_path):
            raise ValueError(f"Path is not a directory: {local_path}")

        # Determine prefix
        if name is None:
            name = os.path.basename(local_path.rstrip(os.sep))

        # Walk directory
        for root, dirs, files in os.walk(local_path):
            # Calculate relative path
            rel_root = os.path.relpath(root, local_path)

            for file in files:
                file_local_path = os.path.join(root, file)

                # Build artifact path
                if rel_root == '.':
                    artifact_path = os.path.join(name, file)
                else:
                    artifact_path = os.path.join(name, rel_root, file)

                # Normalize path separators
                artifact_path = artifact_path.replace(os.sep, '/')

                self.add_file(file_local_path, artifact_path)

    def add_reference(
        self,
        uri: str,
        name: Optional[str] = None,
        checksum: bool = True,
        max_objects: Optional[int] = None,
        size: Optional[int] = None,
        md5_hash: Optional[str] = None,
        sha256_hash: Optional[str] = None
    ) -> ArtifactFile:
        """Add a reference to an external file or directory.

        References allow you to track files without copying them into the artifact.
        Useful for large datasets stored in S3, GCS, or other cloud storage.

        Args:
            uri: URI to reference (e.g., 's3://bucket/path', 'gs://bucket/path', 'https://...')
            name: Name for the reference within the artifact. If None, uses basename from URI
            checksum: If True, compute checksums for validation (not yet supported)
            max_objects: Maximum number of objects to reference (for directories, not yet supported)
            size: File size in bytes (optional, but recommended)
            md5_hash: MD5 hash of the file (optional)
            sha256_hash: SHA256 hash of the file (optional)

        Returns:
            ArtifactFile object representing the reference

        Example:
            >>> artifact = wandb.Artifact('my-dataset', type='dataset')
            >>> artifact.add_reference(
            ...     's3://my-bucket/data/train.csv',
            ...     name='train.csv',
            ...     size=1024000
            ... )
            >>> run.log_artifact(artifact)
        """
        # Validate URI format
        valid_schemes = ['s3://', 'gs://', 'http://', 'https://', 'file://']
        if not any(uri.startswith(scheme) for scheme in valid_schemes):
            raise ValueError(
                f"Invalid URI scheme. Must start with one of: {', '.join(valid_schemes)}"
            )

        # Determine artifact path
        if name is None:
            # Extract basename from URI
            name = uri.split('/')[-1]
            if not name:
                raise ValueError("Cannot infer name from URI. Please provide 'name' parameter.")

        # Create artifact file with reference
        artifact_file = ArtifactFile(
            local_path=uri,  # Store URI in local_path for references
            artifact_path=name,
            size=size or 0,  # Size is optional but recommended
            is_reference=True,
            reference_uri=uri
        )

        # Set hashes if provided
        if md5_hash:
            artifact_file.md5_hash = md5_hash
        if sha256_hash:
            artifact_file.sha256_hash = sha256_hash

        self._files.append(artifact_file)
        return artifact_file

    def download(self, root: Optional[str] = None) -> str:
        """Download the artifact to local storage.

        Args:
            root: Root directory to download to. If None, uses cache directory.

        Returns:
            Path to the downloaded artifact directory

        Raises:
            RuntimeError: If artifact hasn't been logged yet
        """
        if self._version_id is None:
            raise RuntimeError(
                "Cannot download artifact that hasn't been logged. "
                "Use run.log_artifact() first."
            )

        # Import here to avoid circular dependency
        from wanllmdb.artifact_cache import ArtifactCache
        from wanllmdb.config import Config
        from wanllmdb.api_client import APIClient

        # Get cache or custom root
        if root is None:
            cache = ArtifactCache()
            cache_path = cache.get(self._artifact_id, self._version)
            if cache_path:
                print(f"Using cached artifact: {cache_path}")
                return cache_path
        else:
            cache_path = os.path.join(root, self.name, self._version)
            os.makedirs(cache_path, exist_ok=True)

        # Download files
        cfg = Config.load()
        client = APIClient(base_url=cfg.api_url, api_key=cfg.api_key)

        # Get artifact version details
        version_data = client.get(f'/artifacts/versions/{self._version_id}')

        print(f"Downloading artifact {self.name}:{self._version}...")
        print(f"  Files: {len(version_data['files'])}")

        # Download each file
        for file_info in version_data['files']:
            # Get download URL
            download_response = client.get(
                f'/artifacts/files/{file_info["id"]}/download-url'
            )
            download_url = download_response['download_url']

            # Build local path
            local_path = os.path.join(cache_path, file_info['path'])
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            print(f"  Downloading {file_info['name']}...")
            client.download_file(download_url, local_path)

        print(f"Artifact downloaded to: {cache_path}")

        # Update cache
        if root is None:
            cache.put(self._artifact_id, self._version, cache_path)

        return cache_path

    def get_path(self, name: str) -> Path:
        """Get the path to a file in the artifact.

        Args:
            name: Name of the file within the artifact

        Returns:
            Path object

        Raises:
            ValueError: If the artifact hasn't been downloaded
        """
        # Check if artifact is downloaded
        from wanllmdb.artifact_cache import ArtifactCache

        cache = ArtifactCache()
        cache_path = cache.get(self._artifact_id, self._version)

        if cache_path is None:
            raise ValueError(
                f"Artifact {self.name}:{self._version} not downloaded. "
                "Call artifact.download() first."
            )

        file_path = Path(cache_path) / name

        if not file_path.exists():
            raise FileNotFoundError(f"File not found in artifact: {name}")

        return file_path

    def verify(self) -> bool:
        """Verify the integrity of the artifact.

        Returns:
            True if all files are valid, False otherwise
        """
        # TODO: Implement verification by checking hashes
        return True

    def __repr__(self) -> str:
        """String representation of the artifact."""
        version_str = f":{self._version}" if self._version else ""
        return f"<Artifact {self.name}{version_str} ({self.type})>"

    def __str__(self) -> str:
        """Human-readable string of the artifact."""
        return self.__repr__()

    @property
    def file_count(self) -> int:
        """Number of files in the artifact."""
        return len(self._files)

    @property
    def size(self) -> int:
        """Total size of all files in bytes."""
        return sum(f.size for f in self._files)
