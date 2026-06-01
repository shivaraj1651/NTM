"""
Fixtures for core module tests.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings to provide required configuration values."""
    settings_dict = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-minimum-32-characters-long-12345",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
        "REFRESH_TOKEN_EXPIRE_DAYS": 7,
    }

    # Set environment variables
    for key, value in settings_dict.items():
        os.environ[key] = str(value)

    yield

    # Cleanup
    for key in settings_dict.keys():
        if key in os.environ:
            del os.environ[key]
