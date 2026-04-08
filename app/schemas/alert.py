from pydantic import BaseModel, validator
from decimal import Decimal
from typing import Optional
from app.core.config import settings


class AlertCreate(BaseModel):
    symbol: str
    target_price: Decimal
    condition: str  # ABOVE / BELOW
    memo: str = ""

    @validator('symbol')
    def validate_symbol(cls, v):
        if v.upper() not in settings.SUPPORTED_SYMBOLS:
            raise ValueError(f'Unsupported symbol: {v}')
        return v.upper()

    @validator('condition')
    def validate_condition(cls, v):
        if v.upper() not in ('ABOVE', 'BELOW'):
            raise ValueError('Condition must be ABOVE or BELOW')
        return v.upper()


class AlertOut(BaseModel):
    id: int
    symbol: str
    target_price: Decimal
    condition: str
    is_active: bool
    triggered_at: Optional[str] = None
    created_at: str
    memo: str
