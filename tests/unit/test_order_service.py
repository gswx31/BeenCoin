# tests/unit/test_order_service.py
"""
주문 서비스 단위 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.models.database import TradingAccount, Position, Order
from app.schemas.order import OrderCreate, OrderSide, OrderType
from app.services import order_service


class TestOrderService:
    """주문 서비스 테스트 클래스"""
    
    @pytest.mark.asyncio
    async def test_create_buy_market_order_success(self, session, test_user, test_account):
        """시장가 매수 주문 생성 성공 테스트"""
        # Binance API 모킹
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            # 주문 데이터
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1")
            )
            
            # 주문 생성
            order = await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
            
            # 검증
            assert order.id is not None
            assert order.status == "FILLED"
            assert order.symbol == "BTCUSDT"
            assert order.side == "BUY"
            assert order.quantity == Decimal("0.1")
            assert order.price == Decimal("50000")
            
            # 잔액 확인 (5000 + 수수료 5)
            session.refresh(test_account)
            expected_balance = Decimal("1000000") - Decimal("5005")
            assert test_account.balance == expected_balance
    
    
    @pytest.mark.asyncio
    async def test_create_sell_market_order_success(self, session, test_user, test_account, test_position):
        """시장가 매도 주문 생성 성공 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("55000")
            
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.05")  # 보유량의 절반 매도
            )
            
            order = await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
            
            # 검증
            assert order.status == "FILLED"
            assert order.side == "SELL"
            
            # 포지션 수량 감소 확인
            session.refresh(test_position)
            assert test_position.quantity == Decimal("0.05")
    
    
    @pytest.mark.asyncio
    async def test_create_limit_order_success(self, session, test_user, test_account):
        """지정가 주문 생성 성공 테스트"""
        order_data = OrderCreate(
            symbol="ETHUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1"),
            price=Decimal("2000")
        )
        
        order = await order_service.create_order(
            session=session,
            user_id=test_user.id,
            order_data=order_data
        )
        
        # 지정가 주문은 PENDING 상태
        assert order.status == "PENDING"
        assert order.price == Decimal("2000")
        
        # 잔액은 즉시 차감되지 않음
        session.refresh(test_account)
        assert test_account.balance == Decimal("1000000")
    
    
    @pytest.mark.asyncio
    async def test_insufficient_balance(self, session, test_user, test_account):
        """잔액 부족 시 주문 실패 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100")  # 매우 큰 수량
            )
            
            # 예외 발생 확인
            with pytest.raises(Exception) as exc_info:
                await order_service.create_order(
                    session=session,
                    user_id=test_user.id,
                    order_data=order_data
                )
            
            assert "잔액" in str(exc_info.value) or "Insufficient" in str(exc_info.value)
    
    
    @pytest.mark.asyncio
    async def test_sell_without_position(self, session, test_user, test_account):
        """보유하지 않은 코인 매도 시 실패 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("2000")
            
            order_data = OrderCreate(
                symbol="ETHUSDT",  # 보유하지 않은 코인
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("1")
            )
            
            with pytest.raises(Exception) as exc_info:
                await order_service.create_order(
                    session=session,
                    user_id=test_user.id,
                    order_data=order_data
                )
            
            assert "포지션" in str(exc_info.value) or "position" in str(exc_info.value).lower()


class TestPositionUpdate:
    """포지션 업데이트 테스트"""
    
    def test_update_position_buy(self, session, test_account):
        """매수 시 포지션 생성/업데이트 테스트"""
        # 첫 매수
        order_service.update_position(
            session=session,
            account_id=test_account.id,
            symbol="BTCUSDT",
            side="BUY",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
            fee=Decimal("25")
        )
        
        position = session.query(Position).filter(
            Position.account_id == test_account.id,
            Position.symbol == "BTCUSDT"
        ).first()
        
        assert position is not None
        assert position.quantity == Decimal("0.1")
        assert position.average_price == Decimal("50000")
        
        # 추가 매수 (평단가 변경 확인)
        order_service.update_position(
            session=session,
            account_id=test_account.id,
            symbol="BTCUSDT",
            side="BUY",
            quantity=Decimal("0.1"),
            price=Decimal("60000"),
            fee=Decimal("30")
        )
        
        session.refresh(position)
        assert position.quantity == Decimal("0.2")
        assert position.average_price == Decimal("55000")  # (50000 + 60000) / 2
    
    
    def test_update_position_sell(self, session, test_account):
        """매도 시 포지션 감소 테스트"""
        # 먼저 포지션 생성
        position = Position(
            account_id=test_account.id,
            symbol="BTCUSDT",
            quantity=Decimal("0.2"),
            average_price=Decimal("50000"),
            current_value=Decimal("10000"),
            unrealized_profit=Decimal("0")
        )
        session.add(position)
        session.commit()
        
        # 일부 매도
        order_service.update_position(
            session=session,
            account_id=test_account.id,
            symbol="BTCUSDT",
            side="SELL",
            quantity=Decimal("0.1"),
            price=Decimal("55000"),
            fee=Decimal("27.5")
        )
        
        session.refresh(position)
        assert position.quantity == Decimal("0.1")
        
        # 전량 매도
        order_service.update_position(
            session=session,
            account_id=test_account.id,
            symbol="BTCUSDT",
            side="SELL",
            quantity=Decimal("0.1"),
            price=Decimal("55000"),
            fee=Decimal("27.5")
        )
        
        # 포지션 삭제 확인
        session.refresh(position)
        assert position.quantity == Decimal("0") or position not in session