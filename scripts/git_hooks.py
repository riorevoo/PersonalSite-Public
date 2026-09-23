"""Git hooks and CI entry point for the house rules.

    python scripts/git_hooks.py pre-commit          fast checks on what is staged
    python scripts/git_hooks.py commit-msg FILE     check the commit message
    python scripts/git_hooks.py pre-push            the full check (skips the browser tests)
    python scripts/git_hooks.py ci                  house rules over the whole repo and history

Enable the hooks once per clone:  git config core.hooksPath .githooks
"""

import shutil
import subprocess
import sys
from pathlib import Path

import house_rules as rules

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SUFFIXES = {".ts", ".tsx", ".css", ".json", ".html"}


def git(*args: str, check: bool = True) -> bytes:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=check)
    return result.stdout


def staged_paths() -> list[str]:
    raw = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [p for p in raw.decode("utf-8").split("\0") if p]


def report(problems: list[rules.Problem]) -> int:
    for problem in problems:
        print(f"house rules: {problem.render()}", file=sys.stderr)
    return 1 if problems else 0


def run_tool(label: str, command: list[str], cwd: Path) -> bool:
    print(f"  {label} ...", flush=True)
    executable = shutil.which(command[0])
    if executable is None:
        print(f"house rules: cannot run {label}: '{command[0]}' is not installed", file=sys.stderr)
        return False
    result = subprocess.run([executable, *command[1:]], cwd=cwd)
    return result.returncode == 0


def pre_commit() -> int:
    paths = staged_paths()
    if not paths:
        return 0

    problems: list[rules.Problem] = []
    ident = git("var", "GIT_AUTHOR_IDENT").decode("utf-8").strip()
    problems += rules.check_identity(ident)
    for path in paths:
        problems += rules.check_local_only(path)
        blob = git("show", f":{path}")  # what will actually be committed, not the working copy
        problems += rules.find_dashes(path, blob)
    if problems:
        return report(problems)

    ok = True
    # Python in backend/ and in the repo-level scripts/ is checked with the backend's tooling.
    python = [
        p[len("backend/") :] if p.startswith("backend/") else f"../{p}"
        for p in paths
        if p.endswith(".py") and (p.startswith("backend/") or p.startswith("scripts/"))
    ]
    if python:
        backend = ROOT / "backend"
        config = ["--config", "pyproject.toml"]
        ok &= run_tool("ruff check", ["uv", "run", "ruff", "check", *config, *python], backend)
        ok &= run_tool(
            "ruff format", ["uv", "run", "ruff", "format", "--check", *config, *python], backend
        )
        ok &= run_tool("mypy", ["uv", "run", "mypy"], backend)

    frontend = [
        p[len("frontend/") :]
        for p in paths
        if p.startswith("frontend/")
        and Path(p).suffix in FRONTEND_SUFFIXES
        and not p.endswith("package-lock.json")
        and not p.endswith("schema.d.ts")
    ]
    if frontend:
        ok &= run_tool("prettier", ["npx", "prettier", "--check", *frontend], ROOT / "frontend")
        ok &= run_tool("lint", ["npm", "run", "lint"], ROOT / "frontend")
    if not ok:
        print("house rules: fix the problems above (or `git commit --no-verify`).", file=sys.stderr)
    return 0 if ok else 1


def commit_msg(message_file: str) -> int:
    message = Path(message_file).read_text(encoding="utf-8")
    return report(rules.check_commit_message(message))


def pre_push() -> int:
    check = ROOT / "scripts" / "check.py"
    result = subprocess.run([sys.executable, str(check), "--skip-e2e"], cwd=ROOT)
    return result.returncode


def ci() -> int:
    """Whole-repo version of the rules: every tracked file and every commit in history."""
    problems: list[rules.Problem] = []
    tracked = [p for p in git("ls-files", "-z").decode("utf-8").split("\0") if p]
    for path in tracked:
        problems += rules.check_local_only(path)
        problems += rules.find_dashes(path, (ROOT / path).read_bytes())

    log = git("log", "--format=%H%x1f%an <%ae> 0 +0000%x1f%B%x1e").decode("utf-8")
    for entry in filter(None, (e.strip("\n") for e in log.split("\x1e"))):
        sha, ident, message = entry.split("\x1f", 2)
        problems += rules.check_identity(ident, where=f"commit {sha[:8]} author")
        problems += [
            rules.Problem(f"commit {sha[:8]}", p.message)
            for p in rules.check_commit_message(message)
        ]
    if not problems:
        print(f"house rules: {len(tracked)} files and all commits are clean.")
    return report(problems)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else ""
    if command == "pre-commit":
        return pre_commit()
    if command == "commit-msg" and len(argv) > 2:
        return commit_msg(argv[2])
    if command == "pre-push":
        return pre_push()
    if command == "ci":
        return ci()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
