# app/services/portfolio_service.py
"""
포트폴리오 관리 서비스 - UX 중심 기능
"""
from sqlmodel import Session, select, func
from app.models.database import (
    SpotAccount, SpotPosition, Transaction, Order,
    OrderStatus, OrderSide, TradingType
)
from app.services.binance_service import get_current_price
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


async def get_portfolio_summary(session: Session, user_id: int) -> Dict:
    """
    포트폴리오 종합 요약
    - 실시간 총 자산
    - 실현 손익
    - 미실현 손익
    - 수익률
    """
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == user_id)
    ).first()
    
    if not account:
        return {
            "total_value": 0,
            "cash_balance": 0,
            "positions_value": 0,
            "realized_profit": 0,
            "unrealized_profit": 0,
            "total_profit": 0,
            "return_rate": 0,
            "initial_balance": 1000000
        }
    
    # 포지션들의 현재 가치 및 미실현 손익 계산
    positions = session.exec(
        select(SpotPosition).where(SpotPosition.account_id == account.id)
    ).all()
    
    positions_value = Decimal('0')
    unrealized_profit = Decimal('0')
    
    for position in positions:
        if position.quantity > 0:
            try:
                current_price = await get_current_price(position.symbol)
                position.current_price = current_price
                position.current_value = position.quantity * current_price
                position.unrealized_profit = position.quantity * (current_price - position.average_price)
                
                positions_value += position.current_value
                unrealized_profit += position.unrealized_profit
                
                session.add(position)
            except Exception as e:
                logger.error(f"❌ 가격 업데이트 실패 {position.symbol}: {e}")
    
    session.commit()
    
    # 총 자산 = 현금 + 포지션 가치
    total_value = account.usdt_balance + positions_value
    
    # 초기 자본 (환경변수 또는 계정 생성 시 저장된 값)
    initial_balance = Decimal('1000000')  # 100만원
    
    # 총 손익 = 실현 손익 + 미실현 손익
    total_profit = account.total_profit + unrealized_profit
    
    # 수익률 계산
    return_rate = float((total_profit / initial_balance) * 100) if initial_balance > 0 else 0
    
    return {
        "total_value": float(total_value),
        "cash_balance": float(account.usdt_balance),
        "positions_value": float(positions_value),
        "realized_profit": float(account.total_profit),
        "unrealized_profit": float(unrealized_profit),
        "total_profit": float(total_profit),
        "return_rate": round(return_rate, 2),
        "initial_balance": float(initial_balance)
    }


def get_position_details(session: Session, user_id: int) -> List[Dict]:
    """
    포지션 상세 정보
    - 각 코인별 수익률
    - 평가손익
    - 보유 비중
    """
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == user_id)
    ).first()
    
    if not account:
        return []
    
    positions = session.exec(
        select(SpotPosition)
        .where(SpotPosition.account_id == account.id)
        .where(SpotPosition.quantity > 0)
    ).all()
    
    result = []
    total_value = Decimal('0')
    
    for pos in positions:
        position_value = pos.quantity * pos.current_price
        total_value += position_value
    
    for pos in positions:
        position_value = pos.quantity * pos.current_price
        invested_value = pos.quantity * pos.average_price
        profit = pos.unrealized_profit
        profit_rate = float((profit / invested_value) * 100) if invested_value > 0 else 0
        weight = float((position_value / total_value) * 100) if total_value > 0 else 0
        
        result.append({
            "symbol": pos.symbol,
            "quantity": float(pos.quantity),
            "average_price": float(pos.average_price),
            "current_price": float(pos.current_price),
            "invested_value": float(invested_value),
            "current_value": float(position_value),
            "unrealized_profit": float(profit),
            "profit_rate": round(profit_rate, 2),
            "weight": round(weight, 2)
        })
    
    return sorted(result, key=lambda x: x['current_value'], reverse=True)


