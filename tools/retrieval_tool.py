"""
Retrieval tool — queries Pinecone for relevant papers.
"""

from utils.embeddings import generate_query_embedding
from db.pinecone_client import query_vectors


def retrieve_papers(query: str, filters: dict | None = None, top_k: int = 10) -> list[dict]:
    """
    Retrieve relevant papers from Pinecone.

    Args:
        query: User query text
        filters: Optional Pinecone metadata filters
        top_k: Number of results

    Returns:
        List of paper dicts with similarity scores
    """
    query_embedding = generate_query_embedding(query)
    matches = query_vectors(query_embedding, filters=filters, top_k=top_k)

    papers = []
    for match in matches:
        meta = match.get("metadata", {})
        papers.append({
            "paper_id": meta.get("paper_id", match.get("id", "")),
            "title": meta.get("title", ""),
            "snippet": meta.get("snippet", ""),
            "link": meta.get("link", ""),
            "authors": meta.get("authors", ""),
            "year": meta.get("year", ""),
            "source": meta.get("source", ""),
            "score": match.get("score", 0.0),
        })

    return papers
