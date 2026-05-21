from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.database import get_session
from app.routers.orders import get_current_user
from app.services.bankruptcy_service import get_bankruptcy_status, apply_bankruptcy

router = APIRouter(prefix="/bankruptcy", tags=["bankruptcy"])


@router.get("/status")
def status(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_bankruptcy_status(session, current_user.id)


@router.post("/apply")
def apply(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return apply_bankruptcy(session, current_user.id)
