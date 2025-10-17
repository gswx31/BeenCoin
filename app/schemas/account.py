# app/schemas/account.py
from pydantic import BaseModel
from typing import List


class AccountOut(BaseModel):
    """계정 정보 응답"""
    balance: float
    total_profit: float
    
    class Config:
        schema_extra = {
            "example": {
                "balance": 1000000.00,
                "total_profit": 50000.00
            }
        }


class PositionOut(BaseModel):
    """포지션 정보"""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    current_value: float
    unrealized_profit: float


class AccountSummary(BaseModel):
    """계정 종합 정보"""
    balance: float
    total_profit: float
    positions: List[PositionOut]
    total_value: float