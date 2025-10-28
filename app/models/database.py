# app/models/database.py
"""
데이터베이스 모델 - 원래 구조로 복원
TradingAccount 단일 구조로 통합
UUID 기반 사용자 ID
"""
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import UniqueConstraint, Index, CheckConstraint, Column, Numeric, String
import uuid


# ========================================
# Enum 정의
# ========================================

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# ========================================
# 사용자 모델
# ========================================
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True)
    )
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")


# ========================================
# 거래 계정 (통합)
# ========================================

class TradingAccount(SQLModel, table=True):
    __tablename__ = "trading_accounts"
    
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_positive_balance'),
        CheckConstraint('total_profit >= -1000000', name='check_reasonable_profit'),
        Index('idx_user_balance', 'user_id', 'balance'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", unique=True, index=True)
    
    # 잔액 (balance로 통일)
    balance: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('1000000')  # 초기 잔액 100만원
    )
    total_profit: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")


# ========================================
# 포지션 (통합)
# ========================================

class Position(SQLModel, table=True):
    __tablename__ = "positions"
    
    __table_args__ = (
        UniqueConstraint('account_id', 'symbol', name='uix_account_symbol'),
        CheckConstraint('quantity >= 0', name='check_positive_quantity'),
        CheckConstraint('average_price >= 0', name='check_positive_price'),
        Index('idx_account_symbol', 'account_id', 'symbol'),
        Index('idx_symbol_quantity', 'symbol', 'quantity'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="trading_accounts.id", index=True)
    symbol: str = Field(max_length=20, index=True)
    
    quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    average_price: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    current_price: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    current_value: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    unrealized_profit: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    account: TradingAccount = Relationship(back_populates="positions")


# ========================================
# 주문
# ========================================

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_positive_order_quantity'),
        CheckConstraint('filled_quantity >= 0', name='check_positive_filled'),
        CheckConstraint('filled_quantity <= quantity', name='check_filled_not_exceed'),
        Index('idx_account_status', 'account_id', 'order_status'),
        Index('idx_symbol_created', 'symbol', 'created_at'),
        Index('idx_status_created', 'order_status', 'created_at'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="trading_accounts.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    
    symbol: str = Field(max_length=20, index=True)
    side: OrderSide
    order_type: OrderType
    order_status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    
    quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False)
    )
    price: Optional[Decimal] = Field(
        sa_column=Column(Numeric(20, 8), nullable=True),
        default=None
    )
    filled_quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    average_price: Optional[Decimal] = Field(
        sa_column=Column(Numeric(20, 8), nullable=True),
        default=None
    )
    fee: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    user: User = Relationship(back_populates="orders")
    transactions: List["Transaction"] = Relationship(back_populates="order")


# ========================================
# 거래 내역
# ========================================

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_positive_tx_quantity'),
        CheckConstraint('price > 0', name='check_positive_tx_price'),
        CheckConstraint('fee >= 0', name='check_non_negative_fee'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_order_timestamp', 'order_id', 'timestamp'),
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    
    symbol: str = Field(max_length=20, index=True)
    side: OrderSide
    
    quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False)
    )
    price: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False)
    )
    fee: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # 관계
    user: User = Relationship(back_populates="transactions")
    order: Order = Relationship(back_populates="transactions")


# ========================================
# 마이그레이션 헬퍼 함수
# ========================================

def create_all_tables():
    """모든 테이블 생성"""
    from app.core.database import engine
    SQLModel.metadata.create_all(engine)
    print("✅ 모든 테이블이 생성되었습니다")


def drop_all_tables():
    """모든 테이블 삭제"""
    from app.core.database import engine
    SQLModel.metadata.drop_all(engine)
    print("❌ 모든 테이블이 삭제되었습니다")