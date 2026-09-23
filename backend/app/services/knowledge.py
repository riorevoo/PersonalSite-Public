"""The site owner's knowledge base: Markdown files that hold everything the site may say.

Each `*.md` file in the knowledge directory is a document with optional YAML front matter
(`title`, `tags`). Sections start at `## ` headings and become chunks. HTML comments
(`<!-- ... -->`) are author notes and are dropped. Lines that still say `TODO(owner)` mark
unfinished placeholders; the app warns about them, and refuses to start with them in production.

Blog posts live in `posts/` inside the knowledge directory, one file each. They are documents too
and also carry post fields: `title`, `dek`, `tag`, `date`, an optional `slug` and an optional
`draft: true`. Drafts are kept apart from the documents, so nothing unpublished is ever served.
The chat engine does not read posts (`full_text(include_posts=False)`): what a post reveals about
the owner reaches the chat only through reviewed edits to `profile.md` and `interests.md`.

See backend/knowledge/README.md for the writing guide.
"""

import logging
import math
import re
from collections.abc import Collection, Iterator
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml
from fastapi import Request

from app.core.config import Settings

if TYPE_CHECKING:
    from app.services.runtime import AppServices

logger = logging.getLogger(__name__)

TODO_MARKER = "TODO(owner)"
FAQ_DOCUMENT = "faq"
BOUNDARIES_DOCUMENT = "boundaries"
POSTS_DIRECTORY = "posts"
WORDS_PER_MINUTE = 200

_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATED_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})-(.+)")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class KnowledgeError(Exception):
    """The knowledge base is missing, malformed, or not ready for production."""


@dataclass(frozen=True)
class Chunk:
    source: str  # document name (file stem), e.g. "experience"
    title: str  # document title
    heading: str  # section heading; the document title for text before the first heading
    text: str


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    dek: str  # one-sentence summary shown under the title
    tag: str
    date: date
    read_minutes: int
    draft: bool
    body: str  # Markdown, without front matter or author comments


@dataclass(frozen=True)
class Document:
    name: str
    title: str
    tags: tuple[str, ...]
    chunks: tuple[Chunk, ...]
    post: Post | None = None

    def text(self) -> str:
        """The whole document as Markdown, ready to place in a prompt."""
        parts = [f"# {self.title}"]
        for chunk in self.chunks:
            heading = f"## {chunk.heading}\n\n" if chunk.heading != self.title else ""
            parts.append(f"{heading}{chunk.text}")
        return "\n\n".join(parts)


def _normalise(question: str) -> str:
    """Case, punctuation and spacing differences should not stop a question matching."""
    return " ".join(re.sub(r"[^a-z0-9 ]+", "", question.lower()).split())


@dataclass(frozen=True)
class KnowledgeBase:
    documents: tuple[Document, ...]
    # Posts marked `draft: true`. They are not documents, so no chunk or prompt ever includes them.
    drafts: tuple[Post, ...] = ()

    @property
    def chunks(self) -> tuple[Chunk, ...]:
        return tuple(chunk for document in self.documents for chunk in document.chunks)

    def document(self, name: str) -> Document | None:
        return next((d for d in self.documents if d.name == name), None)

    def posts(self, *, include_drafts: bool = False) -> tuple[Post, ...]:
        """Published posts, newest first; drafts too when asked (for previews while writing)."""
        found = [d.post for d in self.documents if d.post is not None]
        if include_drafts:
            found.extend(self.drafts)
        return tuple(sorted(found, key=lambda post: (post.date, post.slug), reverse=True))

    def post(self, slug: str, *, include_drafts: bool = False) -> Post | None:
        return next((p for p in self.posts(include_drafts=include_drafts) if p.slug == slug), None)

    def full_text(self, *, exclude: Collection[str] = (), include_posts: bool = True) -> str:
        """Every document (minus any excluded by name, and posts unless asked) as Markdown."""
        return "\n\n".join(
            d.text()
            for d in self.documents
            if d.name not in exclude and (include_posts or d.post is None)
        )

    def unfinished(self) -> list[Chunk]:
        """Sections that still contain a TODO(owner) placeholder."""
        found = [chunk for chunk in self.chunks if TODO_MARKER in chunk.text]
        for document in self.documents:
            post = document.post
            if post and TODO_MARKER in f"{post.title} {post.dek} {post.tag}":
                found.append(
                    Chunk(document.name, post.title, heading="front matter", text=post.dek)
                )
        return found

    def faq_answer(self, question: str) -> str | None:
        """The hand-written answer whose faq heading matches the question, if there is one.

        An entry that still says TODO(owner) is a placeholder, not an answer: it is skipped, so the
        question reaches the model instead of showing a visitor the placeholder text.
        """
        faq = self.document(FAQ_DOCUMENT)
        if faq is None:
            return None
        wanted = _normalise(question)
        return next(
            (
                c.text
                for c in faq.chunks
                if _normalise(c.heading) == wanted and TODO_MARKER not in c.text
            ),
            None,
        )


