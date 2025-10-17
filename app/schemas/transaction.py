from pydantic import BaseModel
from decimal import Decimal

class TransactionOut(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    timestamp: str
