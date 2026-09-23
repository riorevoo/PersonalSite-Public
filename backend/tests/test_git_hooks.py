"""The hook entry points, exercised against a throwaway git repository."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check as check_script  # noqa: E402
import git_hooks  # noqa: E402

EM = chr(0x2014)
NOREPLY = "1234+someone@users.noreply.github.com"


IDENTITY_VARS = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")
# Git sets these while it runs a hook (the pre-push hook runs this whole suite). Left in place they
# point the throwaway repository's git commands at the real repository.
LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def scrub_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (*IDENTITY_VARS, *LOCATION_VARS):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scrub_git_environment(monkeypatch)
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "someone")
    git(tmp_path, "config", "user.email", NOREPLY)
    git(tmp_path, "config", "commit.gpgsign", "false")
    monkeypatch.setattr(git_hooks, "ROOT", tmp_path)
    return tmp_path


def stage(repo: Path, name: str, content: str, *, force: bool = False) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    git(repo, "add", *(["-f"] if force else []), name)


def commit(repo: Path, message: str) -> None:
    git(repo, "commit", "-q", "-m", message)


def test_the_hook_environment_does_not_leak_into_the_throwaway_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for var in LOCATION_VARS:
        monkeypatch.setenv(var, str(tmp_path / "the-real-repository"))

    scrub_git_environment(monkeypatch)

    assert not [var for var in LOCATION_VARS if var in os.environ]


class TestPreCommit:
    def test_nothing_staged_is_fine(self, repo: Path) -> None:
        assert git_hooks.pre_commit() == 0

    def test_clean_files_pass(self, repo: Path) -> None:
        stage(repo, "notes.txt", "plain text\n")
        stage(repo, "some folder/has spaces.txt", "also plain\n")
        assert git_hooks.pre_commit() == 0

    def test_a_dash_in_a_staged_file_is_reported_with_its_line(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stage(repo, "notes.txt", f"fine\nbad {EM} line\n")

        assert git_hooks.pre_commit() == 1
        assert "notes.txt:2" in capsys.readouterr().err

    def test_it_checks_what_is_staged_not_the_working_copy(self, repo: Path) -> None:
        stage(repo, "notes.txt", "clean\n")
        (repo / "notes.txt").write_text(f"dirty {EM} but unstaged\n", encoding="utf-8")

        assert git_hooks.pre_commit() == 0

    def test_a_forced_local_only_file_is_blocked(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stage(repo, "CLAUDE.md", "agent notes\n", force=True)

        assert git_hooks.pre_commit() == 1
        assert "CLAUDE.md" in capsys.readouterr().err

    def test_a_personal_author_identity_is_blocked(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        git(repo, "config", "user.email", "some.one@example.com")
        stage(repo, "notes.txt", "plain\n")

        assert git_hooks.pre_commit() == 1
        assert "noreply" in capsys.readouterr().err

    def test_backend_python_files_get_ruff_and_mypy(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[str, list[str], Path]] = []

        def fake_run_tool(label: str, command: list[str], cwd: Path) -> bool:
            calls.append((label, command, cwd))
            return True

        monkeypatch.setattr(git_hooks, "run_tool", fake_run_tool)
        stage(repo, "backend/app/x.py", "x = 1\n")
        stage(repo, "backend/README.md", "not python\n")

        assert git_hooks.pre_commit() == 0
        assert [label for label, _, _ in calls] == ["ruff check", "ruff format", "mypy"]
        assert calls[0][1][-1] == "app/x.py"  # paths are relative to backend/
        assert all(cwd == repo / "backend" for _, _, cwd in calls)

    def test_frontend_files_get_prettier_and_lint_but_generated_files_are_skipped(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[str, list[str], Path]] = []

        def fake_run_tool(label: str, command: list[str], cwd: Path) -> bool:
            calls.append((label, command, cwd))
            return True

        monkeypatch.setattr(git_hooks, "run_tool", fake_run_tool)
        stage(repo, "frontend/src/a.tsx", "export const a = 1\n")
        stage(repo, "frontend/package-lock.json", "{}\n")
        stage(repo, "frontend/src/api/schema.d.ts", "export {}\n")

        assert git_hooks.pre_commit() == 0
        assert [label for label, _, _ in calls] == ["prettier", "lint"]
        assert calls[0][1] == ["npx", "prettier", "--check", "src/a.tsx"]

    def test_a_failing_tool_blocks_the_commit(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(git_hooks, "run_tool", lambda label, command, cwd: False)
        stage(repo, "backend/app/x.py", "x = 1\n")

        assert git_hooks.pre_commit() == 1
        assert "--no-verify" in capsys.readouterr().err


class TestRunTool:
    def test_reports_success_and_failure_by_exit_code(self, tmp_path: Path) -> None:
        assert git_hooks.run_tool("ok", [sys.executable, "-c", "pass"], tmp_path) is True
        assert (
            git_hooks.run_tool("bad", [sys.executable, "-c", "raise SystemExit(3)"], tmp_path)
            is False
        )

    def test_a_missing_tool_is_a_clear_failure(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert git_hooks.run_tool("ghost", ["definitely-not-installed-xyz"], tmp_path) is False
        assert "not installed" in capsys.readouterr().err


class TestCommitMsg:
    def test_clean_message_passes(self, tmp_path: Path) -> None:
        message = tmp_path / "MSG"
        message.write_text("Add a thing\n\nBody.\n", encoding="utf-8")
        assert git_hooks.commit_msg(str(message)) == 0

    def test_claude_trailer_fails(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        message = tmp_path / "MSG"
        message.write_text("Add a thing\n\nCo-Authored-By: Claude <x@y.z>\n", encoding="utf-8")

        assert git_hooks.commit_msg(str(message)) == 1
        assert "Co-Authored-By" in capsys.readouterr().err


class TestCi:
    def test_a_clean_repository_passes(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stage(repo, "README.md", "hello\n")
        commit(repo, "Start the project")

        assert git_hooks.ci() == 0
        assert "clean" in capsys.readouterr().out

    def test_a_dash_in_any_tracked_file_fails(self, repo: Path) -> None:
        stage(repo, "docs/a.md", f"text {EM} text\n")
        commit(repo, "Add docs")
        assert git_hooks.ci() == 1

    def test_a_bad_commit_message_anywhere_in_history_fails(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stage(repo, "a.txt", "one\n")
        commit(repo, "First\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
        stage(repo, "b.txt", "two\n")
        commit(repo, "Second")

        assert git_hooks.ci() == 1
        assert "Co-Authored-By" in capsys.readouterr().err

    def test_a_personal_author_anywhere_in_history_fails(self, repo: Path) -> None:
        git(repo, "config", "user.email", "some.one@example.com")
        stage(repo, "a.txt", "one\n")
        commit(repo, "First")
        git(repo, "config", "user.email", NOREPLY)
        stage(repo, "b.txt", "two\n")
        commit(repo, "Second")

        assert git_hooks.ci() == 1

    def test_a_committed_local_only_file_fails(self, repo: Path) -> None:
        stage(repo, "project_tracker.md", "tasks\n", force=True)
        commit(repo, "Oops")
        assert git_hooks.ci() == 1


class TestEntryPoints:
    def test_main_dispatches_commands(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(git_hooks, "pre_commit", lambda: 11)
        monkeypatch.setattr(git_hooks, "pre_push", lambda: 12)
        monkeypatch.setattr(git_hooks, "ci", lambda: 13)
        monkeypatch.setattr(git_hooks, "commit_msg", lambda path: 14 if path == "MSG" else 99)

        assert git_hooks.main(["x", "pre-commit"]) == 11
        assert git_hooks.main(["x", "pre-push"]) == 12
        assert git_hooks.main(["x", "ci"]) == 13
        assert git_hooks.main(["x", "commit-msg", "MSG"]) == 14

    @pytest.mark.parametrize("argv", [["x"], ["x", "nonsense"], ["x", "commit-msg"]])
    def test_bad_usage_prints_help_and_exits_2(
        self, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert git_hooks.main(argv) == 2
        assert "pre-commit" in capsys.readouterr().err

    def test_pre_push_runs_the_full_check_without_the_browser_tests(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            seen.append(command)
            return subprocess.CompletedProcess(command, 3)

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert git_hooks.pre_push() == 3
        assert seen[0][-1] == "--skip-e2e"
        assert seen[0][-2].endswith("check.py")


class TestCheckScript:
    def fake_steps(self, monkeypatch: pytest.MonkeyPatch, failing: set[str]) -> list[str]:
        ran: list[str] = []

        def fake_run(step: check_script.Step) -> tuple[bool, float]:
            ran.append(f"{step.group}/{step.name}")
            return step.name not in failing, 0.1

        monkeypatch.setattr(check_script, "run", fake_run)
        return ran

    def test_runs_every_step_and_exits_zero_when_all_pass(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ran = self.fake_steps(monkeypatch, failing=set())
        monkeypatch.setattr(sys, "argv", ["check.py"])

        assert check_script.main() == 0
        assert len(ran) == len(check_script.STEPS)
        assert "All checks passed." in capsys.readouterr().out

    def test_keeps_going_after_a_failure_and_exits_one(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ran = self.fake_steps(monkeypatch, failing={"mypy"})
        monkeypatch.setattr(sys, "argv", ["check.py"])

        assert check_script.main() == 1
        assert len(ran) == len(check_script.STEPS)  # later steps still ran
        output = capsys.readouterr().out
        assert "FAIL  backend" in output
        assert "1 check(s) failed." in output

    def test_skip_e2e_and_only_narrow_the_steps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ran = self.fake_steps(monkeypatch, failing=set())

        monkeypatch.setattr(sys, "argv", ["check.py", "--skip-e2e"])
        check_script.main()
        assert not any("end-to-end" in name for name in ran)

        ran.clear()
        monkeypatch.setattr(sys, "argv", ["check.py", "--only", "backend"])
        check_script.main()
        assert ran
        assert all(name.startswith("backend/") for name in ran)

    def test_the_steps_are_well_formed(self) -> None:
        assert {s.group for s in check_script.STEPS} == {"house-rules", "backend", "frontend"}
        assert all(s.cwd.is_dir() for s in check_script.STEPS)
        assert [s for s in check_script.STEPS if s.e2e][-1] is check_script.STEPS[-1]

    def test_run_reports_a_pass_a_fail_and_a_missing_tool(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = check_script.ROOT
        ok = check_script.Step("g", "ok", (sys.executable, "-c", "pass"), root)
        bad = check_script.Step("g", "bad", (sys.executable, "-c", "raise SystemExit(1)"), root)
        ghost = check_script.Step("g", "ghost", ("definitely-not-installed-xyz",), root)

        assert check_script.run(ok)[0] is True
        assert check_script.run(bad)[0] is False
        assert check_script.run(ghost)[0] is False
        assert "not installed" in capsys.readouterr().err
