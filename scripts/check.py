"""Run every check for both apps, in the same order as CI, and print a summary.

    uv run --no-project python scripts/check.py              everything, including browser tests
    uv run --no-project python scripts/check.py --skip-e2e   skip the browser tests (faster)
    uv run --no-project python scripts/check.py --only backend|frontend|house-rules

Runs every step even after a failure so one run shows all problems; exits 1 if any step failed.
"""

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


@dataclass(frozen=True)
class Step:
    group: str
    name: str
    command: tuple[str, ...]
    cwd: Path
    e2e: bool = False


STEPS = (
    Step(
        "house-rules",
        "dashes, identity, local-only files",
        (sys.executable, "scripts/git_hooks.py", "ci"),
        ROOT,
    ),
    Step(
        "backend",
        "ruff check",
        ("uv", "run", "ruff", "check", ".", "../scripts", "--config", "pyproject.toml"),
        BACKEND,
    ),
    Step(
        "backend",
        "ruff format",
        ("uv", "run", "ruff", "format", "--check", ".", "../scripts", "--config", "pyproject.toml"),
        BACKEND,
    ),
    Step("backend", "mypy", ("uv", "run", "mypy"), BACKEND),
    Step("backend", "pytest + coverage", ("uv", "run", "pytest", "-q"), BACKEND),
    Step("frontend", "prettier", ("npm", "run", "format:check"), FRONTEND),
    Step("frontend", "lint", ("npm", "run", "lint"), FRONTEND),
    Step("frontend", "typecheck", ("npm", "run", "typecheck"), FRONTEND),
    Step("frontend", "api types in sync", ("npm", "run", "types:check"), FRONTEND),
    Step("frontend", "unit tests + coverage", ("npm", "run", "test:coverage"), FRONTEND),
    Step("frontend", "build", ("npm", "run", "build"), FRONTEND),
    Step("frontend", "end-to-end tests", ("npm", "run", "e2e"), FRONTEND, e2e=True),
)


def run(step: Step) -> tuple[bool, float]:
    print(f"\n==> {step.group}: {step.name}", flush=True)
    executable = shutil.which(step.command[0]) or step.command[0]
    started = time.perf_counter()
    try:
        result = subprocess.run([executable, *step.command[1:]], cwd=step.cwd)
        passed = result.returncode == 0
    except FileNotFoundError:
        print(f"    cannot run '{step.command[0]}': not installed", file=sys.stderr)
        passed = False
    return passed, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--skip-e2e", action="store_true", help="skip the Playwright browser tests")
    parser.add_argument(
        "--only", choices=["backend", "frontend", "house-rules"], help="run one group"
    )
    args = parser.parse_args()

    steps = [
        s
        for s in STEPS
        if (not args.only or s.group == args.only) and not (args.skip_e2e and s.e2e)
    ]
    results = [(step, *run(step)) for step in steps]

    print("\n" + "=" * 60)
    for step, passed, seconds in results:
        print(f"{'PASS' if passed else 'FAIL'}  {step.group:<12} {step.name:<36} {seconds:5.1f}s")
    failed = [step for step, passed, _ in results if not passed]
    print("=" * 60)
    print("All checks passed." if not failed else f"{len(failed)} check(s) failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
