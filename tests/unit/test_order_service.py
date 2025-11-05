"""
주문 서비스 단위 테스트
======================

테스트 전략:
- TDD (Test-Driven Development) 스타일
- 외부 의존성 완전 Mock
- 비즈니스 로직 집중 테스트
- 에지 케이스와 에러 처리
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services import order_service
from app.models.database import User, TradingAccount, Order, Position
from sqlmodel import Session


# =============================================================================
# 주문 생성 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestOrderCreation:
    """주문 생성 로직 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_market_buy_order_success(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        시장가 매수 주문 생성 성공
        
        Given: 충분한 잔액의 계정
        When: 시장가 매수 주문 생성
        Then: 주문 생성 및 잔액 차감
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": Decimal("0.1")
        }
        
        initial_balance = test_account.balance
        
        # Act
        order = order_service.create_order(
            db_session,
            test_user.id,
            order_data
        )
        
        # Assert
        assert order.symbol == "BTCUSDT"
        assert order.side == "BUY"
        assert order.order_status == "FILLED"  # 시장가는 즉시 체결
        assert order.filled_quantity == Decimal("0.1")
        
        # 잔액 확인
        db_session.refresh(test_account)
        expected_cost = Decimal("0.1") * Decimal("50000") * Decimal("1.001")  # 수수료 포함
        assert test_account.balance == initial_balance - expected_cost
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_order_insufficient_balance_fails(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        account_factory
    ):
        """
        잔액 부족 시 주문 실패
        
        Given: 잔액이 부족한 계정
        When: 큰 금액의 매수 주문 시도
        Then: ValueError 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 잔액 1000원인 계정
        poor_account = account_factory(user=test_user, balance=Decimal("1000"))
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": Decimal("1.0")  # 5천만원 필요
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="잔액이 부족합니다"):
            order_service.create_order(
                db_session,
                test_user.id,
                order_data
            )
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_sell_order_without_position_fails(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount
    ):
        """
        포지션 없이 매도 시도 실패
        
        Given: 보유하지 않은 코인
        When: 매도 주문 생성 시도
        Then: ValueError 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": Decimal("0.1")
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="보유한 코인이 없습니다"):
            order_service.create_order(
                db_session,
                test_user.id,
                order_data
            )
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_sell_order_exceeding_position_fails(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount,
        position_factory
    ):
        """
        보유량 초과 매도 실패
        
        Given: 0.5 BTC 보유
        When: 1.0 BTC 매도 시도
        Then: ValueError 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # 0.5 BTC 포지션
        position_factory(
            account=test_account,
            symbol="BTCUSDT",
            quantity=Decimal("0.5")
        )
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": Decimal("1.0")
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="보유 수량을 초과"):
            order_service.create_order(
                db_session,
                test_user.id,
                order_data
            )
    
    
    @patch("app.services.binance_service.get_current_price")
    @pytest.mark.parametrize("invalid_quantity", [
        Decimal("0"),           # 0
        Decimal("-0.1"),        # 음수
        Decimal("0.00000001"),  # 너무 작음
    ])
    def test_create_order_invalid_quantity(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount,
        invalid_quantity: Decimal
    ):
        """
        유효하지 않은 수량으로 주문 실패
        
        Given: 0, 음수, 또는 최소값 미만 수량
        When: 주문 생성 시도
        Then: ValueError 발생
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": invalid_quantity
        }
        
        # Act & Assert
        with pytest.raises(ValueError):
            order_service.create_order(
                db_session,
                test_user.id,
                order_data
            )


