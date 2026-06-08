"""Security utilities module.

This module provides password hashing, password verification, and JWT access
token creation and decoding utilities.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from ai_notes_api.core import settings
from ai_notes_api.exceptions import InvalidTokenError

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash a raw password.

    Args:
        password (str): Raw password to hash.

    Returns:
        str: Hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a raw password against a hashed password.

    Args:
        plain_password (str): Raw password to verify.
        hashed_password (str): Hashed password to compare against.

    Returns:
        bool: True if the password is valid, otherwise False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject (str): Token subject, usually the user identifier.
        expires_delta (timedelta | None): Optional custom token lifetime.

    Returns:
        str: Encoded JWT access token.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token (str): Encoded JWT access token.

    Returns:
        dict[str, Any]: Decoded token payload.

    Raises:
        InvalidTokenError: If the token is invalid or cannot be decoded.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise InvalidTokenError() from exc
