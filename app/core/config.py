"""
Environment configuration loader.
Loads all API keys and settings from .env file.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # SerpAPI
    SERP_API_KEY: str = os.getenv("SERP_API_KEY", "")

    # Pinecone
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json"
    )

    # Redis (checkpoint / session state store)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Pinecone Index
    PINECONE_INDEX_NAME: str = "research-papers"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"

    # Embedding
    EMBEDDING_DIMENSION: int = 3072  # Gemini gemini-embedding-001


settings = Settings()
