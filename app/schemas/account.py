# app/schemas/account.py
from pydantic import BaseModel
from typing import List, Optional


class PositionOut(BaseModel):
    """포지션 출력 스키마 (주문 가능 수량 포함)"""
    id: int
    symbol: str
    quantity: float  # 총 보유 수량
    locked_quantity: float  # 미체결 주문에 묶인 수량
    available_quantity: float  # 주문 가능 수량 (quantity - locked_quantity)
    average_price: float  # 평균 매수가
    current_price: float  # 현재가
    current_value: float  # 현재 평가액 (quantity * current_price)
    unrealized_profit: float  # 미실현 손익
    profit_rate: float  # 수익률 (%)


class AccountSummary(BaseModel):
    """계정 요약"""
    balance: float  # USDT 잔액
    total_profit: float  # 실현 손익
    total_value: float  # 총 자산 (잔액 + 포지션 가치)
    profit_rate: float  # 총 수익률 (%)
    positions: List[PositionOut]  # 보유 포지션 목록


class TransactionOut(BaseModel):
    """거래 내역"""
    id: int
    order_id: Optional[int]
    symbol: str
    side: str  # BUY / SELL
    quantity: float
    price: float
    fee: float  # 수수료 (현재는 0)
    timestamp: str