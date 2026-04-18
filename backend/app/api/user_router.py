from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.dependencies import get_user_service
from app.services.user_service import UserService

user_router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: EmailStr | None = Field(default=None)


class CreateUserResponse(BaseModel):
    user_id: str
    email: EmailStr | None


class ErrorDetailed(BaseModel):
    code: str
    message: str


@user_router.post(
    "",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: CreateUserRequest,
    service: UserService = Depends(get_user_service),
) -> CreateUserResponse:
    try:
        user_id = await service.create_user(email=payload.email)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetailed(code="conflict", message=str(exc)).model_dump(),
        ) from exc

    return CreateUserResponse(
        user_id=user_id,
        email=payload.email,
    )