"""Database models base module.

This module defines the declarative base class used by all SQLAlchemy ORM
models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
