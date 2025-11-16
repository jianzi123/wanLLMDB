"""
Test credential validation security features.

Tests that the application properly validates MinIO and SECRET_KEY credentials
and rejects weak or default values.
"""

import pytest
from pydantic import ValidationError
from app.core.config import Settings


class TestCredentialValidation:
    """Test suite for credential validation"""

    def test_strong_minio_credentials_accepted(self, monkeypatch):
        """Test that strong MinIO credentials are accepted"""
        # Set environment variables with strong credentials
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)  # 32 characters
        monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setenv("MINIO_ACCESS_KEY", "strong-access-key-12-chars")
        monkeypatch.setenv("MINIO_SECRET_KEY", "strong-secret-key-12-chars")
        monkeypatch.setenv("TIMESCALE_URL", "sqlite:///./test.db")

        # Should not raise any exception
        settings = Settings()
        assert len(settings.MINIO_ACCESS_KEY) >= 12
        assert len(settings.MINIO_SECRET_KEY) >= 12

    def test_default_minioadmin_rejected(self, monkeypatch):
        """Test that default 'minioadmin' credentials are rejected"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
        monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
        monkeypatch.setenv("TIMESCALE_URL", "sqlite:///./test.db")

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "minioadmin" in str(exc_info.value).lower() or "default" in str(exc_info.value).lower()

    def test_short_minio_key_rejected(self, monkeypatch):
        """Test that MinIO keys shorter than 12 characters are rejected"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setenv("MINIO_ACCESS_KEY", "short")  # Only 5 chars
        monkeypatch.setenv("MINIO_SECRET_KEY", "short")
        monkeypatch.setenv("TIMESCALE_URL", "sqlite:///./test.db")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "12 characters" in str(exc_info.value)

    def test_weak_common_credentials_rejected(self, monkeypatch):
        """Test that common weak credentials are rejected"""
        weak_credentials = ["admin", "password", "root", "minio", "secret"]

        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setenv("TIMESCALE_URL", "sqlite:///./test.db")

        for weak_cred in weak_credentials:
            monkeypatch.setenv("MINIO_ACCESS_KEY", weak_cred)
            monkeypatch.setenv("MINIO_SECRET_KEY", weak_cred)

            with pytest.raises(ValidationError):
                Settings()

    def test_secret_key_minimum_length(self, monkeypatch):
        """Test that SECRET_KEY must be at least 32 characters"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("SECRET_KEY", "short")  # Less than 32 chars
        monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setenv("MINIO_ACCESS_KEY", "strong-access-key-12")
        monkeypatch.setenv("MINIO_SECRET_KEY", "strong-secret-key-12")
        monkeypatch.setenv("TIMESCALE_URL", "sqlite:///./test.db")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "32 characters" in str(exc_info.value)

    def test_database_pool_optimization(self, monkeypatch):
        """Test that database pool is optimized (50/20 instead of 20/10)"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
        monkeypatch.setenv("MINIO_ACCESS_KEY", "strong-access-key-12")
        monkeypatch.setenv("MINIO_SECRET_KEY", "strong-secret-key-12")
        monkeypatch.setenv("TIMESCALE_URL", "sqlite:///./test.db")

        settings = Settings()

        # Verify optimized pool settings
        assert settings.DATABASE_POOL_SIZE == 50
        assert settings.DATABASE_MAX_OVERFLOW == 20
        assert settings.DATABASE_POOL_RECYCLE == 3600
        assert settings.DATABASE_POOL_PRE_PING is True
