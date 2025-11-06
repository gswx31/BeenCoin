"""
주문 서비스 테스트 - 백엔드 API 완전 연동 버전
=========================================

백엔드 실제 구현:
- app/services/order_service.py
- async def create_order()
- async def cancel_order()
- async def execute_market_order_complete()
- locked_balance 지원
- 최근 체결 내역 기반 시장가 체결

수정 사항:
1. 모든 함수를 async/await로 호출
2. Enum 타입 사용 (OrderSide, OrderType, OrderStatus)
3. OrderCreate 스키마 사용
4. HTTPException 처리
5. locked_balance 테스트
6. get_recent_trades Mock 추가
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from sqlmodel import Session, select

from app.services.order_service import (
    create_order,
    cancel_order,
    get_user_orders,
    calculate_fee
)
from app.models.database import (
    User, TradingAccount, Order, Position, Transaction,
    OrderSide, OrderType, OrderStatus
)
from app.schemas.order import OrderCreate


# =============================================================================
# 주문 생성 테스트 - 시장가 주문
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
@pytest.mark.asyncio
class TestMarketOrderCreation:
    """시장가 주문 생성 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    async def test_create_market_buy_order_success(
        self,
        mock_get_trades,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        시장가 매수 주문 생성 성공
        
        Given: 충분한 잔액의 계정
        When: 시장가 매수 주문 생성
        Then: 주문 체결 및 잔액 차감
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "49800", "qty": "0.05"},
            {"price": "50000", "qty": "0.05"},
        ]
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.1")
        )
        
        initial_balance = test_account.balance
        
        # Act
        order = await create_order(db_session, test_user.id, order_data)
        
        # Assert
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.order_status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal("0.1")
        assert order.average_price is not None
        
        # 잔액 차감 확인
        db_session.refresh(test_account)
        assert test_account.balance < initial_balance
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    async def test_create_market_sell_order_success(
        self,
        mock_get_trades,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        시장가 매도 주문 생성 성공
        
        Given: 보유 포지션이 있는 계정
        When: 시장가 매도 주문 생성
        Then: 주문 체결 및 잔액 증가
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50200", "qty": "0.05"},
            {"price": "50000", "qty": "0.05"},
        ]
        
        # 포지션 생성
        position = Position(
            account_id=test_account.id,
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            average_price=Decimal("45000"),
            current_value=Decimal("5000"),
            unrealized_profit=Decimal("500")
        )
        db_session.add(position)
        db_session.commit()
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="SELL",
            order_type="MARKET",
            quantity=Decimal("0.1")
        )
        
        initial_balance = test_account.balance
        
        # Act
        order = await create_order(db_session, test_user.id, order_data)
        
        # Assert
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.SELL
        assert order.order_status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal("0.1")
        
        # 잔액 증가 확인
        db_session.refresh(test_account)
        assert test_account.balance > initial_balance
    
    
    @patch("app.services.binance_service.get_current_price")
    async def test_create_order_insufficient_balance_fails(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        잔액 부족 시 주문 실패
        
        Given: 잔액이 부족한 계정
        When: 큰 금액의 매수 주문 시도
        Then: HTTPException 400 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 잔액을 1000원으로 설정
        test_account.balance = Decimal("1000")
        db_session.add(test_account)
        db_session.commit()
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("10")  # 50만원 상당
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_order(db_session, test_user.id, order_data)
        
        assert exc_info.value.status_code == 400
        assert "잔액" in str(exc_info.value.detail)
    
    
    @patch("app.services.binance_service.get_current_price")
    async def test_create_sell_order_insufficient_quantity_fails(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        수량 부족 시 매도 실패
        
        Given: 0.05 BTC만 보유
        When: 0.1 BTC 매도 시도
        Then: HTTPException 400 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 0.05 BTC만 보유
        position = Position(
            account_id=test_account.id,
            symbol="BTCUSDT",
            quantity=Decimal("0.05"),
            average_price=Decimal("45000"),
            current_value=Decimal("2500"),
            unrealized_profit=Decimal("250")
        )
        db_session.add(position)
        db_session.commit()
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="SELL",
            order_type="MARKET",
            quantity=Decimal("0.1")  # 보유량 초과
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_order(db_session, test_user.id, order_data)
        
        assert exc_info.value.status_code == 400
        assert "수량" in str(exc_info.value.detail) or "부족" in str(exc_info.value.detail)
    
    
    @patch("app.services.binance_service.get_current_price")
    async def test_create_sell_order_without_position_fails(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        포지션 없이 매도 시도 실패
        
        Given: 보유하지 않은 코인
        When: 매도 주문 생성
        Then: HTTPException 400 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="SELL",
            order_type="MARKET",
            quantity=Decimal("0.1")
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_order(db_session, test_user.id, order_data)
        
        assert exc_info.value.status_code == 400


# =============================================================================
# 지정가 주문 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
@pytest.mark.asyncio
class TestLimitOrderCreation:
    """지정가 주문 생성 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    async def test_create_limit_buy_order_pending(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        지정가 매수 주문 생성 (대기 상태)
        
        Given: 현재가보다 낮은 지정가
        When: 지정가 매수 주문 생성
        Then: PENDING 상태 및 locked_balance 증가
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            price=Decimal("49000"),  # 현재가보다 낮음
            quantity=Decimal("0.1")
        )
        
        initial_locked = test_account.locked_balance
        
        # Act
        order = await create_order(db_session, test_user.id, order_data)
        
        # Assert
        assert order.order_status == OrderStatus.PENDING
        assert order.price == Decimal("49000")
        assert order.filled_quantity == Decimal("0")
        
        # locked_balance 증가 확인
        db_session.refresh(test_account)
        assert test_account.locked_balance > initial_locked
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    async def test_limit_order_immediate_execution(
        self,
        mock_get_trades,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        지정가 도달 시 즉시 체결
        
        Given: 현재가가 지정가보다 낮음
        When: 지정가 매수 주문 생성
        Then: 즉시 FILLED 상태로 체결
        """
        # Arrange
        mock_get_price.return_value = Decimal("48000")  # 지정가보다 낮음
        mock_get_trades.return_value = [
            {"price": "48000", "qty": "0.1"},
        ]
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            price=Decimal("49000"),  # 현재가보다 높음
            quantity=Decimal("0.1")
        )
        
        # Act
        order = await create_order(db_session, test_user.id, order_data)
        
        # Assert
        assert order.order_status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal("0.1")


# =============================================================================
# 주문 취소 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
@pytest.mark.asyncio
class TestOrderCancellation:
    """주문 취소 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    async def test_cancel_pending_order_success(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        대기 중인 주문 취소 성공
        
        Given: PENDING 상태의 지정가 주문
        When: 주문 취소
        Then: CANCELLED 상태 및 locked_balance 해제
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 지정가 주문 생성
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            price=Decimal("49000"),
            quantity=Decimal("0.1")
        )
        
        order = await create_order(db_session, test_user.id, order_data)
        initial_locked = test_account.locked_balance
        
        # Act
        cancelled_order = await cancel_order(db_session, test_user.id, order.id)
        
        # Assert
        assert cancelled_order.order_status == OrderStatus.CANCELLED
        
        # locked_balance 해제 확인
        db_session.refresh(test_account)
        assert test_account.locked_balance < initial_locked
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    async def test_cancel_filled_order_fails(
        self,
        mock_get_trades,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        체결된 주문 취소 실패
        
        Given: FILLED 상태의 주문
        When: 취소 시도
        Then: HTTPException 400 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # 시장가 주문 생성 (즉시 체결)
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.1")
        )
        
        order = await create_order(db_session, test_user.id, order_data)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await cancel_order(db_session, test_user.id, order.id)
        
        assert exc_info.value.status_code == 400
        assert "취소할 수 없는" in str(exc_info.value.detail)
    
    
    async def test_cancel_order_unauthorized_fails(
        self,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        다른 사용자의 주문 취소 실패
        
        Given: 다른 사용자의 주문
        When: 취소 시도
        Then: HTTPException 403 발생
        """
        # Arrange - 다른 사용자 생성
        other_user = User(
            username="otheruser",
            hashed_password="hashedpass",
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        # 다른 사용자의 주문 생성
        order = Order(
            account_id=test_account.id,
            user_id=other_user.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            order_status=OrderStatus.PENDING,
            price=Decimal("49000"),
            quantity=Decimal("0.1"),
            filled_quantity=Decimal("0")
        )
        db_session.add(order)
        db_session.commit()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await cancel_order(db_session, test_user.id, order.id)
        
        assert exc_info.value.status_code == 403


# =============================================================================
# 포지션 업데이트 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
@pytest.mark.asyncio
class TestPositionUpdates:
    """포지션 업데이트 로직 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    async def test_buy_order_creates_new_position(
        self,
        mock_get_trades,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        매수 주문 시 신규 포지션 생성
        
        Given: 포지션이 없는 상태
        When: 매수 주문 체결
        Then: 새로운 포지션 생성
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.1")
        )
        
        # Act
        await create_order(db_session, test_user.id, order_data)
        
        # Assert
        position = db_session.exec(
            select(Position).where(
                Position.account_id == test_account.id,
                Position.symbol == "BTCUSDT"
            )
        ).first()
        
        assert position is not None
        assert position.quantity == Decimal("0.1")
        assert position.average_price > Decimal("0")
    
    
    @patch("app.services.binance_service.get_current_price")
    @patch("app.services.binance_service.get_recent_trades")
    async def test_buy_order_updates_existing_position(
        self,
        mock_get_trades,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        추가 매수 시 평균 단가 업데이트
        
        Given: 기존 포지션 0.1 BTC @ 40000
        When: 0.1 BTC @ 50000 추가 매수
        Then: 0.2 BTC @ 평균단가
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        mock_get_trades.return_value = [
            {"price": "50000", "qty": "0.1"},
        ]
        
        # 기존 포지션 생성
        position = Position(
            account_id=test_account.id,
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            average_price=Decimal("40000"),
            current_value=Decimal("4000"),
            unrealized_profit=Decimal("1000")
        )
        db_session.add(position)
        db_session.commit()
        
        order_data = OrderCreate(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.1")
        )
        
        # Act
        await create_order(db_session, test_user.id, order_data)
        
        # Assert
        db_session.refresh(position)
        assert position.quantity == Decimal("0.2")
        # 평균 단가는 40000과 50000 사이
        assert Decimal("40000") < position.average_price < Decimal("50000")


# =============================================================================
# 주문 조회 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestOrderRetrieval:
    """주문 조회 테스트"""
    
    def test_get_user_orders_all(
        self,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        전체 주문 목록 조회
        
        Given: 여러 개의 주문
        When: 주문 목록 조회
        Then: 모든 주문 반환 (최신순)
        """
        # Arrange - 5개 주문 생성
        for i in range(5):
            order = Order(
                account_id=test_account.id,
                user_id=test_user.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                order_status=OrderStatus.FILLED,
                quantity=Decimal("0.1"),
                filled_quantity=Decimal("0.1"),
                average_price=Decimal("50000")
            )
            db_session.add(order)
        db_session.commit()
        
        # Act
        orders = get_user_orders(db_session, test_user.id)
        
        # Assert
        assert len(orders) == 5


# =============================================================================
# 수수료 계산 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestFeeCalculation:
    """수수료 계산 테스트"""
    
    @pytest.mark.parametrize("quantity,price,expected_fee", [
        (Decimal("0.1"), Decimal("50000"), Decimal("5")),
        (Decimal("1"), Decimal("100"), Decimal("0.1")),
        (Decimal("0.01"), Decimal("1000"), Decimal("0.01")),
    ])
    def test_fee_calculation_correct(
        self,
        quantity: Decimal,
        price: Decimal,
        expected_fee: Decimal
    ):
        """
        수수료 계산 정확성 (0.1%)
        
        Given: 주문 수량과 가격
        When: 수수료 계산
        Then: 0.1% 수수료 정확히 계산
        """
        # Act
        fee = calculate_fee(quantity, price)
        
        # Assert
        # 오차 범위 허용
        assert abs(fee - expected_fee) < Decimal("0.001")