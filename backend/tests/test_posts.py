from collections.abc import Callable, Iterator
from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.knowledge import KnowledgeError
from tests.helpers import write_post

BODY = "<!-- note -->\nFirst paragraph.\n\n## A section\nMore text.\n"


@pytest.fixture
def knowledge_dir(tmp_path: Path) -> Path:
    write_post(tmp_path, "2026-05-01-older", body=BODY, date="2026-05-01", title="Older post")
    write_post(tmp_path, "2026-08-14-newer", body=BODY, date="2026-08-14", title="Newer post")
    write_post(
        tmp_path,
        "2026-09-01-wip",
        body="Not ready.\n",
        date="2026-09-01",
        title="Work in progress",
        draft="true",
    )
    return tmp_path


@pytest.fixture
def make_client(knowledge_dir: Path) -> Iterator[Callable[..., TestClient]]:
    """Exercise real startup and app-scoped knowledge, closing every client after the test."""
    with ExitStack() as stack:

        def build(**settings: object) -> TestClient:
            app = create_app(Settings(knowledge_dir=knowledge_dir, **settings))  # type: ignore[arg-type]
            return stack.enter_context(TestClient(app))

        yield build


class TestListPosts:
    def test_lists_published_posts_newest_first_without_bodies(
        self, make_client: Callable[..., TestClient]
    ) -> None:
        response = make_client().get("/api/posts")

        assert response.status_code == 200
        assert response.json() == [
            {
                "slug": "newer",
                "title": "Newer post",
                "dek": "A leak that only appeared under retries.",
                "tag": "postgres",
                "date": "2026-08-14",
                "read_minutes": 1,
                "draft": False,
            },
            {
                "slug": "older",
                "title": "Older post",
                "dek": "A leak that only appeared under retries.",
                "tag": "postgres",
                "date": "2026-05-01",
                "read_minutes": 1,
                "draft": False,
            },
        ]

    def test_drafts_are_hidden_by_default(self, make_client: Callable[..., TestClient]) -> None:
        slugs = [post["slug"] for post in make_client().get("/api/posts").json()]
        assert "wip" not in slugs

    def test_drafts_are_listed_first_and_marked_when_previewing(
        self, make_client: Callable[..., TestClient]
    ) -> None:
        posts = make_client(show_drafts=True).get("/api/posts").json()

        assert [post["slug"] for post in posts] == ["wip", "newer", "older"]
        assert [post["draft"] for post in posts] == [True, False, False]


class TestGetPost:
    def test_returns_the_markdown_body(self, make_client: Callable[..., TestClient]) -> None:
        response = make_client().get("/api/posts/newer")

        assert response.status_code == 200
        post = response.json()
        assert post["title"] == "Newer post"
        assert post["body"] == "First paragraph.\n\n## A section\nMore text."
        assert "note" not in post["body"]  # author comments are dropped

    def test_an_unknown_slug_is_a_404(self, make_client: Callable[..., TestClient]) -> None:
        response = make_client().get("/api/posts/nope")

        assert response.status_code == 404
        assert response.json() == {"detail": "Post not found."}

    def test_a_draft_is_a_404_for_visitors(self, make_client: Callable[..., TestClient]) -> None:
        assert make_client().get("/api/posts/wip").status_code == 404

    def test_a_draft_can_be_previewed(self, make_client: Callable[..., TestClient]) -> None:
        response = make_client(show_drafts=True).get("/api/posts/wip")

        assert response.status_code == 200
        assert response.json()["draft"] is True


class TestSettings:
    def test_drafts_are_never_shown_in_production(self) -> None:
        with pytest.raises(ValidationError, match="APP_SHOW_DRAFTS must be off in production"):
            Settings(env="production", cors_origins=["https://site.example"], show_drafts=True)


class TestStartup:
    """The app loads the knowledge base when it starts, using the real settings."""

    @pytest.fixture(autouse=True)
    def fresh_caches(self, monkeypatch: pytest.MonkeyPatch, knowledge_dir: Path) -> Iterator[None]:
        monkeypatch.setenv("APP_KNOWLEDGE_DIR", str(knowledge_dir))
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_serves_posts_from_the_configured_directory(self) -> None:
        with TestClient(create_app()) as client:
            slugs = [post["slug"] for post in client.get("/api/posts").json()]

        assert slugs == ["newer", "older"]

    def test_a_broken_post_stops_the_app_from_starting(self, knowledge_dir: Path) -> None:
        write_post(knowledge_dir, "2026-10-01-broken", date="2026-10-01", dek="''")

        with pytest.raises(KnowledgeError, match=r"posts/2026-10-01-broken\.md"):  # noqa: SIM117
            with TestClient(create_app()):
                pass

    def test_explicit_missing_directory_stops_startup(self, tmp_path: Path) -> None:
        settings = Settings(knowledge_dir=tmp_path / "missing")
        with (
            pytest.raises(KnowledgeError, match="knowledge directory not found"),
            TestClient(create_app(settings)),
        ):
            pass

    def test_apps_use_their_own_knowledge(self, knowledge_dir: Path, tmp_path: Path) -> None:
        other = tmp_path / "other"
        other.mkdir()
        write_post(other, "2026-01-01-separate", date="2026-01-01")
        with (
            TestClient(create_app(Settings(knowledge_dir=knowledge_dir))) as first,
            TestClient(create_app(Settings(knowledge_dir=other))) as second,
        ):
            assert [p["slug"] for p in first.get("/api/posts").json()] == ["newer", "older"]
            assert [p["slug"] for p in second.get("/api/posts").json()] == ["separate"]
            assert first.get("/api/posts/separate").status_code == 404
            assert second.get("/api/posts/newer").status_code == 404

    def test_explicit_production_settings_reject_placeholders(self, knowledge_dir: Path) -> None:
        (knowledge_dir / "profile.md").write_text("TODO(owner): finish", encoding="utf-8")
        settings = Settings(
            env="production", knowledge_dir=knowledge_dir, cors_origins=["https://site.example"]
        )
        with (
            pytest.raises(KnowledgeError, match="unfinished section"),
            TestClient(create_app(settings)),
        ):
            pass
