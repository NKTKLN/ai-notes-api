"""User schemas module.

This module defines Pydantic schemas used for user registration, login, and
responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateSchema(BaseModel):
    """Schema for creating a user.

    Attributes:
        email (EmailStr): User email address.
        password (str): Raw user password.
        username (str | None): Optional username.
    """

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
    )


class UserResponseSchema(BaseModel):
    """Schema for returning user data.

    Attributes:
        id (int): Unique user identifier.
        email (EmailStr): User email address.
        username (str | None): Optional username.
        is_active (bool): Whether the user account is active.
        created_at (datetime): Date and time when the user was created.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    email: EmailStr
    username: str | None
    is_active: bool
    created_at: datetime
