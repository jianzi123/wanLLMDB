"""
Artifact API endpoints.
"""

from typing import Optional
from uuid import UUID
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.artifact_repository import ArtifactRepository
from app.services.storage_service import storage_service
from app.schemas.artifact import (
    Artifact,
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactList,
    ArtifactVersion,
    ArtifactVersionCreate,
    ArtifactVersionUpdate,
    ArtifactVersionFinalize,
    ArtifactVersionList,
    ArtifactVersionWithFiles,
    ArtifactFile,
    FileUploadRequest,
    FileUploadResponse,
    FileDownloadResponse,
    ArtifactFileCreate,
)

router = APIRouter()


@router.post("", response_model=Artifact, status_code=status.HTTP_201_CREATED)
def create_artifact(
    artifact_in: ArtifactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new artifact."""
    repo = ArtifactRepository(db)
    artifact = repo.create(artifact_in, current_user.id)
    return artifact


@router.get("", response_model=ArtifactList)
def list_artifacts(
    project_id: Optional[UUID] = None,
    artifact_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List artifacts with filters and pagination."""
    repo = ArtifactRepository(db)

    skip = (page - 1) * page_size
    artifacts, total = repo.list(
        project_id=project_id,
        artifact_type=artifact_type,
        search=search,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": artifacts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{artifact_id}", response_model=Artifact)
def get_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an artifact by ID."""
    repo = ArtifactRepository(db)
    artifact = repo.get(artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    return artifact


@router.put("/{artifact_id}", response_model=Artifact)
def update_artifact(
    artifact_id: UUID,
    artifact_in: ArtifactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an artifact."""
    repo = ArtifactRepository(db)
    artifact = repo.update(artifact_id, artifact_in)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    return artifact


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an artifact."""
    repo = ArtifactRepository(db)
    success = repo.delete(artifact_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )


# Artifact Version endpoints
@router.post("/{artifact_id}/versions", response_model=ArtifactVersion, status_code=status.HTTP_201_CREATED)
def create_artifact_version(
    artifact_id: UUID,
    version_in: ArtifactVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new artifact version."""
    repo = ArtifactRepository(db)

    # Ensure artifact_id matches
    if version_in.artifact_id != artifact_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artifact ID mismatch",
        )

    # Get artifact to determine storage path
    artifact = repo.get(artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Generate storage path
    version_id = UUID(int=0)  # Temporary, will be replaced
    storage_path = storage_service.generate_version_path(
        artifact.project_id,
        artifact_id,
        version_id,
    )

    # Create version
    version = repo.create_version(version_in, current_user.id, storage_path)

    # Update storage path with actual version ID
    version.storage_path = storage_service.generate_version_path(
        artifact.project_id,
        artifact_id,
        version.id,
    )
    db.commit()
    db.refresh(version)

    return version


@router.get("/{artifact_id}/versions", response_model=ArtifactVersionList)
def list_artifact_versions(
    artifact_id: UUID,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List versions of an artifact."""
    repo = ArtifactRepository(db)

    skip = (page - 1) * page_size
    versions, total = repo.list_versions(artifact_id, skip, page_size)

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": versions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/versions/{version_id}", response_model=ArtifactVersionWithFiles)
def get_artifact_version(
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an artifact version with files."""
    repo = ArtifactRepository(db)
    version = repo.get_version_with_files(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact version not found",
        )
    return version


@router.post("/versions/{version_id}/finalize", response_model=ArtifactVersion)
def finalize_artifact_version(
    version_id: UUID,
    finalize_in: ArtifactVersionFinalize,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize an artifact version (make it immutable)."""
    repo = ArtifactRepository(db)
    version = repo.finalize_version(version_id, finalize_in.digest)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact version not found",
        )
    return version


# File upload/download endpoints
@router.post("/versions/{version_id}/files/upload-url", response_model=FileUploadResponse)
def get_file_upload_url(
    version_id: UUID,
    request: FileUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a presigned URL for uploading a file."""
    repo = ArtifactRepository(db)

    # Verify version exists and is not finalized
    version = repo.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact version not found",
        )

    if version.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add files to finalized version",
        )

    # Get artifact for storage path
    artifact = repo.get(version.artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Generate storage key
    storage_key = storage_service.generate_storage_key(
        artifact.project_id,
        artifact.id,
        version.id,
        request.path,
    )

    # Generate presigned upload URL
    upload_url = storage_service.get_upload_url(storage_key)

    return {
        "upload_url": upload_url,
        "storage_key": storage_key,
        "expires_in": 3600,  # 1 hour
    }


@router.post("/versions/{version_id}/files", response_model=ArtifactFile)
def add_file_to_version(
    version_id: UUID,
    file_in: ArtifactFileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a file record to an artifact version after upload."""
    repo = ArtifactRepository(db)

    # Verify version
    version = repo.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact version not found",
        )

    if version.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add files to finalized version",
        )

    # Ensure version_id matches
    if file_in.version_id != version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version ID mismatch",
        )

    # Add file
    file = repo.add_file(file_in)
    return file


@router.get("/files/{file_id}/download-url", response_model=FileDownloadResponse)
def get_file_download_url(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a presigned URL for downloading a file."""
    repo = ArtifactRepository(db)

    file = repo.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Generate presigned download URL
    download_url = storage_service.get_download_url(file.storage_key)

    return {
        "download_url": download_url,
        "file_name": file.name,
        "size": file.size,
        "mime_type": file.mime_type,
        "expires_in": 3600,  # 1 hour
    }


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a file from an artifact version."""
    repo = ArtifactRepository(db)

    file = repo.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Check if version is finalized
    version = repo.get_version(file.version_id)
    if version and version.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete files from finalized version",
        )

    # Delete from storage
    try:
        storage_service.delete_file(file.storage_key)
    except Exception as e:
        print(f"Warning: Failed to delete file from storage: {e}")

    # Delete from database
    repo.delete_file(file_id)
