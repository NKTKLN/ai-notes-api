"""Status response schemas."""

from pydantic import BaseModel


class StatusResponseSchema(BaseModel):
    """Schema for the status response.

    Attributes:
        status (str): Current status.
    """

    status: str
