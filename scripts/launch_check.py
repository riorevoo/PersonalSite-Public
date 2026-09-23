"""Refuse to launch while placeholder content is still in the site.

    uv run --no-project python scripts/launch_check.py

Checks that the page copy in frontend/src/content/profile.ts has no placeholder text or dead
"#" links, and that no TODO(owner) marker is left in the knowledge files. (The backend already
refuses to start in production with such markers; this catches them before a deploy, and covers
profile.ts, which the backend never reads.) Exits 1 and lists every problem it finds.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "frontend" / "src" / "content" / "profile.ts"
KNOWLEDGE = ROOT / "backend" / "knowledge"

TODO_MARKER = "TODO(owner)"
_PLACEHOLDER = re.compile(r"placeholder", re.IGNORECASE)
_DEAD_LINK = re.compile(r"""href:\s*['"]#['"]""")


def profile_problems(path: Path) -> list[str]:
    problems = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if _PLACEHOLDER.search(line) and not line.lstrip().startswith(("*", "//", "/*")):
            problems.append(f"{path.name}:{number}: placeholder text: {line.strip()}")
        if _DEAD_LINK.search(line):
            problems.append(f"{path.name}:{number}: a link that goes nowhere: {line.strip()}")
    return problems


def knowledge_problems(directory: Path) -> list[str]:
    problems = []
    for path in sorted(directory.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        count = path.read_text(encoding="utf-8-sig").count(TODO_MARKER)
        if count:
            relative = path.relative_to(directory).as_posix()
            problems.append(f"knowledge/{relative}: {count} unfinished {TODO_MARKER} marker(s)")
    return problems


def main() -> int:
    problems = [*profile_problems(PROFILE), *knowledge_problems(KNOWLEDGE)]
    if not problems:
        print("Launch check passed: no placeholders left.")
        return 0
    print(f"Not ready to launch: {len(problems)} problem(s)")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
