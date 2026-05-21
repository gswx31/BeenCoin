from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlmodel import Session
from decimal import Decimal
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.routers.orders import get_current_user
from app.services.futures_service import open_position, close_position, get_user_positions

router = APIRouter(prefix="/futures", tags=["futures"])


class OpenPositionRequest(BaseModel):
    symbol: str
    side: str  # LONG / SHORT
    margin: Decimal = Field(gt=0)
    leverage: int = Field(ge=1, le=50)


@router.post("/open")
@limiter.limit("30/minute")
async def open_futures(
    request: Request,
    body: OpenPositionRequest,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    pos = await open_position(session, current_user.id, body.symbol, body.side.upper(),
                              body.margin, body.leverage)
    from app.services.futures_service import calculate_pnl
    return {
        "id": pos.id, "symbol": pos.symbol, "side": pos.side,
        "entry_price": float(pos.entry_price), "quantity": float(pos.quantity),
        "leverage": pos.leverage, "margin": float(pos.margin),
        "liquidation_price": float(pos.liquidation_price),
    }


@router.post("/close/{position_id}")
async def close_futures(position_id: int, current_user=Depends(get_current_user),
                         session: Session = Depends(get_session)):
    return await close_position(session, current_user.id, position_id)


@router.get("/positions")
def list_open_positions(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_user_positions(session, current_user.id, only_open=True)


@router.get("/history")
def list_closed_positions(current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    return get_user_positions(session, current_user.id, only_open=False)
