"""
Custom exceptions for wanLLMDB SDK.
"""


class WanLLMDBError(Exception):
    """Base exception for wanLLMDB SDK."""
    pass


class APIError(WanLLMDBError):
    """API request failed."""
    pass


class AuthenticationError(WanLLMDBError):
    """Authentication failed."""
    pass


class ConfigurationError(WanLLMDBError):
    """Configuration error."""
    pass


class RunError(WanLLMDBError):
    """Run-related error."""
    pass
