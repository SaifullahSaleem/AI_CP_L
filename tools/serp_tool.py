"""
SERP tool for fetching research papers.
Uses SerpAPI Google Scholar to search for academic papers.
"""

import requests
from app.core.config import settings


def search_papers(query: str, num_results: int = 10) -> list[dict]:
    """
    Search for research papers using SerpAPI Google Scholar.

    Args:
        query: Search query string
        num_results: Number of results to return (default 10)

    Returns:
        List of paper dicts with title, snippet, link, authors, year, source
    """
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": settings.SERP_API_KEY,
        "num": num_results,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[SERP] Error fetching papers: {e}")
        return []

    papers = []
    organic = data.get("organic_results", [])

    for i, result in enumerate(organic[:num_results]):
        # Extract authors from publication_info
        pub_info = result.get("publication_info", {})
        authors = pub_info.get("summary", "").split(" - ")[0] if pub_info.get("summary") else ""

        # Try to extract year
        summary = pub_info.get("summary", "")
        year = ""
        for part in summary.replace(",", " ").split():
            if part.isdigit() and len(part) == 4:
                year = part
                break

        paper = {
            "paper_id": f"paper_{i}_{hash(result.get('title', '')) % 10000}",
            "title": result.get("title", "Untitled"),
            "snippet": result.get("snippet", ""),
            "link": result.get("link", ""),
            "authors": authors,
            "year": year,
            "source": result.get("source", result.get("displayed_link", "")),
        }
        papers.append(paper)

    return papers