def _body_lines(body: str) -> Iterator[tuple[str, bool]]:
    """Yield lines and whether they belong to a fenced code block, including its fences."""
    fence = ""
    for line in body.splitlines():
        match = _FENCE.match(line)
        if fence:
            yield line, True
            if (
                match
                and match[1][0] == fence[0]
                and len(match[1]) >= len(fence)
                and not match[2].strip()
            ):
                fence = ""
        elif match and (match[1][0] == "~" or "`" not in match[2]):
            fence = match[1]
            yield line, True
        else:
            yield line, False


def _chunk(name: str, title: str, body: str) -> tuple[Chunk, ...]:
    chunks: list[Chunk] = []
    heading = title
    lines: list[str] = []

    def flush() -> None:
        text = "\n".join(lines).strip("\r\n")
        if text.strip():
            chunks.append(Chunk(source=name, title=title, heading=heading, text=text))
        lines.clear()

    for line, in_fence in _body_lines(body):
        # Inside a code block a "## " or "# " line is code (often a comment), not a heading.
        if not in_fence and line.startswith("## "):
            flush()
            heading = line[3:].strip()
        elif in_fence or not line.startswith("# "):  # "# Title" is redundant with the front matter
            lines.append(line)
    flush()
    return tuple(chunks)


def _read(name: str, raw: str) -> tuple[dict[str, object], str]:
    """Split a file into its front matter mapping and its body without author comments."""
    text = raw.replace("\r\n", "\n")
    meta: object = {}
    body = text
    match = _FRONT_MATTER.match(text)
    if match:
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        # PyYAML raises a plain ValueError for an impossible date such as 2026-02-30.
        except (yaml.YAMLError, ValueError) as error:
            raise KnowledgeError(f"{name}.md: invalid front matter: {error}") from error
        body = text[match.end() :]
    if not isinstance(meta, dict):
        raise KnowledgeError(f"{name}.md: front matter must be a mapping of keys to values")
    return meta, _COMMENT.sub("", body)


def _document(name: str, meta: dict[str, object], body: str) -> Document:
    title = str(
        meta.get("title") or name.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").title()
    )
    raw_tags = meta.get("tags") or []
    tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else (str(raw_tags),)
    return Document(name=name, title=title, tags=tags, chunks=_chunk(name, title, body))


def parse_document(name: str, raw: str) -> Document:
    meta, body = _read(name, raw)
    return _document(name, meta, body)


def _required_text(name: str, meta: dict[str, object], key: str) -> str:
    value = meta.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeError(f"{name}.md: a post needs a non-empty '{key}' in its front matter")
    return value.strip()


