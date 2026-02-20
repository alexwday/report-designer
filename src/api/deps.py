"""
Dependencies for Report Designer API.

Provides dependency injection for FastAPI routes.
"""

from typing import Annotated
from fastapi import Depends


def get_current_user() -> str:
    """
    Get the current user identifier.

    For MVP, returns hardcoded "dev_user".
    In production, this would validate JWT/session and return actual user.
    """
    return "dev_user"


# Type alias for dependency injection
CurrentUser = Annotated[str, Depends(get_current_user)]
