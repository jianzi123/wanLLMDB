"""Repository for model registry operations."""

from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_

from app.models.model_registry import RegisteredModel, ModelVersion, ModelVersionTransition, ModelStage
from app.schemas.model_registry import (
    RegisteredModelCreate,
    RegisteredModelUpdate,
    ModelVersionCreate,
    ModelVersionUpdate,
    StageTransitionRequest,
)


class ModelRegistryRepository:
    """Repository for managing model registry."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Registered Model operations

    def create_model(self, model_data: RegisteredModelCreate, user_id: UUID) -> RegisteredModel:
        """Create a new registered model.

        Args:
            model_data: Model data
            user_id: User ID creating the model

        Returns:
            Created registered model
        """
        model = RegisteredModel(
            name=model_data.name,
            description=model_data.description,
            tags=model_data.tags,
            project_id=model_data.project_id,
            created_by=user_id,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def get_model(self, model_id: UUID) -> Optional[RegisteredModel]:
        """Get a registered model by ID.

        Args:
            model_id: Model ID

        Returns:
            Registered model if found, None otherwise
        """
        return self.db.query(RegisteredModel).filter(RegisteredModel.id == model_id).first()

    def get_model_by_name(self, project_id: UUID, name: str) -> Optional[RegisteredModel]:
        """Get a registered model by name within a project.

        Args:
            project_id: Project ID
            name: Model name

        Returns:
            Registered model if found, None otherwise
        """
        return (
            self.db.query(RegisteredModel)
            .filter(
                and_(
                    RegisteredModel.project_id == project_id,
                    RegisteredModel.name == name
                )
            )
            .first()
        )

    def list_models(
        self,
        project_id: Optional[UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[RegisteredModel], int]:
        """List registered models.

        Args:
            project_id: Filter by project ID
            search: Search in model name
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of models, total count)
        """
        query = self.db.query(RegisteredModel)

        if project_id:
            query = query.filter(RegisteredModel.project_id == project_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(RegisteredModel.name.ilike(search_pattern))

        total = query.count()

        models = (
            query
            .options(joinedload(RegisteredModel.versions))
            .order_by(RegisteredModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return models, total

    def update_model(self, model_id: UUID, model_data: RegisteredModelUpdate) -> Optional[RegisteredModel]:
        """Update a registered model.

        Args:
            model_id: Model ID
            model_data: Updated model data

        Returns:
            Updated model if found, None otherwise
        """
        model = self.get_model(model_id)
        if not model:
            return None

        if model_data.description is not None:
            model.description = model_data.description

        if model_data.tags is not None:
            model.tags = model_data.tags

        self.db.commit()
        self.db.refresh(model)
        return model

    def delete_model(self, model_id: UUID) -> bool:
        """Delete a registered model.

        Args:
            model_id: Model ID

        Returns:
            True if deleted, False if not found
        """
        model = self.get_model(model_id)
        if not model:
            return False

        self.db.delete(model)
        self.db.commit()
        return True

    # Model Version operations

    def create_version(
        self,
        model_id: UUID,
        version_data: ModelVersionCreate
    ) -> ModelVersion:
        """Create a new model version.

        Args:
            model_id: Model ID
            version_data: Version data

        Returns:
            Created model version
        """
        version = ModelVersion(
            model_id=model_id,
            version=version_data.version,
            description=version_data.description,
            stage=version_data.stage,
            run_id=version_data.run_id,
            artifact_version_id=version_data.artifact_version_id,
            metrics=version_data.metrics,
            tags=version_data.tags,
            metadata=version_data.metadata,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_version(self, version_id: UUID) -> Optional[ModelVersion]:
        """Get a model version by ID.

        Args:
            version_id: Version ID

        Returns:
            Model version if found, None otherwise
        """
        return self.db.query(ModelVersion).filter(ModelVersion.id == version_id).first()

    def get_version_by_name(self, model_id: UUID, version: str) -> Optional[ModelVersion]:
        """Get a model version by version string.

        Args:
            model_id: Model ID
            version: Version string

        Returns:
            Model version if found, None otherwise
        """
        return (
            self.db.query(ModelVersion)
            .filter(
                and_(
                    ModelVersion.model_id == model_id,
                    ModelVersion.version == version
                )
            )
            .first()
        )

    def list_versions(
        self,
        model_id: UUID,
        stage: Optional[ModelStage] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ModelVersion], int]:
        """List versions of a model.

        Args:
            model_id: Model ID
            stage: Filter by stage
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of versions, total count)
        """
        query = self.db.query(ModelVersion).filter(ModelVersion.model_id == model_id)

        if stage:
            query = query.filter(ModelVersion.stage == stage)

        total = query.count()

        versions = (
            query
            .order_by(ModelVersion.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return versions, total

    def update_version(
        self,
        version_id: UUID,
        version_data: ModelVersionUpdate
    ) -> Optional[ModelVersion]:
        """Update a model version.

        Args:
            version_id: Version ID
            version_data: Updated version data

        Returns:
            Updated version if found, None otherwise
        """
        version = self.get_version(version_id)
        if not version:
            return None

        if version_data.description is not None:
            version.description = version_data.description

        if version_data.tags is not None:
            version.tags = version_data.tags

        if version_data.metadata is not None:
            version.metadata = version_data.metadata

        self.db.commit()
        self.db.refresh(version)
        return version

    def delete_version(self, version_id: UUID) -> bool:
        """Delete a model version.

        Args:
            version_id: Version ID

        Returns:
            True if deleted, False if not found
        """
        version = self.get_version(version_id)
        if not version:
            return False

        self.db.delete(version)
        self.db.commit()
        return True

    # Stage transition operations

    def transition_stage(
        self,
        version_id: UUID,
        transition_data: StageTransitionRequest,
        user_id: UUID
    ) -> Optional[ModelVersion]:
        """Transition a model version to a different stage.

        Args:
            version_id: Version ID
            transition_data: Transition request data
            user_id: User ID performing the transition

        Returns:
            Updated version if found, None otherwise
        """
        version = self.get_version(version_id)
        if not version:
            return None

        # Record transition history
        transition = ModelVersionTransition(
            model_version_id=version_id,
            from_stage=version.stage,
            to_stage=transition_data.stage,
            comment=transition_data.comment,
            transitioned_by=user_id,
        )
        self.db.add(transition)

        # Update version stage
        version.stage = transition_data.stage

        # If transitioning to production, record approval
        if transition_data.stage == ModelStage.PRODUCTION:
            from datetime import datetime, timezone
            version.approved_by = user_id
            version.approved_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(version)
        return version

    def get_transition_history(
        self,
        version_id: UUID
    ) -> List[ModelVersionTransition]:
        """Get transition history for a model version.

        Args:
            version_id: Version ID

        Returns:
            List of transitions
        """
        return (
            self.db.query(ModelVersionTransition)
            .filter(ModelVersionTransition.model_version_id == version_id)
            .order_by(ModelVersionTransition.transitioned_at.desc())
            .all()
        )

    def get_latest_version_by_stage(
        self,
        model_id: UUID,
        stage: ModelStage
    ) -> Optional[ModelVersion]:
        """Get the latest version in a specific stage.

        Args:
            model_id: Model ID
            stage: Model stage

        Returns:
            Latest version in stage if found, None otherwise
        """
        return (
            self.db.query(ModelVersion)
            .filter(
                and_(
                    ModelVersion.model_id == model_id,
                    ModelVersion.stage == stage
                )
            )
            .order_by(ModelVersion.created_at.desc())
            .first()
        )

    # Statistics

    def get_summary(self, project_id: Optional[UUID] = None) -> dict:
        """Get summary statistics for model registry.

        Args:
            project_id: Filter by project ID

        Returns:
            Dictionary with summary statistics
        """
        # Total models
        model_query = self.db.query(func.count(RegisteredModel.id))
        if project_id:
            model_query = model_query.filter(RegisteredModel.project_id == project_id)
        total_models = model_query.scalar() or 0

        # Total versions
        version_query = self.db.query(func.count(ModelVersion.id))
        if project_id:
            version_query = version_query.join(RegisteredModel).filter(RegisteredModel.project_id == project_id)
        total_versions = version_query.scalar() or 0

        # Versions by stage
        stage_query = (
            self.db.query(ModelVersion.stage, func.count(ModelVersion.id))
            .group_by(ModelVersion.stage)
        )
        if project_id:
            stage_query = stage_query.join(RegisteredModel).filter(RegisteredModel.project_id == project_id)

        by_stage = {stage.value: count for stage, count in stage_query.all()}

        return {
            "total_models": total_models,
            "total_versions": total_versions,
            "by_stage": by_stage,
        }
