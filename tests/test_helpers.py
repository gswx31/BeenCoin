# ============================================================================
# 파일: tests/test_helpers.py
# ============================================================================
# 테스트 헬퍼 유틸리티
# ============================================================================

"""
테스트 헬퍼:
1. 테스트 데이터 팩토리
2. API 테스트 헬퍼
3. 데이터베이스 헬퍼
4. Mock 객체
"""

from datetime import datetime, timedelta
import uuid

# =============================================================================
# 1. 테스트 데이터 팩토리
# =============================================================================


class TestDataFactory:
    """테스트 데이터 생성 팩토리"""

    @staticmethod
    def generate_random_username(prefix: str = "user") -> str:
        """랜덤 사용자명 생성"""
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def generate_random_email(domain: str = "test.com") -> str:
        """랜덤 이메일 생성"""
        return f"{uuid.uuid4().hex[:8]}@{domain}"

    @staticmethod
    def generate_order_data(
        symbol: str = "BTCUSDT",
        side: str = "LONG",
        quantity: str = "0.001",
        leverage: int = 10,
        order_type: str = "MARKET",
        price: str | None = None,
    ) -> dict:
        """주문 데이터 생성"""
        data = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "leverage": leverage,
            "order_type": order_type,
        }
        if price:
            data["price"] = price
        return data

    @staticmethod
    def generate_user_data(username: str | None = None, password: str = "testpass123") -> dict:
        """사용자 데이터 생성"""
        return {
            "username": username or TestDataFactory.generate_random_username(),
            "password": password,
        }

    @staticmethod
    def generate_batch_users(count: int) -> list[dict]:
        """여러 사용자 데이터 생성"""
        return [TestDataFactory.generate_user_data() for _ in range(count)]


# =============================================================================
# 2. API 테스트 헬퍼
# =============================================================================


