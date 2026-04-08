from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.core.database import get_session
from app.services.leaderboard_service import get_leaderboard

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/")
def leaderboard(sort_by: str = Query(default="profit"), session: Session = Depends(get_session)):
    return get_leaderboard(session, sort_by)
