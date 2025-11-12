# init_db.py
"""
Database initialization script
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, SQLModel
from app.core.database import engine
from app.models.database import User, TradingAccount
from app.models.futures import FuturesAccount
from app.utils.security import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with tables and test data"""
    
    logger.info("Dropping existing tables...")
    SQLModel.metadata.drop_all(engine)
    
    logger.info("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create test user
        logger.info("Creating test user...")
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass123")
        )
        session.add(test_user)
        session.commit()
        
        # Create trading accounts
        logger.info("Creating trading accounts...")
        trading_account = TradingAccount(
            user_id=test_user.id,
            balance=100000.0
        )
        futures_account = FuturesAccount(
            user_id=test_user.id,
            usdt_balance=100000.0
        )
        
        session.add(trading_account)
        session.add(futures_account)
        session.commit()
        
        logger.info("Database initialized successfully!")
        logger.info(f"Test user created - username: testuser, password: testpass123")

if __name__ == "__main__":
    init_database()