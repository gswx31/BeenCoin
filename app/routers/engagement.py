"""
참여 기능 통합 라우터: 출석, 티어, 시즌, 피드, 추천.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from app.core.database import get_session
from app.routers.orders import get_current_user
from app.services.tier_service import get_user_tier, get_tier_list
from app.services.checkin_service import get_checkin_status, do_checkin
from app.services.season_service import (
    get_current_season_info, get_hall_of_fame, get_season_rankings, get_or_create_current_season,
)
from app.services.feed_service import get_feed
from app.services.referral_service import get_referral_info, apply_referral

router = APIRouter(tags=["engagement"])


# -- 티어 --
@router.get("/tier/me")
def my_tier(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_user_tier(session, current_user.id)


@router.get("/tier/list")
def list_tiers():
    return get_tier_list()


# -- 출석 체크 --
@router.get("/checkin/status")
def checkin_status(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_checkin_status(session, current_user.id)


@router.post("/checkin")
def checkin(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return do_checkin(session, current_user.id)


# -- 시즌 --
@router.get("/seasons/current")
def current_season(session: Session = Depends(get_session)):
    return get_current_season_info(session)


@router.get("/seasons/hall-of-fame")
def hall_of_fame(session: Session = Depends(get_session)):
    return get_hall_of_fame(session)


@router.get("/seasons/{season_id}/rankings")
def season_rankings(season_id: int, session: Session = Depends(get_session)):
    return get_season_rankings(session, season_id)


# -- 활동 피드 --
@router.get("/feed")
def activity_feed(session: Session = Depends(get_session)):
    return get_feed(session, limit=50)


# -- 추천 코드 --
@router.get("/referral/me")
def my_referral(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_referral_info(session, current_user.id)


class ReferralRequest(BaseModel):
    code: str


@router.post("/referral/use")
def use_referral(body: ReferralRequest, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return apply_referral(session, current_user.id, body.code)
