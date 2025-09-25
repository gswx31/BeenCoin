from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
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
    order_type: str
    order_status: str = "pending"
    price: Decimal = Field(max_digits=20, decimal_places=8)
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
    account: TradingAccount = Relationship(back_populates="positions")

def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)
