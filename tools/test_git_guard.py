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

    def test_a_patch_is_checked_but_never_applied(self):
        # The Tester checks its dry-run patch (Vandox#410); applying it is the orchestrator's commit.
        self.assert_allowed("git apply --check /tmp/dry-run.patch", "git apply --check --index /tmp/p.patch",
                            "git apply --stat /tmp/p.patch", "git -C /repo apply --numstat --summary /tmp/p.patch")
        self.assert_denied("git apply /tmp/p.patch", "git apply --index /tmp/p.patch", "git apply -R /tmp/p.patch",
                           "git apply --check --apply /tmp/p.patch", "git apply --3way /tmp/p.patch",
                           "git apply --stat --ap /tmp/p.patch", "git apply --check --appl /tmp/p.patch")

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

    def test_every_form_of_a_checkout_of_another_revision_is_denied(self):
        # The forms a read-only member uses to read another revision (Seluna#15): each one detaches HEAD.
        self.assert_denied(
            "git checkout e79c609", "git -C /repo checkout e79c609", "cd /repo && git checkout e79c609",
            "env GIT_PAGER=cat git checkout e79c609", "GIT_DIR=/repo/.git git checkout e79c609",
            "git --no-pager checkout e79c609", "command git checkout e79c609", "sudo git checkout e79c609",
            "bash -c 'git checkout e79c609'", "sh -c \"cd /repo && git checkout e79c609\"",
            "bash -lc 'git -C /repo checkout e79c609'", "/bin/sh -ec 'git switch --detach e79c609'",
            "eval 'git checkout e79c609'", "bash -c \"bash -c 'git checkout e79c609'\"")
        self.assert_allowed("git show e79c609:specs/issue-15/plan.md", "bash -c 'git show e79c609:README.md'",
                            "bash scripts/build.sh", "sh -c 'git log --oneline -3'",
                            "git worktree add --detach /tmp/plan e79c609")

    def test_gh_reads_are_allowed_and_writes_denied(self):
        self.assert_allowed("gh api repos/o/r/issues/1", "gh api repos/o/r/issues/1/comments", "gh pr view 1",
                            "gh api -X GET repos/o/r", "gh issue list", "gh pr diff 1")
        self.assert_denied("gh api -X POST repos/o/r/issues/1/comments -f body=x", "gh api --method PATCH repos/o/r",
                           "gh api repos/o/r/issues -f title=x", "gh api --input body.json repos/o/r/issues",
                           "gh pr comment 1 -b x", "gh pr create -t x", "gh issue create -t x", "gh pr merge 1",
                           "gh issue comment 1 -b x", "gh pr review 1 --approve")

    def test_an_alias_set_for_the_call_is_denied(self):
        # The alias's command is never seen by the guard, whatever it is (issue 248).
        self.assert_denied(
            "git -c alias.ci=commit ci -m x", "git -c alias.p=push p origin HEAD", "git -c Alias.l=log l",
            "git -C /repo -c alias.ci=commit ci -m x", "git --config-env=alias.ci=CMD ci -m x",
            "git --config-env alias.ci=CMD ci", "git -c include.path=/tmp/aliases.cfg ci -m x",
            "git -c includeIf.gitdir:/repo/.path=/tmp/a.cfg ci", "bash -c 'git -c alias.ci=commit ci -m x'",
            "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.ci GIT_CONFIG_VALUE_0=commit git ci -m x",
            "env GIT_CONFIG_PARAMETERS=\"'alias.ci'='commit'\" git ci -m x")
        self.assert_allowed("git -c core.pager=cat log --oneline -3", "git -c color.ui=never diff",
                            "git --config-env=core.pager=PAGER log", "GIT_CONFIG_COUNT=0 git status")

    def test_every_form_of_a_gh_api_method_and_field_is_found(self):
        self.assert_denied(
            "gh api -XPOST repos/o/r/issues", "gh api -X=POST repos/o/r/issues", "gh api -iXPOST repos/o/r/issues",
            "gh api -iX DELETE repos/o/r/git/refs/heads/x", "gh api --method=put repos/o/r/rulesets/1",
            "gh api -X PUT repos/o/r/rulesets/1 --input rules.json", "gh api repos/o/r/issues -ftitle=x",
            "gh api repos/o/r/issues -Fbody=@b.md", "gh api repos/o/r/issues -if title=x",
            "gh api repos/o/r/issues --raw-field=title=x", "gh api --input=- repos/o/r/issues")
        self.assert_allowed("gh api -XGET repos/o/r", "gh api -X=get repos/o/r", "gh api -i repos/o/r",
                            "gh api -H 'Accept: application/vnd.github.raw' -H -fx repos/o/r/contents/a",
                            "gh api --jq '.[] | .name' repos/o/r/rulesets", "gh api --paginate repos/o/r/pulls")

    def test_every_gh_write_group_is_denied(self):
        self.assert_denied(
            "gh workflow run .", "gh workflow run ci.yml --ref main", "gh workflow enable 1", "gh workflow disable 1",
            "gh run rerun .", "gh run rerun 1 --failed", "gh run cancel 1", "gh run delete 1", "gh secret set .",
            "gh secret set TOKEN -b x", "gh secret delete TOKEN", "gh secret remove TOKEN", "gh variable set .",
            "gh variable delete X", "gh variable remove X", "gh gist create .", "gh gist new a.txt",
            "gh gist edit 1", "gh gist delete 1", "gh gist rename 1 a b", "gh cache delete --all",
            "gh pr new -t x", "gh issue new -t x", "gh repo new o/x", "gh release new v1", "gh pr checkout 1",
            "gh pr co 1", "gh pr update-branch 1", "gh pr revert 1", "gh issue develop 1", "gh repo set-default o/r",
            "gh repo autolink create JIRA- https://x/<num>", "gh repo deploy-key add key.pub",
            "gh release delete-asset v1 a.zip", "gh discussion create", "gh project item-add 1 --url x",
            "gh agent-task create x", "gh agent create x", "gh alias set co 'pr checkout'", "gh alias import a.yml",
            "gh config set editor vi", "gh auth setup-git", "gh extension install o/gh-x", "gh ext install o/gh-x",
            "gh skill install o/s", "gh ssh-key add k.pub", "gh gpg-key delete 1", "gh cs delete -c x",
            "gh pr -R o/r create -t x", "gh pr --repo o/r merge 1", "gh secret -R o/r set X -b y")
        self.assert_allowed(
            "gh workflow list", "gh workflow view ci.yml", "gh run list", "gh run view 1 --log-failed",
            "gh run watch 1", "gh secret list", "gh variable list", "gh variable get X", "gh gist list",
            "gh gist view 1", "gh cache list", "gh ruleset list", "gh ruleset view 1", "gh ruleset check main",
            "gh rs list", "gh repo deploy-key list", "gh repo autolink list", "gh pr -R o/r view 1", "gh pr checks 1",
            "gh alias list", "gh config get editor", "gh auth status", "gh extension list", "gh search prs x",
            "gh release download v1", "gh repo clone o/r /tmp/r")

    def test_unrelated_commands_pass(self):
        self.assert_allowed("dotnet build X.slnx -c Release", "python3 .squad/tools/coverage-check.py",
                            "grep -rn 'git push' docs/", "echo 'git commit' > note.txt")

    def test_what_the_guard_does_not_see_passes(self):
        # Not a security boundary (the docstring and .squad/team.md say so): a command that runs Git without naming
        # it on the command line, or writes into .git/ directly, is not found.
        self.assert_allowed("python3 -c \"import subprocess; subprocess.run(['git', 'push'])\"",
                            "echo x > .git/HEAD")


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

    def test_the_reason_names_the_alias_and_the_gh_write(self):
        for command, named in (("git -c alias.ci=commit ci -m x", "alias"), ("gh api -XPOST repos/o/r/issues", "POST"),
                               ("gh workflow run ci.yml", "gh workflow run")):
            out = self.run_hook({"tool_name": "Bash", "agent_type": "squad-dev", "tool_input": {"command": command}})
            self.assertIn(named, json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"], command)

    def test_a_denied_delete_or_move_names_the_plain_command_that_does_the_same(self):
        for command, instead in (("git rm docs/old.md", "run `rm <path>`, then `git add <path>`"),
                                 ("git -C . rm -r --cached specs/x", "run `rm <path>`, then `git add <path>`"),
                                 ("git mv a.md b.md", "run `mv <old> <new>`, then `git add <old> <new>`")):
            out = self.run_hook({"tool_name": "Bash", "agent_type": "squad-dev", "tool_input": {"command": command}})
            self.assertIn(instead, json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"], command)
        out = self.run_hook({"tool_name": "Bash", "agent_type": "squad-dev", "tool_input": {"command": "git commit"}})
        self.assertNotIn("rm <path>", json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"],
                         "only a denial with an allowed equivalent names one")
        self.assertIsNone(self.hook.check_command("rm docs/old.md && git add docs/old.md"), "the equivalent runs")

    def test_allowed_command_and_other_tools_give_no_decision(self):
        for data in ({"tool_name": "Bash", "agent_type": "squad-dev", "tool_input": {"command": "git status"}},
                     {"tool_name": "Edit", "agent_type": "squad-dev", "tool_input": {"file_path": "a"}},
                     "not json", "[]"):
            self.assertEqual(self.run_hook(data), "", data)

    def test_only_squad_members_are_guarded(self):
        command = {"command": "git rm -r specs/x"}
        self.assertIn("deny", self.run_hook({"tool_name": "Bash", "agent_type": "squad-dev", "tool_input": command}))
        for data in ({"tool_name": "Bash", "tool_input": command},
                     {"tool_name": "Bash", "agent_type": "Explore", "tool_input": command},
                     {"tool_name": "Bash", "agent_type": None, "tool_input": command}):
            self.assertEqual(self.run_hook(data), "", f"the orchestrator and other agents keep Git writes: {data}")


if __name__ == "__main__":
    unittest.main()
