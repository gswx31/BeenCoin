from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

class IBinanceClient(ABC):
    """Binance API 클라이언트 인터페이스"""

    @abstractmethod
    async def get_current_price(self, symbol: str) -> Decimal:
        pass

class BinanceAPIClient(IBinanceClient):
    """실제 Binance API 클라이언트"""

    async def get_current_price(self, symbol: str) -> Decimal:
        # 실제 Binance API 호출 로직
        pass

class MockBinanceClient(IBinanceClient):
    """Mock Binance 클라이언트 (CI/CD 환경용)"""

    async def get_current_price(self, symbol: str) -> Decimal:
        # Mock 데이터 반환
        return Decimal("50000.00")

async def get_current_price(symbol: str) -> Decimal:
    # 실제 Binance API 클라이언트 사용
    client = BinanceAPIClient()
    return await client.get_current_price(symbol)
