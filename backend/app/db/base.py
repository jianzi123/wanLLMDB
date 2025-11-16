# Import all the models, so that Base has them before being imported by Alembic
from app.db.database import Base  # noqa
from app.models.user import User  # noqa
from app.models.project import Project  # noqa
from app.models.run import Run  # noqa
