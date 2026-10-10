"""Hook-ul commit-msg respinge atribuirea AI și acceptă mesajele normale (rulat prin git real)."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from contracts.runtime import REPO_ROOT

HOOKS = REPO_ROOT / ".githooks"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git indisponibil")

REJECTED = [
    "feat: adaugă regula\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n",
    "fix: prag\n\nco-authored-by: GitHub Copilot <copilot@github.com>\n",
    "docs: readme\n\n\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)\n",
    "chore: x\n\nGenerated with ChatGPT\n",
    "feat: y\n\nAssisted-by: Gemini\n",
    "feat: z\n\nClaude-Session: https://claude.ai/code/abc\n",
    "refactor: w\n\nWritten by Cursor agent\n",
]

ACCEPTED = [
    "feat(detect): regulă de loitering cu fereastră glisantă\n",
    "chore: actualizează .claude/rules și skill-ul verify\n",
    "fix: schema regenerată după contract-change\n\nCo-Authored-By: Ana Popescu <ana@example.com>\n",
    "docs: explicații generate din șabloane, fără LLM extern\n",
]


@pytest.fixture
def repo(tmp_path):
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}

    def git(*args, check=True):
        return subprocess.run(["git", *args], cwd=tmp_path, env=env, capture_output=True, text=True,
                              encoding="utf-8", check=check)

    git("init", "-q")
    git("config", "core.hooksPath", HOOKS.as_posix())
    git("config", "commit.gpgsign", "false")
    return git


def _commit(git, tmp_path, message):
    msg = tmp_path / "msg.txt"
    msg.write_text(message, encoding="utf-8", newline="\n")
    return git("commit", "-q", "--allow-empty", "-F", str(msg), check=False)


@pytest.mark.parametrize("message", REJECTED)
def test_rejects_ai_attribution(repo, tmp_path, message):
    r = _commit(repo, tmp_path, message)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "commit-msg" in r.stderr


@pytest.mark.parametrize("message", ACCEPTED)
def test_accepts_normal_messages(repo, tmp_path, message):
    r = _commit(repo, tmp_path, message)
    assert r.returncode == 0, r.stdout + r.stderr
