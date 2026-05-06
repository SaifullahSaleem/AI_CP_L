"""
Pinecone tool — stores papers as vectors in Pinecone.
"""

from utils.embeddings import generate_embedding
from db.pinecone_client import upsert_vectors


def store_papers(papers: list[dict]) -> int:
    """
    Generate embeddings for each paper and upsert into Pinecone.

    Args:
        papers: List of paper dicts from serp_tool

    Returns:
        Number of papers stored
    """
    vectors = []

    for paper in papers:
        # Build text for embedding (title + abstract/snippet)
        text = f"{paper.get('title', '')}. {paper.get('snippet', '')}"
        embedding = generate_embedding(text)

        vector = {
            "id": paper["paper_id"],
            "values": embedding,
            "metadata": {
                "paper_id": paper["paper_id"],
                "title": paper.get("title", ""),
                "authors": paper.get("authors", ""),
                "year": paper.get("year", ""),
                "source": paper.get("source", ""),
                "snippet": paper.get("snippet", ""),
                "link": paper.get("link", ""),
                "topic": paper.get("topic", "general"),
            },
        }
        vectors.append(vector)

    if vectors:
        upsert_vectors(vectors)

    return len(vectors)
