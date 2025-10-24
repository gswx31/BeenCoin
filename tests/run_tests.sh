#!/bin/bash
# run_tests.sh
# 테스트 실행 스크립트

echo "🧪 BeenCoin 테스트 실행"
echo "=========================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 옵션 처리
case "$1" in
  "unit")
    echo -e "${YELLOW}단위 테스트 실행 중...${NC}"
    pytest tests/unit -v
    ;;
  "integ./tests/run_tests.sh unitration")
    echo -e "${YELLOW}통합 테스트 실행 중...${NC}"
    pytest tests/integration -v
    ;;
  "coverage")
    echo -e "${YELLOW}커버리지 측정 중...${NC}"
    pytest --cov=app --cov-report=html --cov-report=term
    echo ""
    echo -e "${GREEN}커버리지 리포트 생성 완료!${NC}"
    echo "브라우저에서 htmlcov/index.html 파일을 여세요."
    ;;
  "quick")
    echo -e "${YELLOW}빠른 테스트 실행 중...${NC}"
    pytest tests/unit -v --tb=short -x
    ;;
  "verbose")
    echo -e "${YELLOW}상세 출력 모드로 실행 중...${NC}"
    pytest -vv -s
    ;;
  "failed")
    echo -e "${YELLOW}실패한 테스트만 재실행 중...${NC}"
    pytest --lf -v
    ;;
  *)
    echo -e "${YELLOW}전체 테스트 실행 중...${NC}"
    pytest -v
    ;;
esac

# 결과 확인
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 모든 테스트 통과!${NC}"
else
    echo ""
    echo -e "${RED}❌ 일부 테스트 실패${NC}"
    exit 1
fi