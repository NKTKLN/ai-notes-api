"""Token schemas module.

This module defines Pydantic schemas used for authentication token responses.
"""

from pydantic import BaseModel, ConfigDict


class TokenResponseSchema(BaseModel):
    """Schema for returning an authentication token.

    Attributes:
        access_token (str): Access token used to authenticate API requests.
        token_type (str): Type of the returned token.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    access_token: str
    token_type: str
