from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import redis

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize Redis client for token blacklist (lazy initialization)
_redis_client = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for token blacklist (lazy initialization)"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            _redis_client.ping()
        except Exception as e:
            # Log warning but don't fail - token blacklist is optional
            print(f"Warning: Redis connection failed: {e}")
            print("Token blacklist will be disabled")
            return None
    return _redis_client


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Bcrypt has a 72-byte limit, so we truncate if necessary.
    This is safe because we validate password strength separately.
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def revoke_token(token: str) -> bool:
    """
    Add token to blacklist (revoke it).

    Returns True if successfully blacklisted, False if Redis unavailable
    """
    redis_client = get_redis_client()
    if redis_client is None:
        print("Warning: Cannot blacklist token - Redis unavailable")
        return False

    try:
        payload = decode_token(token)
        if payload is None:
            return False  # Invalid token, can't blacklist

        # Calculate TTL (time until token expiration)
        exp = payload.get('exp')
        if exp:
            ttl = exp - int(datetime.utcnow().timestamp())
            if ttl > 0:
                # Add to blacklist with TTL (auto-expires when token would expire anyway)
                redis_client.setex(f"blacklist:{token}", ttl, "1")
                return True
        return False
    except Exception as e:
        print(f"Error blacklisting token: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if token is blacklisted.

    Returns True if blacklisted, False otherwise (including if Redis unavailable)
    """
    redis_client = get_redis_client()
    if redis_client is None:
        # If Redis is unavailable, we can't check blacklist
        # Default to allowing the token (fail-open for availability)
        return False

    try:
        return redis_client.exists(f"blacklist:{token}") > 0
    except Exception as e:
        print(f"Error checking token blacklist: {e}")
        return False  # Fail-open
