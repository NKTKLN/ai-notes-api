"""Error response schemas module.

This module defines Pydantic schemas used for API error responses.
"""

from pydantic import BaseModel


class ErrorResponseSchema(BaseModel):
    """Schema for returning an API error response.

    Attributes:
        detail (str): Human-readable error message.
    """

    detail: str
