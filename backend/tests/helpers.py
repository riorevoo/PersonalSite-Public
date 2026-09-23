"""Builders for blog post files, shared by the knowledge and posts tests."""

from pathlib import Path

POST_BODY = (
    "<!-- author note: dropped -->\n"
    "Intro paragraph.\n\n"
    "## What happened\n"
    "Every failed request left a transaction open.\n"
)


def front_matter(**fields: str) -> str:
    merged = {
        "title": "The pool that never drained",
        "dek": "A leak that only appeared under retries.",
        "tag": "postgres",
        "date": "2026-08-14",
        **fields,
    }
    return "\n".join(f"{key}: {value}" for key, value in merged.items())


def post_text(front: str | None = None, body: str = POST_BODY) -> str:
    return f"---\n{front if front is not None else front_matter()}\n---\n{body}"


def write_post(directory: Path, stem: str, body: str = POST_BODY, **fields: str) -> None:
    posts = directory / "posts"
    posts.mkdir(exist_ok=True)
    (posts / f"{stem}.md").write_text(post_text(front_matter(**fields), body), encoding="utf-8")
