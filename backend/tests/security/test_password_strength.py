"""
Test password strength validation.

Tests that passwords meet security requirements:
- Minimum 12 characters
- Contains uppercase, lowercase, number, special character
- Rejects common weak passwords
"""

import pytest
from app.core.security_utils import validate_password_strength


class TestPasswordStrength:
    """Test suite for password strength validation"""

    def test_strong_password_accepted(self):
        """Test that a strong password is accepted"""
        strong_passwords = [
            "MySecureP@ssw0rd2024!",
            "C0mpl3x!P@ssw0rd",
            "Str0ng_Passw0rd#123",
            "Secur3!P@ss2024Word",
        ]

        for password in strong_passwords:
            # Should not raise any exception
            assert validate_password_strength(password) is True

    def test_too_short_password_rejected(self):
        """Test that passwords shorter than 12 characters are rejected"""
        short_passwords = [
            "Short1!",
            "P@ss1",
            "Weak123!",
        ]

        for password in short_passwords:
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(password)
            assert "12 characters" in str(exc_info.value)

    def test_no_uppercase_rejected(self):
        """Test that passwords without uppercase letters are rejected"""
        no_uppercase = [
            "nouppercase123!",
            "alllowercase1!",
            "weak_password_123!",
        ]

        for password in no_uppercase:
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(password)
            assert "uppercase" in str(exc_info.value).lower()

    def test_no_lowercase_rejected(self):
        """Test that passwords without lowercase letters are rejected"""
        no_lowercase = [
            "ALLUPPER123!",
            "NO_LOWER_CASE_123!",
        ]

        for password in no_lowercase:
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(password)
            assert "lowercase" in str(exc_info.value).lower()

    def test_no_number_rejected(self):
        """Test that passwords without numbers are rejected"""
        no_number = [
            "NoNumbersHere!",
            "OnlyLetters@Words",
        ]

        for password in no_number:
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(password)
            assert "number" in str(exc_info.value).lower()

    def test_no_special_char_rejected(self):
        """Test that passwords without special characters are rejected"""
        no_special = [
            "NoSpecialChars123",
            "OnlyAlphanumeric2024",
        ]

        for password in no_special:
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(password)
            assert "special" in str(exc_info.value).lower()

    def test_common_weak_passwords_rejected(self):
        """Test that common weak passwords are rejected"""
        # These passwords meet all complexity requirements but are still rejected
        # because they are in the weak password list
        # Only testing passwords that are 12+ characters (meet length requirement)
        common_weak = [
            "Password123!",  # 12 chars
            "Changeme123!",  # 12 chars
        ]

        for password in common_weak:
            with pytest.raises(ValueError) as exc_info:
                validate_password_strength(password)
            assert "too common" in str(exc_info.value).lower() or "common" in str(exc_info.value).lower()

    def test_password_with_all_requirements(self):
        """Test edge case: exactly 12 characters with all requirements"""
        # Exactly 12 characters: 1 upper, 1 lower, 1 number, 1 special
        password = "Abcdefgh1@xy"
        assert len(password) == 12
        assert validate_password_strength(password) is True

    def test_very_long_password_accepted(self):
        """Test that very long passwords are accepted"""
        # 50+ character password
        long_password = "ThisIsAVeryLongP@ssw0rd" * 3
        assert len(long_password) > 50
        assert validate_password_strength(long_password) is True

    def test_special_characters_variety(self):
        """Test that various special characters are accepted"""
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        for char in special_chars:
            password = f"StrongP@ss123{char}"
            assert validate_password_strength(password) is True