def get_transaction_history(
    session: Session, 
    user_id: int,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict:
    """
    거래 내역 조회 (필터링 및 페이지네이션)
    """
    query = select(Transaction).where(Transaction.user_id == user_id)
    
    if symbol:
        query = query.where(Transaction.symbol == symbol)
    
    if side:
        query = query.where(Transaction.side == side)
    
    # 전체 개수
    count_query = select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
    if symbol:
        count_query = count_query.where(Transaction.symbol == symbol)
    if side:
        count_query = count_query.where(Transaction.side == side)
    
    total = session.exec(count_query).first()
    
    # 페이지네이션
    transactions = session.exec(
        query.order_by(Transaction.timestamp.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    
    result = []
    for tx in transactions:
        result.append({
            "id": tx.id,
            "symbol": tx.symbol,
            "side": tx.side,
            "quantity": float(tx.quantity),
            "price": float(tx.price),
            "total": float(tx.quantity * tx.price),
            "fee": float(tx.fee),
            "timestamp": tx.timestamp.isoformat()
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": result
    }


def get_order_history(
    session: Session,
    user_id: int,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """
    주문 내역 조회 (상태별 필터링)
    """
    query = select(Order).where(Order.user_id == user_id)
    
    if status:
        query = query.where(Order.status == status)
    
    if symbol:
        query = query.where(Order.symbol == symbol)
    
    orders = session.exec(
        query.order_by(Order.created_at.desc()).limit(limit)
    ).all()
    
    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side,
            "order_type": order.order_type,
            "status": order.status,
            "quantity": float(order.quantity),
            "price": float(order.price) if order.price else None,
            "filled_quantity": float(order.filled_quantity),
            "average_price": float(order.average_price) if order.average_price else None,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat()
        })
    
    return result


def get_performance_metrics(session: Session, user_id: int) -> Dict:
    """
    성과 지표
    - 거래 횟수
    - 승률
    - 평균 수익률
    - 최대 손실
    - 최대 수익
    """
    # 완료된 매도 거래만 (실현 손익 계산)
    sell_transactions = session.exec(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.side == OrderSide.SELL)
    ).all()
    
    if not sell_transactions:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_profit_rate": 0,
            "max_profit": 0,
            "max_loss": 0,
            "best_trade": None,
            "worst_trade": None
        }
    
    # 각 매도 거래에 대해 매수 평균가 찾기
    profits = []
    
    for sell_tx in sell_transactions:
        # 해당 심볼의 매수 거래들 찾기
        buy_transactions = session.exec(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .where(Transaction.symbol == sell_tx.symbol)
            .where(Transaction.side == OrderSide.BUY)
            .where(Transaction.timestamp < sell_tx.timestamp)
        ).all()
        
        if buy_transactions:
            # 평균 매수가 계산
            total_qty = sum(float(tx.quantity) for tx in buy_transactions)
            avg_buy_price = sum(float(tx.price * tx.quantity) for tx in buy_transactions) / total_qty if total_qty > 0 else 0
            
            # 수익률 계산
            profit_rate = ((float(sell_tx.price) - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0
            profit_amount = (float(sell_tx.price) - avg_buy_price) * float(sell_tx.quantity)
            
            profits.append({
                "symbol": sell_tx.symbol,
                "profit_rate": profit_rate,
                "profit_amount": profit_amount,
                "sell_price": float(sell_tx.price),
                "buy_price": avg_buy_price,
                "quantity": float(sell_tx.quantity),
                "timestamp": sell_tx.timestamp
            })
    
    if not profits:
        return {
            "total_trades": len(sell_transactions),
            "win_rate": 0,
            "avg_profit_rate": 0,
            "max_profit": 0,
            "max_loss": 0,
            "best_trade": None,
            "worst_trade": None
        }
    
    winning_trades = [p for p in profits if p['profit_amount'] > 0]
    win_rate = (len(winning_trades) / len(profits) * 100) if profits else 0
    avg_profit_rate = sum(p['profit_rate'] for p in profits) / len(profits)
    
    best_trade = max(profits, key=lambda x: x['profit_amount'])
    worst_trade = min(profits, key=lambda x: x['profit_amount'])
    
    return {
        "total_trades": len(profits),
        "winning_trades": len(winning_trades),
        "losing_trades": len(profits) - len(winning_trades),
        "win_rate": round(win_rate, 2),
        "avg_profit_rate": round(avg_profit_rate, 2),
        "max_profit": round(best_trade['profit_amount'], 2),
        "max_loss": round(worst_trade['profit_amount'], 2),
        "best_trade": {
            "symbol": best_trade['symbol'],
            "profit": round(best_trade['profit_amount'], 2),
            "profit_rate": round(best_trade['profit_rate'], 2),
            "timestamp": best_trade['timestamp'].isoformat()
        },
        "worst_trade": {
            "symbol": worst_trade['symbol'],
            "loss": round(worst_trade['profit_amount'], 2),
            "loss_rate": round(worst_trade['profit_rate'], 2),
            "timestamp": worst_trade['timestamp'].isoformat()
        }
    }


def get_daily_performance(session: Session, user_id: int, days: int = 30) -> List[Dict]:
    """
    일별 성과 추이 (차트용)
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 일별 거래 내역 집계
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.timestamp >= start_date)
        .order_by(Transaction.timestamp)
    ).all()
    
    # 일별로 그룹화
    daily_data = {}
    
    for tx in transactions:
        date_key = tx.timestamp.date().isoformat()
        
        if date_key not in daily_data:
            daily_data[date_key] = {
                "date": date_key,
                "buy_volume": 0,
                "sell_volume": 0,
                "trades": 0
            }
        
        if tx.side == OrderSide.BUY:
            daily_data[date_key]["buy_volume"] += float(tx.quantity * tx.price)
        else:
            daily_data[date_key]["sell_volume"] += float(tx.quantity * tx.price)
        
        daily_data[date_key]["trades"] += 1
    
    return sorted(daily_data.values(), key=lambda x: x['date'])