# app/models/database.py
from sqlmodel import SQLModel, Field, Relationship, create_engine
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.core.config import settings
import os

class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["TransactionHistory"] = Relationship(back_populates="user")

class TradingAccount(SQLModel, table=True):
    __tablename__ = "tradingaccount"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: Decimal = Field(default=Decimal('1000000.00'), max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=8)
    
    # Relationships
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")

class Order(SQLModel, table=True):
    __tablename__ = "order"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    symbol: str = Field(max_length=20)
    side: str = Field(max_length=10)  # LONG or SHORT (선물)
    order_type: str = Field(max_length=10)  # MARKET or LIMIT
    order_status: str = Field(default="PENDING", max_length=20)
    
    # 선물 거래 필드
    leverage: int = Field(default=1)
    position_side: str = Field(max_length=10)  # OPEN or CLOSE
    
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    
    # 증거금
    margin: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="orders")


class Position(SQLModel, table=True):
    __tablename__ = "position"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id")
    symbol: str = Field(max_length=20)
    
    # 선물 거래 필드
    side: str = Field(max_length=10)  # LONG or SHORT
    leverage: int = Field(default=1)  # 레버리지 1~125
    quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    entry_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    
    # 마진 정보
    margin: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)  # 증거금
    liquidation_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)  # 청산가
    
    # 수익/손실
    unrealized_pnl: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)  # 미실현 손익
    realized_pnl: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)  # 실현 손익
    
    # 상태
    status: str = Field(default="OPEN", max_length=20)  # OPEN, CLOSED, LIQUIDATED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    # Relationships
    account: "TradingAccount" = Relationship(back_populates="positions")

class TransactionHistory(SQLModel, table=True):
    __tablename__ = "transactionhistory"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    symbol: str = Field(max_length=20)
    side: str = Field(max_length=10)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    fee: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="transactions")

def create_db_and_tables():
    """데이터베이스 및 테이블 생성"""
    # URL 정리 - Windows 경로 문제 해결
    db_url = settings.DATABASE_URL
    
    # aiosqlite를 sqlite로 변경
    if "sqlite+aiosqlite" in db_url:
        db_url = db_url.replace("sqlite+aiosqlite:", "sqlite:")
    
    # 경로 정규화 (Windows 호환)
    if db_url.startswith("sqlite:///"):
        # sqlite:///./file.db → sqlite:///file.db
        db_url = db_url.replace("sqlite:///./", "sqlite:///")
        # 현재 디렉토리 기준 절대 경로로 변경
        db_file = db_url.replace("sqlite:///", "")
        db_path = os.path.abspath(db_file)
        db_url = f"sqlite:///{db_path}"
    
    print(f"Creating database: {db_url}")
    
    try:
        engine = create_engine(
            db_url, 
            echo=True,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
        
        SQLModel.metadata.create_all(engine)
        print("✅ Database and tables created successfully!")
        
    except Exception as e:
        print(f"❌ Database creation error: {e}")
        raise