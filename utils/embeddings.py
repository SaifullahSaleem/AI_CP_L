"""
Embeddings utility using Google Gemini text-embedding-004.
"""

import google.generativeai as genai
from app.core.config import settings

# Configure the Gemini API key
genai.configure(api_key=settings.GOOGLE_API_KEY)

_MODEL = "models/gemini-embedding-001"


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 768-dimensional embedding for the given text
    using Gemini text-embedding-004.

    Args:
        text: Input text to embed

    Returns:
        List of floats (768-d vector)
    """
    result = genai.embed_content(
        model=_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


def generate_query_embedding(text: str) -> list[float]:
    """
    Generate an embedding optimized for queries / retrieval.

    Args:
        text: Query text

    Returns:
        List of floats (768-d vector)
    """
    result = genai.embed_content(
        model=_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]
