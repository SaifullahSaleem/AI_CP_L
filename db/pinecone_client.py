"""
Pinecone vector database client.
Handles connection, index creation, upsert, and query operations.
"""

from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings


# ── Globals ──────────────────────────────────────────────────────────
_pc: Pinecone | None = None
_index = None


def _get_client() -> Pinecone:
    """Lazy-init Pinecone client."""
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _pc


def get_index():
    """
    Return the Pinecone index, creating it if it doesn't exist yet.
    Uses serverless spec (AWS / us-east-1).
    Recreates the index if dimension has changed.
    """
    global _index
    if _index is not None:
        return _index

    pc = _get_client()
    index_name = settings.PINECONE_INDEX_NAME

    # Create index if it doesn't exist
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name in existing:
        # Check if dimension matches
        desc = pc.describe_index(index_name)
        if desc.dimension != settings.EMBEDDING_DIMENSION:
            print(f"[Pinecone] Index dimension mismatch ({desc.dimension} vs {settings.EMBEDDING_DIMENSION}). Recreating index...")
            pc.delete_index(index_name)
            import time
            time.sleep(2)
            existing = []

    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=settings.EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.PINECONE_CLOUD,
                region=settings.PINECONE_REGION,
            ),
        )

    _index = pc.Index(index_name)
    return _index


# ── Public helpers ───────────────────────────────────────────────────
def upsert_vectors(vectors: list[dict]):
    """
    Upsert vectors into Pinecone.

    Each item in `vectors` must have:
        id       – unique string id
        values   – list[float] embedding
        metadata – dict with paper_id, title, authors, year, source, topic
    """
    index = get_index()
    # Pinecone accepts batches of up to 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch)


def query_vectors(query_embedding: list[float], filters: dict | None = None, top_k: int = 10):
    """
    Query Pinecone for similar vectors.

    Returns list of matches with id, score, and metadata.
    """
    index = get_index()
    params = {
        "vector": query_embedding,
        "top_k": top_k,
        "include_metadata": True,
    }
    if filters:
        params["filter"] = filters

    results = index.query(**params)
    return results.get("matches", [])
