from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.database import get_session
from app.routers.orders import get_current_user
from app.services.achievement_service import get_user_achievements, get_achievement_list, check_and_award
from app.services.mission_service import get_daily_missions, claim_mission_reward

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
def my_achievements(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_user_achievements(session, current_user.id)


@router.get("/all")
def all_achievements():
    return get_achievement_list()


@router.post("/check")
def check_achievements(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    newly = check_and_award(session, current_user.id)
    return {"newly_unlocked": newly}


@router.get("/missions")
def my_missions(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_daily_missions(session, current_user.id)


@router.post("/missions/{mission_id}/claim")
def claim_reward(mission_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return claim_mission_reward(session, current_user.id, mission_id)
