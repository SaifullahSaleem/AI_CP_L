"""
LangGraph agent graph — wires together all nodes and edges.
"""

from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes.guardrail_node import guardrail_node
from agent.nodes.agent_node import agent_node
from agent.nodes.tool_node import tool_node
from agent.nodes.response_node import response_node
from agent.router import route_after_guardrail, route_after_agent


def build_graph():
    """
    Build and compile the agent graph.

    Flow:
        START → guardrail_node
                  ├─ unsafe   → response_node → END
                  └─ safe     → agent_node
                                  ├─ tool_call → tool_node → response_node → END
                                  └─ no tools  → response_node → END
    """
    graph = StateGraph(AgentState)

    # ── Add nodes ────────────────────────────────────────────────────
    graph.add_node("guardrail_node", guardrail_node)
    graph.add_node("agent_node", agent_node)
    graph.add_node("tool_node", tool_node)
    graph.add_node("response_node", response_node)

    # ── Set entry point ──────────────────────────────────────────────
    graph.set_entry_point("guardrail_node")

    # ── Add conditional edges ────────────────────────────────────────
    graph.add_conditional_edges(
        "guardrail_node",
        route_after_guardrail,
        {
            "response_node": "response_node",
            "agent_node": "agent_node",
        },
    )

    graph.add_conditional_edges(
        "agent_node",
        route_after_agent,
        {
            "tool_node": "tool_node",
            "response_node": "response_node",
        },
    )

    # ── Add fixed edges ──────────────────────────────────────────────
    graph.add_edge("tool_node", "response_node")
    graph.add_edge("response_node", END)

    # ── Compile ──────────────────────────────────────────────────────
    compiled = graph.compile()
    return compiled


# Pre-compiled graph singleton
agent_graph = build_graph()
