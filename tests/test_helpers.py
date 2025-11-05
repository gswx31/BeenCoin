"""
테스트 유틸리티 모듈
===================

재사용 가능한 테스트 헬퍼 함수들
"""
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random
import string

from app.models.database import User, TradingAccount, Order, Position
from sqlmodel import Session


# =============================================================================
# 데이터 생성 헬퍼
# =============================================================================

class TestDataFactory:
    """테스트 데이터 생성 팩토리"""
    
    @staticmethod
    def generate_random_username(prefix: str = "user") -> str:
        """랜덤 사용자명 생성"""
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}_{suffix}"
    
    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """랜덤 비밀번호 생성"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choices(chars, k=length))
    
    @staticmethod
    def create_test_users(
        session: Session,
        count: int = 5,
        **kwargs
    ) -> List[User]:
        """여러 테스트 사용자 생성"""
        from app.utils.security import hash_password
        
        users = []
        for i in range(count):
            user = User(
                username=f"testuser_{i}",
                hashed_password=hash_password(f"password{i}"),
                is_active=kwargs.get('is_active', True)
            )
            session.add(user)
            users.append(user)
        
        session.commit()
        return users
    
    @staticmethod
    def create_test_orders(
        session: Session,
        user: User,
        count: int = 10,
        **kwargs
    ) -> List[Order]:
        """여러 테스트 주문 생성"""
        orders = []
        symbols = kwargs.get('symbols', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
        
        for i in range(count):
            order = Order(
                user_id=user.id,
                symbol=random.choice(symbols),
                side=random.choice(['BUY', 'SELL']),
                order_type=kwargs.get('order_type', 'MARKET'),
                price=Decimal(str(random.uniform(100, 100000))),
                quantity=Decimal(str(random.uniform(0.001, 10))),
                filled_quantity=Decimal("0"),
                order_status=kwargs.get('order_status', 'PENDING'),
            )
            session.add(order)
            orders.append(order)
        
        session.commit()
        return orders


# =============================================================================
# Assertion 헬퍼
# =============================================================================

class TestAssertions:
    """커스텀 assertion 헬퍼"""
    
    @staticmethod
    def assert_decimal_equal(
        actual: Decimal,
        expected: Decimal,
        tolerance: Decimal = Decimal("0.01")
    ):
        """Decimal 값 동등성 검증 (오차 허용)"""
        diff = abs(actual - expected)
        assert diff <= tolerance, (
            f"Expected {expected}, but got {actual}. "
            f"Difference: {diff} (tolerance: {tolerance})"
        )
    
    @staticmethod
    def assert_response_success(response, expected_status: int = 200):
        """API 응답 성공 검증"""
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, but got {response.status_code}. "
            f"Response: {response.json()}"
        )
    
    @staticmethod
    def assert_has_keys(data: dict, required_keys: List[str]):
        """딕셔너리 필수 키 존재 검증"""
        missing_keys = set(required_keys) - set(data.keys())
        assert not missing_keys, f"Missing required keys: {missing_keys}"
    
    @staticmethod
    def assert_balance_changed(
        initial: Decimal,
        final: Decimal,
        expected_change: Decimal,
        tolerance: Decimal = Decimal("1")
    ):
        """잔액 변화 검증"""
        actual_change = final - initial
        TestAssertions.assert_decimal_equal(
            actual_change,
            expected_change,
            tolerance
        )


# =============================================================================
# Mock 헬퍼
# =============================================================================

class MockBinanceService:
    """Binance Service Mock 헬퍼"""
    
    def __init__(self):
        self.prices = {
            "BTCUSDT": Decimal("50000"),
            "ETHUSDT": Decimal("3000"),
            "BNBUSDT": Decimal("400"),
            "ADAUSDT": Decimal("0.5")
        }
        self.call_count = 0
    
    def get_current_price(self, symbol: str) -> Decimal:
        """현재가 조회 Mock"""
        self.call_count += 1
        return self.prices.get(symbol, Decimal("1000"))
    
    def set_price(self, symbol: str, price: Decimal):
        """가격 설정"""
        self.prices[symbol] = price
    
    def simulate_price_change(self, symbol: str, change_percent: float):
        """가격 변동 시뮬레이션"""
        current = self.prices.get(symbol, Decimal("1000"))
        new_price = current * Decimal(str(1 + change_percent / 100))
        self.prices[symbol] = new_price
        return new_price


# =============================================================================
# 시간 관련 헬퍼
# =============================================================================

class TimeHelper:
    """시간 관련 헬퍼"""
    
    @staticmethod
    def freeze_time(dt: datetime):
        """시간 고정 (pytest-freezegun 사용 시)"""
        from freezegun import freeze_time
        return freeze_time(dt)
    
    @staticmethod
    def travel_time(days: int = 0, hours: int = 0, minutes: int = 0):
        """시간 이동"""
        delta = timedelta(days=days, hours=hours, minutes=minutes)
        return datetime.now() + delta


# =============================================================================
# 데이터베이스 헬퍼
# =============================================================================

class DatabaseHelper:
    """데이터베이스 관련 헬퍼"""
    
    @staticmethod
    def count_records(session: Session, model) -> int:
        """특정 모델의 레코드 수 조회"""
        return session.query(model).count()
    
    @staticmethod
    def clear_table(session: Session, model):
        """특정 테이블 모든 레코드 삭제"""
        session.query(model).delete()
        session.commit()
    
    @staticmethod
    def get_last_record(session: Session, model):
        """마지막 레코드 조회"""
        return session.query(model).order_by(model.id.desc()).first()


# =============================================================================
# API 테스트 헬퍼
# =============================================================================

class APITestHelper:
    """API 테스트 헬퍼"""
    
    @staticmethod
    def create_auth_user_and_get_headers(client, username: str = None, password: str = None):
        """사용자 생성 및 인증 헤더 반환"""
        username = username or TestDataFactory.generate_random_username()
        password = password or "testpass123"
        
        # 회원가입
        client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password}
        )
        
        # 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    def extract_error_message(response) -> str:
        """API 에러 메시지 추출"""
        try:
            return response.json().get("detail", "Unknown error")
        except:
            return response.text


# =============================================================================
# 성능 측정 헬퍼
# =============================================================================

class PerformanceHelper:
    """성능 측정 헬퍼"""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """함수 실행 시간 측정"""
        import time
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    
    @staticmethod
    def assert_performance(func, max_time: float, *args, **kwargs):
        """성능 요구사항 검증"""
        _, elapsed = PerformanceHelper.measure_execution_time(func, *args, **kwargs)
        assert elapsed <= max_time, (
            f"Function took {elapsed:.4f}s, but max allowed is {max_time}s"
        )


# =============================================================================
# 로깅 헬퍼
# =============================================================================

class LogHelper:
    """로깅 관련 헬퍼"""
    
    @staticmethod
    def assert_log_contains(caplog, message: str, level: str = "INFO"):
        """로그에 특정 메시지 포함 확인"""
        log_records = [
            record for record in caplog.records
            if record.levelname == level and message in record.message
        ]
        assert log_records, f"Log message '{message}' with level '{level}' not found"
    
    @staticmethod
    def get_log_messages(caplog, level: str = None) -> List[str]:
        """로그 메시지 목록 반환"""
        records = caplog.records
        if level:
            records = [r for r in records if r.levelname == level]
        return [r.message for r in records]


# =============================================================================
# 파라미터 생성 헬퍼
# =============================================================================

class ParameterHelper:
    """파라미터 생성 헬퍼"""
    
    @staticmethod
    def invalid_username_cases():
        """유효하지 않은 사용자명 케이스"""
        return [
            ("ab", "Too short"),
            ("a" * 51, "Too long"),
            ("user@name", "Special char @"),
            ("user#123", "Special char #"),
            ("user space", "Contains space"),
            ("", "Empty string"),
        ]
    
    @staticmethod
    def invalid_password_cases():
        """유효하지 않은 비밀번호 케이스"""
        return [
            ("12345", "Too short"),
            ("a" * 129, "Too long"),
            ("", "Empty string"),
        ]
    
    @staticmethod
    def valid_order_types():
        """유효한 주문 타입"""
        return ["MARKET", "LIMIT"]
    
    @staticmethod
    def valid_order_sides():
        """유효한 주문 방향"""
        return ["BUY", "SELL"]
    
    @staticmethod
    def supported_symbols():
        """지원하는 코인 심볼"""
        return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]


# =============================================================================
# 비교 헬퍼
# =============================================================================

class ComparisonHelper:
    """비교 관련 헬퍼"""
    
    @staticmethod
    def are_dicts_equal_ignore_keys(
        dict1: dict,
        dict2: dict,
        ignore_keys: List[str]
    ) -> bool:
        """특정 키를 무시하고 딕셔너리 비교"""
        d1_filtered = {k: v for k, v in dict1.items() if k not in ignore_keys}
        d2_filtered = {k: v for k, v in dict2.items() if k not in ignore_keys}
        return d1_filtered == d2_filtered
    
    @staticmethod
    def assert_lists_equal_unordered(list1: list, list2: list):
        """순서 무관 리스트 비교"""
        assert sorted(list1) == sorted(list2)


# =============================================================================
# 파일 헬퍼
# =============================================================================

class FileHelper:
    """파일 관련 헬퍼"""
    
    @staticmethod
    def create_temp_csv(data: List[dict], filename: str = "test.csv"):
        """임시 CSV 파일 생성"""
        import csv
        import tempfile
        
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.csv',
            newline=''
        )
        
        if data:
            writer = csv.DictWriter(temp_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def read_test_fixture(filename: str) -> str:
        """테스트 fixture 파일 읽기"""
        import os
        fixture_path = os.path.join("tests", "fixtures", filename)
        with open(fixture_path, 'r') as f:
            return f.read()


# =============================================================================
# WebSocket 테스트 헬퍼
# =============================================================================

class WebSocketTestHelper:
    """WebSocket 테스트 헬퍼"""
    
    @staticmethod
    async def connect_and_receive(client, url: str, timeout: float = 5.0):
        """WebSocket 연결 및 메시지 수신"""
        import asyncio
        
        with client.websocket_connect(url) as websocket:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=timeout
                )
                return data
            except asyncio.TimeoutError:
                return None
    
    @staticmethod
    async def send_and_receive(client, url: str, message: dict, timeout: float = 5.0):
        """WebSocket 메시지 송수신"""
        import asyncio
        
        with client.websocket_connect(url) as websocket:
            await websocket.send_json(message)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=timeout
                )
                return data
            except asyncio.TimeoutError:
                return None


# =============================================================================
# 통합 테스트 시나리오 빌더
# =============================================================================

class ScenarioBuilder:
    """테스트 시나리오 빌더"""
    
    def __init__(self, client):
        self.client = client
        self.username = None
        self.headers = None
        self.orders = []
    
    def with_registered_user(self, username: str = None, password: str = None):
        """사용자 등록"""
        self.username = username or TestDataFactory.generate_random_username()
        password = password or "testpass123"
        
        self.client.post(
            "/api/v1/auth/register",
            json={"username": self.username, "password": password}
        )
        return self
    
    def with_authentication(self, password: str = "testpass123"):
        """인증"""
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": self.username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}
        return self
    
    def with_buy_order(self, symbol: str, quantity: str, price: Decimal = None):
        """매수 주문 추가"""
        order_data = {
            "symbol": symbol,
            "side": "BUY",
            "order_type": "LIMIT" if price else "MARKET",
            "quantity": quantity
        }
        if price:
            order_data["price"] = str(price)
        
        response = self.client.post(
            "/api/v1/orders/",
            headers=self.headers,
            json=order_data
        )
        self.orders.append(response.json())
        return self
    
    def execute(self):
        """시나리오 실행 완료"""
        return {
            "username": self.username,
            "headers": self.headers,
            "orders": self.orders
        }