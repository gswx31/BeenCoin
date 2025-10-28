"""데이터베이스 초기화"""
import os
import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent))

from app.models.database import create_all_tables
from app.core.config import settings

def init_database(force: bool = False):
    """데이터베이스 초기화"""
    print("\n" + "="*70)
    print("🗄️  BeenCoin 데이터베이스 초기화")
    print("="*70)
    
    db_file = settings.DATABASE_URL.replace("sqlite:///", "").replace("./", "")
    db_path = Path(db_file)
    
    if db_path.exists():
        print(f"\n⚠️  기존 데이터베이스 발견: {db_path}")
        print(f"   크기: {db_path.stat().st_size / 1024:.2f} KB")
        
        if not force:
            response = input("\n삭제하고 새로 만드시겠습니까? (y/N): ")
            if response.lower() != 'y':
                print("❌ 초기화가 취소되었습니다.")
                return False
        
        db_path.unlink()
        print(f"✅ 기존 데이터베이스 삭제됨")
    
    print(f"\n📝 새 데이터베이스 생성 중...")
    try:
        create_all_tables()
        print(f"\n✅ 데이터베이스가 성공적으로 생성되었습니다!")
        print(f"📂 위치: {db_path.absolute()}")
        
        import sqlite3
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n📋 생성된 테이블 ({len(tables)}개):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table[0]} (레코드: {count}개)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_data(num_users: int = 3):
    """테스트 데이터 생성"""
    print("\n" + "="*70)
    print("👥 테스트 데이터 생성")
    print("="*70)
    
    try:
        from sqlmodel import Session, select
        from app.core.database import engine
        from app.models.database import User, TradingAccount, Position
        from app.utils.security import hash_password
        from decimal import Decimal
        from datetime import datetime, timedelta
        import random
        
        with Session(engine) as session:
            test_users = []
            for i in range(1, num_users + 1):
                username = f"testuser{i}"
                
                existing = session.exec(
                    select(User).where(User.username == username)
                ).first()
                
                if existing:
                    print(f"⚠️  사용자 '{username}'가 이미 존재합니다. 건너뜀.")
                    continue
                
                user = User(
                    username=username,
                    hashed_password=hash_password("testpass123"),
                    is_active=True,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                session.add(user)
                session.flush()
                
                balance = Decimal(str(settings.INITIAL_BALANCE))
                account = TradingAccount(
                    user_id=user.id,
                    balance=balance,
                    total_profit=Decimal('0'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(account)
                session.flush()
                
                if i > 1:
                    for symbol in random.sample(settings.SUPPORTED_SYMBOLS, 2):
                        quantity = Decimal(str(random.uniform(0.01, 0.5)))
                        avg_price = Decimal(str(random.uniform(30000, 50000)))
                        current_price = avg_price * Decimal(str(random.uniform(0.95, 1.05)))
                        
                        position = Position(
                            account_id=account.id,
                            symbol=symbol,
                            quantity=quantity,
                            average_price=avg_price,
                            current_price=current_price,
                            current_value=quantity * current_price,
                            unrealized_profit=quantity * (current_price - avg_price),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(position)
                
                test_users.append(user)
                print(f"✅ 사용자 생성: {username} (잔액: ${balance:,.0f})")
            
            session.commit()
            
            print(f"\n✅ {len(test_users)}명의 테스트 사용자가 생성되었습니다!")
            print("\n로그인 정보:")
            for i in range(1, num_users + 1):
                print(f"  아이디: testuser{i}, 비밀번호: testpass123")
            
            return True
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_stats():
    """데이터베이스 통계"""
    print("\n" + "="*70)
    print("📊 데이터베이스 통계")
    print("="*70)
    
    try:
        from sqlmodel import Session, select, func
        from app.core.database import engine
        from app.models.database import User, TradingAccount, Order, Position, Transaction
        
        with Session(engine) as session:
            user_count = session.exec(select(func.count(User.id))).one()
            print(f"\n👥 사용자: {user_count}명")
            
            total_balance = session.exec(
                select(func.sum(TradingAccount.balance))
            ).one() or 0
            total_profit = session.exec(
                select(func.sum(TradingAccount.total_profit))
            ).one() or 0
            
            print(f"💰 총 잔액: ${total_balance:,.2f}")
            print(f"📈 총 수익: ${total_profit:,.2f}")
            
            order_count = session.exec(select(func.count(Order.id))).one()
            print(f"\n📝 총 주문: {order_count}개")
            
            if order_count > 0:
                order_stats = session.exec(
                    select(
                        Order.order_status,
                        func.count(Order.id)
                    ).group_by(Order.order_status)
                ).all()
                
                for status, count in order_stats:
                    print(f"   - {status}: {count}개")
            
            position_count = session.exec(select(func.count(Position.id))).one()
            print(f"\n📊 활성 포지션: {position_count}개")
            
            tx_count = session.exec(select(func.count(Transaction.id))).one()
            print(f"💱 총 거래: {tx_count}건")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='BeenCoin 데이터베이스 관리')
    parser.add_argument(
        'command',
        nargs='?',
        choices=['init', 'test-data', 'stats', 'reset'],
        default='reset'
    )
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--users', type=int, default=3)
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("BeenCoin 데이터베이스 관리 도구")
    print("="*70)
    
    if args.command == 'init':
        init_database(force=args.force)
    elif args.command == 'test-data':
        create_test_data(num_users=args.users)
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'reset':
        if init_database(force=args.force):
            create_test_data(num_users=args.users)
    
    print("\n" + "="*70)
    print("완료!")
    print("="*70)


if __name__ == "__main__":
    main()