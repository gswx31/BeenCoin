from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.schemas.alert import AlertCreate, AlertOut
from app.services.order_service import create_price_alert, get_user_alerts, delete_price_alert
from app.core.database import get_session
from app.routers.orders import get_current_user
from app.services.price_engine import price_engine
from typing import List

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_to_out(a) -> AlertOut:
    return AlertOut(
        id=a.id, symbol=a.symbol,
        target_price=a.target_price, condition=a.condition,
        is_active=a.is_active,
        triggered_at=str(a.triggered_at) if a.triggered_at else None,
        created_at=str(a.created_at), memo=a.memo,
    )


@router.post("/", response_model=AlertOut)
def create_alert(
    alert: AlertCreate,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = create_price_alert(
        session, current_user.id,
        alert.symbol, alert.target_price, alert.condition, alert.memo,
    )
    return _alert_to_out(result)


@router.get("/", response_model=List[AlertOut])
def list_alerts(
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return [_alert_to_out(a) for a in get_user_alerts(session, current_user.id)]


@router.delete("/{alert_id}")
def remove_alert(
    alert_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    delete_price_alert(session, current_user.id, alert_id)
    return {"detail": "Alert deleted"}


@router.get("/prices")
def get_live_prices():
    """Get latest cached prices for all symbols."""
    prices = price_engine.latest_prices
    return {symbol: str(price) for symbol, price in prices.items()}
