from pathlib import Path
import subprocess
import sys


SRC_DIR = Path(__file__).resolve().parents[1]


def run_trace(shape: str) -> str:
    result = subprocess.run(
        [
            sys.executable, "-m", "lab9.trace_case",
            "--shape", shape, "--claim", "C-002", "--seed", "11",
        ],
        cwd=SRC_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


def test_c002_trace_regression_detected_and_fixed():
    broken = run_trace("seeded_regression")
    fixed = run_trace("fixed")

    assert "lab8 grader: FAIL" in broken, broken
    assert "lab8 grader: PASS" in fixed, fixed