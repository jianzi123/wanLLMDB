"""
Repository for artifact operations.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload

from app.models.artifact import Artifact, ArtifactVersion, ArtifactFile, ArtifactAlias
from app.schemas.artifact import ArtifactCreate, ArtifactUpdate, ArtifactVersionCreate, ArtifactFileCreate, ArtifactAliasCreate


class ArtifactRepository:
    """Repository for artifact CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    # Artifact operations
    def create(self, artifact_in: ArtifactCreate, user_id: UUID) -> Artifact:
        """Create a new artifact."""
        artifact = Artifact(
            **artifact_in.model_dump(),
            created_by=user_id,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def get(self, artifact_id: UUID) -> Optional[Artifact]:
        """Get artifact by ID."""
        return self.db.get(Artifact, artifact_id)

    def get_with_versions(self, artifact_id: UUID) -> Optional[Artifact]:
        """Get artifact with all versions."""
        stmt = (
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(Artifact.id == artifact_id)
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list(
        self,
        project_id: Optional[UUID] = None,
        artifact_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Artifact], int]:
        """List artifacts with filters and pagination."""
        # Build query
        query = select(Artifact)
        count_query = select(func.count()).select_from(Artifact)

        # Apply filters
        filters = []
        if project_id:
            filters.append(Artifact.project_id == project_id)
        if artifact_type:
            filters.append(Artifact.type == artifact_type)
        if search:
            filters.append(Artifact.name.ilike(f"%{search}%"))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Get total count
        total = self.db.execute(count_query).scalar()

        # Apply pagination and sorting
        query = query.order_by(Artifact.updated_at.desc()).offset(skip).limit(limit)

        # Execute query
        result = self.db.execute(query)
        artifacts = list(result.scalars().all())

        return artifacts, total

    def update(self, artifact_id: UUID, artifact_in: ArtifactUpdate) -> Optional[Artifact]:
        """Update an artifact."""
        artifact = self.get(artifact_id)
        if not artifact:
            return None

        update_data = artifact_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(artifact, field, value)

        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def delete(self, artifact_id: UUID) -> bool:
        """Delete an artifact."""
        artifact = self.get(artifact_id)
        if not artifact:
            return False

        self.db.delete(artifact)
        self.db.commit()
        return True

    # Artifact Version operations
    def create_version(
        self,
        version_in: ArtifactVersionCreate,
        user_id: UUID,
        storage_path: str,
    ) -> ArtifactVersion:
        """Create a new artifact version."""
        artifact = self.get(version_in.artifact_id)
        if not artifact:
            raise ValueError("Artifact not found")

        # Generate version if not provided
        version = version_in.version
        if not version:
            artifact.version_count += 1
            version = f"v{artifact.version_count}"

        # Create version
        artifact_version = ArtifactVersion(
            artifact_id=version_in.artifact_id,
            version=version,
            description=version_in.description,
            notes=version_in.notes,
            metadata=version_in.metadata or {},
            run_id=version_in.run_id,
            storage_path=storage_path,
            created_by=user_id,
        )

        self.db.add(artifact_version)

        # Update artifact
        artifact.latest_version = version
        artifact.version_count = max(artifact.version_count, int(version.lstrip('v'))) if version.startswith('v') else artifact.version_count + 1

        self.db.commit()
        self.db.refresh(artifact_version)
        return artifact_version

    def get_version(self, version_id: UUID) -> Optional[ArtifactVersion]:
        """Get artifact version by ID."""
        return self.db.get(ArtifactVersion, version_id)

    def get_version_with_files(self, version_id: UUID) -> Optional[ArtifactVersion]:
        """Get artifact version with all files."""
        stmt = (
            select(ArtifactVersion)
            .options(selectinload(ArtifactVersion.files))
            .where(ArtifactVersion.id == version_id)
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list_versions(
        self,
        artifact_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ArtifactVersion], int]:
        """List versions for an artifact."""
        # Count query
        count_query = (
            select(func.count())
            .select_from(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
        )
        total = self.db.execute(count_query).scalar()

        # Data query
        query = (
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = self.db.execute(query)
        versions = list(result.scalars().all())

        return versions, total

    def finalize_version(self, version_id: UUID, digest: Optional[str] = None) -> Optional[ArtifactVersion]:
        """Finalize an artifact version (make it immutable)."""
        version = self.get_version(version_id)
        if not version:
            return None

        version.is_finalized = True
        version.digest = digest
        from datetime import datetime
        version.finalized_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(version)
        return version

    # Artifact File operations
    def add_file(self, file_in: ArtifactFileCreate) -> ArtifactFile:
        """Add a file to an artifact version."""
        file = ArtifactFile(**file_in.model_dump())
        self.db.add(file)

        # Update version stats
        version = self.get_version(file_in.version_id)
        if version:
            version.file_count += 1
            version.total_size += file_in.size

        self.db.commit()
        self.db.refresh(file)
        return file

    def get_file(self, file_id: UUID) -> Optional[ArtifactFile]:
        """Get artifact file by ID."""
        return self.db.get(ArtifactFile, file_id)

    def list_files(self, version_id: UUID) -> List[ArtifactFile]:
        """List all files in an artifact version."""
        query = (
            select(ArtifactFile)
            .where(ArtifactFile.version_id == version_id)
            .order_by(ArtifactFile.path)
        )
        result = self.db.execute(query)
        return list(result.scalars().all())

    def delete_file(self, file_id: UUID) -> bool:
        """Delete a file from an artifact version."""
        file = self.get_file(file_id)
        if not file:
            return False

        # Update version stats
        version = self.get_version(file.version_id)
        if version:
            version.file_count -= 1
            version.total_size -= file.size

        self.db.delete(file)
        self.db.commit()
        return True

    # Alias operations
    def create_or_update_alias(
        self, artifact_id: UUID, alias_in: ArtifactAliasCreate, user_id: UUID
    ) -> ArtifactAlias:
        """Create or update an artifact alias.

        If the alias already exists for this artifact, update it to point to the new version.
        Otherwise, create a new alias.
        """
        # Check if alias already exists
        existing = self.get_alias(artifact_id, alias_in.alias)

        if existing:
            # Update existing alias to point to new version
            existing.version_id = alias_in.version_id
            existing.created_by = user_id
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new alias
            alias = ArtifactAlias(
                artifact_id=artifact_id,
                version_id=alias_in.version_id,
                alias=alias_in.alias,
                created_by=user_id,
            )
            self.db.add(alias)
            self.db.commit()
            self.db.refresh(alias)
            return alias

    def get_alias(self, artifact_id: UUID, alias: str) -> Optional[ArtifactAlias]:
        """Get an alias by artifact ID and alias name."""
        query = select(ArtifactAlias).where(
            and_(
                ArtifactAlias.artifact_id == artifact_id,
                ArtifactAlias.alias == alias
            )
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def list_aliases(self, artifact_id: UUID) -> List[ArtifactAlias]:
        """List all aliases for an artifact."""
        query = (
            select(ArtifactAlias)
            .where(ArtifactAlias.artifact_id == artifact_id)
            .order_by(ArtifactAlias.alias)
        )
        result = self.db.execute(query)
        return list(result.scalars().all())

    def delete_alias(self, artifact_id: UUID, alias: str) -> bool:
        """Delete an alias."""
        alias_obj = self.get_alias(artifact_id, alias)
        if not alias_obj:
            return False

        self.db.delete(alias_obj)
        self.db.commit()
        return True
