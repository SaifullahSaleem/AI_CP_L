"""
Tool node — executes tool calls (search, store, retrieve).
"""

from agent.state import AgentState
from tools.serp_tool import search_papers
from tools.pinecone_tool import store_papers
from tools.retrieval_tool import retrieve_papers


def tool_node(state: AgentState) -> dict:
    """
    Execute the tool calls decided by the agent node.

    Supported tools:
        search_papers   → Fetch from SERP + store in Pinecone
        retrieve_papers → Query Pinecone for relevant papers
    """
    tool_calls = state.get("tool_calls", [])
    messages = state.get("messages", [])
    papers = state.get("papers", [])

    # Get user query
    last_msg = messages[-1] if messages else None
    user_query = ""
    if last_msg:
        if hasattr(last_msg, "content"):
            user_query = last_msg.content
        elif isinstance(last_msg, dict):
            user_query = last_msg.get("content", "")

    if "search_papers" in tool_calls:
        # Researcher flow: fetch papers → store in Pinecone
        fetched = search_papers(user_query)
        if fetched:
            store_papers(fetched)
        return {"papers": fetched, "tool_calls": []}

    elif "retrieve_papers" in tool_calls:
        # Retrieve from Pinecone
        intent = state.get("intent", "follow_up")

        filters = None
        # If paper_specific and we have papers, try to filter by paper_id
        if intent == "paper_specific" and papers:
            # Try to extract paper number from user message
            import re
            match = re.search(r"paper\s*(\d+)", user_query, re.IGNORECASE)
            if match:
                idx = int(match.group(1)) - 1  # 1-indexed
                if 0 <= idx < len(papers):
                    selected = papers[idx]
                    return {
                        "papers": papers,
                        "selected_paper": selected,
                        "tool_calls": [],
                    }

        retrieved = retrieve_papers(user_query, filters=filters)
        if retrieved:
            return {"papers": retrieved, "tool_calls": []}
        else:
            # No results in Pinecone — keep existing papers
            return {"tool_calls": []}

    return {"tool_calls": []}
