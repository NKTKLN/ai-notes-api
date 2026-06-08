"""Security utilities module.

This module provides password hashing, password verification, and JWT access
token creation and decoding utilities.
"""

from passlib.context import CryptContext

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
