from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api.v1 import api_router
from app.api import monitoring
from app.executors import ExecutorFactory
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"/api/v1/openapi.json",
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Initializing WanLLMDB backend...")

    # Initialize job executors
    executor_config = {}

    if settings.EXECUTOR_KUBERNETES_ENABLED:
        logger.info("Initializing Kubernetes executor...")
        executor_config["kubernetes"] = {
            "kubeconfig_path": settings.EXECUTOR_KUBERNETES_KUBECONFIG or None,
            "default_namespace": settings.EXECUTOR_KUBERNETES_NAMESPACE,
            "default_service_account": settings.EXECUTOR_KUBERNETES_SERVICE_ACCOUNT,
        }

    if settings.EXECUTOR_SLURM_ENABLED:
        logger.info("Initializing Slurm executor...")
        if not settings.EXECUTOR_SLURM_REST_API_URL:
            logger.warning("Slurm executor enabled but REST API URL not configured")
        else:
            executor_config["slurm"] = {
                "rest_api_url": settings.EXECUTOR_SLURM_REST_API_URL,
                "auth_token": settings.EXECUTOR_SLURM_AUTH_TOKEN,
                "default_partition": settings.EXECUTOR_SLURM_PARTITION,
                "default_account": settings.EXECUTOR_SLURM_ACCOUNT or None,
            }

    if executor_config:
        try:
            ExecutorFactory.initialize(executor_config)
            logger.info(f"Executors initialized: {list(executor_config.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize executors: {e}")
    else:
        logger.info("No job executors configured")

    logger.info("WanLLMDB backend initialized successfully")

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include monitoring router (health checks, metrics)
app.include_router(monitoring.router, tags=["monitoring"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
