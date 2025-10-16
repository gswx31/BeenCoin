# app/schemas/transaction.py
from pydantic import BaseModel

class TransactionOut(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    timestamp: str
    
    class Config:
        from_attributes = True