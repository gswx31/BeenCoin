# app/schemas/transaction.py
from pydantic import BaseModel


class TransactionOut(BaseModel):
    """거래 내역 응답"""
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    timestamp: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.001,
                "price": 50000.00,
                "fee": 0.0,
                "timestamp": "2025-10-17T12:00:00"
            }
        }