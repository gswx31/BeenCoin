from pydantic_settings import BaseSettings
from typing import Optional, List, Dict
from dotenv import load_dotenv
import os
import secrets

load_dotenv()


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BeenCoin API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./beencoin.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    INITIAL_BALANCE: float = 1000000.0

    SUPPORTED_SYMBOLS: list = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    # -- Binance-style symbol rules --
    # stepSize: minimum quantity increment
    # minQty: minimum order quantity
    # minNotional: minimum order value in USDT
    # tickSize: price precision
    SYMBOL_RULES: dict = {
        "BTCUSDT": {"stepSize": "0.00001", "minQty": "0.00001", "minNotional": "10", "tickSize": "0.01", "baseAsset": "BTC"},
        "ETHUSDT": {"stepSize": "0.0001",  "minQty": "0.0001",  "minNotional": "10", "tickSize": "0.01", "baseAsset": "ETH"},
        "BNBUSDT": {"stepSize": "0.001",   "minQty": "0.001",   "minNotional": "10", "tickSize": "0.01", "baseAsset": "BNB"},
    }

    # -- Fee tiers (Binance VIP levels) --
    # 30-day trading volume (USDT) -> (maker_fee, taker_fee)
    FEE_TIERS: list = [
        {"min_volume": 0,          "maker": "0.1000", "taker": "0.1000", "label": "Regular"},
        {"min_volume": 1000000,    "maker": "0.0900", "taker": "0.1000", "label": "VIP 1"},
        {"min_volume": 5000000,    "maker": "0.0800", "taker": "0.1000", "label": "VIP 2"},
        {"min_volume": 10000000,   "maker": "0.0700", "taker": "0.0900", "label": "VIP 3"},
        {"min_volume": 50000000,   "maker": "0.0500", "taker": "0.0700", "label": "VIP 4"},
        {"min_volume": 100000000,  "maker": "0.0400", "taker": "0.0600", "label": "VIP 5"},
    ]
    BNB_FEE_DISCOUNT: float = 0.25  # 25% discount when using BNB for fees

    # -- Slippage simulation for market orders --
    SLIPPAGE_BPS: float = 2.0  # basis points (0.02%)

    class Config:
        case_sensitive = True


settings = Settings()
