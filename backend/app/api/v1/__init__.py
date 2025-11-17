from fastapi import APIRouter
from app.api.v1 import auth, projects, runs, artifacts, sweeps, run_files, run_logs, model_registry, audit, jobs

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(sweeps.router, prefix="/sweeps", tags=["sweeps"])
api_router.include_router(run_files.router, prefix="/runs", tags=["run-files"])
api_router.include_router(run_logs.router, prefix="/runs", tags=["run-logs"])
api_router.include_router(model_registry.router, prefix="/registry/models", tags=["model-registry"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
