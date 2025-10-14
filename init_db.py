"""
데이터베이스 초기화 스크립트
기존 DB를 삭제하고 새로 생성합니다.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.models.database import create_db_and_tables
from app.core.config import settings

def init_database():
    """데이터베이스 초기화"""
    print("\n" + "="*60)
    print("🗄️  데이터베이스 초기화")
    print("="*60)
    
    # 기존 DB 파일 확인
    db_file = "beencoin.db"
    if os.path.exists(db_file):
        print(f"\n⚠️  기존 데이터베이스 발견: {db_file}")
        response = input("삭제하고 새로 만드시겠습니까? (y/N): ")
        
        if response.lower() == 'y':
            os.remove(db_file)
            print(f"✅ 기존 데이터베이스 삭제됨")
        else:
            print("❌ 초기화가 취소되었습니다.")
            return
    
    # 새 DB 생성
    print(f"\n📝 새 데이터베이스 생성 중...")
    try:
        create_db_and_tables()
        print("\n✅ 데이터베이스가 성공적으로 생성되었습니다!")
        print(f"📂 위치: {os.path.abspath(db_file)}")
        
        # 테이블 확인
        import sqlite3
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n📋 생성된 테이블:")
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def create_test_user():
    """테스트 사용자 생성"""
    print("\n" + "="*60)
    print("👤 테스트 사용자 생성")
    print("="*60)
    
    response = input("\n테스트 사용자를 생성하시겠습니까? (y/N): ")
    
    if response.lower() != 'y':
        print("건너뛰기")
        return
    
    try:
        from sqlmodel import Session, select
        from app.core.database import engine
        from app.models.database import User, TradingAccount
        from app.utils.security import get_password_hash
        from decimal import Decimal
        
        with Session(engine) as session:
            # 테스트 사용자 생성
            test_username = "testuser"
            test_password = "testpass123"
            
            # 기존 사용자 확인
            existing = session.exec(
                select(User).where(User.username == test_username)
            ).first()
            
            if existing:
                print(f"⚠️  사용자 '{test_username}'가 이미 존재합니다.")
                return
            
            # 사용자 생성
            user = User(
                username=test_username,
                hashed_password=get_password_hash(test_password)
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # 계정 생성
            account = TradingAccount(
                user_id=user.id,
                balance=Decimal(str(settings.INITIAL_BALANCE))
            )
            session.add(account)
            session.commit()
            
            print(f"\n✅ 테스트 사용자 생성 완료!")
            print(f"  아이디: {test_username}")
            print(f"  비밀번호: {test_password}")
            print(f"  초기 잔액: ${settings.INITIAL_BALANCE:,.0f}")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("BeenCoin 데이터베이스 초기화 도구")
    print("="*80)
    
    init_database()
    create_test_user()
    
    print("\n" + "="*80)
    print("완료!")
    print("="*80)
    print("\n다음 명령어로 서버를 시작하세요:")
    print("  python -m app.main")

if __name__ == "__main__":
    main()