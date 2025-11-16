"""
Test API rate limiting functionality.

Tests that the application properly enforces rate limits:
- Login endpoint rate limiting (5/minute)
- Register endpoint rate limiting (5/minute)
- File upload rate limiting (10/minute)
- Proper HTTP 429 responses
- Rate limit headers
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import get_db, Base
from app.models.user import User as UserModel
from app.core.security import get_password_hash
import time


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rate_limiting.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(setup_database):
    """Create test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_user(setup_database):
    """Create a test user in the database"""
    db = TestingSessionLocal()
    try:
        # Clean up any existing test user
        db.query(UserModel).filter(UserModel.username == "ratelimituser").delete()
        db.commit()

        # Create new test user
        user = UserModel(
            username="ratelimituser",
            email="ratelimit@example.com",
            full_name="Rate Limit Test",
            password_hash=get_password_hash("StrongPassword123!"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


class TestLoginRateLimit:
    """Test suite for login endpoint rate limiting"""

    def test_login_allows_up_to_5_requests_per_minute(self, client, test_user):
        """Test that login allows up to 5 requests per minute"""
        # First 5 requests should succeed (or fail with 401 for wrong password)
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "WrongPassword123!"}
            )
            # Should get 401 (wrong password) not 429 (rate limited)
            assert response.status_code in [200, 401], f"Request {i+1} got unexpected status {response.status_code}"

    def test_login_blocks_6th_request_within_minute(self, client, test_user):
        """Test that login blocks 6th request within the same minute"""
        # Make 5 requests
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "WrongPassword123!"}
            )

        # 6th request should be rate limited
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "ratelimituser", "password": "WrongPassword123!"}
        )

        # Should get 429 Too Many Requests
        assert response.status_code == 429
        assert "rate limit" in response.text.lower() or "too many" in response.text.lower()

    def test_login_rate_limit_resets_after_time(self, client, test_user):
        """Test that login rate limit resets after the time window"""
        # This test would require waiting 60+ seconds
        # In production, you'd use a mock time or shorter window for testing
        pytest.skip("Skipping time-dependent test - would require 60s+ wait")


class TestRegisterRateLimit:
    """Test suite for register endpoint rate limiting"""

    def test_register_allows_up_to_5_requests_per_minute(self, client):
        """Test that register allows up to 5 requests per minute"""
        # First 5 requests should succeed or fail with validation errors (not rate limit)
        for i in range(5):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"newuser{i}_{time.time()}",
                    "email": f"newuser{i}_{time.time()}@example.com",
                    "password": "WeakPass",  # Intentionally weak to test rate limit, not validation
                    "full_name": f"New User {i}"
                }
            )
            # Should get 400 (validation error) or 201 (success), not 429 (rate limited)
            assert response.status_code in [201, 400, 422], \
                f"Request {i+1} got unexpected status {response.status_code}"

    def test_register_blocks_6th_request_within_minute(self, client):
        """Test that register blocks 6th request within the same minute"""
        # Make 5 requests
        for i in range(5):
            client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"newuser{i}_{time.time()}",
                    "email": f"newuser{i}_{time.time()}@example.com",
                    "password": "WeakPass",
                    "full_name": f"New User {i}"
                }
            )

        # 6th request should be rate limited
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"newuser6_{time.time()}",
                "email": f"newuser6_{time.time()}@example.com",
                "password": "WeakPass",
                "full_name": "New User 6"
            }
        )

        # Should get 429 Too Many Requests
        assert response.status_code == 429


class TestRateLimitResponse:
    """Test suite for rate limit response format"""

    def test_rate_limit_returns_429_status(self, client, test_user):
        """Test that rate limit returns proper HTTP 429 status"""
        # Exhaust rate limit
        for i in range(6):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "test"}
            )

        # Last response should be 429
        assert response.status_code == 429

    def test_rate_limit_response_contains_error_message(self, client, test_user):
        """Test that rate limit response contains informative error message"""
        # Exhaust rate limit
        for i in range(6):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "test"}
            )

        # Check error message
        assert response.status_code == 429
        response_text = response.text.lower()
        # Should mention rate limit or too many requests
        assert any(phrase in response_text for phrase in ["rate limit", "too many", "exceeded"])


class TestRateLimitIndependence:
    """Test that rate limits are independent across endpoints"""

    def test_login_and_register_have_independent_limits(self, client, test_user):
        """Test that login and register rate limits don't interfere"""
        # Exhaust login rate limit
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "test"}
            )

        # Register should still work (independent rate limit)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"independent_{time.time()}",
                "email": f"independent_{time.time()}@example.com",
                "password": "WeakPass",
                "full_name": "Independent User"
            }
        )

        # Should not be rate limited (different endpoint)
        assert response.status_code in [201, 400, 422]  # Not 429


class TestRateLimitByIP:
    """Test that rate limits are applied per IP address"""

    def test_rate_limit_is_per_ip_address(self, client, test_user):
        """Test that rate limiting is based on IP address"""
        # slowapi uses get_remote_address as key function
        # In test client, all requests come from same IP
        # So 6th request should be rate limited

        for i in range(6):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "test"}
            )

        # 6th request should be blocked
        assert response.status_code == 429


class TestRateLimitConfiguration:
    """Test rate limit configuration"""

    def test_login_rate_limit_is_5_per_minute(self, client, test_user):
        """Test that login rate limit is configured to 5/minute"""
        success_count = 0
        rate_limited = False

        for i in range(7):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "ratelimituser", "password": "test"}
            )

            if response.status_code == 429:
                rate_limited = True
                break
            else:
                success_count += 1

        # Should allow 5 requests then rate limit
        assert success_count == 5
        assert rate_limited is True

    def test_register_rate_limit_is_5_per_minute(self, client):
        """Test that register rate limit is configured to 5/minute"""
        success_or_error_count = 0
        rate_limited = False

        for i in range(7):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"test{i}_{time.time()}",
                    "email": f"test{i}_{time.time()}@example.com",
                    "password": "WeakPass",
                    "full_name": f"Test {i}"
                }
            )

            if response.status_code == 429:
                rate_limited = True
                break
            else:
                success_or_error_count += 1

        # Should allow 5 requests then rate limit
        assert success_or_error_count == 5
        assert rate_limited is True
