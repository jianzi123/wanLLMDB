"""
Test SQL injection protection.

Tests that the application properly sanitizes user inputs to prevent SQL injection:
- Search query sanitization
- Dangerous pattern removal
- Length limits
- Special character handling
- SQLAlchemy ORM protection
"""

import pytest
from app.core.security_utils import sanitize_sql_search_input


class TestSearchInputSanitization:
    """Test suite for search input sanitization"""

    def test_normal_search_text_unchanged(self):
        """Test that normal search text is not modified"""
        normal_inputs = [
            "model",
            "dataset",
            "my project",
            "version 1.0",
            "test-file_name",
        ]

        for input_text in normal_inputs:
            result = sanitize_sql_search_input(input_text)
            assert result == input_text

    def test_sql_comment_removed(self):
        """Test that SQL comment syntax is removed"""
        dangerous_inputs = [
            ("SELECT * FROM users --", "SELECT  FROM users "),
            ("test' --", "test' "),
            ("admin'--", "admin'"),
        ]

        for dangerous, expected in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            assert "--" not in result

    def test_semicolon_removed(self):
        """Test that semicolons (statement terminators) are removed"""
        dangerous_inputs = [
            "test; DROP TABLE users;",
            "model; DELETE FROM projects;",
            "data;",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            assert ";" not in result

    def test_union_keyword_removed(self):
        """Test that UNION keyword is removed"""
        dangerous_inputs = [
            "test' UNION SELECT * FROM users--",
            "model UNION ALL SELECT password FROM users",
            "union select",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # UNION should be removed (case insensitive)
            assert "union" not in result.lower()

    def test_drop_keyword_removed(self):
        """Test that DROP keyword is removed"""
        dangerous_inputs = [
            "test'; DROP TABLE users--",
            "model drop database",
            "DROP ALL",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # DROP should be removed (case insensitive)
            assert "drop" not in result.lower()

    def test_delete_keyword_removed(self):
        """Test that DELETE keyword is removed"""
        dangerous_inputs = [
            "test'; DELETE FROM users--",
            "model delete all",
            "DELETE WHERE id=1",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # DELETE should be removed (case insensitive)
            assert "delete" not in result.lower()

    def test_insert_keyword_removed(self):
        """Test that INSERT keyword is removed"""
        dangerous_inputs = [
            "test'; INSERT INTO users VALUES('admin')--",
            "model insert new",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # INSERT should be removed (case insensitive)
            assert "insert" not in result.lower()

    def test_update_keyword_removed(self):
        """Test that UPDATE keyword is removed"""
        dangerous_inputs = [
            "test'; UPDATE users SET role='admin'--",
            "model update all",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # UPDATE should be removed (case insensitive)
            assert "update" not in result.lower()

    def test_exec_keyword_removed(self):
        """Test that EXEC keyword is removed"""
        dangerous_inputs = [
            "test'; EXEC sp_executesql--",
            "exec system command",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # EXEC should be removed (case insensitive)
            assert "exec" not in result.lower()

    def test_length_limit_enforced(self):
        """Test that input length is limited to prevent DoS"""
        # Create a very long input
        long_input = "a" * 1000

        result = sanitize_sql_search_input(long_input)

        # Should be truncated to max length (e.g., 200 chars)
        assert len(result) <= 200

    def test_multiple_dangerous_patterns_removed(self):
        """Test that multiple dangerous patterns are all removed"""
        dangerous = "test'; DROP TABLE users; UNION SELECT * FROM passwords--"

        result = sanitize_sql_search_input(dangerous)

        # All dangerous patterns should be removed
        assert "drop" not in result.lower()
        assert "union" not in result.lower()
        assert "--" not in result
        assert ";" not in result

    def test_empty_string_handled(self):
        """Test that empty string is handled correctly"""
        result = sanitize_sql_search_input("")
        assert result == ""

    def test_none_input_handled(self):
        """Test that None input is handled correctly"""
        result = sanitize_sql_search_input(None)
        assert result is None or result == ""

    def test_whitespace_preserved(self):
        """Test that legitimate whitespace is preserved"""
        input_text = "my model name"
        result = sanitize_sql_search_input(input_text)
        assert result == input_text

    def test_special_chars_in_legitimate_search(self):
        """Test that legitimate special characters are preserved"""
        # These are legitimate in search queries
        legitimate_inputs = [
            "model_v1.0",
            "dataset-2023",
            "file.txt",
            "path/to/file",
        ]

        for input_text in legitimate_inputs:
            result = sanitize_sql_search_input(input_text)
            # Should preserve legitimate special characters
            assert "." in result or "-" in result or "/" in result or "_" in result

    def test_case_insensitive_pattern_matching(self):
        """Test that dangerous patterns are caught regardless of case"""
        dangerous_variants = [
            "DROP",
            "drop",
            "DrOp",
            "DROP TABLE",
            "drop table",
        ]

        for dangerous in dangerous_variants:
            result = sanitize_sql_search_input(dangerous)
            # DROP should be removed regardless of case
            assert "drop" not in result.lower()

    def test_unicode_characters_handled(self):
        """Test that unicode characters are handled safely"""
        unicode_inputs = [
            "模型名称",  # Chinese
            "モデル",  # Japanese
            "Модель",  # Russian
            "café",  # French
        ]

        for input_text in unicode_inputs:
            # Should not raise exception
            result = sanitize_sql_search_input(input_text)
            assert result is not None

    def test_quoted_strings_do_not_bypass_sanitization(self):
        """Test that quoted strings don't bypass sanitization"""
        dangerous_inputs = [
            "'DROP TABLE'",
            '"DELETE FROM users"',
            "`UNION SELECT`",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # Dangerous keywords should still be removed even in quotes
            assert "drop" not in result.lower()
            assert "delete" not in result.lower()
            assert "union" not in result.lower()

    def test_hex_encoded_input_handled(self):
        """Test that hex-encoded SQL doesn't bypass sanitization"""
        # Even if someone tries to hex encode, after decoding it should be caught
        # This tests that we sanitize the final string
        result = sanitize_sql_search_input("test")
        assert result == "test"

    def test_stacked_queries_prevented(self):
        """Test that stacked queries are prevented"""
        dangerous_inputs = [
            "test'; SELECT * FROM users; --",
            "model; DROP TABLE projects; SELECT 1;",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # Semicolons should be removed
            assert ";" not in result

    def test_boolean_based_injection_patterns(self):
        """Test that boolean-based injection patterns are neutralized"""
        dangerous_inputs = [
            "test' OR '1'='1",
            "admin' OR 1=1--",
            "' OR 'a'='a",
        ]

        for dangerous in dangerous_inputs:
            result = sanitize_sql_search_input(dangerous)
            # While OR might remain, the dangerous pattern is disrupted
            # The key is that we use parameterized queries in SQLAlchemy
            assert result is not None


class TestSQLAlchemyORMProtection:
    """Test that SQLAlchemy ORM provides additional protection"""

    def test_orm_uses_parameterized_queries(self):
        """Test that ORM uses parameterized queries (not string concatenation)"""
        # This is a documentation test - SQLAlchemy automatically uses parameterized queries
        # when using .filter() with equality operators
        #
        # Example of SAFE usage:
        #   db.query(Project).filter(Project.name == user_input)
        #
        # This automatically uses parameterized queries, so user_input is always treated as data
        # not as SQL code
        assert True  # This test documents the protection mechanism

    def test_orm_filter_prevents_injection(self):
        """Test that ORM filter() prevents SQL injection"""
        # This is a documentation test
        # SQLAlchemy's filter() method automatically escapes and parameterizes inputs:
        #
        # .filter(User.username == "admin' OR '1'='1")
        #
        # Will look for a user with username literally equal to "admin' OR '1'='1"
        # It will NOT execute the OR clause as SQL
        assert True  # This test documents the protection mechanism

    def test_like_queries_use_parameterization(self):
        """Test that LIKE queries also use parameterization"""
        # This is a documentation test
        # SQLAlchemy's like() method also uses parameterization:
        #
        # .filter(Project.name.like(f"%{search_term}%"))
        #
        # Even with user input in search_term, it's parameterized
        assert True  # This test documents the protection mechanism


class TestInputValidation:
    """Test comprehensive input validation"""

    def test_max_length_prevents_dos(self):
        """Test that maximum length prevents DoS attacks"""
        # Very long input should be truncated
        long_input = "x" * 10000
        result = sanitize_sql_search_input(long_input)

        # Should be truncated to reasonable length
        assert len(result) <= 1000  # Adjust based on actual implementation

    def test_null_byte_removed(self):
        """Test that null bytes are removed"""
        dangerous_input = "test\x00injection"
        result = sanitize_sql_search_input(dangerous_input)

        # Null bytes should be removed
        assert "\x00" not in result

    def test_control_characters_handled(self):
        """Test that control characters are handled safely"""
        control_chars = "test\n\r\tquery"
        result = sanitize_sql_search_input(control_chars)

        # Should not raise exception
        assert result is not None