class APITestHelper:
    """API 테스트 헬퍼"""

    def __init__(self, client):
        self.client = client
        self.headers = {}

    def register_user(self, username: str | None = None, password: str = "testpass123") -> dict:
        """사용자 등록"""
        username = username or TestDataFactory.generate_random_username()
        response = self.client.post(
            "/api/v1/auth/register", json={"username": username, "password": password}
        )
        return {"response": response, "username": username, "password": password}

    def login(self, username: str, password: str) -> dict:
        """로그인"""
        response = self.client.post(
            "/api/v1/auth/login", data={"username": username, "password": password}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {token}"}
        return {
            "response": response,
            "token": response.json().get("access_token") if response.status_code == 200 else None,
            "headers": self.headers,
        }

    def register_and_login(
        self, username: str | None = None, password: str = "testpass123"
    ) -> dict:
        """등록 및 로그인"""
        reg = self.register_user(username, password)
        if reg["response"].status_code not in [200, 201]:
            return reg

        login = self.login(reg["username"], password)
        return {
            "register_response": reg["response"],
            "login_response": login["response"],
            "username": reg["username"],
            "headers": login["headers"],
        }

    def open_position(
        self,
        symbol: str = "BTCUSDT",
        side: str = "LONG",
        quantity: str = "0.001",
        leverage: int = 10,
    ) -> dict:
        """포지션 개설"""
        response = self.client.post(
            "/api/v1/futures/positions/open",
            headers=self.headers,
            json={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "leverage": leverage,
                "order_type": "MARKET",
            },
        )
        return {
            "response": response,
            "position_id": (
                response.json().get("id") if response.status_code in [200, 201] else None
            ),
        }

    def close_position(self, position_id: str) -> dict:
        """포지션 청산"""
        response = self.client.post(
            f"/api/v1/futures/positions/{position_id}/close", headers=self.headers
        )
        return {"response": response}

    def get_positions(self, status: str = "OPEN") -> dict:
        """포지션 목록 조회"""
        response = self.client.get(
            "/api/v1/futures/positions", params={"status": status}, headers=self.headers
        )
        return {
            "response": response,
            "positions": response.json() if response.status_code == 200 else [],
        }

    def get_account(self) -> dict:
        """계정 조회"""
        response = self.client.get("/api/v1/futures/account", headers=self.headers)
        return {
            "response": response,
            "account": response.json() if response.status_code == 200 else None,
        }


# =============================================================================
# 3. 시나리오 빌더
# =============================================================================


class ScenarioBuilder:
    """테스트 시나리오 빌더"""

    def __init__(self, client):
        self.client = client
        self.helper = APITestHelper(client)
        self.username = None
        self.headers = None
        self.positions = []
        self.results = {}

    def with_new_user(self, username: str = None, password: str = "testpass123"):
        """새 사용자 생성 및 로그인"""
        result = self.helper.register_and_login(username, password)
        self.username = result.get("username")
        self.headers = result.get("headers")
        self.helper.headers = self.headers
        self.results["user"] = result
        return self

    def with_existing_user(self, username: str, password: str):
        """기존 사용자 로그인"""
        result = self.helper.login(username, password)
        self.username = username
        self.headers = result.get("headers")
        self.helper.headers = self.headers
        self.results["login"] = result
        return self

    def open_position(
        self,
        symbol: str = "BTCUSDT",
        side: str = "LONG",
        quantity: str = "0.001",
        leverage: int = 10,
    ):
        """포지션 개설"""
        result = self.helper.open_position(symbol, side, quantity, leverage)
        if result["position_id"]:
            self.positions.append(result["position_id"])
        self.results[f"position_{len(self.positions)}"] = result
        return self

    def close_all_positions(self):
        """모든 포지션 청산"""
        for pos_id in self.positions:
            result = self.helper.close_position(pos_id)
            self.results[f"close_{pos_id}"] = result
        self.positions = []
        return self

    def verify_account_balance(self, min_balance: float = 0):
        """계정 잔액 확인"""
        result = self.helper.get_account()
        account = result.get("account")
        if account:
            assert account.get("balance", 0) >= min_balance
        self.results["account_check"] = result
        return self

    def execute(self) -> dict:
        """시나리오 실행 완료"""
        return {
            "username": self.username,
            "headers": self.headers,
            "positions": self.positions,
            "results": self.results,
        }


# =============================================================================
# 4. Mock 객체
# =============================================================================


class MockBinanceResponse:
    """Binance API Mock 응답"""

    @staticmethod
    def ticker_24hr(symbol: str = "BTCUSDT") -> dict:
        """24시간 티커 응답"""
        return {
            "symbol": symbol,
            "priceChange": "1000.00",
            "priceChangePercent": "2.00",
            "lastPrice": "50000.00",
            "volume": "10000.00",
            "highPrice": "51000.00",
            "lowPrice": "49000.00",
        }

    @staticmethod
    def ticker_price(symbol: str = "BTCUSDT") -> dict:
        """현재가 응답"""
        return {"symbol": symbol, "price": "50000.00"}

    @staticmethod
    def klines(symbol: str = "BTCUSDT", count: int = 24) -> list:
        """캔들스틱 데이터"""
        base_time = int(datetime.now().timestamp() * 1000)
        return [
            [
                base_time - (i * 3600000),  # Open time
                "50000.00",  # Open
                "51000.00",  # High
                "49000.00",  # Low
                "50500.00",  # Close
                "1000.00",  # Volume
                base_time - (i * 3600000) + 3599999,  # Close time
                "50000000.00",  # Quote asset volume
                100,  # Number of trades
                "500.00",  # Taker buy base
                "25000000.00",  # Taker buy quote
                "0",  # Ignore
            ]
            for i in range(count)
        ]

    @staticmethod
    def recent_trades(symbol: str = "BTCUSDT", limit: int = 20) -> list:
        """최근 거래 내역"""
        return [
            {
                "id": 12345678 + i,
                "price": "50000.00",
                "qty": "0.001",
                "time": int(datetime.now().timestamp() * 1000) - (i * 1000),
                "isBuyerMaker": i % 2 == 0,
            }
            for i in range(limit)
        ]


# =============================================================================
# 5. 어설션 헬퍼
# =============================================================================


class AssertionHelper:
    """커스텀 어설션 헬퍼"""

    @staticmethod
    def assert_response_ok(response, expected_status: list = None):
        """응답 성공 확인"""
        expected = expected_status or [200, 201]
        assert (
            response.status_code in expected
        ), f"Expected {expected}, got {response.status_code}: {response.text}"

    @staticmethod
    def assert_response_error(response, expected_status: list = None):
        """응답 에러 확인"""
        expected = expected_status or [400, 401, 403, 404, 422]
        assert (
            response.status_code in expected
        ), f"Expected {expected}, got {response.status_code}: {response.text}"

    @staticmethod
    def assert_has_fields(data: dict, fields: list):
        """필수 필드 존재 확인"""
        for field in fields:
            assert field in data, f"Missing field: {field}"

    @staticmethod
    def assert_list_not_empty(data: list, message: str = "List should not be empty"):
        """리스트가 비어있지 않은지 확인"""
        assert len(data) > 0, message

    @staticmethod
    def assert_positive(value: float, field_name: str = "value"):
        """양수 확인"""
        assert value > 0, f"{field_name} should be positive, got {value}"

    @staticmethod
    def assert_in_range(value: float, min_val: float, max_val: float, field_name: str = "value"):
        """범위 확인"""
        assert (
            min_val <= value <= max_val
        ), f"{field_name} should be between {min_val} and {max_val}, got {value}"


# =============================================================================
# 6. 시간 관련 헬퍼
# =============================================================================


class TimeHelper:
    """시간 관련 헬퍼"""

    @staticmethod
    def now_utc() -> datetime:
        """현재 UTC 시간"""
        return datetime.utcnow()

    @staticmethod
    def days_ago(days: int) -> datetime:
        """N일 전"""
        return datetime.utcnow() - timedelta(days=days)

    @staticmethod
    def hours_ago(hours: int) -> datetime:
        """N시간 전"""
        return datetime.utcnow() - timedelta(hours=hours)

    @staticmethod
    def to_timestamp(dt: datetime) -> int:
        """datetime을 밀리초 타임스탬프로 변환"""
        return int(dt.timestamp() * 1000)

    @staticmethod
    def from_timestamp(ts: int) -> datetime:
        """밀리초 타임스탬프를 datetime으로 변환"""
        return datetime.fromtimestamp(ts / 1000)


# =============================================================================
# 사용 예시
# =============================================================================
"""
# API 테스트 헬퍼 사용
def test_with_helper(client):
    helper = APITestHelper(client)
    result = helper.register_and_login()
    assert result["login_response"].status_code == 200

    pos = helper.open_position("BTCUSDT", "LONG")
    assert pos["response"].status_code in [200, 201]


# 시나리오 빌더 사용
def test_with_scenario(client):
    result = (
        ScenarioBuilder(client)
        .with_new_user()
        .open_position("BTCUSDT", "LONG")
        .open_position("ETHUSDT", "SHORT")
        .verify_account_balance(100)
        .close_all_positions()
        .execute()
    )
    assert len(result["results"]) > 0


# 어설션 헬퍼 사용
def test_with_assertions(client):
    response = client.get("/api/v1/market/coins")
    AssertionHelper.assert_response_ok(response)
    AssertionHelper.assert_list_not_empty(response.json())
"""
