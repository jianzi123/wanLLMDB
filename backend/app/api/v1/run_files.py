"""API endpoints for run file management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.repositories.run_file_repository import RunFileRepository
from app.schemas.run_file import (
    RunFile,
    RunFileCreate,
    RunFileUpdate,
    RunFileList,
    FileUploadUrlRequest,
    FileUploadUrlResponse,
    FileDownloadUrlResponse,
)
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("/{run_id}/files/upload-url", response_model=FileUploadUrlResponse)
def get_file_upload_url(
    run_id: UUID,
    request: FileUploadUrlRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    storage_service: StorageService = Depends(deps.get_storage_service),
):
    """Get presigned URL for file upload.

    Args:
        run_id: Run ID
        request: Upload request with file info
        db: Database session
        current_user: Current authenticated user

    Returns:
        Presigned upload URL and storage key
    """
    # TODO: Check if user has access to the run

    # Generate storage key
    storage_key = f"runs/{run_id}/files/{request.path}"

    # Get presigned upload URL (expires in 1 hour)
    upload_url = storage_service.get_upload_url(storage_key, expires_in=3600)

    return FileUploadUrlResponse(
        upload_url=upload_url,
        storage_key=storage_key,
        expires_in=3600
    )


@router.post("/{run_id}/files", response_model=RunFile, status_code=status.HTTP_201_CREATED)
def register_file(
    run_id: UUID,
    file_data: RunFileCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Register a file that was uploaded to storage.

    Args:
        run_id: Run ID
        file_data: File metadata
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created run file
    """
    # TODO: Check if user has access to the run

    repo = RunFileRepository(db)

    # Check if file already exists
    existing_file = repo.get_by_run_and_path(run_id, file_data.path)
    if existing_file:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File already exists at path: {file_data.path}"
        )

    # Create file record
    run_file = repo.create(run_id, file_data)
    return run_file


@router.get("/{run_id}/files", response_model=RunFileList)
def list_files(
    run_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """List all files for a run.

    Args:
        run_id: Run ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of files
    """
    # TODO: Check if user has access to the run

    repo = RunFileRepository(db)
    files, total = repo.list_by_run(run_id, skip=skip, limit=limit)

    return RunFileList(
        items=files,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/files/{file_id}", response_model=RunFile)
def get_file(
    file_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get a file by ID.

    Args:
        file_id: File ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        File metadata
    """
    repo = RunFileRepository(db)
    run_file = repo.get(file_id)

    if not run_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # TODO: Check if user has access to the run

    return run_file


@router.get("/files/{file_id}/download-url", response_model=FileDownloadUrlResponse)
def get_file_download_url(
    file_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    storage_service: StorageService = Depends(deps.get_storage_service),
):
    """Get presigned URL for file download.

    Args:
        file_id: File ID
        db: Database session
        current_user: Current authenticated user
        storage_service: Storage service

    Returns:
        Presigned download URL
    """
    repo = RunFileRepository(db)
    run_file = repo.get(file_id)

    if not run_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # TODO: Check if user has access to the run

    # Get presigned download URL (expires in 1 hour)
    download_url = storage_service.get_download_url(
        run_file.storage_key,
        expires_in=3600
    )

    return FileDownloadUrlResponse(
        download_url=download_url,
        filename=run_file.name,
        size=run_file.size,
        content_type=run_file.content_type,
        expires_in=3600
    )


@router.patch("/files/{file_id}", response_model=RunFile)
def update_file(
    file_id: UUID,
    file_data: RunFileUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Update file metadata.

    Args:
        file_id: File ID
        file_data: Updated file data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated file
    """
    repo = RunFileRepository(db)
    run_file = repo.update(file_id, file_data)

    if not run_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # TODO: Check if user has access to the run

    return run_file


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    storage_service: StorageService = Depends(deps.get_storage_service),
):
    """Delete a file.

    Args:
        file_id: File ID
        db: Database session
        current_user: Current authenticated user
        storage_service: Storage service
    """
    repo = RunFileRepository(db)
    run_file = repo.get(file_id)

    if not run_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # TODO: Check if user has access to the run

    # Delete from storage
    try:
        storage_service.delete_file(run_file.storage_key)
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Warning: Failed to delete file from storage: {e}")

    # Delete from database
    repo.delete(file_id)
