"""
FloodLink Master Test Runner
Executes the full suite of automated unit, integration, and security tests.
"""

import sys
import subprocess
from pathlib import Path

def run_suite():
    tests_dir = Path(__file__).resolve().parent
    backend_dir = tests_dir.parent

    test_scripts = [
        "tests/test_stage2_full.py",
        "tests/test_stage3_db.py",
        "tests/test_stage4_reports.py",
        "tests/test_stages_5_to_8.py",
        "tests/test_e2e_integration.py",
    ]

    print("=" * 70)
    print("FLOODLINK DISASTER MANAGEMENT PLATFORM: COMPLETE MASTER TEST SUITE")
    print("=" * 70)

    total_suites = len(test_scripts)
    passed_suites = 0

    for script in test_scripts:
        script_path = backend_dir / script
        print(f"\n>>> Running: {script} ...")
        res = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )

        if res.returncode == 0:
            print(res.stdout)
            passed_suites += 1
        else:
            print("ERROR IN SUITE:")
            print(res.stdout)
            print(res.stderr)
            sys.exit(res.returncode)

    print("\n" + "=" * 70)
    print(f"MASTER TEST SUITE SUMMARY: {passed_suites}/{total_suites} TEST SUITES PASSED (100% SUCCESS)")
    print("=" * 70)

if __name__ == "__main__":
    run_suite()
