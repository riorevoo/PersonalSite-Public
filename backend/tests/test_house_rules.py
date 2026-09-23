"""The house rules: what they accept, what they reject, and that the wording of the rules holds."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import house_rules as rules  # noqa: E402

EM = chr(0x2014)
EN = chr(0x2013)
NOREPLY = "1234+someone@users.noreply.github.com"


class TestDashes:
    def test_finds_em_and_en_dashes_with_line_numbers(self) -> None:
        text = f"clean line\nan em{EM}dash\nfine\na range 2{EN}5\n".encode()

        problems = rules.find_dashes("docs/a.md", text)

        assert [p.where for p in problems] == ["docs/a.md:2", "docs/a.md:4"]
        assert "dash" in problems[0].message

    def test_ordinary_hyphens_and_minus_signs_are_fine(self) -> None:
        assert rules.find_dashes("a.md", b"well-known -- and a - b, minus \xe2\x88\x92 sign") == []

    def test_no_file_is_exempt(self) -> None:
        data = f"comment {EM} with a dash".encode()
        assert rules.find_dashes("docs/page.html", data) != []

    def test_binary_files_and_undecodable_bytes_are_skipped(self) -> None:
        assert rules.find_dashes("docs/picture.png", f"{EM}".encode()) == []
        assert rules.find_dashes("weird.dat", b"\xff\xfe\x00 not utf-8") == []

    def test_an_empty_file_is_fine(self) -> None:
        assert rules.find_dashes("empty.md", b"") == []

    def test_the_rules_module_itself_contains_no_literal_dashes(self) -> None:
        source = (SCRIPTS / "house_rules.py").read_bytes()
        assert rules.find_dashes("scripts/house_rules.py", source) == []


class TestLocalOnlyFiles:
    def test_agent_notes_and_tracker_are_flagged_anywhere(self) -> None:
        for path in (
            "CLAUDE.md",
            "project_tracker.md",
            "sub/dir/CLAUDE.md",
            "PS-5_engine_options.md",
        ):
            assert rules.check_local_only(path), path

    def test_everything_in_the_offline_folder_is_flagged(self) -> None:
        for path in ("offline/notes.md", "offline/private/design.html", "offline/a/b/c.py"):
            assert rules.check_local_only(path), path
        for path in ("docs/offline/notes.md", "offline.md", "backend/offline/x.py"):
            assert rules.check_local_only(path) == [], path

    def test_env_files_are_flagged_but_examples_are_allowed(self) -> None:
        for path in (".env", "backend/.env", "frontend/.env.local", "backend/.env.production"):
            assert rules.check_local_only(path), path
        for path in (".env.example", "backend/.env.example", "frontend/.env.example"):
            assert rules.check_local_only(path) == [], path

    def test_ordinary_files_are_fine(self) -> None:
        for path in ("README.md", "backend/README.md", "environment.md", "backend/app/main.py"):
            assert rules.check_local_only(path) == [], path


class TestCommitMessages:
    def test_a_plain_message_passes(self) -> None:
        assert rules.check_commit_message("Add a thing\n\nWhy it matters.\n") == []

    def test_a_claude_co_author_trailer_is_rejected(self) -> None:
        for trailer in (
            "Co-Authored-By: Claude <noreply@anthropic.com>",
            "co-authored-by: claude opus <x@y.z>",
            "  CO-AUTHORED-BY: Anthropic Assistant <a@b.c>",
        ):
            problems = rules.check_commit_message(f"Subject\n\nBody\n\n{trailer}\n")
            assert any("Co-Authored-By" in p.message for p in problems), trailer

    def test_a_human_co_author_is_allowed(self) -> None:
        message = "Subject\n\nCo-authored-by: Pat Example <pat@example.com>\n"
        assert rules.check_commit_message(message) == []

    def test_generated_with_lines_are_rejected(self) -> None:
        problems = rules.check_commit_message("Subject\n\nGenerated with [Claude Code](x)\n")
        assert any("Generated with" in p.message for p in problems)

    def test_the_anthropic_noreply_address_is_rejected(self) -> None:
        assert rules.check_commit_message("Subject\n\nnoreply@anthropic.com\n")

    def test_dashes_are_rejected(self) -> None:
        assert rules.check_commit_message(f"Subject {EM} with a dash\n")
        assert rules.check_commit_message(f"Subject\n\nrange 1{EN}2\n")

    def test_git_comment_lines_are_ignored(self) -> None:
        message = f"Subject\n\n# Co-Authored-By: Claude {EM} from a template comment\n"
        assert rules.check_commit_message(message) == []


class TestIdentity:
    def test_a_github_noreply_address_is_accepted(self) -> None:
        assert rules.check_identity(f"someone <{NOREPLY}> 1700000000 +0000") == []
        assert rules.check_identity(f"someone <{NOREPLY.upper()}> 1700000000 +0000") == []

    def test_a_personal_address_is_rejected_with_instructions(self) -> None:
        (problem,) = rules.check_identity("Some One <some.one@example.com> 1700000000 +0000")

        assert "some.one@example.com" in problem.message
        assert "git config user.email" in problem.message

    def test_a_missing_address_is_rejected(self) -> None:
        assert rules.check_identity("Nobody 1700000000 +0000")
        assert rules.check_identity("Nobody <> 1700000000 +0000")

    def test_the_location_is_configurable(self) -> None:
        (problem,) = rules.check_identity("x <a@b.c> 0 +0000", where="commit abc12345 author")
        assert problem.where == "commit abc12345 author"


def test_problems_render_as_where_and_message() -> None:
    assert rules.Problem("a.md:3", "bad").render() == "a.md:3: bad"
