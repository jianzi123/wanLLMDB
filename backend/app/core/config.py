from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator, ValidationError


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "wanLLMDB"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 50  # Increased from 20
    DATABASE_MAX_OVERFLOW: int = 20  # Increased from 10
    DATABASE_POOL_RECYCLE: int = 3600  # Recycle connections every hour
    DATABASE_POOL_PRE_PING: bool = True  # Test connections before use

    # Redis
    REDIS_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin users (for audit log access and other admin operations)
    # Comma-separated list of admin usernames
    ADMIN_USERS: str = ""  # Empty by default, must be configured

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # MinIO / S3 - NO DEFAULT VALUES FOR SECURITY
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str  # ✅ No default - must be configured
    MINIO_SECRET_KEY: str  # ✅ No default - must be configured
    MINIO_BUCKET: str = "wanllmdb"
    MINIO_SECURE: bool = False

    # TimescaleDB
    TIMESCALE_URL: str

    # Cluster Job Executors
    EXECUTOR_KUBERNETES_ENABLED: bool = False
    EXECUTOR_KUBERNETES_KUBECONFIG: str = ""
    EXECUTOR_KUBERNETES_NAMESPACE: str = "wanllmdb-jobs"
    EXECUTOR_KUBERNETES_SERVICE_ACCOUNT: str = "default"

    EXECUTOR_SLURM_ENABLED: bool = False
    EXECUTOR_SLURM_REST_API_URL: str = ""
    EXECUTOR_SLURM_AUTH_TOKEN: str = ""
    EXECUTOR_SLURM_PARTITION: str = "compute"
    EXECUTOR_SLURM_ACCOUNT: str = ""

    @field_validator('MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY')
    @classmethod
    def validate_not_default_credentials(cls, v: str, info) -> str:
        """Prevent use of default/weak credentials (except in development)"""
        # Allow default credentials in development mode (DEBUG=True)
        debug_mode = info.data.get('DEBUG', False)
        if debug_mode:
            return v
        
        dangerous_values = {
            'minioadmin', 'admin', 'password', 'root',
            'minio', 'secret', '123456', 'changeme'
        }
        if v.lower() in dangerous_values:
            raise ValueError(
                f"{info.field_name} cannot be a default/weak value. "
                "Please use a strong, unique credential."
            )
        if len(v) < 12:
            raise ValueError(
                f"{info.field_name} must be at least 12 characters long"
            )
        return v

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key_strength(cls, v: str) -> str:
        """Ensure SECRET_KEY is strong enough"""
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long. "
                "Generate with: openssl rand -hex 32"
            )
        return v

    def get_admin_users(self) -> List[str]:
        """Get list of admin usernames from comma-separated string"""
        if not self.ADMIN_USERS:
            return []
        return [user.strip() for user in self.ADMIN_USERS.split(',') if user.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
