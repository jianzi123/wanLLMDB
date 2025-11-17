# Import all the models, so that Base has them before being imported by Alembic
from app.db.database import Base  # noqa
from app.models.user import User  # noqa
from app.models.project import Project  # noqa
from app.models.run import Run  # noqa
from app.models.run_config import RunConfig  # noqa
from app.models.run_summary import RunSummary  # noqa
from app.models.artifact import Artifact, ArtifactVersion, ArtifactFile, ArtifactDownload  # noqa
from app.models.sweep import Sweep, SweepRun  # noqa
from app.models.audit_log import AuditLog  # noqa
from app.models.model_registry import RegisteredModel, ModelVersion, ModelVersionTransition  # noqa
from app.models.run_file import RunFile  # noqa
from app.models.run_log import RunLog  # noqa
