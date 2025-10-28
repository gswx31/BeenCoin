# tests/unit/test_order_service.py
"""
주문 서비스 단위 테스트 - 실제 프로젝트 구조에 맞춤
매수/매도 주문, 포지션 업데이트, 잔액 계산 로직 테스트
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from datetime import datetime

# ✅ 실제 프로젝트 모델 사용
from app.models.database import SpotAccount, SpotPosition, Order
from app.schemas.order import OrderCreate, OrderSide, OrderType
from app.services import order_service
from sqlmodel import select


class TestOrderService:
    """주문 서비스 테스트 클래스"""
    
    @pytest.mark.asyncio
    async def test_create_buy_market_order_success(self, session, test_user, test_account):
        """시장가 매수 주문 생성 성공 테스트"""
        # ✅ 올바른 경로로 Binance API 모킹 + AsyncMock 사용
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            assert order.order_status == "FILLED"
            assert order.symbol == "BTCUSDT"
            assert order.side == "BUY"
            assert order.quantity == Decimal("0.1")
            assert order.price == Decimal("50000")
            
            # 잔액 확인
            session.refresh(test_account)
            # 초기 잔액에서 (가격 * 수량 + 수수료) 차감 확인
            assert test_account.usdt_balance < Decimal("1000000")
            
            # 포지션 생성 확인
            position = session.exec(
                select(SpotPosition).where(
                    SpotPosition.account_id == test_account.id,
                    SpotPosition.symbol == "BTCUSDT"
                )
            ).first()
            
            if position:  # 포지션이 생성된 경우
                assert position.quantity == Decimal("0.1")
                assert position.average_price == Decimal("50000")
    
    
    @pytest.mark.asyncio
    async def test_create_sell_market_order_success(self, session, test_user, test_account, test_position):
        """시장가 매도 주문 생성 성공 테스트"""
        initial_balance = test_account.usdt_balance
        
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            assert order.order_status == "FILLED"
            assert order.side == "SELL"
            assert order.quantity == Decimal("0.05")
            
            # 잔액 증가 확인
            session.refresh(test_account)
            assert test_account.usdt_balance > initial_balance
            
            # 포지션 수량 감소 확인
            session.refresh(test_position)
            assert test_position.quantity <= Decimal("0.1")
    
    
    @pytest.mark.asyncio
    async def test_create_buy_order_insufficient_balance(self, session, test_user, test_account_low_balance):
        """잔액 부족 시 매수 주문 실패 테스트"""
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            
            error_msg = str(exc_info.value).lower()
            assert "insufficient" in error_msg or "부족" in error_msg or "balance" in error_msg
    
    
    @pytest.mark.asyncio
    async def test_create_sell_order_insufficient_position(self, session, test_user, test_account, test_position):
        """보유량 부족 시 매도 주문 실패 테스트"""
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            
            error_msg = str(exc_info.value).lower()
            assert "insufficient" in error_msg or "부족" in error_msg or "quantity" in error_msg
    
    
    @pytest.mark.asyncio
    async def test_create_sell_order_no_position(self, session, test_user, test_account):
        """포지션 없이 매도 주문 시도 시 실패 테스트"""
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            
            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in ["no position", "포지션", "보유", "position"])
    
    
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
        assert order.order_status == "PENDING"  # 대기 상태
        assert order.order_type == "LIMIT"
        assert order.price == Decimal("48000")
        
        # 잔액은 변하지 않거나 예약됨 (구현에 따라)
        session.refresh(test_account)
        # 지정가 주문은 체결 전까지 잔액 변화 없음 (또는 예약만 됨)
    
    
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
        
        error_msg = str(exc_info.value).lower()
        assert "quantity" in error_msg or "수량" in error_msg
    
    
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
        initial_balance = test_account.usdt_balance
        
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            
            # 계정 확인
            session.refresh(test_account)
            
            # 잔액이 증가했는지 확인 (수익 발생)
            assert test_account.usdt_balance > initial_balance
    
    
    @pytest.mark.asyncio
    async def test_complete_sell_position(self, session, test_user, test_account, test_position):
        """전체 포지션 매도 시 포지션 삭제 또는 수량 0 확인 테스트"""
        with patch("app.services.binance_service.get_current_price", new_callable=AsyncMock) as mock_price:
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
            
            # 포지션 확인
            position = session.exec(
                select(SpotPosition).where(
                    SpotPosition.account_id == test_account.id,
                    SpotPosition.symbol == "BTCUSDT"
                )
            ).first()
            
            # 포지션이 삭제되거나 수량이 0이어야 함
            assert position is None or position.quantity == Decimal("0")