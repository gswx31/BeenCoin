# app/routers/alerts.py
"""
가격 알림 API 라우터 (신규 기능)
"""
from datetime import datetime
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.database import PriceAlert, User
from app.utils.security import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# ===== Schemas =====

class AlertCreate(BaseModel):
    """알림 생성 요청"""

    symbol: str = Field(..., description="거래 심볼")
    target_price: Decimal = Field(..., gt=0, description="목표 가격")
    condition: str = Field(..., description="ABOVE(이상) 또는 BELOW(이하)")

    class Config:
        json_schema_extra = {
            "example": {"symbol": "BTCUSDT", "target_price": "50000", "condition": "ABOVE"}
        }

class AlertOut(BaseModel):
    """알림 응답"""

    id: int
    user_id: str
    symbol: str
    target_price: Decimal
    condition: str
    is_active: bool
    is_triggered: bool
    created_at: datetime
    triggered_at: datetime | None

    class Config:
        from_attributes = True

# ===== API Endpoints =====

@router.post("/", response_model=AlertOut, status_code=201)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    가격 알림 생성

    예시:
    - BTC가 50,000달러 이상이 되면 알림
    - ETH가 3,000달러 이하로 떨어지면 알림
    """

    if alert_data.condition not in ["ABOVE", "BELOW"]:
        raise HTTPException(status_code=400, detail="condition must be ABOVE or BELOW")

    alert = PriceAlert(
        user_id=current_user.id,
        symbol=alert_data.symbol,
        target_price=alert_data.target_price,
        condition=alert_data.condition,
        is_active=True,
        is_triggered=False,
        created_at=datetime.utcnow(),
    )

    session.add(alert)
    session.commit()
    session.refresh(alert)

    logger.info(
        f"🔔 알림 생성: {alert.symbol} "
        f"{'≥' if alert.condition == 'ABOVE' else '≤'} ${alert.target_price}"
    )

    return alert

@router.get("/", response_model=list[AlertOut])
async def get_alerts(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """알림 목록 조회"""

    query = select(PriceAlert).where(PriceAlert.user_id == current_user.id)

    if active_only:
        query = query.where(PriceAlert.is_active is True, PriceAlert.is_triggered is False)

    alerts = session.exec(query.order_by(PriceAlert.created_at.desc())).all()

    return list(alerts)

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """알림 삭제"""

    alert = session.get(PriceAlert, alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")

    if alert.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="권한이 없습니다")

    session.delete(alert)
    session.commit()

    logger.info(f"🗑️ 알림 삭제: ID={alert_id}")

    return {"message": "알림이 삭제되었습니다"}

async def check_price_alerts(session: Session):
    """
    가격 알림 체크 (백그라운드 작업)

    - 주기적으로 실행 (예: 10초마다)
    - 조건 만족 시 알림 트리거
    """

    from app.services.binance_service import get_current_price

    try:
        # 활성 알림 조회
        alerts = session.exec(
            select(PriceAlert).where(PriceAlert.is_active is True, PriceAlert.is_triggered is False)
        ).all()

        for alert in alerts:
            current_price = await get_current_price(alert.symbol)

            triggered = False

            if alert.condition == "ABOVE" and current_price >= alert.target_price:
                triggered = True
            elif alert.condition == "BELOW" and current_price <= alert.target_price:
                triggered = True

            if triggered:
                alert.is_triggered = True
                alert.triggered_at = datetime.utcnow()
                session.add(alert)

                logger.info(
                    f"🔔 알림 트리거: {alert.symbol} "
                    f"${current_price} "
                    f"{'≥' if alert.condition == 'ABOVE' else '≤'} "
                    f"${alert.target_price}"
                )

                # 여기에 실제 알림 전송 로직 추가
                # (이메일, 푸시 알림 등)

        session.commit()

    except Exception as e:
        logger.error(f"❌ 가격 알림 체크 실패: {e}")
