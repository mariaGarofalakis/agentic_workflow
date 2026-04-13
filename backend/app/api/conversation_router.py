from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import get_conversation_service
from app.services.conversation_service import ConversationService

conversation_router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=36)
    title: str | None = Field(default=None, max_length=255)


class CreateConversationResponse(BaseModel):
    conversation_id: str
    user_id: str | None
    title: str | None


@conversation_router.post(
    "",
    response_model=CreateConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> CreateConversationResponse:
    try:
        conversation_id = await service.create_conversation(
            user_id=payload.user_id,
            title=payload.title,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CreateConversationResponse(
        conversation_id=conversation_id,
        user_id=payload.user_id,
        title=payload.title,
    )