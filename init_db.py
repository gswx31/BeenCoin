# init_db.py
"""
데이터베이스 초기화 스크립트
- SQLModel로 모든 테이블 자동 생성 (현물 + 선물)
- 테스트 사용자 생성
- 초기 자본금 설정 (100,000 USDT)

사용법:
    python init_db.py
"""
import sys
from sqlmodel import Session, select
from app.core.database import engine, create_db_and_tables
from app.models.database import User, TradingAccount
from app.models.futures import FuturesAccount
from app.utils.security import hash_password
from datetime import datetime
from decimal import Decimal


def init_database():
    """데이터베이스 초기화"""
    
    print("="*60)
    print("🔧 BeenCoin 데이터베이스 초기화")
    print("="*60)
    
    # 1. 테이블 자동 생성 (SQLModel)
    print("\n1️⃣ 테이블 생성 중...")
    print("   📊 SQLModel로 자동 생성:")
    print("   - 현물: users, trading_accounts, orders, positions, transactions, price_alerts")
    print("   - 선물: futures_accounts, futures_positions, futures_orders, futures_transactions")
    
    create_db_and_tables()  # ✅ 이것만으로 모든 테이블 생성!
    
    print("   ✅ 모든 테이블 생성 완료!")
    
    # 2. 테스트 사용자 생성
    print("\n2️⃣ 테스트 사용자 생성 중...")
    
    with Session(engine) as session:
        # 기존 사용자 확인
        existing_user = session.exec(
            select(User).where(User.username == "testuser")
        ).first()
        
        if existing_user:
            print("   ⚠️ 테스트 사용자가 이미 존재합니다.")
        else:
            # 사용자 생성
            user = User(
                username="testuser",
                hashed_password=hash_password("testpass123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # 현물 계정 생성
            spot_account = TradingAccount(
                user_id=user.id,
                balance=Decimal("100000"),  # ✅ 100,000 USDT
                locked_balance=Decimal("0"),
                total_profit=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(spot_account)
            
            # 선물 계정 생성
            futures_account = FuturesAccount(
                user_id=user.id,
                balance=Decimal("100000"),  # ✅ 100,000 USDT
                margin_used=Decimal("0"),
                total_profit=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(futures_account)
            
            session.commit()
            
            print("   ✅ 테스트 사용자 생성 완료!")
            print(f"      아이디: testuser")
            print(f"      비밀번호: testpass123")
            print(f"      현물 잔액: 100,000 USDT")  # ✅ 수정
            print(f"      선물 잔액: 100,000 USDT")  # ✅ 수정
    
    print("\n" + "="*60)
    print("✅ 데이터베이스 초기화 완료!")
    print("="*60)
    print("\n📊 생성된 테이블:")
    print("   현물: users, trading_accounts, orders, positions, transactions, price_alerts")
    print("   선물: futures_accounts, futures_positions, futures_orders, futures_transactions")
    print("\n🚀 서버를 시작하세요:")
    print("   python -m app.main")
    print("\n📖 API 문서:")
    print("   http://localhost:8000/docs")
    print("\n🔑 로그인 정보:")
    print("   아이디: testuser")
    print("   비밀번호: testpass123")
    print("   현물 잔액: 100,000 USDT")
    print("   선물 잔액: 100,000 USDT")
    print("="*60)


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)