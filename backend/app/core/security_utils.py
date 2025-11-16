"""
Security utility functions for input validation and protection.
"""

from urllib.parse import urlparse
from typing import Set
import ipaddress


# Allowed URI schemes for external file references
ALLOWED_URI_SCHEMES: Set[str] = {'s3', 'gs', 'https'}  # No http, no file://

# Blocked hosts to prevent SSRF attacks
BLOCKED_HOSTS: Set[str] = {
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '169.254.169.254',  # AWS metadata service
    'metadata.google.internal',  # GCP metadata service
    '169.254.169.253',  # AWS Time Sync Service
}

# Private IP ranges (IPv4 and IPv6)
PRIVATE_IP_RANGES = [
    ipaddress.IPv4Network('10.0.0.0/8'),
    ipaddress.IPv4Network('172.16.0.0/12'),
    ipaddress.IPv4Network('192.168.0.0/16'),
    ipaddress.IPv4Network('127.0.0.0/8'),  # Loopback
    ipaddress.IPv4Network('169.254.0.0/16'),  # Link-local
    ipaddress.IPv6Network('::1/128'),  # IPv6 loopback
    ipaddress.IPv6Network('fc00::/7'),  # IPv6 private
]


def validate_reference_uri(uri: str) -> bool:
    """
    Validate external file reference URI to prevent SSRF attacks.

    Args:
        uri: The URI to validate

    Returns:
        True if valid

    Raises:
        ValueError: If URI is invalid or potentially dangerous
    """
    try:
        parsed = urlparse(uri)
    except Exception as e:
        raise ValueError(f"Invalid URI format: {e}")

    # Validate scheme
    if parsed.scheme not in ALLOWED_URI_SCHEMES:
        raise ValueError(
            f"Invalid URI scheme '{parsed.scheme}'. "
            f"Allowed schemes: {', '.join(ALLOWED_URI_SCHEMES)}"
        )

    # Validate hostname (only for https URIs, s3/gs don't have normal hostnames)
    if parsed.scheme == 'https' and parsed.hostname:
        # Check against blocked hosts
        if parsed.hostname.lower() in BLOCKED_HOSTS:
            raise ValueError(
                f"Cannot reference internal/metadata host: {parsed.hostname}"
            )

        # Check if it's a private IP address
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            for private_range in PRIVATE_IP_RANGES:
                if ip in private_range:
                    raise ValueError(
                        f"Cannot reference private IP address: {parsed.hostname}"
                    )
        except ValueError as e:
            # Not an IP address (domain name), continue with domain validation
            # But re-raise if it's our own validation error about private IPs
            if "Cannot reference private IP" in str(e):
                raise
            # Otherwise, hostname is a domain name which is OK
            pass

        # Check for localhost variations
        if 'localhost' in parsed.hostname.lower():
            raise ValueError("Cannot reference localhost")

        # Check for internal TLDs
        if parsed.hostname.endswith(('.local', '.internal', '.localhost')):
            raise ValueError(f"Cannot reference internal domain: {parsed.hostname}")

    # Additional validation for S3/GS URIs
    if parsed.scheme in ['s3', 'gs']:
        if not parsed.netloc or not parsed.path:
            raise ValueError(
                f"{parsed.scheme.upper()} URI must include bucket and path: "
                f"{parsed.scheme}://bucket-name/path/to/file"
            )

    return True


def sanitize_sql_search_input(search: str) -> str:
    """
    Sanitize search input to prevent SQL injection.

    Note: This is defense-in-depth. SQLAlchemy ORM should already prevent
    SQL injection, but this provides an additional safety layer.

    Args:
        search: User search input

    Returns:
        Sanitized search string
    """
    import re

    if not search:
        return ""

    sanitized = search

    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')

    # Remove SQL comment indicators (exact match, case-sensitive for special chars)
    sanitized = sanitized.replace('--', '')
    sanitized = sanitized.replace('/*', '')
    sanitized = sanitized.replace('*/', '')
    sanitized = sanitized.replace(';', '')

    # Remove dangerous SQL keywords (case-insensitive)
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'UNION', 'EXEC',
        'EXECUTE', 'SELECT', 'ALTER', 'CREATE', 'TRUNCATE'
    ]

    for keyword in dangerous_keywords:
        # Use regex for case-insensitive replacement
        # Use word boundaries to only match whole words
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        sanitized = pattern.sub('', sanitized)

    # Limit length to prevent DoS
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def validate_password_strength(password: str) -> bool:
    """
    Validate password meets security requirements.

    Args:
        password: Password to validate

    Returns:
        True if password is strong enough

    Raises:
        ValueError: If password doesn't meet requirements
    """
    import re

    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one number")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")

    # Check for common weak passwords
    weak_passwords = {
        'password123!', 'Password123!', 'Admin123!',
        'Welcome123!', 'Changeme123!', 'Qwerty123!'
    }
    if password in weak_passwords:
        raise ValueError("This password is too common. Please choose a stronger password.")

    return True
