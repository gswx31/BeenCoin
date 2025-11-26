#!/bin/bash
# ============================================================================
# 파일: run_tests.sh
# ============================================================================
# 테스트 실행 스크립트
# ============================================================================

set -e

echo "=============================================="
echo "🧪 BeenCoin 테스트 실행"
echo "=============================================="

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 가상환경 활성화됨"
fi

# 테스트 유형 선택
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    "unit")
        echo "📋 단위 테스트 실행..."
        pytest tests/unit/ -v --tb=short
        ;;
    "integration")
        echo "📋 통합 테스트 실행..."
        pytest tests/integration/ -v --tb=short
        ;;
    "api")
        echo "📋 API 테스트 실행..."
        pytest -v -m "api" --tb=short
        ;;
    "e2e")
        echo "📋 E2E 테스트 실행..."
        pytest -v -m "e2e" --tb=short
        ;;
    "fast")
        echo "📋 빠른 테스트만 실행..."
        pytest -v -m "not slow" --tb=short
        ;;
    "coverage")
        echo "📋 커버리지 포함 테스트..."
        pytest --cov=app --cov-report=html --cov-report=term-missing -v
        echo "✅ 커버리지 리포트: htmlcov/index.html"
        ;;
    "all")
        echo "📋 전체 테스트 실행..."
        pytest -v --tb=short
        ;;
    *)
        echo "사용법: $0 [unit|integration|api|e2e|fast|coverage|all]"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "✅ 테스트 완료"
echo "=============================================="
