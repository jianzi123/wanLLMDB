"""
Storage service for MinIO object storage.
"""

import os
from typing import Optional, BinaryIO
from datetime import timedelta
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    """Service for managing file storage in MinIO."""

    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket_name = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            print(f"Error ensuring bucket: {e}")

    def get_upload_url(
        self,
        object_key: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        Get a presigned URL for uploading a file.

        Args:
            object_key: Object key/path in storage
            expires: Expiration time for the URL

        Returns:
            Presigned upload URL
        """
        try:
            url = self.client.presigned_put_object(
                self.bucket_name,
                object_key,
                expires=expires,
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate upload URL: {e}")

    def get_download_url(
        self,
        object_key: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        Get a presigned URL for downloading a file.

        Args:
            object_key: Object key/path in storage
            expires: Expiration time for the URL

        Returns:
            Presigned download URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_key,
                expires=expires,
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate download URL: {e}")

    def upload_file(
        self,
        object_key: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: Optional[str] = None,
    ) -> None:
        """
        Upload a file directly to storage.

        Args:
            object_key: Object key/path in storage
            file_data: File data stream
            file_size: Size of the file in bytes
            content_type: MIME type of the file
        """
        try:
            self.client.put_object(
                self.bucket_name,
                object_key,
                file_data,
                file_size,
                content_type=content_type,
            )
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")

    def download_file(self, object_key: str) -> BinaryIO:
        """
        Download a file from storage.

        Args:
            object_key: Object key/path in storage

        Returns:
            File data stream
        """
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            return response
        except S3Error as e:
            raise Exception(f"Failed to download file: {e}")

    def delete_file(self, object_key: str) -> None:
        """
        Delete a file from storage.

        Args:
            object_key: Object key/path in storage
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
        except S3Error as e:
            raise Exception(f"Failed to delete file: {e}")

    def delete_files(self, object_keys: list[str]) -> None:
        """
        Delete multiple files from storage.

        Args:
            object_keys: List of object keys/paths in storage
        """
        try:
            errors = self.client.remove_objects(
                self.bucket_name,
                [{"Key": key} for key in object_keys],
            )
            for error in errors:
                print(f"Error deleting object {error.object_name}: {error}")
        except S3Error as e:
            raise Exception(f"Failed to delete files: {e}")

    def list_files(self, prefix: str) -> list[str]:
        """
        List files with a given prefix.

        Args:
            prefix: Prefix to filter files

        Returns:
            List of object keys
        """
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            raise Exception(f"Failed to list files: {e}")

    def get_file_info(self, object_key: str) -> dict:
        """
        Get information about a file.

        Args:
            object_key: Object key/path in storage

        Returns:
            File information dictionary
        """
        try:
            stat = self.client.stat_object(self.bucket_name, object_key)
            return {
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata,
            }
        except S3Error as e:
            raise Exception(f"Failed to get file info: {e}")

    @staticmethod
    def generate_storage_key(
        project_id: UUID,
        artifact_id: UUID,
        version_id: UUID,
        file_path: str,
    ) -> str:
        """
        Generate a storage key for a file.

        Args:
            project_id: Project ID
            artifact_id: Artifact ID
            version_id: Version ID
            file_path: File path within artifact

        Returns:
            Storage key
        """
        return f"projects/{project_id}/artifacts/{artifact_id}/versions/{version_id}/{file_path}"

    @staticmethod
    def generate_version_path(
        project_id: UUID,
        artifact_id: UUID,
        version_id: UUID,
    ) -> str:
        """
        Generate a storage path prefix for an artifact version.

        Args:
            project_id: Project ID
            artifact_id: Artifact ID
            version_id: Version ID

        Returns:
            Storage path prefix
        """
        return f"projects/{project_id}/artifacts/{artifact_id}/versions/{version_id}"


# Global storage service instance
storage_service = StorageService()
