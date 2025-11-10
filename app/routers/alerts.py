# app/routers/alerts.py
"""
Price alert routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.database import get_session
from app.models.database import User, PriceAlert
from app.utils.security import get_current_user
from app.services.binance_service import get_current_price
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Price Alerts"])

class CreateAlertRequest(BaseModel):
    """Create alert request"""
    symbol: str
    target_price: Decimal
    condition: str  # ABOVE or BELOW

class AlertResponse(BaseModel):
    """Alert response"""
    id: int
    symbol: str
    target_price: Decimal
    condition: str
    is_active: bool
    triggered_at: datetime | None
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/", response_model=AlertResponse)
async def create_alert(
    request: CreateAlertRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a price alert"""
    
    if request.condition not in ["ABOVE", "BELOW"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Condition must be 'ABOVE' or 'BELOW'"
        )
    
    alert = PriceAlert(
        user_id=current_user.id,
        symbol=request.symbol,
        target_price=request.target_price,
        condition=request.condition
    )
    
    session.add(alert)
    session.commit()
    session.refresh(alert)
    
    return alert

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    active_only: bool = True,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's price alerts"""
    
    query = select(PriceAlert).where(PriceAlert.user_id == current_user.id)
    
    if active_only:
        query = query.where(PriceAlert.is_active == True)
    
    alerts = session.exec(query).all()
    return alerts

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a price alert"""
    
    alert = session.exec(
        select(PriceAlert).where(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == current_user.id
        )
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    session.delete(alert)
    session.commit()
    
    return {"message": "Alert deleted successfully"}

@router.put("/{alert_id}/deactivate")
async def deactivate_alert(
    alert_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a price alert"""
    
    alert = session.exec(
        select(PriceAlert).where(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == current_user.id
        )
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.is_active = False
    session.commit()
    session.refresh(alert)
    
    return alert

async def check_price_alerts(session: Session):
    """
    Check and trigger price alerts
    This should be called periodically by a background task
    """
    active_alerts = session.exec(
        select(PriceAlert).where(PriceAlert.is_active == True)
    ).all()
    
    for alert in active_alerts:
        try:
            current_price = await get_current_price(alert.symbol)
            
            should_trigger = False
            
            if alert.condition == "ABOVE":
                should_trigger = current_price >= float(alert.target_price)
            elif alert.condition == "BELOW":
                should_trigger = current_price <= float(alert.target_price)
            
            if should_trigger:
                alert.is_active = False
                alert.triggered_at = datetime.utcnow()
                session.commit()
                
                logger.info(
                    f"Price alert triggered for user {alert.user_id}: "
                    f"{alert.symbol} {alert.condition} {alert.target_price}"
                )
                
                # Here you would send notification to user
                # For now, just log it
        
        except Exception as e:
            logger.error(f"Failed to check alert {alert.id}: {e}")
            continue