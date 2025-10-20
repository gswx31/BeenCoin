
# ============================================
# app/services/portfolio_service_optimized.py
# ============================================
"""
최적화된 포트폴리오 서비스
"""
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from app.models.database import SpotAccount, SpotPosition, Transaction
from typing import Dict
import logging

logger = logging.getLogger(__name__)


async def get_portfolio_summary_optimized(session: Session, user_id: int) -> Dict:
    """
    N+1 쿼리 문제 해결
    - JOIN을 사용해 단일 쿼리로 처리
    """
    # 계정 + 포지션을 한 번에 로드
    account = session.exec(
        select(SpotAccount)
        .where(SpotAccount.user_id == user_id)
        .options(selectinload(SpotAccount.positions))  # Eager Loading
    ).first()
    
    if not account:
        return {
            "total_value": 0,
            "balance": 0,
            "positions_value": 0,
            "total_profit": 0,
            "profit_rate": 0
        }
    
    # 포지션 총 가치 계산
    positions_value = sum(
        float(pos.current_value) for pos in account.positions
    )
    
    total_value = float(account.usdt_balance) + positions_value
    profit_rate = (float(account.total_profit) / 1000000.0) * 100 if total_value > 0 else 0
    
    return {
        "total_value": total_value,
        "balance": float(account.usdt_balance),
        "positions_value": positions_value,
        "total_profit": float(account.total_profit),
        "profit_rate": profit_rate
    }
