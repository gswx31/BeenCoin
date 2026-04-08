from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.database import get_session
from app.routers.orders import get_current_user
from app.services.analytics_service import get_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/")
def analytics(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_analytics(session, current_user.id)
