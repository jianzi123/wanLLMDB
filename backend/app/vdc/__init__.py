"""
VDC (Virtual Data Center) module for multi-cluster scheduling.
"""

from app.vdc.vdc_scheduler import VDCScheduler
from app.vdc.cluster_selector import ClusterSelector
from app.vdc.quota_manager import VDCQuotaManager

__all__ = [
    "VDCScheduler",
    "ClusterSelector",
    "VDCQuotaManager",
]