# =============================================================================
# 지정가 주문 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestLimitOrders:
    """지정가 주문 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_create_limit_buy_order_pending(
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
        Then: PENDING 상태로 생성
        """
        # Arrange
        current_price = Decimal("50000")
        limit_price = Decimal("49000")  # 현재가보다 낮음
        
        mock_get_price.return_value = current_price
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": limit_price,
            "quantity": Decimal("0.1")
        }
        
        # Act
        order = order_service.create_order(
            db_session,
            test_user.id,
            order_data
        )
        
        # Assert
        assert order.order_status == "PENDING"
        assert order.price == limit_price
        assert order.filled_quantity == Decimal("0")
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_limit_order_execution_when_price_reached(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount,
        order_factory
    ):
        """
        지정가 도달 시 주문 체결
        
        Given: PENDING 상태의 지정가 매수 주문
        When: 시장가가 지정가에 도달
        Then: 주문 체결 (FILLED)
        """
        # Arrange
        target_price = Decimal("49000")
        
        # PENDING 주문 생성
        order = order_factory(
            user=test_user,
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            price=target_price,
            quantity=Decimal("0.1"),
            order_status="PENDING"
        )
        
        # 가격이 목표가에 도달
        mock_get_price.return_value = Decimal("48900")
        
        # Act
        order_service.execute_pending_orders(db_session)
        
        # Assert
        db_session.refresh(order)
        assert order.order_status == "FILLED"
        assert order.filled_quantity == Decimal("0.1")


# =============================================================================
# 주문 취소 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestOrderCancellation:
    """주문 취소 테스트"""
    
    def test_cancel_pending_order_success(
        self,
        db_session: Session,
        test_user: User,
        order_factory
    ):
        """
        대기 중인 주문 취소 성공
        
        Given: PENDING 상태의 주문
        When: 취소 요청
        Then: CANCELLED 상태로 변경
        """
        # Arrange
        order = order_factory(
            user=test_user,
            order_status="PENDING"
        )
        
        # Act
        cancelled_order = order_service.cancel_order(
            db_session,
            order.id,
            test_user.id
        )
        
        # Assert
        assert cancelled_order.order_status == "CANCELLED"
    
    
    def test_cannot_cancel_filled_order(
        self,
        db_session: Session,
        test_user: User,
        order_factory
    ):
        """
        이미 체결된 주문은 취소 불가
        
        Given: FILLED 상태의 주문
        When: 취소 요청
        Then: ValueError 발생
        """
        # Arrange
        order = order_factory(
            user=test_user,
            order_status="FILLED"
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="체결된 주문은 취소할 수 없습니다"):
            order_service.cancel_order(
                db_session,
                order.id,
                test_user.id
            )
    
    
    def test_cannot_cancel_other_users_order(
        self,
        db_session: Session,
        user_factory,
        order_factory
    ):
        """
        다른 사용자의 주문 취소 불가
        
        Given: 다른 사용자의 주문
        When: 취소 요청
        Then: PermissionError 발생
        """
        # Arrange
        owner = user_factory(username="owner")
        hacker = user_factory(username="hacker")
        
        order = order_factory(
            user=owner,
            order_status="PENDING"
        )
        
        # Act & Assert
        with pytest.raises(PermissionError):
            order_service.cancel_order(
                db_session,
                order.id,
                hacker.id  # 다른 사용자
            )


