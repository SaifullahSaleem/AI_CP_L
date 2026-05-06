"""
Chat service — orchestrates the full chat flow.
Handles message persistence, agent execution, and streaming.
"""

import json
import asyncio
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import agent_graph
from db.firebase_client import save_chat, load_chat


async def handle_chat(message: str, thread_id: str) -> dict:
    """
    Full synchronous chat flow:
    1. Load chat history from Firebase
    2. Append user message
    3. Run agent graph
    4. Append AI response
    5. Save to Firebase
    6. Return response

    Args:
        message: User message text
        thread_id: Chat thread ID

    Returns:
        dict with answer, papers, status
    """
    # 1. Load existing chat from Firebase
    stored_messages = load_chat(thread_id)

    # Convert stored messages to LangChain format
    lc_messages = []
    for msg in stored_messages:
        if msg.get("role") == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # 2. Append user message
    lc_messages.append(HumanMessage(content=message))

    # 3. Build initial state
    initial_state = {
        "messages": lc_messages,
        "papers": [],
        "selected_paper": None,
        "tool_calls": [],
        "final_answer": "",
        "intent": "",
        "thread_id": thread_id,
    }

    # 4. Run agent graph
    result = await asyncio.to_thread(agent_graph.invoke, initial_state)

    # 5. Extract results
    final_answer = result.get("final_answer", "I couldn't generate a response.")
    papers = result.get("papers", [])

    # 6. Build papers response
    papers_response = None
    if papers:
        papers_response = [
            {
                "title": p.get("title", ""),
                "snippet": p.get("snippet", ""),
                "link": p.get("link", ""),
                "authors": p.get("authors", ""),
                "year": p.get("year", ""),
                "source": p.get("source", ""),
                "paper_id": p.get("paper_id", ""),
            }
            for p in papers
        ]

    # 7. Save updated chat to Firebase
    stored_messages.append({"role": "user", "content": message})
    stored_messages.append({"role": "assistant", "content": final_answer})
    save_chat(thread_id, stored_messages)

    return {
        "answer": final_answer,
        "papers": papers_response,
        "status": "success",
    }


async def handle_stream(message: str, thread_id: str):
    """
    Streaming chat flow using Server-Sent Events (SSE).
    Streams the response token-by-token.

    Yields:
        SSE-formatted chunks: data: {"token": "...", "done": false}
    """
    # Load history
    stored_messages = load_chat(thread_id)

    lc_messages = []
    for msg in stored_messages:
        if msg.get("role") == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    lc_messages.append(HumanMessage(content=message))

    initial_state = {
        "messages": lc_messages,
        "papers": [],
        "selected_paper": None,
        "tool_calls": [],
        "final_answer": "",
        "intent": "",
        "thread_id": thread_id,
    }

    # Run graph (non-streaming internally, stream the result)
    result = await asyncio.to_thread(agent_graph.invoke, initial_state)

    final_answer = result.get("final_answer", "")
    papers = result.get("papers", [])

    # Stream papers first if available
    if papers:
        papers_data = [
            {
                "title": p.get("title", ""),
                "snippet": p.get("snippet", ""),
                "link": p.get("link", ""),
                "authors": p.get("authors", ""),
                "year": p.get("year", ""),
                "source": p.get("source", ""),
                "paper_id": p.get("paper_id", ""),
            }
            for p in papers
        ]
        yield f"data: {json.dumps({'papers': papers_data, 'done': False})}\n\n"

    # Stream answer in chunks (simulate token streaming)
    words = final_answer.split(" ")
    chunk_size = 3  # Stream 3 words at a time
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        if i > 0:
            chunk = " " + chunk
        yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
        await asyncio.sleep(0.03)

    # Final done signal
    yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"

    # Save to Firebase
    stored_messages.append({"role": "user", "content": message})
    stored_messages.append({"role": "assistant", "content": final_answer})
    save_chat(thread_id, stored_messages)
