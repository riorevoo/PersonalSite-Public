"""Resume files: backend/knowledge/resume/resume_dd_mm_yyyy.<ext>, and the newest date wins."""

import re
from datetime import date
from pathlib import Path

RESUME_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "resume"
EXTENSIONS = "pdf|docx|md|txt"
NAME = re.compile(rf"resume_(\d{{2}})_(\d{{2}})_(\d{{4}})\.({EXTENSIONS})")


def resume_date(name: str) -> date | None:
    """The date in a resume file name, or None if the name does not follow the format."""
    match = NAME.fullmatch(name)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.group(1, 2, 3))
    try:
        return date(year, month, day)
    except ValueError:  # for example 31_02_2026
        return None


def resume_files() -> list[Path]:
    return sorted(p for p in RESUME_DIR.iterdir() if p.is_file()) if RESUME_DIR.is_dir() else []


class TestNamingFormat:
    def test_accepts_day_month_year(self) -> None:
        assert resume_date("resume_21_09_2026.pdf") == date(2026, 9, 21)
        assert resume_date("resume_01_12_2027.docx") == date(2027, 12, 1)
        assert resume_date("resume_05_03_2026.md") == date(2026, 3, 5)

    def test_rejects_other_shapes_and_impossible_dates(self) -> None:
        for name in (
            "resume_2026_09_21.pdf",  # year first
            "resume_31_02_2026.pdf",  # no such day
            "resume_21_13_2026.pdf",  # no such month
            "resume_21-09-2026.pdf",
            "Resume_21_09_2026.pdf",
            "resume_21_09_2026",
            "resume_21_09_2026.exe",
            "cv_21_09_2026.pdf",
            "resume_1_9_2026.pdf",
        ):
            assert resume_date(name) is None, name


class TestTheResumeFolder:
    def test_every_file_follows_the_format(self) -> None:
        for path in resume_files():
            assert resume_date(path.name), (
                f"{path.name}: name resume files resume_dd_mm_yyyy.pdf (or .docx, .md, .txt), "
                "for example resume_21_09_2026.pdf"
            )

    def test_no_two_files_share_a_date(self) -> None:
        dates = [resume_date(path.name) for path in resume_files()]

        assert len(dates) == len(set(dates))
