"""
API routes for chat and streaming endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.request import ChatRequest
from schemas.response import ChatResponse
from services.chat_service import handle_chat, handle_stream

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Synchronous chat endpoint.
    Accepts a message and thread_id, returns full response.
    """
    result = await handle_chat(request.message, request.thread_id)
    return result


@router.post("/stream")
async def stream_endpoint(request: ChatRequest):
    """
    Streaming chat endpoint.
    Streams tokens from the agent as they are generated.
    """
    return StreamingResponse(
        handle_stream(request.message, request.thread_id),
        media_type="text/event-stream",
    )
