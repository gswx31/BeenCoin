from fastapi import APIRouter, Depends
from app.schemas.account import AccountOut
from app.services.order_service import get_account_summary
from app.core.database import get_session
from app.routers.orders import get_current_user

router = APIRouter(prefix="/account", tags=["account"])

@router.get("/", response_model=AccountOut)
def get_account(current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    summary = get_account_summary(session, current_user.id)
    return AccountOut(**summary)
