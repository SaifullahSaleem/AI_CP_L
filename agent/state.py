"""
Agent state definition for LangGraph.
Defines the shared state that flows through the agent graph.
"""

from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State shared across all agent nodes.

    messages       – Full conversation history (LangGraph message list)
    papers         – Papers fetched / retrieved in this turn
    selected_paper – A specific paper the user is asking about
    tool_calls     – Tool calls decided by the agent node
    final_answer   – The formatted answer to return
    intent         – Classified intent: new_topic | follow_up | paper_specific | unsafe
    thread_id      – Chat thread ID for persistence
    """

    messages: Annotated[list, add_messages]
    papers: list[dict]
    selected_paper: Optional[dict]
    tool_calls: list[str]
    final_answer: str
    intent: str
    thread_id: str
