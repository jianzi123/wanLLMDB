"""API endpoints for model registry."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.model_registry import ModelStage
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.model_registry import (
    RegisteredModel,
    RegisteredModelCreate,
    RegisteredModelUpdate,
    RegisteredModelList,
    RegisteredModelWithVersions,
    ModelVersion,
    ModelVersionCreate,
    ModelVersionUpdate,
    ModelVersionList,
    StageTransitionRequest,
    ModelVersionTransitionList,
    ModelRegistrySummary,
)

router = APIRouter()


# Registered Model endpoints

@router.post("", response_model=RegisteredModel, status_code=status.HTTP_201_CREATED)
def create_model(
    model_data: RegisteredModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new registered model.

    Args:
        model_data: Model data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created registered model
    """
    repo = ModelRegistryRepository(db)

    # Check if model name already exists in project
    existing = repo.get_model_by_name(model_data.project_id, model_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model '{model_data.name}' already exists in this project"
        )

    model = repo.create_model(model_data, current_user.id)
    return model


@router.get("", response_model=RegisteredModelList)
def list_models(
    project_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List registered models.

    Args:
        project_id: Filter by project ID
        search: Search in model name
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of registered models
    """
    repo = ModelRegistryRepository(db)
    models, total = repo.list_models(
        project_id=project_id,
        search=search,
        skip=skip,
        limit=limit
    )

    return RegisteredModelList(
        items=models,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/summary", response_model=ModelRegistrySummary)
def get_summary(
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary statistics for model registry.

    Args:
        project_id: Filter by project ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Summary statistics
    """
    repo = ModelRegistryRepository(db)
    summary = repo.get_summary(project_id=project_id)
    return summary


@router.get("/{model_id}", response_model=RegisteredModelWithVersions)
def get_model(
    model_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a registered model with its versions.

    Args:
        model_id: Model ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Registered model with versions
    """
    repo = ModelRegistryRepository(db)
    model = repo.get_model(model_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return model


@router.patch("/{model_id}", response_model=RegisteredModel)
def update_model(
    model_id: UUID,
    model_data: RegisteredModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a registered model.

    Args:
        model_id: Model ID
        model_data: Updated model data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated registered model
    """
    repo = ModelRegistryRepository(db)
    model = repo.update_model(model_id, model_data)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a registered model.

    Args:
        model_id: Model ID
        db: Database session
        current_user: Current authenticated user
    """
    repo = ModelRegistryRepository(db)
    success = repo.delete_model(model_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )


# Model Version endpoints

@router.post("/{model_id}/versions", response_model=ModelVersion, status_code=status.HTTP_201_CREATED)
def create_version(
    model_id: UUID,
    version_data: ModelVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new model version.

    Args:
        model_id: Model ID
        version_data: Version data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created model version
    """
    repo = ModelRegistryRepository(db)

    # Check if model exists
    model = repo.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Check if version already exists
    existing = repo.get_version_by_name(model_id, version_data.version)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version '{version_data.version}' already exists"
        )

    version = repo.create_version(model_id, version_data)
    return version


@router.get("/{model_id}/versions", response_model=ModelVersionList)
def list_versions(
    model_id: UUID,
    stage: Optional[ModelStage] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List versions of a model.

    Args:
        model_id: Model ID
        stage: Filter by stage
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of model versions
    """
    repo = ModelRegistryRepository(db)

    # Check if model exists
    model = repo.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    versions, total = repo.list_versions(
        model_id=model_id,
        stage=stage,
        skip=skip,
        limit=limit
    )

    return ModelVersionList(
        items=versions,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{model_id}/versions/{version}", response_model=ModelVersion)
def get_version(
    model_id: UUID,
    version: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific model version.

    Args:
        model_id: Model ID
        version: Version string
        db: Database session
        current_user: Current authenticated user

    Returns:
        Model version
    """
    repo = ModelRegistryRepository(db)
    model_version = repo.get_version_by_name(model_id, version)

    if not model_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found"
        )

    return model_version


@router.get("/stages/{stage}/latest", response_model=ModelVersion)
def get_latest_by_stage(
    model_id: UUID,
    stage: ModelStage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest version in a specific stage.

    Args:
        model_id: Model ID
        stage: Model stage
        db: Database session
        current_user: Current authenticated user

    Returns:
        Latest model version in stage
    """
    repo = ModelRegistryRepository(db)
    version = repo.get_latest_version_by_stage(model_id, stage)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No version found in stage '{stage.value}'"
        )

    return version


@router.patch("/versions/{version_id}", response_model=ModelVersion)
def update_version(
    version_id: UUID,
    version_data: ModelVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a model version.

    Args:
        version_id: Version ID
        version_data: Updated version data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated model version
    """
    repo = ModelRegistryRepository(db)
    version = repo.update_version(version_id, version_data)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found"
        )

    return version


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version(
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a model version.

    Args:
        version_id: Version ID
        db: Database session
        current_user: Current authenticated user
    """
    repo = ModelRegistryRepository(db)
    success = repo.delete_version(version_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found"
        )


# Stage Transition endpoints

@router.post("/versions/{version_id}/transition", response_model=ModelVersion)
def transition_stage(
    version_id: UUID,
    transition_data: StageTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transition a model version to a different stage.

    Args:
        version_id: Version ID
        transition_data: Transition request data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated model version
    """
    repo = ModelRegistryRepository(db)
    version = repo.transition_stage(version_id, transition_data, current_user.id)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found"
        )

    return version


@router.get("/versions/{version_id}/transitions", response_model=ModelVersionTransitionList)
def get_transition_history(
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get transition history for a model version.

    Args:
        version_id: Version ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of transitions
    """
    repo = ModelRegistryRepository(db)

    # Check if version exists
    version = repo.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found"
        )

    transitions = repo.get_transition_history(version_id)

    return ModelVersionTransitionList(
        items=transitions,
        total=len(transitions)
    )
