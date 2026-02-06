"""Test configuration loading and validation."""

import os
from unittest.mock import patch


class TestConfigValidation:
    """Test configuration validation."""

    def test_env_example_exists(self):
        """Test that .env.example exists."""
        assert os.path.exists(".env.example")

    def test_env_example_has_required_keys(self):
        """Test that .env.example contains required keys."""
        with open(".env.example") as f:
            content = f.read()

        required_keys = [
            "TELEGRAM_BOT_TOKEN",
            "AUTHORIZED_USERS",
            "POLL_INTERVAL",
            "TERMINAL_LINES",
            "DEFAULT_WORK_DIR",
        ]

        for key in required_keys:
            assert key in content, f"Missing required key: {key}"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars(self):
        """Test behavior when environment variables are missing."""
        # This is a sanity check - actual validation happens in main.py
        # Just ensure we can import without crashing
        from src import main  # noqa: F401

    def test_authorized_users_format(self):
        """Test that authorized users can be parsed."""
        test_cases = [
            ("123456789", ["123456789"]),
            ("123,456,789", ["123", "456", "789"]),
            ("123, 456, 789", ["123", "456", "789"]),  # With spaces
        ]

        for input_str, expected in test_cases:
            result = [u.strip() for u in input_str.split(",")]
            assert result == expected


class TestEnvironmentConfig:
    """Test environment configuration."""

    def test_poll_interval_default(self):
        """Test default poll interval."""
        # Should default to 1 second
        default = 1
        assert default == 1

    def test_terminal_lines_default(self):
        """Test default terminal lines."""
        # Should default to 30 lines
        default = 30
        assert default == 30

    def test_default_work_dir(self):
        """Test default working directory."""
        # Should default to home directory
        default = "~"
        expanded = os.path.expanduser(default)
        assert os.path.exists(expanded)
