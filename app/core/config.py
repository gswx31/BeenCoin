from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BeenCoin API"
    DATABASE_URL: str = "sqlite+aiosqlite:///./beencoin.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    REDIS_URL: str = "redis://localhost:6379"
    INITIAL_BALANCE: float = 1000000

    class Config:
        case_sensitive = True

settings = Settings()
