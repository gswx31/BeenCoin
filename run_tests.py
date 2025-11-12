#!/usr/bin/env python3
"""
고급 테스트 러너
===============

다양한 테스트 실행 옵션 제공
- 마커별 실행
- 커버리지 측정
- 병렬 실행
- HTML 리포트 생성
"""
import sys
import subprocess
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """테스트 실행 관리 클래스"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        
    def run_command(self, cmd: List[str]) -> int:
        """명령어 실행"""
        print(f"\n{'='*70}")
        print(f"실행: {' '.join(cmd)}")
        print(f"{'='*70}\n")
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode
    
    def run_all_tests(self, verbose: bool = True) -> int:
        """전체 테스트 실행"""
        cmd = ["pytest"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_unit_tests(self) -> int:
        """단위 테스트만 실행"""
        return self.run_command(["pytest", "-m", "unit", "-v"])
    
    def run_integration_tests(self) -> int:
        """통합 테스트만 실행"""
        return self.run_command(["pytest", "-m", "integration", "-v"])
    
    def run_e2e_tests(self) -> int:
        """E2E 테스트만 실행"""
        return self.run_command(["pytest", "-m", "e2e", "-v"])
    
    def run_fast_tests(self) -> int:
        """빠른 테스트만 실행"""
        return self.run_command(["pytest", "-m", "fast", "-v"])
    
    def run_with_coverage(self, html: bool = True) -> int:
        """커버리지 측정과 함께 실행"""
        cmd = [
            "pytest",
            "--cov=app",
            "--cov-report=term-missing",
        ]
        if html:
            cmd.append("--cov-report=html")
        return self.run_command(cmd)
    
    def run_parallel(self, num_workers: int = 4) -> int:
        """병렬 실행 (pytest-xdist 필요)"""
        return self.run_command([
            "pytest",
            "-n", str(num_workers),
            "-v"
        ])
    
    def run_specific_file(self, filepath: str) -> int:
        """특정 파일만 실행"""
        return self.run_command(["pytest", filepath, "-v"])
    
    def run_specific_test(self, test_path: str) -> int:
        """
        특정 테스트만 실행
        예: tests/unit/test_auth.py::TestUserRegistration::test_register_success
        """
        return self.run_command(["pytest", test_path, "-v", "-s"])
    
    def run_failed_tests(self) -> int:
        """마지막에 실패한 테스트만 재실행"""
        return self.run_command(["pytest", "--lf", "-v"])
    
    def run_smoke_tests(self) -> int:
        """스모크 테스트 실행"""
        return self.run_command(["pytest", "-m", "smoke", "-v"])
    
    def run_security_tests(self) -> int:
        """보안 테스트 실행"""
        return self.run_command(["pytest", "-m", "security", "-v"])
    
    def run_performance_tests(self) -> int:
        """성능 테스트 실행"""
        return self.run_command(["pytest", "-m", "performance", "-v"])
    
    def run_with_html_report(self) -> int:
        """HTML 리포트 생성"""
        return self.run_command([
            "pytest",
            "--html=tests/reports/report.html",
            "--self-contained-html",
            "-v"
        ])
    
    def run_critical_tests(self) -> int:
        """중요한 테스트만 실행"""
        return self.run_command(["pytest", "-m", "critical", "-v"])
    
    def check_code_quality(self) -> int:
        """코드 품질 검사"""
        print("\n[1/4] Running Black (포매팅 검사)...")
        black_result = subprocess.run(
            ["black", "--check", "app", "tests"],
            cwd=self.project_root
        )
        
        print("\n[2/4] Running Ruff (린트 검사)...")
        ruff_result = subprocess.run(
            ["ruff", "check", "app", "tests"],
            cwd=self.project_root
        )
        
        print("\n[3/4] Running MyPy (타입 검사)...")
        mypy_result = subprocess.run(
            ["mypy", "app"],
            cwd=self.project_root
        )
        
        print("\n[4/4] Running Safety (보안 검사)...")
        safety_result = subprocess.run(
            ["safety", "check"],
            cwd=self.project_root
        )
        
        all_passed = all(
            result.returncode == 0
            for result in [black_result, ruff_result, mypy_result, safety_result]
        )
        
        return 0 if all_passed else 1
    
    def show_coverage_report(self):
        """커버리지 리포트 열기"""
        import webbrowser
        html_path = self.project_root / "htmlcov" / "index.html"
        if html_path.exists():
            webbrowser.open(str(html_path))
            print(f"\n✅ 커버리지 리포트를 브라우저에서 열었습니다: {html_path}")
        else:
            print("\n❌ 커버리지 리포트가 없습니다. 먼저 테스트를 실행하세요:")
            print("   python run_tests.py --coverage")


def print_usage():
    """사용법 출력"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                   BeenCoin 테스트 러너 v2.0                          ║