def _post_date(name: str, meta: dict[str, object]) -> date:
    value = meta.get("date")
    # YAML turns an unquoted 2026-08-14 into a date; a time of day (a datetime) is not wanted.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and _ISO_DATE.fullmatch(value.strip()):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise KnowledgeError(f"{name}.md: a post's 'date' must be a real YYYY-MM-DD date")


def _has_top_heading(body: str) -> bool:
    """True when the body has a `# ` heading outside a code block (the page supplies the title)."""
    return any(not in_fence and line.startswith("# ") for line, in_fence in _body_lines(body))


def _post(stem: str, name: str, meta: dict[str, object], body: str) -> Post:
    published = _post_date(name, meta)
    dated = _DATED_NAME.fullmatch(stem)
    slug = meta.get("slug", dated.group(2) if dated else stem)
    if not isinstance(slug, str) or not _SLUG.fullmatch(slug):
        raise KnowledgeError(f"{name}.md: the slug must be lowercase words joined by hyphens")
    if dated and dated.group(1) != published.isoformat():
        raise KnowledgeError(
            f"{name}.md: the file name starts with {dated.group(1)} but the date is {published}"
        )
    draft = meta.get("draft", False)
    if not isinstance(draft, bool):
        raise KnowledgeError(f"{name}.md: 'draft' must be true or false")
    text = body.strip("\r\n")
    if not text.strip():
        raise KnowledgeError(f"{name}.md: a post needs some text")
    if _has_top_heading(text):
        raise KnowledgeError(
            f"{name}.md: remove the '# ' heading; the title comes from the front matter"
        )
    return Post(
        slug=slug,
        title=_required_text(name, meta, "title"),
        dek=_required_text(name, meta, "dek"),
        tag=_required_text(name, meta, "tag"),
        date=published,
        read_minutes=max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE)),
        draft=draft,
        body=text,
    )


def parse_post(stem: str, raw: str) -> tuple[Document, Post]:
    """Read one file from `posts/`; `stem` is its file name without the extension."""
    name = f"{POSTS_DIRECTORY}/{stem}"
    meta, body = _read(name, raw)
    post = _post(stem, name, meta, body)
    return replace(_document(name, meta, body), post=post), post


def _markdown_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.md") if p.name.lower() != "readme.md")


def load_knowledge(directory: Path) -> KnowledgeBase:
    if not directory.is_dir():
        raise KnowledgeError(f"knowledge directory not found: {directory}")
    documents = [
        parse_document(path.stem, path.read_text(encoding="utf-8-sig"))
        for path in _markdown_files(directory)
    ]

    drafts: list[Post] = []
    slugs: dict[str, str] = {}
    posts_directory = directory / POSTS_DIRECTORY
    for path in _markdown_files(posts_directory) if posts_directory.is_dir() else []:
        document, post = parse_post(path.stem, path.read_text(encoding="utf-8-sig"))
        if post.slug in slugs:
            raise KnowledgeError(
                f"{POSTS_DIRECTORY}/{path.stem}.md: the slug '{post.slug}' is already used by "
                f"{POSTS_DIRECTORY}/{slugs[post.slug]}.md"
            )
        slugs[post.slug] = path.stem
        if post.draft:
            drafts.append(post)
        else:
            documents.append(document)
    return KnowledgeBase(documents=tuple(documents), drafts=tuple(drafts))


def build_knowledge(settings: Settings) -> KnowledgeBase:
    """Load and validate knowledge using the owning application's settings."""
    knowledge = load_knowledge(settings.knowledge_dir)
    unfinished = knowledge.unfinished()
    if unfinished:
        places = ", ".join(sorted({f"{c.source}: {c.heading}" for c in unfinished}))
        message = f"knowledge base has {len(unfinished)} unfinished section(s): {places}"
        if settings.env == "production":
            raise KnowledgeError(message)
        logger.warning(message)
    return knowledge


def get_knowledge(request: Request) -> KnowledgeBase:
    services = cast("AppServices", request.app.state.services)
    return services.knowledge