# =============================================================================
# 포지션 업데이트 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestPositionUpdates:
    """포지션 업데이트 로직 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_buy_order_creates_new_position(
        self,
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
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": Decimal("0.1")
        }
        
        # Act
        order_service.create_order(
            db_session,
            test_user.id,
            order_data
        )
        
        # Assert
        position = db_session.query(Position).filter_by(
            account_id=test_account.id,
            symbol="BTCUSDT"
        ).first()
        
        assert position is not None
        assert position.quantity == Decimal("0.1")
        assert position.average_price == Decimal("50000")
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_buy_order_updates_existing_position(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount,
        position_factory
    ):
        """
        추가 매수 시 평균 단가 업데이트
        
        Given: 기존 포지션 0.1 BTC @ 40000
        When: 0.1 BTC @ 50000 추가 매수
        Then: 0.2 BTC @ 45000 (평균 단가)
        """
        # Arrange
        # 기존 포지션: 0.1 BTC @ 40000
        position_factory(
            account=test_account,
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            average_price=Decimal("40000")
        )
        
        # 추가 매수: 0.1 BTC @ 50000
        mock_get_price.return_value = Decimal("50000")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": Decimal("0.1")
        }
        
        # Act
        order_service.create_order(
            db_session,
            test_user.id,
            order_data
        )
        
        # Assert
        position = db_session.query(Position).filter_by(
            account_id=test_account.id,
            symbol="BTCUSDT"
        ).first()
        
        assert position.quantity == Decimal("0.2")
        # 평균 단가: (0.1*40000 + 0.1*50000) / 0.2 = 45000
        assert position.average_price == Decimal("45000")
    
    
    @patch("app.services.binance_service.get_current_price")
    def test_full_sell_removes_position(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount,
        position_factory
    ):
        """
        전량 매도 시 포지션 삭제
        
        Given: 0.1 BTC 보유
        When: 0.1 BTC 전량 매도
        Then: 포지션 삭제
        """
        # Arrange
        position = position_factory(
            account=test_account,
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            average_price=Decimal("40000")
        )
        
        mock_get_price.return_value = Decimal("50000")
        
        order_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": Decimal("0.1")
        }
        
        # Act
        order_service.create_order(
            db_session,
            test_user.id,
            order_data
        )
        
        # Assert
        position_after = db_session.query(Position).filter_by(
            account_id=test_account.id,
            symbol="BTCUSDT"
        ).first()
        
        assert position_after is None  # 삭제됨


# =============================================================================
# 수수료 계산 테스트
# =============================================================================

@pytest.mark.unit
@pytest.mark.order
class TestFeeCalculation:
    """수수료 계산 테스트"""
    
    @pytest.mark.parametrize("quantity,price,expected_fee", [
        (Decimal("1.0"), Decimal("50000"), Decimal("50")),      # 0.1%
        (Decimal("0.1"), Decimal("50000"), Decimal("5")),
        (Decimal("10.0"), Decimal("1000"), Decimal("10")),
    ])
    def test_fee_calculation_correct(
        self,
        quantity: Decimal,
        price: Decimal,
        expected_fee: Decimal
    ):
        """
        수수료 계산 정확성
        
        Given: 주문 수량과 가격
        When: 수수료 계산
        Then: 0.1% 수수료 정확히 계산
        """
        # Arrange & Act
        fee = order_service.calculate_fee(quantity, price)
        
        # Assert
        assert fee == expected_fee


# =============================================================================
# 비동기 작업 테스트
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.order
class TestAsyncOrderProcessing:
    """비동기 주문 처리 테스트"""
    
    async def test_async_order_validation(self):
        """
        비동기 주문 검증
        
        Given: 주문 데이터
        When: 비동기 검증 수행
        Then: 유효성 확인
        """
        # Arrange
        order_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": Decimal("0.1")
        }
        
        # Act
        is_valid = await order_service.validate_order_async(order_data)
        
        # Assert
        assert is_valid is True


# =============================================================================
# 성능 테스트
# =============================================================================

@pytest.mark.performance
@pytest.mark.order
class TestOrderPerformance:
    """주문 처리 성능 테스트"""
    
    @patch("app.services.binance_service.get_current_price")
    def test_bulk_order_creation_performance(
        self,
        mock_get_price,
        db_session: Session,
        test_user: User,
        test_account: TradingAccount,
        benchmark_timer
    ):
        """
        대량 주문 생성 성능
        
        Given: 100개 주문 데이터
        When: 주문 생성
        Then: 5초 이내 완료
        """
        # Arrange
        mock_get_price.return_value = Decimal("50000")
        
        # Act
        benchmark_timer.start()
        
        for i in range(100):
            order_data = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "price": Decimal(f"{49000 + i}"),
                "quantity": Decimal("0.001")
            }
            order_service.create_order(
                db_session,
                test_user.id,
                order_data
            )
        
        benchmark_timer.stop()
        
        # Assert
        assert benchmark_timer.elapsed < 5.0  # 5초 이내