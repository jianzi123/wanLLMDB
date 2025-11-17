"""
VDC API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.vdc import VDC
from app.models.cluster import Cluster
from app.schemas.vdc import (
    VDCCreate,
    VDCUpdate,
    VDCResponse,
    VDCListResponse,
    VDCStats,
    ClusterCreate,
    ClusterUpdate,
    ClusterResponse,
    ClusterListResponse,
    ClusterStats,
    ProjectVDCQuotaCreate,
    ProjectVDCQuotaUpdate,
    ProjectVDCQuotaResponse,
    ProjectVDCQuotaListResponse,
    QuotaUsage,
)
from app.repositories.vdc_repository import (
    VDCRepository,
    ClusterRepository,
    ProjectVDCQuotaRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vdcs", tags=["vdcs"])


# VDC Management
@router.post("", response_model=VDCResponse, status_code=status.HTTP_201_CREATED)
def create_vdc(
    vdc_data: VDCCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VDCResponse:
    """Create a new VDC"""
    vdc_repo = VDCRepository(db)

    # Check if name already exists
    existing = vdc_repo.get_by_name(vdc_data.name)
    if existing:
        raise HTTPException(status_code=400, detail="VDC with this name already exists")

    vdc = vdc_repo.create(vdc_data.model_dump())
    logger.info(f"User {current_user.id} created VDC {vdc.id}")

    return VDCResponse.model_validate(vdc)


@router.get("", response_model=VDCListResponse)
def list_vdcs(
    enabled_only: bool = Query(False, description="Only return enabled VDCs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VDCListResponse:
    """List all VDCs"""
    vdc_repo = VDCRepository(db)
    vdcs = vdc_repo.get_all(enabled_only=enabled_only)

    return VDCListResponse(
        items=[VDCResponse.model_validate(v) for v in vdcs],
        total=len(vdcs)
    )


@router.get("/{vdc_id}", response_model=VDCResponse)
def get_vdc(
    vdc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VDCResponse:
    """Get VDC by ID"""
    vdc_repo = VDCRepository(db)
    vdc = vdc_repo.get_by_id(vdc_id)

    if not vdc:
        raise HTTPException(status_code=404, detail="VDC not found")

    return VDCResponse.model_validate(vdc)


@router.put("/{vdc_id}", response_model=VDCResponse)
def update_vdc(
    vdc_id: UUID,
    vdc_data: VDCUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VDCResponse:
    """Update VDC"""
    vdc_repo = VDCRepository(db)
    vdc = vdc_repo.get_by_id(vdc_id)

    if not vdc:
        raise HTTPException(status_code=404, detail="VDC not found")

    # Check name uniqueness if updating name
    if vdc_data.name and vdc_data.name != vdc.name:
        existing = vdc_repo.get_by_name(vdc_data.name)
        if existing:
            raise HTTPException(status_code=400, detail="VDC with this name already exists")

    update_data = vdc_data.model_dump(exclude_unset=True)
    vdc = vdc_repo.update(vdc, update_data)

    logger.info(f"User {current_user.id} updated VDC {vdc.id}")
    return VDCResponse.model_validate(vdc)


@router.delete("/{vdc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vdc(
    vdc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete VDC"""
    vdc_repo = VDCRepository(db)
    vdc = vdc_repo.get_by_id(vdc_id)

    if not vdc:
        raise HTTPException(status_code=404, detail="VDC not found")

    # Check if VDC has running jobs
    if vdc.current_jobs > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete VDC with {vdc.current_jobs} running jobs"
        )

    vdc_repo.delete(vdc)
    logger.info(f"User {current_user.id} deleted VDC {vdc.id}")


