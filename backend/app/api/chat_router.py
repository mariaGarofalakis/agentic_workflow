import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service
from app.services.chat_service import ChatService
from pydantic import BaseModel, Field

chat_router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

@chat_router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    async def event_generator():
        try:
            async for chunk in service.reply_stream(payload.message):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )