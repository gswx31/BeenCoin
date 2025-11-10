# app/routers/portfolio.py
"""
포트폴리오 API 라우터
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User
from app.services import portfolio_service
from typing import Optional
import logging

router = APIRouter(tags=["portfolio"])
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    포트폴리오 종합 요약
    - 총 자산, 실현/미실현 손익, 수익률
    """
    try:
        summary = await portfolio_service.get_portfolio_summary(session, current_user.id)
        return summary
    except Exception as e:
        logger.error(f"❌ 포트폴리오 요약 조회 실패: {e}")
        return {"error": "포트폴리오 요약 조회 실패"}


@router.get("/positions")
def get_positions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    포지션 상세 정보
    - 각 코인별 수익률, 평가손익, 보유 비중
    """
    try:
        positions = portfolio_service.get_position_details(session, current_user.id)
        return positions
    except Exception as e:
        logger.error(f"❌ 포지션 조회 실패: {e}")
        return []


@router.get("/transactions")
def get_transactions(
    symbol: Optional[str] = Query(None, description="코인 심볼 (예: BTCUSDT)"),
    side: Optional[str] = Query(None, description="거래 종류 (BUY/SELL)"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    거래 내역 조회 (필터링 및 페이지네이션)
    
    - symbol: 특정 코인만 조회
    - side: BUY 또는 SELL
    - limit: 한 번에 가져올 개수
    - offset: 페이지 오프셋
    """
    try:
        history = portfolio_service.get_transaction_history(
            session, current_user.id, symbol, side, limit, offset
        )
        return history
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        return {"total": 0, "transactions": []}


@router.get("/orders")
def get_orders(
    status: Optional[str] = Query(None, description="주문 상태 (PENDING/FILLED/CANCELLED/REJECTED/EXPIRED)"),
    symbol: Optional[str] = Query(None, description="코인 심볼"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    주문 내역 조회 (상태별 필터링)
    
    - status: 주문 상태로 필터링
    - symbol: 특정 코인만 조회
    """
    try:
        orders = portfolio_service.get_order_history(
            session, current_user.id, status, symbol, limit
        )
        return orders
    except Exception as e:
        logger.error(f"❌ 주문 내역 조회 실패: {e}")
        return []


@router.get("/performance")
def get_performance(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    성과 지표
    - 거래 횟수, 승률, 평균 수익률
    - 최대 손실/수익
    - 최고/최악의 거래
    """
    try:
        metrics = portfolio_service.get_performance_metrics(session, current_user.id)
        return metrics
    except Exception as e:
        logger.error(f"❌ 성과 지표 조회 실패: {e}")
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_profit_rate": 0,
            "max_profit": 0,
            "max_loss": 0
        }


@router.get("/daily-performance")
def get_daily_performance(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    일별 성과 추이 (차트용)
    
    - days: 최근 며칠간의 데이터
    """
    try:
        daily_data = portfolio_service.get_daily_performance(session, current_user.id, days)
        return daily_data
    except Exception as e:
        logger.error(f"❌ 일별 성과 조회 실패: {e}")
        return []