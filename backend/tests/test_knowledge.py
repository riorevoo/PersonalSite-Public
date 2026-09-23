import logging
import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from app.core.config import BACKEND_ROOT, Settings, get_settings
from app.services.answerer import CANNED
from app.services.knowledge import (
    TODO_MARKER,
    KnowledgeBase,
    KnowledgeError,
    load_knowledge,
    parse_document,
    parse_post,
)
from app.services.runtime import AppServices
from tests.helpers import front_matter, post_text, write_post

EXPERIENCE = """---
title: Work history
tags: [work, jobs]
---
<!-- author note: dropped -->
Intro text before any heading.

## Backend engineer, Acme
Built the ingestion pipeline.

<!-- multi
line note -->
- 40M events a day

## Intern, Globex
Wrote the on-call runbook.
"""


class TestParseDocument:
    @pytest.mark.parametrize(
        ("opening", "inside", "closing"),
        [
            ("````markdown", "```python\n# code\n```", "````"),
            ("~~~markdown", "```\n# code\n```", "~~~"),
            ("````", "```\n## code", "`````"),
            ("```", "``` trailing text\n## code", "```"),
            ("   ~~~~", "~~~\n# code", "   ~~~~"),
        ],
    )
    def test_fences_preserve_code_and_resume_headings(
        self, opening: str, inside: str, closing: str
    ) -> None:
        code = f"{opening}\n{inside}\n{closing}"
        body = f"{code}\n\n## Real heading\nText"
        document, post = parse_post("2026-08-14-example", post_text(body=body))
        assert [chunk.heading for chunk in document.chunks] == [document.title, "Real heading"]
        assert document.chunks[0].text == code
        assert post.body == body

    def test_unclosed_fence_keeps_remaining_headings_as_code(self) -> None:
        body = "````\n```\n# Code\n## Still code"
        document, _ = parse_post("2026-08-14-example", post_text(body=body))
        assert len(document.chunks) == 1
        assert document.chunks[0].text == body

    @pytest.mark.parametrize("opening", ["```bad`info", "    ```"])
    def test_invalid_fence_does_not_hide_a_top_heading(self, opening: str) -> None:
        with pytest.raises(KnowledgeError, match="remove the '# ' heading"):
            parse_post("2026-08-14-example", post_text(body=f"{opening}\n# Heading"))

    def test_top_heading_after_a_closed_fence_is_rejected(self) -> None:
        with pytest.raises(KnowledgeError, match="remove the '# ' heading"):
            parse_post("2026-08-14-example", post_text(body="```\n# code\n```\n# Heading"))

    def test_reads_front_matter_and_sections(self) -> None:
        doc = parse_document("experience", EXPERIENCE)

        assert doc.name == "experience"
        assert doc.title == "Work history"
        assert doc.tags == ("work", "jobs")
        assert [c.heading for c in doc.chunks] == [
            "Work history",  # text before the first heading takes the document title
            "Backend engineer, Acme",
            "Intern, Globex",
        ]
        assert doc.chunks[0].text == "Intro text before any heading."
        assert doc.chunks[1].text == "Built the ingestion pipeline.\n\n\n- 40M events a day"
        assert all(c.source == "experience" and c.title == "Work history" for c in doc.chunks)

    def test_drops_html_comments(self) -> None:
        doc = parse_document("experience", EXPERIENCE)
        assert "author note" not in doc.text()
        assert "multi" not in doc.text()

    def test_without_front_matter_the_title_comes_from_the_file_name(self) -> None:
        doc = parse_document("side-projects", "## One\nText\n")
        assert doc.title == "Side Projects"
        assert doc.tags == ()
        assert [c.heading for c in doc.chunks] == ["One"]

    def test_a_single_tag_string_is_accepted(self) -> None:
        doc = parse_document("x", "---\ntags: solo\n---\n## A\nb\n")
        assert doc.tags == ("solo",)

    def test_empty_front_matter_is_allowed(self) -> None:
        doc = parse_document("x", "---\n---\n## A\nb\n")
        assert doc.title == "X"

    def test_handles_windows_line_endings(self) -> None:
        doc = parse_document("x", "---\r\ntitle: T\r\n---\r\n## A\r\nline one\r\nline two\r\n")
        assert doc.title == "T"
        assert doc.chunks[0].text == "line one\nline two"

    def test_ignores_the_redundant_level_one_title_line(self) -> None:
        doc = parse_document("x", "# X\n\nintro\n\n## A\nb\n")
        assert doc.chunks[0].text == "intro"

    def test_empty_sections_are_skipped(self) -> None:
        doc = parse_document("x", "## Empty\n\n## Full\ntext\n")
        assert [c.heading for c in doc.chunks] == ["Full"]

    def test_invalid_yaml_is_a_clear_error(self) -> None:
        with pytest.raises(KnowledgeError, match=r"x\.md: invalid front matter"):
            parse_document("x", "---\ntitle: [unclosed\n---\n## A\nb\n")

    def test_front_matter_must_be_a_mapping(self) -> None:
        with pytest.raises(KnowledgeError, match="must be a mapping"):
            parse_document("x", "---\n- just\n- a list\n---\n## A\nb\n")

    def test_text_renders_the_whole_document_as_markdown(self) -> None:
        doc = parse_document("experience", EXPERIENCE)
        rendered = doc.text()

        assert rendered.startswith("# Work history\n\nIntro text before any heading.")
        assert "## Backend engineer, Acme\n\nBuilt the ingestion pipeline." in rendered
        assert rendered.count("# Work history") == 1


