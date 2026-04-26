import json
from app.core.logging import get_logger
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import get_chat_service
from app.services.chat_service import ChatService


logger = get_logger(__name__)
chat_router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=36)
    message: str = Field(min_length=1, max_length=4000)


@chat_router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    async def event_generator():
        try:
            async for event in service.reply_stream(
                conversation_id=payload.conversation_id,
                message=payload.message,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            logger.exception("Error during chat stream for conversation '%s'", payload.conversation_id)
            yield f"data: {json.dumps({'type': 'error', 'message':'An internal error occured'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )