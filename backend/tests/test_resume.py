"""GET /api/resume: the newest resume PDF, for the site's resume link."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import BACKEND_ROOT, Settings
from app.main import create_app
from app.services.resume import latest_resume_pdf

OLD, NEW = b"%PDF-1.4 the old one", b"%PDF-1.4 the newest one"


@pytest.fixture
def resume_dir(tmp_path: Path) -> Path:
    (tmp_path / "a.md").write_text("## A\nb\n", encoding="utf-8")  # a knowledge base to load
    folder = tmp_path / "resume"
    folder.mkdir()
    (folder / "resume_01_03_2026.pdf").write_bytes(OLD)
    (folder / "resume_21_09_2026.pdf").write_bytes(NEW)
    # None of these may be picked, even though they look newer:
    (folder / "resume_05_05_2027.docx").write_bytes(b"a newer Word file")
    (folder / "resume_31_02_2028.pdf").write_bytes(b"no such day")
    (folder / "resume_latest.pdf").write_bytes(b"not named by date")
    return tmp_path


@pytest.fixture
def client(resume_dir: Path) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(knowledge_dir=resume_dir))) as client:
        yield client


class TestLatestResumePdf:
    def test_picks_the_newest_dated_pdf_and_ignores_everything_else(self, resume_dir: Path) -> None:
        assert (
            latest_resume_pdf(resume_dir / "resume") == resume_dir / "resume/resume_21_09_2026.pdf"
        )

    def test_is_none_without_a_pdf(self, tmp_path: Path) -> None:
        (tmp_path / "resume_21_09_2026.md").write_text("text", encoding="utf-8")

        assert latest_resume_pdf(tmp_path) is None

    def test_is_none_when_the_folder_is_missing(self, tmp_path: Path) -> None:
        assert latest_resume_pdf(tmp_path / "nope") is None

    def test_the_shipped_knowledge_has_a_pdf_for_the_site_to_link_to(self) -> None:
        # Without it the résumé link on the live site would be a 404.
        assert latest_resume_pdf(BACKEND_ROOT / "knowledge" / "resume") is not None


class TestGetResume:
    def test_serves_the_newest_pdf_for_the_browser_to_show(self, client: TestClient) -> None:
        response = client.get("/api/resume")

        assert response.status_code == 200
        assert response.content == NEW
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"].startswith("inline")
        assert "resume.pdf" in response.headers["content-disposition"]
        assert response.headers["cache-control"] == "public, max-age=3600"

    def test_a_missing_pdf_is_a_404(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("## A\nb\n", encoding="utf-8")

        with TestClient(create_app(Settings(knowledge_dir=tmp_path))) as client:
            response = client.get("/api/resume")

        assert response.status_code == 404
        assert response.json() == {"detail": "Resume not found."}

    def test_serves_a_new_file_without_a_restart(
        self, resume_dir: Path, client: TestClient
    ) -> None:
        (resume_dir / "resume" / "resume_01_01_2027.pdf").write_bytes(b"%PDF-1.4 next year")

        assert client.get("/api/resume").content == b"%PDF-1.4 next year"
