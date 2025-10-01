from sqlmodel import SQLModel, Field, Relationship, create_engine
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.core.config import settings

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["TransactionHistory"] = Relationship(back_populates="user")

class TradingAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: Decimal = Field(default=Decimal('1000000.00000000'), max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    symbol: str
    side: str
    order_type: str
    order_status: str = "PENDING"
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="orders")

class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id")
    symbol: str
    quantity: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    average_price: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    current_value: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    unrealized_profit: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    account: TradingAccount = Relationship(back_populates="positions")

class TransactionHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    symbol: str
    side: str
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    fee: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="transactions")

def create_db_and_tables():
    # 동기 SQLite 연결 사용
    sync_db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(sync_db_url, echo=True)
    SQLModel.metadata.create_all(engine)
