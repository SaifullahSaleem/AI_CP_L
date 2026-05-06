"""
Response node — formats the final output.
"""

from agent.state import AgentState
from agent.nodes.agent_node import generate_response
from agent.nodes.guardrail_node import clean_output
from langchain_core.messages import AIMessage


def response_node(state: AgentState) -> dict:
    """
    Generate and format the final response.

    1. If intent is 'unsafe', the guardrail already set final_answer — pass through.
    2. Otherwise, call generate_response to get the LLM answer.
    3. Clean the output and append as an AI message.
    """
    intent = state.get("intent", "")

    # If guardrail already blocked, just return
    if intent == "unsafe":
        answer = state.get("final_answer", "Request blocked.")
        return {
            "messages": [AIMessage(content=answer)],
            "final_answer": answer,
        }

    # Generate response using the agent's LLM
    result = generate_response(state)
    answer = clean_output(result.get("final_answer", "I couldn't generate a response."))

    return {
        "messages": [AIMessage(content=answer)],
        "final_answer": answer,
    }
