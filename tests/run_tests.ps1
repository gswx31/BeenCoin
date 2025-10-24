# run_tests.ps1
# Windows PowerShell용 테스트 실행 스크립트

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  🧪 BeenCoin 테스트 실행 (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# PYTHONPATH 설정
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"

# Python 확인
try {
    $pythonVersion = python --version
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python을 찾을 수 없습니다" -ForegroundColor Red
    Write-Host "가상환경을 활성화했는지 확인하세요: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    pause
    exit 1
}

# pytest 설치 확인
try {
    python -c "import pytest" 2>$null
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Write-Host ""
    Write-Host "⚠️  pytest가 설치되지 않았습니다" -ForegroundColor Yellow
    Write-Host "설치 중..." -ForegroundColor Yellow
    pip install pytest pytest-asyncio pytest-cov
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ pytest 설치 실패" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "✅ pytest 설치 완료" -ForegroundColor Green
    Write-Host ""
}

# 백엔드 서버 실행 여부 확인
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host ""
    Write-Host "⚠️  경고: 포트 8000이 사용 중입니다" -ForegroundColor Yellow
    Write-Host "백엔드 서버가 실행 중이면 종료하세요" -ForegroundColor Yellow
    Write-Host "테스트는 독립적인 환경에서 실행되어야 합니다" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "계속 진행하시겠습니까? (Y/N)"
    if ($continue -ne "Y" -and $continue -ne "y") {
        exit 1
    }
}

# 옵션 처리
$option = $args[0]

switch ($option) {
    "unit" {
        Write-Host "📝 단위 테스트 실행 중..." -ForegroundColor Yellow
        Write-Host ""
        pytest tests/unit -v
    }
    "integration" {
        Write-Host "🔗 통합 테스트 실행 중..." -ForegroundColor Yellow
        Write-Host ""
        pytest tests/integration -v
    }
    "coverage" {
        Write-Host "📊 커버리지 측정 중..." -ForegroundColor Yellow
        Write-Host ""
        pytest --cov=app --cov-report=html --cov-report=term tests/
        Write-Host ""
        Write-Host "✅ 커버리지 리포트 생성 완료!" -ForegroundColor Green
        Write-Host "📂 브라우저에서 htmlcov\index.html 파일을 여세요" -ForegroundColor Cyan
        Write-Host ""
        $openReport = Read-Host "리포트를 지금 여시겠습니까? (Y/N)"
        if ($openReport -eq "Y" -or $openReport -eq "y") {
            Start-Process "htmlcov\index.html"
        }
    }
    "quick" {
        Write-Host "⚡ 빠른 테스트 실행 중 (첫 실패 시 중단)..." -ForegroundColor Yellow
        Write-Host ""
        pytest tests/unit -v --tb=short -x
    }
    "verbose" {
        Write-Host "📋 상세 출력 모드로 실행 중..." -ForegroundColor Yellow
        Write-Host ""
        pytest -vv -s
    }
    "failed" {
        Write-Host "🔄 실패한 테스트만 재실행 중..." -ForegroundColor Yellow
        Write-Host ""
        pytest --lf -v
    }
    default {
        Write-Host "🧪 전체 테스트 실행 중..." -ForegroundColor Yellow
        Write-Host ""
        pytest -v
    }
}

# 결과 확인
Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  ✅ 모든 테스트 통과!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  ❌ 일부 테스트 실패" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 문제 해결 팁:" -ForegroundColor Yellow
    Write-Host "   1. 에러 메시지를 확인하세요" -ForegroundColor Yellow
    Write-Host "   2. 백엔드 서버가 실행 중이면 종료하세요" -ForegroundColor Yellow
    Write-Host "   3. 가상환경이 활성화되었는지 확인하세요" -ForegroundColor Yellow
    Write-Host "   4. .\run_tests.ps1 failed 로 실패한 테스트만 재실행하세요" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}