class TestLoadKnowledge:
    def test_loads_markdown_files_sorted_and_skips_the_readme(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("## B\nbee\n", encoding="utf-8")
        (tmp_path / "a.md").write_text("## A\nay\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("## Not content\nhow to write\n", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

        knowledge = load_knowledge(tmp_path)

        assert [d.name for d in knowledge.documents] == ["a", "b"]
        assert knowledge.document("a") is not None
        assert knowledge.document("missing") is None

    def test_tolerates_a_byte_order_mark(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_bytes(b"\xef\xbb\xbf---\ntitle: T\n---\n## A\nb\n")
        assert load_knowledge(tmp_path).documents[0].title == "T"

    def test_an_empty_directory_is_an_empty_knowledge_base(self, tmp_path: Path) -> None:
        assert load_knowledge(tmp_path).documents == ()

    def test_a_missing_directory_is_a_clear_error(self, tmp_path: Path) -> None:
        with pytest.raises(KnowledgeError, match="knowledge directory not found"):
            load_knowledge(tmp_path / "nope")


class TestKnowledgeBase:
    @pytest.fixture
    def knowledge(self, tmp_path: Path) -> KnowledgeBase:
        (tmp_path / "experience.md").write_text(EXPERIENCE, encoding="utf-8")
        (tmp_path / "boundaries.md").write_text("## Never\nsalary\n", encoding="utf-8")
        (tmp_path / "faq.md").write_text(
            "## what do you build?\nBackends.\n\n## Are you hireable?\nYes.\n", encoding="utf-8"
        )
        return load_knowledge(tmp_path)

    def test_chunks_span_every_document(self, knowledge: KnowledgeBase) -> None:
        assert len(knowledge.chunks) == 3 + 1 + 2

    def test_full_text_joins_documents_and_can_exclude_some(self, knowledge: KnowledgeBase) -> None:
        everything = knowledge.full_text()
        assert "Built the ingestion pipeline." in everything
        assert "salary" in everything

        without_rules = knowledge.full_text(exclude={"boundaries"})
        assert "salary" not in without_rules
        assert "Built the ingestion pipeline." in without_rules

    def test_faq_answer_ignores_case_punctuation_and_spacing(
        self, knowledge: KnowledgeBase
    ) -> None:
        assert knowledge.faq_answer("What do you build?") == "Backends."
        assert knowledge.faq_answer("  what   do you build ") == "Backends."
        assert knowledge.faq_answer("ARE YOU HIREABLE!!!") == "Yes."

    def test_faq_answer_is_none_for_unknown_questions(self, knowledge: KnowledgeBase) -> None:
        assert knowledge.faq_answer("what is your favourite colour?") is None

    def test_faq_answer_skips_an_entry_that_is_still_a_placeholder(self, tmp_path: Path) -> None:
        (tmp_path / "faq.md").write_text(
            f"## done?\nYes.\n\n## not done?\n{TODO_MARKER}: write the answer.\n", encoding="utf-8"
        )
        knowledge = load_knowledge(tmp_path)

        assert knowledge.faq_answer("done?") == "Yes."
        assert knowledge.faq_answer("not done?") is None

    def test_faq_answer_is_none_without_a_faq_document(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("## A\nb\n", encoding="utf-8")
        assert load_knowledge(tmp_path).faq_answer("anything") is None

    def test_unfinished_finds_placeholder_sections(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(
            f"## Done\nreal text\n\n## Not done\n{TODO_MARKER}: write this\n", encoding="utf-8"
        )
        unfinished = load_knowledge(tmp_path).unfinished()
        assert [c.heading for c in unfinished] == ["Not done"]


CODE_BODY = (
    "Intro.\n\n```python\n# a comment\n## not a heading\nprint(1)\n```\n\n## Real section\nText.\n"
)


class TestCodeBlocks:
    def test_lines_that_look_like_headings_inside_a_code_block_are_code(self) -> None:
        doc = parse_document("x", f"---\ntitle: T\n---\n{CODE_BODY}")

        assert [c.heading for c in doc.chunks] == ["T", "Real section"]
        assert "# a comment\n## not a heading\nprint(1)" in doc.chunks[0].text


class TestParsePost:
    def test_reads_the_post_fields(self) -> None:
        document, post = parse_post("2026-08-14-the-pool", post_text())

        assert post.slug == "the-pool"
        assert post.title == "The pool that never drained"
        assert post.dek == "A leak that only appeared under retries."
        assert post.tag == "postgres"
        assert post.date == date(2026, 8, 14)
        assert post.draft is False
        assert post.body.startswith("Intro paragraph.")
        assert "author note" not in post.body
        assert document.name == "posts/2026-08-14-the-pool"
        assert document.post is post
        assert [c.heading for c in document.chunks] == [
            "The pool that never drained",
            "What happened",
        ]

    def test_the_slug_is_the_file_name_without_its_date_prefix(self) -> None:
        assert parse_post("2026-08-14-the-pool", post_text())[1].slug == "the-pool"

    def test_a_file_name_without_a_date_prefix_is_the_slug(self) -> None:
        assert parse_post("the-pool", post_text())[1].slug == "the-pool"

    def test_the_front_matter_can_set_the_slug(self) -> None:
        text = post_text(front_matter(slug="custom-slug"))
        assert parse_post("2026-08-14-the-pool", text)[1].slug == "custom-slug"

    def test_a_quoted_date_is_accepted(self) -> None:
        assert parse_post("p", post_text(front_matter(date='"2026-08-14"')))[1].date == date(
            2026, 8, 14
        )

    def test_draft_can_be_set(self) -> None:
        assert parse_post("p", post_text(front_matter(draft="true")))[1].draft is True

    @pytest.mark.parametrize(
        ("words", "minutes"), [(1, 1), (200, 1), (201, 2), (450, 3), (2000, 10)]
    )
    def test_reading_time_rounds_up_at_200_words_a_minute(self, words: int, minutes: int) -> None:
        body = " ".join(["word"] * words)
        assert parse_post("p", post_text(body=body))[1].read_minutes == minutes

    def test_a_code_block_may_hold_heading_like_lines(self) -> None:
        document, post = parse_post("p", post_text(body=CODE_BODY))

        assert "# a comment" in post.body
        assert [c.heading for c in document.chunks] == [
            "The pool that never drained",
            "Real section",
        ]

    @pytest.mark.parametrize(
        ("front", "message"),
        [
            ("dek: d\ntag: t\ndate: 2026-08-14", "non-empty 'title'"),
            ("title: T\ntag: t\ndate: 2026-08-14", "non-empty 'dek'"),
            ("title: T\ndek: '  '\ntag: t\ndate: 2026-08-14", "non-empty 'dek'"),
            ("title: T\ndek: d\ndate: 2026-08-14", "non-empty 'tag'"),
            ("title: T\ndek: d\ntag: t", "'date' must be a real"),
            ("title: T\ndek: d\ntag: t\ndate: August", "'date' must be a real"),
            ("title: T\ndek: d\ntag: t\ndate: 2026-08-14 10:30:00", "'date' must be a real"),
            ("title: T\ndek: d\ntag: t\ndate: '2026-13-01'", "'date' must be a real"),
            ("title: T\ndek: d\ntag: t\ndate: 2026-02-30", "invalid front matter"),
            (front_matter(slug="Not A Slug"), "slug must be lowercase"),
            (front_matter(draft="maybe"), "'draft' must be true or false"),
        ],
    )
    def test_invalid_front_matter_is_a_clear_error(self, front: str, message: str) -> None:
        with pytest.raises(KnowledgeError, match=rf"posts/p\.md: .*{message}"):
            parse_post("p", post_text(front))

    def test_the_file_name_date_must_match_the_front_matter_date(self) -> None:
        with pytest.raises(
            KnowledgeError, match="starts with 2026-08-15 but the date is 2026-08-14"
        ):
            parse_post("2026-08-15-the-pool", post_text())

    def test_a_post_needs_some_text(self) -> None:
        with pytest.raises(KnowledgeError, match="needs some text"):
            parse_post("p", post_text(body="<!-- only a note -->\n"))

    def test_the_body_may_not_repeat_the_title_as_a_top_heading(self) -> None:
        with pytest.raises(KnowledgeError, match="remove the '# ' heading"):
            parse_post("p", post_text(body="# Title again\n\ntext\n"))


class TestPostsInTheKnowledgeBase:
    def test_published_posts_are_documents_listed_newest_first(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-05-01-old", date="2026-05-01", title="Old one")
        write_post(tmp_path, "2026-08-14-new", date="2026-08-14", title="New one")

        knowledge = load_knowledge(tmp_path)

        assert [p.slug for p in knowledge.posts()] == ["new", "old"]
        assert knowledge.post("old") is not None
        assert knowledge.post("missing") is None
        assert knowledge.document("posts/2026-08-14-new") is not None
        assert "Every failed request left a transaction open." in knowledge.full_text()
        assert {c.source for c in knowledge.chunks} == {
            "posts/2026-05-01-old",
            "posts/2026-08-14-new",
        }

    def test_full_text_can_leave_the_posts_out(self, tmp_path: Path) -> None:
        (tmp_path / "profile.md").write_text(
            "---\ntitle: Profile\n---\n\n## Bio\nA bio.\n", encoding="utf-8"
        )
        write_post(tmp_path, "2026-08-14-new", date="2026-08-14", title="New one")

        knowledge = load_knowledge(tmp_path)

        assert "A bio." in knowledge.full_text(include_posts=False)
        assert "Every failed request left a transaction open." not in knowledge.full_text(
            include_posts=False
        )
        assert "Every failed request left a transaction open." in knowledge.full_text()

    def test_drafts_are_never_part_of_the_chat_knowledge(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-08-14-live", title="Live")
        write_post(
            tmp_path,
            "2026-09-01-secret",
            body="Unpublished thoughts.\n",
            date="2026-09-01",
            draft="true",
        )

        knowledge = load_knowledge(tmp_path)

        assert [p.slug for p in knowledge.posts()] == ["live"]
        assert knowledge.post("secret") is None
        assert "Unpublished thoughts." not in knowledge.full_text()
        assert all("Unpublished" not in c.text for c in knowledge.chunks)
        assert knowledge.document("posts/2026-09-01-secret") is None

    def test_drafts_can_be_listed_for_previews(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-08-14-live", title="Live")
        write_post(tmp_path, "2026-09-01-secret", date="2026-09-01", draft="true")

        knowledge = load_knowledge(tmp_path)

        assert [p.slug for p in knowledge.posts(include_drafts=True)] == ["secret", "live"]
        secret = knowledge.post("secret", include_drafts=True)
        assert secret is not None
        assert secret.draft is True

    def test_a_knowledge_directory_without_posts_has_none(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("## A\nb\n", encoding="utf-8")
        assert load_knowledge(tmp_path).posts() == ()

    def test_the_posts_readme_is_not_a_post(self, tmp_path: Path) -> None:
        (tmp_path / "posts").mkdir()
        (tmp_path / "posts" / "README.md").write_text("how to write posts", encoding="utf-8")
        assert load_knowledge(tmp_path).posts() == ()

    def test_two_posts_may_not_share_a_slug(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-05-01-same", date="2026-05-01")
        write_post(tmp_path, "2026-06-01-same", date="2026-06-01")

        with pytest.raises(
            KnowledgeError,
            match=r"2026-06-01-same\.md: the slug 'same' is already used by "
            r"posts/2026-05-01-same\.md",
        ):
            load_knowledge(tmp_path)

    def test_a_draft_may_not_reuse_a_published_slug(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-05-01-same", date="2026-05-01")
        write_post(tmp_path, "2026-06-01-same", date="2026-06-01", draft="true")

        with pytest.raises(KnowledgeError, match="already used"):
            load_knowledge(tmp_path)

    def test_an_invalid_post_names_its_file(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-08-14-bad", dek="''")
        with pytest.raises(
            KnowledgeError, match=r"posts/2026-08-14-bad\.md: a post needs a non-empty 'dek'"
        ):
            load_knowledge(tmp_path)

    def test_placeholders_in_published_posts_count_as_unfinished(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-08-14-body", body=f"## Todo\n{TODO_MARKER}: write it\n")
        write_post(tmp_path, "2026-08-15-dek", date="2026-08-15", dek=f"'{TODO_MARKER} summary'")

        unfinished = load_knowledge(tmp_path).unfinished()

        assert sorted((c.source, c.heading) for c in unfinished) == [
            ("posts/2026-08-14-body", "Todo"),
            ("posts/2026-08-15-dek", "front matter"),
        ]

    def test_placeholders_in_drafts_do_not_block_production(self, tmp_path: Path) -> None:
        write_post(tmp_path, "2026-08-14-wip", body=f"{TODO_MARKER}: not done\n", draft="true")
        assert load_knowledge(tmp_path).unfinished() == []


class TestGetKnowledge:
    @pytest.fixture(autouse=True)
    def fresh_caches(self) -> Iterator[None]:
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def point_at(self, monkeypatch: pytest.MonkeyPatch, directory: Path, env: str) -> None:
        monkeypatch.setenv("APP_KNOWLEDGE_DIR", str(directory))
        monkeypatch.setenv("APP_ENV", env)
        # Production refuses to start on the localhost default, so name a real origin.
        monkeypatch.setenv("APP_CORS_ORIGINS", '["https://site.example"]')

    def test_defaults_to_the_backend_knowledge_directory(self) -> None:
        assert Settings().knowledge_dir == BACKEND_ROOT / "knowledge"

    def test_is_loaded_once_and_cached(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "a.md").write_text("## A\nfinished\n", encoding="utf-8")
        self.point_at(monkeypatch, tmp_path, "development")

        services = AppServices(Settings())
        assert services.knowledge is services.knowledge

    def test_warns_about_placeholders_in_development(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        (tmp_path / "a.md").write_text(f"## Draft\n{TODO_MARKER}\n", encoding="utf-8")
        self.point_at(monkeypatch, tmp_path, "development")

        with caplog.at_level(logging.WARNING):
            knowledge = AppServices(Settings()).knowledge

        assert len(knowledge.documents) == 1
        assert "1 unfinished section(s): a: Draft" in caplog.text

    def test_refuses_placeholders_in_production(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "a.md").write_text(f"## Draft\n{TODO_MARKER}\n", encoding="utf-8")
        self.point_at(monkeypatch, tmp_path, "production")

        with pytest.raises(KnowledgeError, match="unfinished section"):
            _ = AppServices(Settings()).knowledge

    def test_production_accepts_a_finished_knowledge_base(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        (tmp_path / "a.md").write_text("## Done\nreal\n", encoding="utf-8")
        self.point_at(monkeypatch, tmp_path, "production")

        with caplog.at_level(logging.WARNING):
            assert len(AppServices(Settings()).knowledge.documents) == 1
        assert caplog.text == ""


def faq_headings(knowledge: KnowledgeBase) -> set[str]:
    """The questions faq.md has an entry for, whether or not the entry is finished yet."""
    faq = knowledge.document("faq")
    return {" ".join(c.heading.lower().split()) for c in faq.chunks} if faq else set()


class TestShippedTemplates:
    """The generated public knowledge base is complete in shape but contains no owner facts."""

    def test_the_expected_documents_exist(self) -> None:
        knowledge = load_knowledge(BACKEND_ROOT / "knowledge")
        names = {document.name for document in knowledge.documents if document.post is None}

        assert names == {
            "boundaries",
            "education",
            "experience",
            "faq",
            "interests",
            "profile",
            "projects",
            "skills",
        }
        assert knowledge.unfinished()

    def test_every_suggestion_chip_has_a_faq_entry(self) -> None:
        knowledge = load_knowledge(BACKEND_ROOT / "knowledge")
        source = (BACKEND_ROOT.parent / "frontend/src/content/profile.ts").read_text(
            encoding="utf-8"
        )
        block = re.search(r"suggestions:\s*\[(.*?)\]", source, re.DOTALL)
        assert block, "could not find the suggestions list"
        chips = re.findall(r"'([^']+)'", block.group(1))
        faq = knowledge.document("faq")
        headings = {chunk.heading for chunk in faq.chunks} if faq else set()

        assert len(chips) == 3
        assert set(chips) <= headings
        assert set(CANNED) <= headings
