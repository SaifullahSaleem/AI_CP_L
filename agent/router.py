"""
Router — conditional edge logic for the agent graph.
"""

from agent.state import AgentState


def route_after_guardrail(state: AgentState) -> str:
    """
    Route after the guardrail node.

    - unsafe → response_node (return blocked message)
    - else   → agent_node (continue processing)
    """
    intent = state.get("intent", "")
    if intent == "unsafe":
        return "response_node"
    return "agent_node"


def route_after_agent(state: AgentState) -> str:
    """
    Route after the agent node.

    - has tool_calls → tool_node
    - else           → response_node
    """
    tool_calls = state.get("tool_calls", [])
    if tool_calls:
        return "tool_node"
    return "response_node"
