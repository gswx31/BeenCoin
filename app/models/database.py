from sqlmodel import SQLModel, Field, Relationship, create_engine
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")

class TradingAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: Decimal = Field(default=1000000, max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=0, max_digits=20, decimal_places=8)
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market' or 'limit'
    order_status: str = "pending"
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)  # for limit orders
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=0, max_digits=20, decimal_places=8)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="orders")

class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id")
    symbol: str
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    average_price: Decimal = Field(max_digits=20, decimal_places=8)
    current_value: Decimal = Field(max_digits=20, decimal_places=8)
    unrealized_profit: Decimal = Field(default=0, max_digits=20, decimal_places=8)
    account: TradingAccount = Relationship(back_populates="positions")

def create_db_and_tables():
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)
