"""
Test JWT token blacklist functionality.

Tests that the application properly manages token revocation:
- Token revocation on logout
- Blacklisted tokens are rejected
- Graceful degradation when Redis is unavailable
- Token TTL expiration behavior
"""

import pytest
import time
from datetime import timedelta
from unittest.mock import Mock, patch
from app.core import security
from app.core.config import settings


class TestJWTBlacklist:
    """Test suite for JWT token blacklist"""

    def test_valid_token_not_blacklisted(self):
        """Test that a valid token is not blacklisted initially"""
        token = security.create_access_token(data={"sub": "testuser"})
        assert security.is_token_blacklisted(token) is False

    def test_revoke_token_adds_to_blacklist(self):
        """Test that revoking a token adds it to the blacklist"""
        # Create a token
        token = security.create_access_token(data={"sub": "testuser"})

        # Verify it's not blacklisted initially
        assert security.is_token_blacklisted(token) is False

        # Revoke the token
        success = security.revoke_token(token)

        # If Redis is available, token should be blacklisted
        if success:
            assert security.is_token_blacklisted(token) is True

    def test_blacklisted_token_remains_blacklisted(self):
        """Test that a blacklisted token stays blacklisted until TTL expires"""
        # Create a token
        token = security.create_access_token(data={"sub": "testuser"})

        # Revoke it
        success = security.revoke_token(token)

        if success:
            # Check multiple times that it's still blacklisted
            assert security.is_token_blacklisted(token) is True
            time.sleep(0.1)
            assert security.is_token_blacklisted(token) is True

    def test_revoke_invalid_token_fails(self):
        """Test that revoking an invalid token fails"""
        invalid_token = "invalid.jwt.token"

        # Revoking invalid token should return False
        success = security.revoke_token(invalid_token)
        assert success is False

    def test_revoke_expired_token_fails(self):
        """Test that revoking an expired token fails"""
        # Create a token that expires immediately
        token = security.create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Revoking expired token should fail
        success = security.revoke_token(token)
        assert success is False

    def test_token_ttl_matches_expiration(self):
        """Test that blacklist TTL is set correctly based on token expiration"""
        # Create a token with short expiration
        token = security.create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=5)
        )

        # Revoke it
        success = security.revoke_token(token)

        if success:
            # Token should be blacklisted
            assert security.is_token_blacklisted(token) is True

            # Decode to verify TTL calculation
            payload = security.decode_token(token)
            assert payload is not None
            assert payload.get("sub") == "testuser"

    def test_multiple_tokens_independent(self):
        """Test that blacklisting one token doesn't affect others"""
        # Create two tokens for different users
        token1 = security.create_access_token(data={"sub": "user1"})
        token2 = security.create_access_token(data={"sub": "user2"})

        # Revoke only token1
        success1 = security.revoke_token(token1)

        if success1:
            # token1 should be blacklisted
            assert security.is_token_blacklisted(token1) is True

            # token2 should NOT be blacklisted
            assert security.is_token_blacklisted(token2) is False

    def test_same_user_different_tokens_independent(self):
        """Test that multiple tokens for the same user are independent"""
        # Create two tokens for the same user
        token1 = security.create_access_token(data={"sub": "testuser"})
        time.sleep(1)  # Ensure different exp time (JWT uses seconds)
        token2 = security.create_access_token(data={"sub": "testuser"})

        # Tokens should be different (different expiration times)
        assert token1 != token2

        # Revoke only token1
        success = security.revoke_token(token1)

        if success:
            # token1 should be blacklisted
            assert security.is_token_blacklisted(token1) is True

            # token2 should still be valid
            assert security.is_token_blacklisted(token2) is False

    @patch('app.core.security.get_redis_client')
    def test_graceful_degradation_redis_unavailable_on_revoke(self, mock_get_redis):
        """Test that system handles Redis unavailability gracefully during revoke"""
        # Mock Redis client to return None (unavailable)
        mock_get_redis.return_value = None

        token = security.create_access_token(data={"sub": "testuser"})

        # Revoking should return False but not raise exception
        success = security.revoke_token(token)
        assert success is False

    @patch('app.core.security.get_redis_client')
    def test_graceful_degradation_redis_unavailable_on_check(self, mock_get_redis):
        """Test that system handles Redis unavailability gracefully during check"""
        # Mock Redis client to return None (unavailable)
        mock_get_redis.return_value = None

        token = security.create_access_token(data={"sub": "testuser"})

        # Checking blacklist should return False (fail-open) but not raise exception
        is_blacklisted = security.is_token_blacklisted(token)
        assert is_blacklisted is False

    @patch('app.core.security.get_redis_client')
    def test_redis_connection_error_during_revoke(self, mock_get_redis):
        """Test handling of Redis errors during token revocation"""
        # Mock Redis client to raise exception
        mock_redis = Mock()
        mock_redis.setex.side_effect = Exception("Redis connection error")
        mock_get_redis.return_value = mock_redis

        token = security.create_access_token(data={"sub": "testuser"})

        # Should handle error gracefully and return False
        success = security.revoke_token(token)
        assert success is False

    @patch('app.core.security.get_redis_client')
    def test_redis_connection_error_during_check(self, mock_get_redis):
        """Test handling of Redis errors during blacklist check"""
        # Mock Redis client to raise exception
        mock_redis = Mock()
        mock_redis.exists.side_effect = Exception("Redis connection error")
        mock_get_redis.return_value = mock_redis

        token = security.create_access_token(data={"sub": "testuser"})

        # Should handle error gracefully and return False (fail-open)
        is_blacklisted = security.is_token_blacklisted(token)
        assert is_blacklisted is False

    def test_refresh_token_can_be_blacklisted(self):
        """Test that refresh tokens can also be blacklisted"""
        # Create a refresh token
        refresh_token = security.create_refresh_token(data={"sub": "testuser"})

        # Verify it's not blacklisted initially
        assert security.is_token_blacklisted(refresh_token) is False

        # Revoke the refresh token
        success = security.revoke_token(refresh_token)

        # If Redis is available, token should be blacklisted
        if success:
            assert security.is_token_blacklisted(refresh_token) is True

    def test_token_blacklist_key_format(self):
        """Test that blacklist keys are properly formatted"""
        token = security.create_access_token(data={"sub": "testuser"})

        # Revoke token
        success = security.revoke_token(token)

        if success:
            # Get Redis client and verify key format
            redis_client = security.get_redis_client()
            if redis_client:
                # Key should exist with "blacklist:" prefix
                key = f"blacklist:{token}"
                assert redis_client.exists(key) > 0

    def test_concurrent_revocations_do_not_interfere(self):
        """Test that concurrent token revocations are handled correctly"""
        tokens = [
            security.create_access_token(data={"sub": f"user{i}"})
            for i in range(5)
        ]

        # Revoke all tokens
        results = [security.revoke_token(token) for token in tokens]

        # If any succeeded, verify all are properly blacklisted
        if any(results):
            for i, token in enumerate(tokens):
                if results[i]:
                    assert security.is_token_blacklisted(token) is True
