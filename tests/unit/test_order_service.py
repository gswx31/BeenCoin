# tests/unit/test_order_service.py
"""
주문 서비스 단위 테스트
매수/매도 주문, 포지션 업데이트, 잔액 계산 로직 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models.database import TradingAccount, Position, Order
from app.schemas.order import OrderCreate, OrderSide, OrderType
from app.services import order_service
from sqlmodel import select


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
            
            # 수수료 계산 확인 (거래금액 * 0.001)
            expected_fee = Decimal("0.1") * Decimal("50000") * Decimal("0.001")
            assert order.fee == expected_fee
            
            # 잔액 확인 (초기 1,000,000 - (50000*0.1 + 수수료))
            session.refresh(test_account)
            expected_cost = Decimal("50000") * Decimal("0.1") + expected_fee
            expected_balance = Decimal("1000000") - expected_cost
            assert test_account.balance == expected_balance
            
            # 포지션 생성 확인
            position = session.exec(
                select(Position).where(
                    Position.account_id == test_account.id,
                    Position.symbol == "BTCUSDT"
                )
            ).first()
            assert position is not None
            assert position.quantity == Decimal("0.1")
            assert position.average_price == Decimal("50000")
    
    
    @pytest.mark.asyncio
    async def test_create_sell_market_order_success(self, session, test_user, test_account, test_position):
        """시장가 매도 주문 생성 성공 테스트"""
        initial_balance = test_account.balance
        
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("52000")  # 수익 상황
            
            # 매도 주문 데이터
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.05")  # 보유량의 절반만 매도
            )
            
            # 주문 생성
            order = await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
            
            # 검증
            assert order.status == "FILLED"
            assert order.side == "SELL"
            assert order.quantity == Decimal("0.05")
            assert order.price == Decimal("52000")
            
            # 수수료 계산
            expected_fee = Decimal("0.05") * Decimal("52000") * Decimal("0.001")
            assert order.fee == expected_fee
            
            # 잔액 확인 (판매 금액 - 수수료 추가)
            session.refresh(test_account)
            sell_amount = Decimal("0.05") * Decimal("52000")
            expected_balance = initial_balance + sell_amount - expected_fee
            assert test_account.balance == expected_balance
            
            # 포지션 수량 감소 확인
            session.refresh(test_position)
            assert test_position.quantity == Decimal("0.05")  # 0.1 - 0.05
    
    
    @pytest.mark.asyncio
    async def test_create_buy_order_insufficient_balance(self, session, test_user, test_account_low_balance):
        """잔액 부족 시 매수 주문 실패 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            # 큰 수량 주문 (잔액 부족)
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("1.0")  # 50000 * 1.0 = 50000원 필요 (잔액 1000원)
            )
            
            # 예외 발생 확인
            with pytest.raises(Exception) as exc_info:
                await order_service.create_order(
                    session=session,
                    user_id=test_user.id,
                    order_data=order_data
                )
            
            assert "insufficient" in str(exc_info.value).lower() or "부족" in str(exc_info.value)
    
    
    @pytest.mark.asyncio
    async def test_create_sell_order_insufficient_position(self, session, test_user, test_account, test_position):
        """보유량 부족 시 매도 주문 실패 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            # 보유량보다 많은 수량 매도 시도
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.5")  # 보유량 0.1개보다 많음
            )
            
            # 예외 발생 확인
            with pytest.raises(Exception) as exc_info:
                await order_service.create_order(
                    session=session,
                    user_id=test_user.id,
                    order_data=order_data
                )
            
            assert "insufficient" in str(exc_info.value).lower() or "부족" in str(exc_info.value)
    
    
    @pytest.mark.asyncio
    async def test_create_sell_order_no_position(self, session, test_user, test_account):
        """포지션 없이 매도 주문 시도 시 실패 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            # 보유하지 않은 코인 매도 시도
            order_data = OrderCreate(
                symbol="ETHUSDT",  # 보유하지 않음
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("1.0")
            )
            
            # 예외 발생 확인
            with pytest.raises(Exception) as exc_info:
                await order_service.create_order(
                    session=session,
                    user_id=test_user.id,
                    order_data=order_data
                )
            
            assert "no position" in str(exc_info.value).lower() or "포지션" in str(exc_info.value)
    
    
    @pytest.mark.asyncio
    async def test_create_limit_order_buy(self, session, test_user, test_account):
        """지정가 매수 주문 생성 테스트"""
        # 지정가 주문은 즉시 체결되지 않음
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("48000")  # 지정가
        )
        
        # 주문 생성
        order = await order_service.create_order(
            session=session,
            user_id=test_user.id,
            order_data=order_data
        )
        
        # 검증
        assert order.status == "PENDING"  # 대기 상태
        assert order.order_type == "LIMIT"
        assert order.price == Decimal("48000")
        assert order.fee == Decimal("0")  # 체결 전이므로 수수료 없음
        
        # 잔액은 변하지 않음 (아직 체결되지 않음)
        session.refresh(test_account)
        assert test_account.balance == Decimal("1000000")
    
    
    @pytest.mark.asyncio
    async def test_update_position_average_price(self, session, test_account, test_position):
        """포지션 평균가 업데이트 테스트"""
        # 추가 매수로 평균가 변경
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("55000")  # 더 높은 가격에 매수
            
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1")  # 동일한 수량 추가 매수
            )
            
            await order_service.create_order(
                session=session,
                user_id=test_account.user_id,
                order_data=order_data
            )
            
            # 포지션 확인
            session.refresh(test_position)
            
            # 평균가 계산: (50000 * 0.1 + 55000 * 0.1) / 0.2 = 52500
            expected_avg_price = Decimal("52500")
            assert test_position.quantity == Decimal("0.2")
            assert test_position.average_price == expected_avg_price
    
    
    @pytest.mark.asyncio
    async def test_complete_sell_position(self, session, test_user, test_account, test_position):
        """전체 포지션 매도 시 포지션 삭제 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("51000")
            
            # 전체 수량 매도
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1")  # 전체 매도
            )
            
            await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
            
            # 포지션이 삭제되었는지 확인
            position = session.exec(
                select(Position).where(
                    Position.account_id == test_account.id,
                    Position.symbol == "BTCUSDT"
                )
            ).first()
            
            assert position is None or position.quantity == Decimal("0")
    
    
    @pytest.mark.asyncio
    async def test_calculate_trading_fee(self):
        """거래 수수료 계산 로직 테스트"""
        # 0.1% 수수료
        quantity = Decimal("1.0")
        price = Decimal("50000")
        
        fee = order_service.calculate_fee(quantity, price)
        expected_fee = quantity * price * Decimal("0.001")
        
        assert fee == expected_fee
        assert fee == Decimal("50")  # 50000 * 0.001
    
    
    @pytest.mark.asyncio
    async def test_multiple_orders_same_symbol(self, session, test_user, test_account):
        """동일한 심볼에 여러 주문 생성 테스트"""
        with patch("app.services.order_service.get_current_price") as mock_price:
            mock_price.return_value = Decimal("50000")
            
            # 첫 번째 주문
            order1_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1")
            )
            order1 = await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order1_data
            )
            
            # 두 번째 주문
            mock_price.return_value = Decimal("51000")
            order2_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.05")
            )
            order2 = await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order2_data
            )
            
            # 두 주문 모두 성공
            assert order1.status == "FILLED"
            assert order2.status == "FILLED"
            
            # 포지션 확인 (누적되어야 함)
            position = session.exec(
                select(Position).where(
                    Position.account_id == test_account.id,
                    Position.symbol == "BTCUSDT"
                )
            ).first()
            
            assert position.quantity == Decimal("0.15")  # 0.1 + 0.05
    
    
    @pytest.mark.asyncio
    async def test_order_with_zero_quantity(self, session, test_user, test_account):
        """수량이 0인 주문 시도 시 실패 테스트"""
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0")
        )
        
        with pytest.raises(Exception) as exc_info:
            await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
        
        assert "quantity" in str(exc_info.value).lower() or "수량" in str(exc_info.value)
    
    
    @pytest.mark.asyncio
    async def test_order_with_negative_quantity(self, session, test_user, test_account):
        """음수 수량으로 주문 시도 시 실패 테스트"""
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("-0.1")
        )
        
        with pytest.raises(Exception):
            await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
    
    
    @pytest.mark.asyncio
    async def test_profit_calculation_on_sell(self, session, test_user, test_account, test_position):
        """매도 시 수익 계산 테스트"""
        initial_total_profit = test_account.total_profit
        
        with patch("app.services.order_service.get_current_price") as mock_price:
            # 매수가 50000, 매도가 55000으로 수익 발생
            mock_price.return_value = Decimal("55000")
            
            order_data = OrderCreate(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1")
            )
            
            await order_service.create_order(
                session=session,
                user_id=test_user.id,
                order_data=order_data
            )
            
            # 계정의 총 수익 증가 확인
            session.refresh(test_account)
            
            # 수익 = (매도가 - 매수가) * 수량
            expected_profit = (Decimal("55000") - Decimal("50000")) * Decimal("0.1")
            expected_total_profit = initial_total_profit + expected_profit
            
            # 수수료 고려
            fee = Decimal("0.1") * Decimal("55000") * Decimal("0.001")
            expected_total_profit -= fee
            
            assert test_account.total_profit >= expected_profit - fee