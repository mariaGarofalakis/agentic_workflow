from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TravelPreference, User
from app.db.session import get_db_session


travel_preferences_router = APIRouter(
    prefix="/travel-preferences",
    tags=["travel-preferences"],
)


class TravelPreferencesUpsertRequest(BaseModel):
    home_city: str | None = Field(default=None, max_length=255)
    home_airport: str | None = Field(default=None, max_length=16)
    budget_style: str | None = Field(default=None, max_length=64)
    pace: Literal["relaxed", "balanced", "packed"] | None = None
    dietary_needs: list[str] = Field(default_factory=list)


class TravelPreferencesResponse(BaseModel):
    user_id: str
    home_city: str | None
    home_airport: str | None
    budget_style: str | None
    pace: str | None
    dietary_needs: list[str]


@travel_preferences_router.get(
    "/{user_id}",
    response_model=TravelPreferencesResponse | None,
)
async def get_travel_preferences(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> TravelPreferencesResponse | None:
    result = await session.execute(
        select(TravelPreference).where(TravelPreference.user_id == user_id)
    )

    preferences = result.scalar_one_or_none()

    if preferences is None:
        return None

    return TravelPreferencesResponse(
        user_id=preferences.user_id,
        home_city=preferences.home_city,
        home_airport=preferences.home_airport,
        budget_style=preferences.budget_style,
        pace=preferences.pace,
        dietary_needs=preferences.dietary_needs,
    )


@travel_preferences_router.put(
    "/{user_id}",
    response_model=TravelPreferencesResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_travel_preferences(
    user_id: str,
    payload: TravelPreferencesUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TravelPreferencesResponse:
    user = await session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "not_found",
                "message": f"User '{user_id}' was not found.",
            },
        )

    result = await session.execute(
        select(TravelPreference).where(TravelPreference.user_id == user_id)
    )

    preferences = result.scalar_one_or_none()

    if preferences is None:
        preferences = TravelPreference(user_id=user_id)
        session.add(preferences)

    preferences.home_city = payload.home_city
    preferences.home_airport = payload.home_airport
    preferences.budget_style = payload.budget_style
    preferences.pace = payload.pace
    preferences.dietary_needs = payload.dietary_needs

    await session.commit()
    await session.refresh(preferences)

    return TravelPreferencesResponse(
        user_id=preferences.user_id,
        home_city=preferences.home_city,
        home_airport=preferences.home_airport,
        budget_style=preferences.budget_style,
        pace=preferences.pace,
        dietary_needs=preferences.dietary_needs,
    )