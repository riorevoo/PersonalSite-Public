import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import launch_check  # noqa: E402

FINISHED_PROFILE = """\
/** Placeholder values were replaced by the owner. */
export const profile = {
  bio: 'A real bio.',
  links: [{ label: 'github', href: 'https://github.com/example' }],
}
"""


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestProfile:
    def test_a_finished_profile_passes_even_if_a_comment_mentions_placeholders(
        self, tmp_path: Path
    ) -> None:
        path = write(tmp_path, "profile.ts", FINISHED_PROFILE)

        assert launch_check.profile_problems(path) == []

    def test_placeholder_text_is_reported_with_its_line(self, tmp_path: Path) -> None:
        path = write(tmp_path, "profile.ts", "a\n  bio: 'Placeholder bio.',\n")

        assert launch_check.profile_problems(path) == [
            "profile.ts:2: placeholder text: bio: 'Placeholder bio.',"
        ]

    def test_a_hash_link_is_reported(self, tmp_path: Path) -> None:
        path = write(tmp_path, "profile.ts", "{ label: 'github', href: '#' },\n")

        problems = launch_check.profile_problems(path)

        assert len(problems) == 1
        assert "a link that goes nowhere" in problems[0]

    def test_the_real_profile_file_is_readable_by_the_check(self) -> None:
        assert isinstance(launch_check.profile_problems(launch_check.PROFILE), list)


class TestKnowledge:
    def test_counts_todo_markers_per_file_and_skips_the_readme(self, tmp_path: Path) -> None:
        write(tmp_path, "profile.md", "TODO(owner): a\nTODO(owner): b\n")
        write(tmp_path, "faq.md", "done\n")
        write(tmp_path, "README.md", "TODO(owner) is explained here\n")
        write(tmp_path, "posts/2026-01-01-x.md", "TODO(owner)\n")

        assert launch_check.knowledge_problems(tmp_path) == [
            "knowledge/posts/2026-01-01-x.md: 1 unfinished TODO(owner) marker(s)",
            "knowledge/profile.md: 2 unfinished TODO(owner) marker(s)",
        ]

    def test_a_finished_knowledge_base_passes(self, tmp_path: Path) -> None:
        write(tmp_path, "profile.md", "All written.\n")

        assert launch_check.knowledge_problems(tmp_path) == []


class TestMain:
    def test_fails_and_lists_problems_while_content_is_unfinished(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        profile = write(tmp_path, "profile.ts", "href: '#'\n")
        knowledge = tmp_path / "knowledge"
        write(knowledge, "faq.md", "TODO(owner)\n")
        monkeypatch.setattr(launch_check, "PROFILE", profile)
        monkeypatch.setattr(launch_check, "KNOWLEDGE", knowledge)

        assert launch_check.main() == 1

        output = capsys.readouterr().out
        assert "Not ready to launch: 2 problem(s)" in output
        assert "knowledge/faq.md" in output

    def test_passes_when_everything_is_written(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(launch_check, "PROFILE", write(tmp_path, "profile.ts", "ok\n"))
        monkeypatch.setattr(launch_check, "KNOWLEDGE", tmp_path / "empty")
        (tmp_path / "empty").mkdir()

        assert launch_check.main() == 0
        assert "Launch check passed" in capsys.readouterr().out
