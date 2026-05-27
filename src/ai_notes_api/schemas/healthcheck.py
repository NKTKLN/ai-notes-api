"""Healthcheck response schemas."""

from pydantic import BaseModel


class HealthcheckResponseSchema(BaseModel):
    """Schema for the healthcheck endpoint response.

    Attributes:
        status (str): Current service health status.
    """

    status: str
