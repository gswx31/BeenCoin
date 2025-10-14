"""
DB 생성 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🧪 DB 생성 테스트")
print("=" * 60)

# 1. 설정 확인
print("\n1️⃣ 설정 확인...")
from app.core.config import settings
print(f"   DATABASE_URL: {settings.DATABASE_URL}")

# 2. DB 파일 경로 추출
if "sqlite:///" in settings.DATABASE_URL:
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    db_path = Path(db_file)
    print(f"   DB 파일 경로: {db_path}")
    print(f"   상위 디렉토리: {db_path.parent}")
    print(f"   디렉토리 존재: {db_path.parent.exists()}")
    print(f"   디렉토리 쓰기 권한: {db_path.parent.exists() and db_path.parent.is_dir()}")

# 3. 기존 DB 파일 삭제
print("\n2️⃣ 기존 DB 파일 확인...")
if db_path.exists():
    print(f"   ⚠️  기존 DB 파일 발견: {db_path}")
    try:
        db_path.unlink()
        print(f"   ✅ 기존 DB 파일 삭제 완료")
    except Exception as e:
        print(f"   ❌ 삭제 실패: {e}")
        sys.exit(1)
else:
    print(f"   ✅ 기존 DB 파일 없음")

# 4. 디렉토리 생성
print("\n3️⃣ 디렉토리 생성...")
try:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ 디렉토리 준비 완료")
except Exception as e:
    print(f"   ❌ 디렉토리 생성 실패: {e}")
    sys.exit(1)

# 5. DB 생성
print("\n4️⃣ 데이터베이스 생성...")
try:
    from app.models.database import create_db_and_tables
    create_db_and_tables()
    print(f"   ✅ 데이터베이스 생성 완료")
except Exception as e:
    print(f"   ❌ DB 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. 생성 확인
print("\n5️⃣ 생성 확인...")
if db_path.exists():
    size = db_path.stat().st_size
    print(f"   ✅ DB 파일 존재: {db_path}")
    print(f"   📊 파일 크기: {size:,} bytes")
    
    # 테이블 확인
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    
    print(f"   📋 테이블 수: {len(tables)}")
    for table in tables:
        print(f"      - {table[0]}")
else:
    print(f"   ❌ DB 파일이 생성되지 않았습니다!")
    sys.exit(1)

# 7. 테스트 사용자 생성
print("\n6️⃣ 테스트 사용자 생성...")
try:
    from sqlmodel import Session, select
    from app.core.database import engine
    from app.models.database import User, TradingAccount
    from app.utils.security import get_password_hash
    from decimal import Decimal
    from datetime import datetime
    
    with Session(engine) as session:
        # 사용자 생성
        user = User(
            username="testuser",
            hashed_password=get_password_hash("testpass123"),
            created_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # 계정 생성
        account = TradingAccount(
            user_id=user.id,
            balance=Decimal('1000000')
        )
        session.add(account)
        session.commit()
        
        print(f"   ✅ 테스트 사용자 생성 완료")
        print(f"      아이디: testuser")
        print(f"      비밀번호: testpass123")
        print(f"      잔액: $1,000,000")
        
except Exception as e:
    print(f"   ❌ 사용자 생성 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 모든 테스트 완료!")
print("=" * 60)
print("\n다음 명령어로 서버를 시작하세요:")
print("  python -m app.main")