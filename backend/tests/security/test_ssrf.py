"""
Test SSRF (Server-Side Request Forgery) protection.

Tests that the application properly validates external file reference URIs
and blocks dangerous targets:
- AWS/GCP metadata services
- Private IP addresses
- Localhost
- Internal domains
- Dangerous schemes
"""

import pytest
from app.core.security_utils import validate_reference_uri


class TestSSRFProtection:
    """Test suite for SSRF protection"""

    def test_valid_s3_uri_accepted(self):
        """Test that valid S3 URIs are accepted"""
        valid_s3_uris = [
            "s3://my-bucket/path/to/file.txt",
            "s3://company-data/models/model.pkl",
            "s3://artifacts-bucket/version-1/weights.h5",
        ]

        for uri in valid_s3_uris:
            assert validate_reference_uri(uri) is True

    def test_valid_gs_uri_accepted(self):
        """Test that valid Google Cloud Storage URIs are accepted"""
        valid_gs_uris = [
            "gs://my-bucket/path/to/file.txt",
            "gs://company-data/models/model.pkl",
        ]

        for uri in valid_gs_uris:
            assert validate_reference_uri(uri) is True

    def test_valid_https_uri_accepted(self):
        """Test that valid HTTPS URIs are accepted"""
        valid_https_uris = [
            "https://example.com/file.txt",
            "https://cdn.example.com/data/model.pkl",
            "https://storage.googleapis.com/bucket/file",
            "https://8.8.8.8/public/file.txt",  # Public IP
        ]

        for uri in valid_https_uris:
            assert validate_reference_uri(uri) is True

    def test_http_scheme_rejected(self):
        """Test that HTTP (non-secure) scheme is rejected"""
        http_uris = [
            "http://example.com/file.txt",
            "http://169.254.169.254/metadata",
        ]

        for uri in http_uris:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "scheme" in str(exc_info.value).lower()

    def test_file_scheme_rejected(self):
        """Test that file:// scheme is rejected"""
        file_uris = [
            "file:///etc/passwd",
            "file:///c:/windows/system32/config/sam",
            "file://localhost/etc/hosts",
        ]

        for uri in file_uris:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "scheme" in str(exc_info.value).lower()

    def test_ftp_scheme_rejected(self):
        """Test that FTP scheme is rejected"""
        with pytest.raises(ValueError) as exc_info:
            validate_reference_uri("ftp://example.com/file.txt")
        assert "scheme" in str(exc_info.value).lower()

    def test_aws_metadata_service_blocked(self):
        """Test that AWS metadata service is blocked"""
        aws_metadata_uris = [
            "https://169.254.169.254/latest/meta-data/",
            "https://169.254.169.254/latest/dynamic/instance-identity/",
        ]

        for uri in aws_metadata_uris:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            # Should mention either IP or metadata
            error_msg = str(exc_info.value).lower()
            assert "169.254.169.254" in error_msg or "private" in error_msg or "internal" in error_msg

    def test_gcp_metadata_service_blocked(self):
        """Test that GCP metadata service is blocked"""
        gcp_uris = [
            "https://metadata.google.internal/computeMetadata/v1/",
            "https://metadata.google.internal/",
        ]

        for uri in gcp_uris:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "metadata.google.internal" in str(exc_info.value).lower()

    def test_localhost_blocked(self):
        """Test that localhost is blocked"""
        localhost_uris = [
            "https://localhost/file.txt",
            "https://localhost:8080/api/data",
            "https://LOCALHOST/file.txt",  # Case insensitive
        ]

        for uri in localhost_uris:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "localhost" in str(exc_info.value).lower()

    def test_127_0_0_1_blocked(self):
        """Test that 127.0.0.1 is blocked"""
        with pytest.raises(ValueError) as exc_info:
            validate_reference_uri("https://127.0.0.1/file.txt")
        error_msg = str(exc_info.value).lower()
        assert "127.0.0.1" in error_msg or "private" in error_msg or "internal" in error_msg

    def test_private_ip_10_x_blocked(self):
        """Test that 10.x.x.x private IP range is blocked"""
        private_ips = [
            "https://10.0.0.1/file.txt",
            "https://10.10.10.10/data",
            "https://10.255.255.255/api",
        ]

        for uri in private_ips:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "private" in str(exc_info.value).lower()

    def test_private_ip_172_16_blocked(self):
        """Test that 172.16.x.x - 172.31.x.x private IP range is blocked"""
        private_ips = [
            "https://172.16.0.1/file.txt",
            "https://172.20.0.1/data",
            "https://172.31.255.255/api",
        ]

        for uri in private_ips:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "private" in str(exc_info.value).lower()

    def test_private_ip_192_168_blocked(self):
        """Test that 192.168.x.x private IP range is blocked"""
        private_ips = [
            "https://192.168.0.1/file.txt",
            "https://192.168.1.1/router",
            "https://192.168.255.255/api",
        ]

        for uri in private_ips:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            assert "private" in str(exc_info.value).lower()

    def test_link_local_169_254_blocked(self):
        """Test that 169.254.x.x link-local range is blocked"""
        link_local_ips = [
            "https://169.254.0.1/file.txt",
            "https://169.254.100.100/data",
        ]

        for uri in link_local_ips:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            error_msg = str(exc_info.value).lower()
            assert "private" in error_msg or "169.254" in error_msg

    def test_internal_domain_blocked(self):
        """Test that internal domain TLDs are blocked"""
        internal_domains = [
            "https://server.local/file.txt",
            "https://api.internal/data",
            "https://service.localhost/api",
        ]

        for uri in internal_domains:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            error_msg = str(exc_info.value).lower()
            # Accept either "internal", "domain", or "localhost" in error message
            assert any(keyword in error_msg for keyword in ["internal", "domain", "localhost"])

    def test_s3_uri_requires_bucket_and_path(self):
        """Test that S3 URIs must include bucket and path"""
        invalid_s3_uris = [
            "s3://",
            "s3://bucket-only",
        ]

        for uri in invalid_s3_uris:
            with pytest.raises(ValueError) as exc_info:
                validate_reference_uri(uri)
            error_msg = str(exc_info.value).lower()
            assert "bucket" in error_msg or "path" in error_msg

    def test_public_ips_accepted(self):
        """Test that public IP addresses are accepted"""
        public_ips = [
            "https://8.8.8.8/file.txt",  # Google DNS
            "https://1.1.1.1/data",  # Cloudflare DNS
            "https://208.67.222.222/api",  # OpenDNS
        ]

        for uri in public_ips:
            assert validate_reference_uri(uri) is True

    def test_public_domains_accepted(self):
        """Test that public domains are accepted"""
        public_domains = [
            "https://storage.googleapis.com/bucket/file",
            "https://s3.amazonaws.com/bucket/file",
            "https://cdn.example.com/data/model.pkl",
        ]

        for uri in public_domains:
            assert validate_reference_uri(uri) is True
