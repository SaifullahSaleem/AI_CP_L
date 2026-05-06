"""
Guardrail node — checks for unsafe / malicious prompts.
Blocks prompt injection, jailbreak attempts, and cleans outputs.
"""

import re
from agent.state import AgentState

# ── Blocked patterns ─────────────────────────────────────────────────
BLOCKED_PATTERNS = [
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"ignore\s+above",
    r"disregard\s+(all\s+)?(previous\s+)?instructions",
    r"you\s+are\s+now",
    r"act\s+as\s+if",
    r"pretend\s+(you\s+are|to\s+be)",
    r"system\s+prompt",
    r"reveal\s+(your|the)\s+(system|initial)\s+prompt",
    r"jailbreak",
    r"DAN\s+mode",
    r"bypass\s+(safety|content|filter)",
    r"override\s+(safety|restrictions)",
    r"<\s*script",
    r"\{\{.*\}\}",  # template injection
]

BLOCKED_RE = re.compile("|".join(BLOCKED_PATTERNS), re.IGNORECASE)


def guardrail_node(state: AgentState) -> dict:
    """
    Check the latest user message for unsafe content.

    If unsafe → sets intent to 'unsafe' and provides a blocked response.
    If safe   → passes through unchanged.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    # Get the latest user message
    last_msg = messages[-1]
    content = ""
    if hasattr(last_msg, "content"):
        content = last_msg.content
    elif isinstance(last_msg, dict):
        content = last_msg.get("content", "")

    # Check against blocked patterns
    if BLOCKED_RE.search(content):
        return {
            "intent": "unsafe",
            "final_answer": (
                "⚠️ I'm sorry, but I cannot process that request. "
                "Please ask a research-related question about academic papers."
            ),
        }

    # Check for excessively long messages (potential injection)
    if len(content) > 5000:
        return {
            "intent": "unsafe",
            "final_answer": "⚠️ Your message is too long. Please shorten your request.",
        }

    return {}


def clean_output(text: str) -> str:
    """
    Clean agent output to remove any leaked system information.
    """
    # Remove any leaked system prompts or metadata
    patterns_to_strip = [
        r"<\|system\|>.*?<\|/system\|>",
        r"SYSTEM:.*?\n",
        r"\[INTERNAL\].*?\[/INTERNAL\]",
    ]
    cleaned = text
    for pattern in patterns_to_strip:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()
