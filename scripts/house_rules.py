"""Repository house rules, shared by the git hooks, the check script and CI.

Pure functions with no git or filesystem access, so they are easy to test. The rules:

- No em dashes or en dashes in any text file.
- No Claude co-author trailers or "generated with" lines in commit messages.
- Commits use the GitHub noreply identity, so a personal name or email never lands in history.
- Local-only files (agent notes, the tracker, env files) are never committed.
"""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

# Built with chr() on purpose: an escape sequence can be turned into the literal character by an
# editor, a formatter or a tool, which would put a dash in this file and break its own rule.
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)

BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".pdf", ".zip"}
)

# Files that stay on the owner's machine (also git-ignored; this catches a forced add).
LOCAL_ONLY_NAMES = frozenset({"CLAUDE.md", "project_tracker.md", "PS-5_engine_options.md"})
# Everything private lives in this folder (also excluded via .git/info/exclude).
LOCAL_ONLY_FOLDER = "offline"
_ENV_FILE = re.compile(r"(^|/)\.env(\.(?!example$)[^/]+)?$")

NOREPLY_SUFFIX = "@users.noreply.github.com"

_CO_AUTHOR = re.compile(r"^\s*co-authored-by:.*(claude|anthropic)", re.IGNORECASE | re.MULTILINE)
_GENERATED_WITH = re.compile(r"generated with\b.*\bclaude", re.IGNORECASE)
_ANTHROPIC_NOREPLY = re.compile(r"noreply@anthropic\.com", re.IGNORECASE)
_IDENT_EMAIL = re.compile(r"<([^<>]*)>")


@dataclass(frozen=True)
class Problem:
    where: str
    message: str

    def render(self) -> str:
        return f"{self.where}: {self.message}"


def is_binary_path(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in BINARY_SUFFIXES


def find_dashes(path: str, data: bytes) -> list[Problem]:
    """Every line of a text file that contains an em dash or an en dash."""
    if is_binary_path(path):
        return []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []  # not text
    problems = []
    for number, line in enumerate(text.splitlines(), start=1):
        if EM_DASH in line or EN_DASH in line:
            problems.append(
                Problem(f"{path}:{number}", "contains an em or en dash; use a colon, comma or 'to'")
            )
    return problems


def check_local_only(path: str) -> list[Problem]:
    pure = PurePosixPath(path)
    in_private_folder = pure.parts[:1] == (LOCAL_ONLY_FOLDER,)
    if pure.name in LOCAL_ONLY_NAMES or in_private_folder or _ENV_FILE.search(path):
        return [
            Problem(
                path,
                "is local-only (private notes, offline files or secrets) and must not be committed",
            )
        ]
    return []


def check_commit_message(message: str) -> list[Problem]:
    # Lines starting with '#' are git's own comments and are not part of the message.
    text = "\n".join(line for line in message.splitlines() if not line.startswith("#"))
    problems = []
    if _CO_AUTHOR.search(text):
        problems.append(Problem("commit message", "has a Claude/Anthropic Co-Authored-By trailer"))
    if _GENERATED_WITH.search(text):
        problems.append(Problem("commit message", "has a 'Generated with ... Claude' line"))
    if _ANTHROPIC_NOREPLY.search(text):
        problems.append(Problem("commit message", "mentions the Anthropic noreply address"))
    if EM_DASH in text or EN_DASH in text:
        problems.append(Problem("commit message", "contains an em or en dash"))
    return problems


def check_identity(ident: str, *, where: str = "commit author") -> list[Problem]:
    """`ident` looks like 'Name <email> 1700000000 +0000' (git var GIT_AUTHOR_IDENT)."""
    match = _IDENT_EMAIL.search(ident)
    email = match.group(1) if match else ""
    if email.lower().endswith(NOREPLY_SUFFIX):
        return []
    return [
        Problem(
            where,
            f"uses '{email or ident}', not a GitHub noreply address. In this repo run "
            "`git config user.name <github-username>` and "
            "`git config user.email <id>+<github-username>@users.noreply.github.com`",
        )
    ]
