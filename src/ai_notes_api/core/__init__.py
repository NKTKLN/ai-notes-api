"""API core package.

This package re-exports core application objects and utilities.
"""

from ai_notes_api.core.config import settings
from ai_notes_api.core.logger import setup_logger
from ai_notes_api.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "settings",
    "setup_logger",
    "verify_password",
]
