# app/models/database.py
"""
데이터베이스 모델 정의 - 수정 버전
주문 금액 락(locked_balance) 기능 추가
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
import uuid


# =====================================================
# Enums
# =====================================================

class OrderSide(str, Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """주문 타입"""
    MARKET = "MARKET"  # 시장가
    LIMIT = "LIMIT"    # 지정가
    STOP_LOSS = "STOP_LOSS"  # 손절
    TAKE_PROFIT = "TAKE_PROFIT"  # 익절


class OrderStatus(str, Enum):
    """주문 상태"""
    PENDING = "PENDING"      # 대기 중
    FILLED = "FILLED"        # 체결 완료
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 부분 체결
    CANCELLED = "CANCELLED"  # 취소됨
    REJECTED = "REJECTED"    # 거부됨


# =====================================================
# 사용자 모델
# =====================================================

class User(SQLModel, table=True):
    """사용자"""
    __tablename__ = "users"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    trading_account: Optional["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")


# =====================================================
# 거래 계정 모델 (수정)
# =====================================================

class TradingAccount(SQLModel, table=True):
    """
    거래 계정 - locked_balance 추가
    
    - balance: 사용 가능한 잔액
    - locked_balance: 미체결 주문에 걸려있는 금액
    - total_balance: balance + locked_balance (계산 필드)
    """
    __tablename__ = "trading_accounts"
    
    id: int = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True, unique=True)
    
    # 잔액 정보
    balance: Decimal = Field(
        default=Decimal("100000"),  # ✅ 100,000 USDT로 변경
        max_digits=20,
        decimal_places=8,
        description="사용 가능한 잔액"
    )
    locked_balance: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="주문에 걸려있는 금액 (미체결 주문)"
    )
    
    # 수익 정보
    total_profit: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="trading_account")
    positions: List["Position"] = Relationship(back_populates="account")
    
    @property
    def total_balance(self) -> Decimal:
        """총 잔액 = 사용가능 + 락"""
        return self.balance + self.locked_balance
    
    @property
    def available_balance(self) -> Decimal:
        """구매 가능 금액 (balance와 동일하지만 명시적)"""
        return self.balance


# =====================================================
# 주문 모델
# =====================================================

class Order(SQLModel, table=True):
    """주문"""
    __tablename__ = "orders"
    
    id: int = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="trading_accounts.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    
    # 주문 정보
    symbol: str = Field(index=True, max_length=20)
    side: OrderSide = Field(index=True)
    order_type: OrderType = Field(index=True)
    order_status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    
    # 가격/수량
    price: Optional[Decimal] = Field(
        default=None,
        max_digits=20,
        decimal_places=8,
        description="지정가 (시장가는 None)"
    )
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8
    )
    average_price: Optional[Decimal] = Field(
        default=None,
        max_digits=20,
        decimal_places=8
    )
    
    # 수수료
    fee: Optional[Decimal] = Field(
        default=None,
        max_digits=20,
        decimal_places=8
    )
    
    # 손절/익절 가격 (추가)
    stop_price: Optional[Decimal] = Field(
        default=None,
        max_digits=20,
        decimal_places=8,
        description="손절 또는 익절 가격"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="orders")
    transactions: List["Transaction"] = Relationship(back_populates="order")


# =====================================================
# 포지션 모델
# =====================================================

class Position(SQLModel, table=True):
    """포지션 (보유 자산)"""
    __tablename__ = "positions"
    
    id: int = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="trading_accounts.id", index=True)
    symbol: str = Field(index=True, max_length=20)
    
    # 수량/가격
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    average_price: Decimal = Field(max_digits=20, decimal_places=8)
    current_price: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8
    )
    
    # 평가 정보
    current_value: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8
    )
    unrealized_profit: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    account: Optional[TradingAccount] = Relationship(back_populates="positions")
    
    @property
    def profit_percent(self) -> Decimal:
        """수익률 (%)"""
        if self.average_price == 0:
            return Decimal("0")
        return ((self.current_price - self.average_price) / self.average_price) * 100


# =====================================================
# 거래 내역 모델
# =====================================================

class Transaction(SQLModel, table=True):
    """거래 내역"""
    __tablename__ = "transactions"
    
    id: int = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    
    # 거래 정보
    symbol: str = Field(index=True, max_length=20)
    side: OrderSide
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    fee: Decimal = Field(max_digits=20, decimal_places=8)
    
    # 실현 손익 (매도 시에만)
    realized_profit: Optional[Decimal] = Field(
        default=None,
        max_digits=20,
        decimal_places=8
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="transactions")
    order: Optional[Order] = Relationship(back_populates="transactions")


# =====================================================
# 가격 알림 모델 (신규)
# =====================================================

class PriceAlert(SQLModel, table=True):
    """가격 알림"""
    __tablename__ = "price_alerts"
    
    id: int = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    symbol: str = Field(index=True, max_length=20)
    
    # 알림 조건
    target_price: Decimal = Field(max_digits=20, decimal_places=8)
    condition: str = Field(
        max_length=10,
        description="ABOVE(이상) 또는 BELOW(이하)"
    )
    
    # 상태
    is_active: bool = Field(default=True)
    is_triggered: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    triggered_at: Optional[datetime] = None