@router.get("/{vdc_id}/stats", response_model=VDCStats)
def get_vdc_stats(
    vdc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VDCStats:
    """Get VDC statistics"""
    vdc_repo = VDCRepository(db)
    cluster_repo = ClusterRepository(db)
    quota_repo = ProjectVDCQuotaRepository(db)

    vdc = vdc_repo.get_by_id(vdc_id)
    if not vdc:
        raise HTTPException(status_code=404, detail="VDC not found")

    clusters = cluster_repo.get_by_vdc(vdc_id)
    healthy_clusters = sum(1 for c in clusters if c.status.value == "healthy")

    project_quotas = quota_repo.get_by_vdc(vdc_id)

    return VDCStats(
        total_clusters=len(clusters),
        healthy_clusters=healthy_clusters,
        total_capacity=vdc.get_total_cluster_resources(),
        effective_quota=vdc.get_effective_quota(),
        used_resources={
            "cpu": vdc.used_cpu,
            "memory": vdc.used_memory,
            "gpu": vdc.used_gpu
        },
        available_resources=vdc.get_available_resources(),
        usage_percentage=vdc.get_usage_percentage(),
        total_projects=len(project_quotas),
        current_jobs=vdc.current_jobs
    )


# Cluster Management
@router.post("/{vdc_id}/clusters", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
def create_cluster(
    vdc_id: UUID,
    cluster_data: ClusterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClusterResponse:
    """Add a cluster to VDC"""
    vdc_repo = VDCRepository(db)
    cluster_repo = ClusterRepository(db)

    # Verify VDC exists
    vdc = vdc_repo.get_by_id(vdc_id)
    if not vdc:
        raise HTTPException(status_code=404, detail="VDC not found")

    # Ensure cluster belongs to this VDC
    if cluster_data.vdc_id != vdc_id:
        raise HTTPException(status_code=400, detail="Cluster vdc_id must match URL vdc_id")

    cluster = cluster_repo.create(cluster_data.model_dump())
    logger.info(f"User {current_user.id} created cluster {cluster.id} in VDC {vdc_id}")

    return ClusterResponse.model_validate(cluster)


@router.get("/{vdc_id}/clusters", response_model=ClusterListResponse)
def list_clusters(
    vdc_id: UUID,
    enabled_only: bool = Query(False, description="Only return enabled clusters"),
    healthy_only: bool = Query(False, description="Only return healthy clusters"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClusterListResponse:
    """List clusters in a VDC"""
    cluster_repo = ClusterRepository(db)
    clusters = cluster_repo.get_by_vdc(vdc_id, enabled_only=enabled_only, healthy_only=healthy_only)

    return ClusterListResponse(
        items=[ClusterResponse.model_validate(c) for c in clusters],
        total=len(clusters)
    )


# Project VDC Quota Management
@router.post("/{vdc_id}/quotas", response_model=ProjectVDCQuotaResponse, status_code=status.HTTP_201_CREATED)
def create_project_quota(
    vdc_id: UUID,
    quota_data: ProjectVDCQuotaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectVDCQuotaResponse:
    """Allocate VDC quota to a project"""
    vdc_repo = VDCRepository(db)
    quota_repo = ProjectVDCQuotaRepository(db)

    # Verify VDC exists
    vdc = vdc_repo.get_by_id(vdc_id)
    if not vdc:
        raise HTTPException(status_code=404, detail="VDC not found")

    # Ensure quota belongs to this VDC
    if quota_data.vdc_id != vdc_id:
        raise HTTPException(status_code=400, detail="Quota vdc_id must match URL vdc_id")

    # Check if quota already exists
    existing = quota_repo.get_by_project_and_vdc(quota_data.project_id, vdc_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Quota already exists for this project in this VDC"
        )

    quota = quota_repo.create(quota_data.model_dump())
    logger.info(
        f"User {current_user.id} created quota for project {quota_data.project_id} in VDC {vdc_id}"
    )

    return ProjectVDCQuotaResponse.model_validate(quota)


@router.get("/{vdc_id}/quotas", response_model=ProjectVDCQuotaListResponse)
def list_vdc_quotas(
    vdc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectVDCQuotaListResponse:
    """List all project quotas in a VDC"""
    quota_repo = ProjectVDCQuotaRepository(db)
    quotas = quota_repo.get_by_vdc(vdc_id)

    return ProjectVDCQuotaListResponse(
        items=[ProjectVDCQuotaResponse.model_validate(q) for q in quotas],
        total=len(quotas)
    )
