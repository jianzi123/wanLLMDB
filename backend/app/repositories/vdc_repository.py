"""
Repositories for VDC, Cluster, and ProjectVDCQuota models.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.vdc import VDC
from app.models.cluster import Cluster, ClusterStatusEnum
from app.models.project_vdc_quota import ProjectVDCQuota


class VDCRepository:
    """VDC repository"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> VDC:
        """Create a new VDC"""
        vdc = VDC(**data)
        self.db.add(vdc)
        self.db.commit()
        self.db.refresh(vdc)
        return vdc

    def get_by_id(self, vdc_id: UUID) -> Optional[VDC]:
        """Get VDC by ID"""
        return self.db.query(VDC).filter(VDC.id == vdc_id).first()

    def get_by_name(self, name: str) -> Optional[VDC]:
        """Get VDC by name"""
        return self.db.query(VDC).filter(VDC.name == name).first()

    def get_all(self, enabled_only: bool = False) -> List[VDC]:
        """Get all VDCs"""
        query = self.db.query(VDC)
        if enabled_only:
            query = query.filter(VDC.enabled == True)
        return query.all()

    def update(self, vdc: VDC, data: dict) -> VDC:
        """Update VDC"""
        for key, value in data.items():
            setattr(vdc, key, value)
        self.db.commit()
        self.db.refresh(vdc)
        return vdc

    def delete(self, vdc: VDC) -> None:
        """Delete VDC"""
        self.db.delete(vdc)
        self.db.commit()


class ClusterRepository:
    """Cluster repository"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Cluster:
        """Create a new cluster"""
        cluster = Cluster(**data)
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)
        return cluster

    def get_by_id(self, cluster_id: UUID) -> Optional[Cluster]:
        """Get cluster by ID"""
        return self.db.query(Cluster).filter(Cluster.id == cluster_id).first()

    def get_by_vdc(
        self,
        vdc_id: UUID,
        enabled_only: bool = False,
        healthy_only: bool = False
    ) -> List[Cluster]:
        """Get all clusters in a VDC"""
        query = self.db.query(Cluster).filter(Cluster.vdc_id == vdc_id)

        if enabled_only:
            query = query.filter(Cluster.enabled == True)
        if healthy_only:
            query = query.filter(Cluster.status == ClusterStatusEnum.HEALTHY)

        return query.all()

    def get_all(self) -> List[Cluster]:
        """Get all clusters"""
        return self.db.query(Cluster).all()

    def update(self, cluster: Cluster, data: dict) -> Cluster:
        """Update cluster"""
        for key, value in data.items():
            setattr(cluster, key, value)
        self.db.commit()
        self.db.refresh(cluster)
        return cluster

    def delete(self, cluster: Cluster) -> None:
        """Delete cluster"""
        self.db.delete(cluster)
        self.db.commit()

    def update_heartbeat(self, cluster: Cluster) -> None:
        """Update cluster heartbeat"""
        from datetime import datetime
        cluster.last_heartbeat = datetime.utcnow()
        self.db.commit()

    def update_status(
        self,
        cluster: Cluster,
        status: ClusterStatusEnum,
        message: str = None
    ) -> None:
        """Update cluster status"""
        cluster.status = status
        if message:
            cluster.status_message = message
        self.db.commit()


class ProjectVDCQuotaRepository:
    """ProjectVDCQuota repository"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> ProjectVDCQuota:
        """Create a new project VDC quota"""
        quota = ProjectVDCQuota(**data)
        self.db.add(quota)
        self.db.commit()
        self.db.refresh(quota)
        return quota

    def get_by_id(self, quota_id: UUID) -> Optional[ProjectVDCQuota]:
        """Get quota by ID"""
        return self.db.query(ProjectVDCQuota).filter(
            ProjectVDCQuota.id == quota_id
        ).first()

    def get_by_project_and_vdc(
        self,
        project_id: UUID,
        vdc_id: UUID
    ) -> Optional[ProjectVDCQuota]:
        """Get quota for a project in a specific VDC"""
        return self.db.query(ProjectVDCQuota).filter(
            ProjectVDCQuota.project_id == project_id,
            ProjectVDCQuota.vdc_id == vdc_id
        ).first()

    def get_by_project(self, project_id: UUID) -> List[ProjectVDCQuota]:
        """Get all quotas for a project (across all VDCs)"""
        return self.db.query(ProjectVDCQuota).filter(
            ProjectVDCQuota.project_id == project_id
        ).all()

    def get_by_vdc(self, vdc_id: UUID) -> List[ProjectVDCQuota]:
        """Get all project quotas in a VDC"""
        return self.db.query(ProjectVDCQuota).filter(
            ProjectVDCQuota.vdc_id == vdc_id
        ).all()

    def update(self, quota: ProjectVDCQuota, data: dict) -> ProjectVDCQuota:
        """Update quota"""
        for key, value in data.items():
            setattr(quota, key, value)
        self.db.commit()
        self.db.refresh(quota)
        return quota

    def delete(self, quota: ProjectVDCQuota) -> None:
        """Delete quota"""
        self.db.delete(quota)
        self.db.commit()

    def get_or_create(
        self,
        project_id: UUID,
        vdc_id: UUID,
        defaults: dict = None
    ) -> ProjectVDCQuota:
        """Get existing quota or create with defaults"""
        quota = self.get_by_project_and_vdc(project_id, vdc_id)
        if quota:
            return quota

        data = {
            "project_id": project_id,
            "vdc_id": vdc_id
        }
        if defaults:
            data.update(defaults)

        return self.create(data)
