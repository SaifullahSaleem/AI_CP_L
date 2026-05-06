"""
Response schemas for the API.
"""

from typing import List, Optional
from pydantic import BaseModel


class PaperInfo(BaseModel):
    """Individual paper information."""
    title: str
    snippet: str = ""
    link: str = ""
    authors: str = ""
    year: str = ""
    source: str = ""
    paper_id: str = ""


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    papers: Optional[List[PaperInfo]] = None
    status: str = "success"