╚══════════════════════════════════════════════════════════════════════╝

사용법: python run_tests.py [옵션]

🎯 기본 실행:
  --all, -a              전체 테스트 실행 (기본값)
  --unit, -u             단위 테스트만 실행
  --integration, -i      통합 테스트만 실행
  --e2e, -e              E2E 테스트만 실행
  --fast, -f             빠른 테스트만 실행

📊 커버리지 & 리포트:
  --coverage, -c         커버리지 측정
  --html-report          HTML 리포트 생성
  --show-coverage        커버리지 리포트 브라우저에서 열기

⚡ 성능 최적화:
  --parallel [N], -p [N] N개 워커로 병렬 실행 (기본: 4)
  --failed, --lf         실패한 테스트만 재실행

🎭 특정 카테고리:
  --smoke                스모크 테스트
  --security             보안 테스트
  --performance          성능 테스트
  --critical             중요한 테스트만

🔍 특정 테스트:
  --file <경로>          특정 파일 실행
  --test <경로>          특정 테스트 함수 실행

🛠️ 코드 품질:
  --quality, -q          코드 품질 검사 (Black, Ruff, MyPy, Safety)

예제:
  python run_tests.py --unit --coverage
  python run_tests.py --parallel 8
  python run_tests.py --test tests/unit/test_auth.py::test_login
  python run_tests.py --smoke --html-report
  python run_tests.py --quality
    """)


def main():
    """메인 함수"""
    runner = TestRunner()
    
    if len(sys.argv) == 1:
        # 인자 없으면 전체 테스트 실행
        sys.exit(runner.run_all_tests())
    
    arg = sys.argv[1].lower()
    
    # 도움말
    if arg in ["--help", "-h", "help"]:
        print_usage()
        sys.exit(0)
    
    # 전체 테스트
    elif arg in ["--all", "-a"]:
        sys.exit(runner.run_all_tests())
    
    # 단위 테스트
    elif arg in ["--unit", "-u"]:
        sys.exit(runner.run_unit_tests())
    
    # 통합 테스트
    elif arg in ["--integration", "-i"]:
        sys.exit(runner.run_integration_tests())
    
    # E2E 테스트
    elif arg in ["--e2e", "-e"]:
        sys.exit(runner.run_e2e_tests())
    
    # 빠른 테스트
    elif arg in ["--fast", "-f"]:
        sys.exit(runner.run_fast_tests())
    
    # 커버리지
    elif arg in ["--coverage", "-c"]:
        sys.exit(runner.run_with_coverage())
    
    # 병렬 실행
    elif arg in ["--parallel", "-p"]:
        num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        sys.exit(runner.run_parallel(num_workers))
    
    # 특정 파일
    elif arg == "--file":
        if len(sys.argv) < 3:
            print("❌ 오류: 파일 경로를 지정해주세요")
            print("예: python run_tests.py --file tests/unit/test_auth.py")
            sys.exit(1)
        sys.exit(runner.run_specific_file(sys.argv[2]))
    
    # 특정 테스트
    elif arg == "--test":
        if len(sys.argv) < 3:
            print("❌ 오류: 테스트 경로를 지정해주세요")
            print("예: python run_tests.py --test tests/unit/test_auth.py::test_login")
            sys.exit(1)
        sys.exit(runner.run_specific_test(sys.argv[2]))
    
    # 실패한 테스트만
    elif arg in ["--failed", "--lf"]:
        sys.exit(runner.run_failed_tests())
    
    # 스모크 테스트
    elif arg == "--smoke":
        sys.exit(runner.run_smoke_tests())
    
    # 보안 테스트
    elif arg == "--security":
        sys.exit(runner.run_security_tests())
    
    # 성능 테스트
    elif arg == "--performance":
        sys.exit(runner.run_performance_tests())
    
    # 중요 테스트
    elif arg == "--critical":
        sys.exit(runner.run_critical_tests())
    
    # HTML 리포트
    elif arg == "--html-report":
        sys.exit(runner.run_with_html_report())
    
    # 커버리지 리포트 보기
    elif arg == "--show-coverage":
        runner.show_coverage_report()
        sys.exit(0)
    
    # 코드 품질 검사
    elif arg in ["--quality", "-q"]:
        sys.exit(runner.check_code_quality())
    
    else:
        print(f"❌ 알 수 없는 옵션: {arg}")
        print("도움말을 보려면: python run_tests.py --help")
        sys.exit(1)


if __name__ == "__main__":
    main()