# app/models/database.py
"""
Database models for BeenCoin API
"""
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import field_serializer

# Enums
class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

# User Model
class User(SQLModel, table=True):
    """User model"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    trading_account: Optional["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    positions: List["Position"] = Relationship(back_populates="user")

# Trading Account Model
class TradingAccount(SQLModel, table=True):
    """Trading account model"""
    __tablename__ = "trading_accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    balance: Decimal = Field(default=100000.0)  # Starting balance
    locked_balance: Decimal = Field(default=0.0)
    total_profit: Decimal = Field(default=0.0)
    total_volume: Decimal = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="trading_account")
    
    @field_serializer('balance', 'locked_balance', 'total_profit', 'total_volume')
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize Decimal fields"""
        if value is None:
            return None
        return f"{value:.8f}".rstrip('0').rstrip('.')

# Order Model
class Order(SQLModel, table=True):
    """Order model"""
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    symbol: str = Field(index=True)
    order_type: OrderType
    order_side: OrderSide
    order_status: OrderStatus = Field(default=OrderStatus.PENDING)
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    executed_quantity: Decimal = Field(default=0.0)
    executed_price: Optional[Decimal] = None
    fee: Decimal = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="orders")
    
    @field_serializer('quantity', 'price', 'stop_price', 'executed_quantity', 'executed_price', 'fee')
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize Decimal fields"""
        if value is None:
            return None
        return f"{value:.8f}".rstrip('0').rstrip('.')

# Position Model
class Position(SQLModel, table=True):
    """Position model"""
    __tablename__ = "positions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    symbol: str = Field(index=True)
    quantity: Decimal
    average_price: Decimal
    current_price: Optional[Decimal] = None
    unrealized_pnl: Decimal = Field(default=0.0)
    realized_pnl: Decimal = Field(default=0.0)
    position_status: PositionStatus = Field(default=PositionStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="positions")

# Transaction Model
class Transaction(SQLModel, table=True):
    """Transaction history model"""
    __tablename__ = "transactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    order_id: Optional[int] = Field(foreign_key="orders.id")
    transaction_type: str  # DEPOSIT, WITHDRAWAL, TRADE_BUY, TRADE_SELL, FEE
    amount: Decimal
    balance_after: Decimal
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Price Alert Model
class PriceAlert(SQLModel, table=True):
    """Price alert model"""
    __tablename__ = "price_alerts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    symbol: str
    target_price: Decimal
    condition: str  # ABOVE, BELOW
    is_active: bool = Field(default=True)
    triggered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)