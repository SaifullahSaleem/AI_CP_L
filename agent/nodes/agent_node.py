"""
Agent node — multi-agent brain of the system.
Contains Researcher (fetches papers) and Analyst (answers questions).
Uses Gemini LLM to classify intent and generate responses.
"""

import google.generativeai as genai
from app.core.config import settings
from agent.state import AgentState

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

_LLM_MODEL = "gemini-2.5-flash"


def _get_conversation_text(messages) -> str:
    """Extract plain text from message history for the LLM."""
    parts = []
    for msg in messages:
        if hasattr(msg, "content"):
            role = getattr(msg, "type", "user")
            parts.append(f"{role}: {msg.content}")
        elif isinstance(msg, dict):
            parts.append(f"{msg.get('role', 'user')}: {msg.get('content', '')}")
    return "\n".join(parts)


def _classify_intent(user_message: str, history_text: str, papers: list[dict]) -> str:
    """
    Use Gemini to classify the user's intent.

    Returns one of: new_topic, follow_up, paper_specific
    """
    model = genai.GenerativeModel(_LLM_MODEL)

    has_papers = len(papers) > 0
    paper_titles = ", ".join([p.get("title", "")[:60] for p in papers[:5]]) if has_papers else "none"

    prompt = f"""You are an intent classifier for a research paper assistant.

Classify the user's message into exactly ONE of these categories:
- new_topic: The user is asking about a NEW research topic, wants to find papers, or is starting a new line of inquiry
- follow_up: The user is asking a follow-up question about papers already retrieved
- paper_specific: The user is asking about a SPECIFIC paper (e.g. "summarize paper 1", "tell me about the second paper")

Context:
- Papers already loaded: {paper_titles}
- Conversation has papers: {has_papers}

Recent conversation:
{history_text[-1500:]}

User message: {user_message}

Reply with ONLY the category name (new_topic, follow_up, or paper_specific). Nothing else."""

    response = model.generate_content(prompt)
    intent = response.text.strip().lower().replace(" ", "_")

    # Validate
    if intent not in ("new_topic", "follow_up", "paper_specific"):
        # Default: if we have no papers yet → new_topic, else follow_up
        intent = "new_topic" if not has_papers else "follow_up"

    return intent


def _researcher_respond(user_message: str, papers: list[dict]) -> str:
    """
    Researcher agent: presents fetched papers to the user.
    """
    model = genai.GenerativeModel(_LLM_MODEL)

    papers_text = ""
    for i, p in enumerate(papers, 1):
        papers_text += f"\n{i}. **{p.get('title', 'Untitled')}**\n"
        papers_text += f"   Authors: {p.get('authors', 'N/A')}\n"
        papers_text += f"   Year: {p.get('year', 'N/A')}\n"
        papers_text += f"   Summary: {p.get('snippet', 'No abstract available')}\n"
        papers_text += f"   Link: {p.get('link', 'N/A')}\n"

    prompt = f"""You are a Research Assistant. The user asked: "{user_message}"

I found the following research papers:
{papers_text}

Provide a brief, helpful overview of these papers. Mention key themes and suggest which papers might be most relevant. 
Keep your response concise and well-formatted using markdown.
Number each paper clearly so the user can reference them (e.g., "Paper 1", "Paper 2")."""

    response = model.generate_content(prompt)
    return response.text


def _analyst_respond(user_message: str, papers: list[dict], history_text: str) -> str:
    """
    Analyst agent: answers questions using retrieved paper context.
    """
    model = genai.GenerativeModel(_LLM_MODEL)

    context = ""
    for i, p in enumerate(papers, 1):
        context += f"\nPaper {i}: {p.get('title', '')}\n"
        context += f"Abstract: {p.get('snippet', '')}\n"
        context += f"Authors: {p.get('authors', 'N/A')}, Year: {p.get('year', 'N/A')}\n"

    prompt = f"""You are a Research Analyst AI assistant. Answer the user's question using the research paper context below.

Paper Context:
{context}

Recent Conversation:
{history_text[-2000:]}

User Question: {user_message}

Instructions:
- Answer based on the paper context provided
- If the user refers to a paper by number (e.g., "paper 1"), use the corresponding paper
- Provide accurate, well-structured answers
- If you cannot answer from the given context, say so honestly
- Use markdown formatting for readability"""

    response = model.generate_content(prompt)
    return response.text


def agent_node(state: AgentState) -> dict:
    """
    Main agent node — classifies intent and decides next action.

    - new_topic    → sets tool_calls to ["search_papers"]
    - follow_up    → sets tool_calls to ["retrieve_papers"]
    - paper_specific → sets tool_calls to ["retrieve_papers"]
    """
    messages = state.get("messages", [])
    papers = state.get("papers", [])

    # Get the latest user message
    last_msg = messages[-1] if messages else None
    if not last_msg:
        return {"intent": "follow_up", "tool_calls": []}

    user_message = ""
    if hasattr(last_msg, "content"):
        user_message = last_msg.content
    elif isinstance(last_msg, dict):
        user_message = last_msg.get("content", "")

    # ── Fast path: no papers in state (always the case at request start) ──
    # Papers are not persisted between requests, so we use a heuristic:
    # - If user references a specific paper → retrieve from Pinecone
    # - Otherwise → always search SerpAPI for fresh papers
    if not papers:
        import re
        # Check if user is referencing a specific paper by number
        paper_ref = re.search(
            r'paper\s*#?\s*\d+|first\s+paper|second\s+paper|third\s+paper|'
            r'summarize\s+(paper|it|them|the)|compare\s+(the\s+)?papers|'
            r'these\s+papers|those\s+papers|the\s+papers\s+(above|listed|mentioned)',
            user_message, re.IGNORECASE
        )
        if paper_ref:
            return {
                "intent": "paper_specific",
                "tool_calls": ["retrieve_papers"],
            }
        # Default: treat as new topic → search SerpAPI
        return {
            "intent": "new_topic",
            "tool_calls": ["search_papers"],
        }

    # ── Slow path: papers loaded (mid-graph) — use LLM classifier ──
    history_text = _get_conversation_text(messages[:-1])  # exclude current
    intent = _classify_intent(user_message, history_text, papers)

    if intent == "new_topic":
        return {
            "intent": "new_topic",
            "tool_calls": ["search_papers"],
        }
    elif intent == "paper_specific":
        return {
            "intent": "paper_specific",
            "tool_calls": ["retrieve_papers"],
        }
    else:  # follow_up
        return {
            "intent": "follow_up",
            "tool_calls": ["retrieve_papers"],
        }


def generate_response(state: AgentState) -> dict:
    """
    Generate the final LLM response based on intent and available papers.
    Called by the response node after tools have run.
    """
    messages = state.get("messages", [])
    papers = state.get("papers", [])
    intent = state.get("intent", "follow_up")

    last_msg = messages[-1] if messages else None
    user_message = ""
    if last_msg:
        if hasattr(last_msg, "content"):
            user_message = last_msg.content
        elif isinstance(last_msg, dict):
            user_message = last_msg.get("content", "")

    history_text = _get_conversation_text(messages[:-1])

    if intent == "new_topic":
        answer = _researcher_respond(user_message, papers)
    else:
        answer = _analyst_respond(user_message, papers, history_text)

    return {"final_answer": answer}
