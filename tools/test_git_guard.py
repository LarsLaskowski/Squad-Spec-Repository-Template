"""Unit tests for core/.claude/hooks/git-guard.py: run `python3 -m unittest discover tools`."""
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".claude", "hooks", "git-guard.py")


def load_hook():
    sys.dont_write_bytecode = True  # the hook lives in core/, which the template check scans for placeholders
    spec = importlib.util.spec_from_file_location("git_guard", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.hook = load_hook()

    def assert_allowed(self, *commands):
        for command in commands:
            self.assertIsNone(self.hook.check_command(command), command)

    def assert_denied(self, *commands):
        for command in commands:
            self.assertIsNotNone(self.hook.check_command(command), command)

    def test_read_only_git_is_allowed(self):
        self.assert_allowed(
            "git status --short", "git diff origin/main...HEAD", "git log --oneline -5", "git show HEAD:README.md",
            "git -C /tmp/x log", "git --no-pager diff", "git ls-files -- src", "git grep -n foo", "git rev-parse HEAD",
            "git merge-base origin/main HEAD", "git fetch origin main", "git tag --list 'v*'",
            "git tag --contains abc --list 'v*'", "git branch --show-current", "git branch", "git branch -a",
            "git ls-remote --tags https://github.com/o/r", "git clone --depth 1 --branch v1 https://github.com/o/r /tmp/s",
            "git config --get user.name", "git config --list", "go test ./... && git diff --stat")

    def test_staging_and_scratch_worktrees_are_allowed(self):
        self.assert_allowed(
            "git add -A", "git add src/new.go", "git worktree add --detach /tmp/review HEAD",
            "git worktree remove --force /tmp/review", "git worktree prune", "git worktree list")

    def test_git_writes_are_denied(self):
        self.assert_denied(
            "git commit -m x", "git commit --amend", "git push -u origin b", "git push --force", "git stash",
            "git stash pop", "git reset --hard", "git checkout main", "git checkout -- src/a.go", "git switch -c b",
            "git restore src/a.go", "git rebase main", "git merge main", "git cherry-pick abc", "git revert HEAD",
            "git rm -r specs/x", "git mv a b", "git clean -fd", "git pull", "git tag v1.0.0", "git branch -D x",
            "git branch new-branch", "git -C /tmp/x checkout main", "git -c user.name=t commit -m x",
            "git worktree move a b", "git config user.email x@y", "git notes add -m x", "git update-ref refs/heads/x abc")

    def test_writes_hidden_in_a_chain_are_found(self):
        self.assert_denied(
            "cd /tmp/x && git push", "go test ./... ; git commit -am done", "echo ok | git stash",
            "echo $(git commit -m x)", "/usr/bin/git push", "git add -A && git commit -m wip")

    def test_gh_reads_are_allowed_and_writes_denied(self):
        self.assert_allowed("gh api repos/o/r/issues/1", "gh api repos/o/r/issues/1/comments", "gh pr view 1",
                            "gh api -X GET repos/o/r", "gh issue list", "gh pr diff 1")
        self.assert_denied("gh api -X POST repos/o/r/issues/1/comments -f body=x", "gh api --method PATCH repos/o/r",
                           "gh api repos/o/r/issues -f title=x", "gh api --input body.json repos/o/r/issues",
                           "gh pr comment 1 -b x", "gh pr create -t x", "gh issue create -t x", "gh pr merge 1",
                           "gh issue comment 1 -b x", "gh pr review 1 --approve")

    def test_unrelated_commands_pass(self):
        self.assert_allowed("dotnet build X.slnx -c Release", "python3 .squad/tools/coverage-check.py",
                            "grep -rn 'git push' docs/", "echo 'git commit' > note.txt")


class TestHookInput(unittest.TestCase):
    def setUp(self):
        self.hook = load_hook()

    def run_hook(self, data):
        sys.stdin = io.StringIO(data if isinstance(data, str) else json.dumps(data))
        out = io.StringIO()
        with redirect_stdout(out):
            self.hook.main()
        sys.stdin = sys.__stdin__
        return out.getvalue()

    def test_denied_command_answers_a_deny_decision(self):
        out = self.run_hook({"tool_name": "Bash", "agent_type": "squad-reviewer",
                             "tool_input": {"command": "git commit -m x"}})
        decision = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("squad-reviewer", decision["permissionDecisionReason"])
        self.assertIn("git commit", decision["permissionDecisionReason"])

    def test_allowed_command_and_other_tools_give_no_decision(self):
        for data in ({"tool_name": "Bash", "tool_input": {"command": "git status"}},
                     {"tool_name": "Edit", "tool_input": {"file_path": "a"}}, "not json", "[]"):
            self.assertEqual(self.run_hook(data), "", data)


if __name__ == "__main__":
    unittest.main()
