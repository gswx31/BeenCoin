# app/schemas/account.py
"""
계정 관련 스키마 - 수정 버전
locked_balance 필드 추가
"""
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional


class AccountOut(BaseModel):
    """계정 정보 응답"""
    id: int
    user_id: str
    balance: float = Field(..., description="사용 가능한 잔액")
    locked_balance: float = Field(..., description="주문에 걸린 금액")
    total_balance: float = Field(..., description="총 잔액 (balance + locked_balance)")
    available_balance: float = Field(..., description="구매 가능 금액 (balance와 동일)")
    total_profit: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PositionOut(BaseModel):
    """포지션 응답"""
    id: int
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    current_value: float
    unrealized_profit: float
    profit_percent: float = Field(..., description="수익률 (%)")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class TransactionOut(BaseModel):
    """거래 내역 응답"""
    id: int
    order_id: int
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    realized_profit: Optional[float] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class AccountSummary(BaseModel):
    """계정 요약"""
    account: AccountOut
    positions: List[PositionOut]
    total_asset_value: float = Field(..., description="총 자산 평가액")
    total_unrealized_profit: float = Field(..., description="총 미실현 손익")
    return_rate: float = Field(..., description="총 수익률 (%)")


class TradingStats(BaseModel):
    """거래 통계"""
    total_trades: int = Field(..., description="총 거래 횟수")
    win_trades: int = Field(..., description="수익 거래 수")
    lose_trades: int = Field(..., description="손실 거래 수")
    win_rate: float = Field(..., description="승률 (%)")
    total_profit: float = Field(..., description="총 실현 손익")
    average_profit_per_trade: float = Field(..., description="거래당 평균 수익")
    largest_profit: float = Field(..., description="최대 수익")
    largest_loss: float = Field(..., description="최대 손실")