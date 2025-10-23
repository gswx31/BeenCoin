# 파일 6: 서버 시작 전 점검 스크립트
# ========================================
# check_imports.py
"""
서버 시작 전 import 문제 점검
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🔍 Import 점검 시작")
print("=" * 60)

errors = []

# 1. 캐시 모듈
print("\n1️⃣ 캐시 모듈 점검...")
try:
    from app.cache.cache_manager import cache_manager
    print("   ✅ cache_manager import 성공")
    
    # 메서드 확인
    assert hasattr(cache_manager, 'get'), "get 메서드 없음"
    assert hasattr(cache_manager, 'set'), "set 메서드 없음"
    assert hasattr(cache_manager, 'clear'), "clear 메서드 없음"
    assert hasattr(cache_manager, 'get_stats'), "get_stats 메서드 없음"
    print("   ✅ 모든 메서드 확인")
except Exception as e:
    errors.append(f"캐시 모듈: {e}")
    print(f"   ❌ 오류: {e}")

# 2. 설정 모듈
print("\n2️⃣ 설정 모듈 점검...")
try:
    from app.core.config import settings
    print("   ✅ settings import 성공")
    print(f"   📊 지원 심볼: {settings.SUPPORTED_SYMBOLS}")
    print(f"   💾 캐시 TTL: {settings.CACHE_TTL}s")
except Exception as e:
    errors.append(f"설정 모듈: {e}")
    print(f"   ❌ 오류: {e}")

# 3. 데이터베이스 모듈
print("\n3️⃣ 데이터베이스 모듈 점검...")
try:
    from app.core.database import create_db_and_tables
    print("   ✅ database import 성공")
except Exception as e:
    errors.append(f"데이터베이스 모듈: {e}")
    print(f"   ❌ 오류: {e}")

# 4. 서비스 모듈
print("\n4️⃣ 서비스 모듈 점검...")
try:
    from app.services.binance_service import get_current_price, get_multiple_prices
    print("   ✅ binance_service import 성공")
except Exception as e:
    errors.append(f"서비스 모듈: {e}")
    print(f"   ❌ 오류: {e}")

# 5. 라우터 모듈
print("\n5️⃣ 라우터 모듈 점검...")
try:
    from app.routers import auth, orders, account, market
    print("   ✅ 모든 라우터 import 성공")
except Exception as e:
    errors.append(f"라우터 모듈: {e}")
    print(f"   ❌ 오류: {e}")

# 6. 메인 앱
print("\n6️⃣ 메인 앱 점검...")
try:
    from app.main import app
    print("   ✅ FastAPI 앱 import 성공")
except Exception as e:
    errors.append(f"메인 앱: {e}")
    print(f"   ❌ 오류: {e}")

# 결과 요약
print("\n" + "=" * 60)
if errors:
    print("❌ 점검 실패!")
    print("\n발견된 문제:")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")
    print("\n수정 후 다시 실행하세요.")
    sys.exit(1)
else:
    print("✅ 모든 점검 통과!")
    print("\n서버를 시작해도 됩니다:")
    print("  python -m uvicorn app.main:app --reload")
print("=" * 60)