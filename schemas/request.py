"""
Request schemas for the API.
"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    thread_id: str
