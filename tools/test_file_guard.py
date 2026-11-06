"""Unit tests for core/.claude/hooks/file-guard.py and its declaration in the seeded .claude/settings.json, which
apply-template.py adds on a refresh: run `python3 -m unittest discover tools`."""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock as mock
from contextlib import redirect_stdout

sys.dont_write_bytecode = True
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HOOK = os.path.join(ROOT, "core", ".claude", "hooks", "file-guard.py")
SEED_SETTINGS = os.path.join(ROOT, "seed", ".claude", "settings.json")
APPLY = os.path.join(ROOT, "tools", "apply-template.py")
DOTNET_SETTINGS = 'COVERAGE_EXCLUDES = []\nCOVERAGE_TEST_PATHSPECS = ["tests/*.cs"]\n'
GO_SETTINGS = 'COVERAGE_EXCLUDES = ["*_test.go"]\n'
TEST_DOCUMENT = "docs/UNIT_TESTS.md"
PROJECT_MD = ".squad/project.md"
SETTINGS_JSON = ".claude/settings.json"


def load(name, path):
    sys.dont_write_bytecode = True  # the hook lives in core/, which the template check scans for placeholders
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class GuardTestCase(unittest.TestCase):
    """A working tree with a squad_settings.py; CLAUDE_PROJECT_DIR points at it, as Claude Code sets it for hooks."""
    settings = DOTNET_SETTINGS

    def setUp(self):
        self.hook = load("file_guard", HOOK)
        self.dir = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.dir.name)
        os.makedirs(os.path.join(self.root, ".git"))
        if self.settings is not None:
            write(os.path.join(self.root, ".squad", "tools", "squad_settings.py"), self.settings)
        patcher = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.root})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.dir.cleanup()

    def reason(self, agent, path, tool="Write"):
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        full = path if os.path.isabs(path) else os.path.join(self.root, path)
        return self.hook.deny_reason({"tool_name": tool, "agent_type": agent, "tool_input": {key: full}})

    def assert_allowed(self, agent, *paths):
        for path in paths:
            self.assertIsNone(self.reason(agent, path), f"{agent} may write {path}")

    def assert_denied(self, agent, *paths):
        for path in paths:
            self.assertIsNotNone(self.reason(agent, path), f"{agent} may not write {path}")


class TestOwnership(GuardTestCase):
    def test_no_member_writes_git_claude_or_squad_files(self):
        protected = (".git/HEAD", ".git/config", ".git", SETTINGS_JSON, ".claude/hooks/git-guard.py",
                     ".claude/agents/squad-dev.md", ".squad/team.md", PROJECT_MD, ".squad/tools/squad_settings.py",
                     ".squad/tools/coverage-check.py", ".Claude/settings.json", "src/../.git/HEAD")
        for agent in ("squad-dev", "squad-code-officer", "squad-tester", "squad-lead", "squad-docs"):
            self.assert_denied(agent, *protected)

    def test_only_the_code_officer_writes_stack_md(self):
        self.assert_allowed("squad-code-officer", ".squad/stack.md", "src/App/Service.cs", "tests/App.Tests/ServiceTests.cs")
        self.assert_denied("squad-code-officer", PROJECT_MD, ".squad/routing.md")
        for agent in ("squad-dev", "squad-tester", "squad-lead"):
            self.assert_denied(agent, ".squad/stack.md")

    def test_the_lead_writes_only_specs_and_decision_records(self):
        self.assert_allowed("squad-lead", "specs/issue-12/plan.md", "specs/feature-x/spec.md",
                            "docs/decisions/0007-retry-policy.md", "docs/decisions/README.md")
        self.assert_denied("squad-lead", "src/App/Service.cs", "tests/App.Tests/ServiceTests.cs", "README.md",
                           "docs/ARCHITECTURE.md", "docs/areas/storage.md", "AGENTS.md", "specs.md", "docs/decisions.md")

    def test_the_tester_writes_only_the_test_paths_and_the_test_document(self):
        self.assert_allowed("squad-tester", "tests/App.Tests/ServiceTests.cs", "tests/Root.cs", TEST_DOCUMENT)
        self.assert_denied("squad-tester", "src/App/Service.cs", "tests/App.Tests/App.Tests.csproj",
                           "tests/App.Tests/Data/sample.json", "README.md", "docs/ARCHITECTURE.md", "specs/x/plan.md",
                           "src/tests/A.cs")

    def test_the_tester_is_told_where_test_files_go(self):
        reason = self.reason("squad-tester", "src/App/Service.cs")
        self.assertIn("tests/*.cs", reason)
        self.assertIn("COVERAGE_TEST_PATHSPECS", reason)
        self.assertIn("orchestrator", reason)

    def test_read_only_members_write_nothing(self):
        for agent in ("squad-reviewer", "squad-security", "squad-devils-advocate"):
            self.assert_denied(agent, "src/App/Service.cs", "specs/x/plan.md", TEST_DOCUMENT, "notes.txt")

    def test_the_dev_and_other_members_write_everything_else(self):
        for agent in ("squad-dev", "squad-docs"):
            self.assert_allowed(agent, "src/App/Service.cs", "tests/App.Tests/ServiceTests.cs", "README.md",
                                "docs/areas/storage.md", "docs/ARCHITECTURE.md", "Dockerfile", "a/.gitkeep")

    def test_every_file_tool_is_guarded(self):
        for tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            self.assertIsNotNone(self.reason("squad-lead", "src/analysis.ipynb", tool), tool)
            self.assertIsNone(self.reason("squad-lead", "specs/x/analysis.ipynb", tool), tool)
        for tool in ("Read", "Bash", "Glob"):
            self.assertIsNone(self.reason("squad-lead", "src/App/Service.cs", tool), tool)

    def test_a_relative_path_is_read_from_the_working_tree(self):
        data = {"tool_name": "Edit", "agent_type": "squad-lead", "tool_input": {"file_path": "src/a.cs"}}
        self.assertIsNotNone(self.hook.deny_reason(data))


class TestWhereTheGuardApplies(GuardTestCase):
    def test_the_orchestrator_and_other_agents_are_not_guarded(self):
        path = os.path.join(self.root, SETTINGS_JSON)
        for agent in (None, "", "Explore", "general-purpose", 5):
            data = {"tool_name": "Write", "agent_type": agent, "tool_input": {"file_path": path}}
            self.assertIsNone(self.hook.deny_reason(data), agent)

    def test_a_scratch_directory_outside_the_working_tree_is_free(self):
        with tempfile.TemporaryDirectory() as scratch:
            # the Tester's throwaway mutation of production code in a scratch worktree (squad-tester.md, mode coverage)
            self.assertIsNone(self.reason("squad-tester", os.path.join(scratch, "src", "App", "Service.cs")))
            self.assertIsNone(self.reason("squad-lead", os.path.join(scratch, "notes.md")))

    def test_a_nested_worktree_is_judged_by_its_own_paths(self):
        worktree = os.path.join(self.root, ".claude", "worktrees", "agent-1")
        write(os.path.join(worktree, ".git"), "gitdir: ../../../.git/worktrees/agent-1\n")
        write(os.path.join(worktree, ".squad", "tools", "squad_settings.py"), DOTNET_SETTINGS)
        nested = ".claude/worktrees/agent-1/"
        self.assert_allowed("squad-dev", nested + "src/App/Service.cs")
        self.assert_allowed("squad-tester", nested + "tests/App.Tests/ServiceTests.cs")
        self.assert_denied("squad-dev", nested + SETTINGS_JSON, nested + PROJECT_MD)
        self.assert_denied("squad-tester", nested + "src/App/Service.cs")

    def test_without_claude_project_dir_the_session_cwd_is_the_working_tree(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": ""}):
            data = {"tool_name": "Write", "agent_type": "squad-lead", "cwd": self.root,
                    "tool_input": {"file_path": os.path.join(self.root, "src", "a.cs")}}
            self.assertIsNotNone(self.hook.deny_reason(data))
            del data["cwd"]
            self.assertIsNone(self.hook.deny_reason(data), "no working tree known: no decision")


class TestGoTestPaths(GuardTestCase):
    """A profile without COVERAGE_TEST_PATHSPECS: the test paths are its COVERAGE_EXCLUDES, as in coverage-check.py."""
    settings = GO_SETTINGS

    def test_the_coverage_excludes_are_the_test_paths(self):
        self.assert_allowed("squad-tester", "internal/store/store_test.go", "main_test.go", TEST_DOCUMENT)
        self.assert_denied("squad-tester", "internal/store/store.go", "internal/store/testdata/a.json")


class TestUnreadableSettings(GuardTestCase):
    settings = None

    def test_a_tester_write_is_left_to_the_permission_flow(self):
        self.assert_allowed("squad-tester", "src/a.cs")
        self.assert_denied("squad-tester", PROJECT_MD, SETTINGS_JSON)

    def test_a_broken_settings_file_is_no_decision_either(self):
        write(os.path.join(self.root, ".squad", "tools", "squad_settings.py"), "COVERAGE_EXCLUDES = [\n")
        self.assert_allowed("squad-tester", "src/a.cs")


class TestPathspecs(unittest.TestCase):
    def setUp(self):
        self.hook = load("file_guard", HOOK)

    def test_git_pathspec_semantics(self):
        cases = [
            ("tests/a/b.cs", ["tests/*.cs"], True), ("src/tests/b.cs", ["tests/*.cs"], False),
            ("pkg/a_test.go", ["*_test.go"], True), ("pkg/a.go", ["*_test.go"], False),
            ("test/fixtures/a.json", ["test"], True), ("test/fixtures/a.json", ["test/"], True),
            ("testing/a.ts", ["test"], False), ("src/a.spec.ts", ["*.test.ts", "*.spec.ts"], True),
            ("tests/generated/a.cs", ["tests/", ":(exclude)tests/generated/*"], False),
            ("tests/generated/a.cs", ["tests/", ":!tests/generated"], False),
            ("tests/a.cs", ["tests/", ":^tests/generated"], True), ("tests/a.cs", [":(glob)tests/**/*.cs"], True),
            ("src/a.cs", [":(exclude)tests"], True), ("tests/a.cs", [], False), ("tests/a.cs", ["./tests"], True),
        ]
        for rel, pathspecs, expected in cases:
            self.assertEqual(self.hook.is_test_path(rel, pathspecs), expected, f"{rel} {pathspecs}")


class TestHookInput(GuardTestCase):
    def run_hook(self, data):
        sys.stdin = io.StringIO(data if isinstance(data, str) else json.dumps(data))
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                self.hook.main()
        finally:
            sys.stdin = sys.__stdin__
        return out.getvalue()

    def test_denied_write_answers_a_deny_decision(self):
        out = self.run_hook({"tool_name": "Edit", "agent_type": "squad-lead",
                             "tool_input": {"file_path": os.path.join(self.root, "src", "a.cs")}})
        decision = json.loads(out)["hookSpecificOutput"]
        self.assertEqual((decision["hookEventName"], decision["permissionDecision"]), ("PreToolUse", "deny"))
        self.assertIn("squad-lead may not write src/a.cs", decision["permissionDecisionReason"])
        self.assertIn(".squad/team.md", decision["permissionDecisionReason"])

    def test_allowed_write_and_odd_input_give_no_decision(self):
        for data in ({"tool_name": "Write", "agent_type": "squad-lead",
                      "tool_input": {"file_path": os.path.join(self.root, "specs", "x", "plan.md")}},
                     {"tool_name": "Write", "agent_type": "squad-lead", "tool_input": "x"},
                     {"tool_name": "Write", "agent_type": "squad-lead", "tool_input": {"file_path": 5}},
                     "not json", "[]", "null"):
            self.assertEqual(self.run_hook(data), "", data)


class TestDeclaredHooks(unittest.TestCase):
    def test_the_seed_declares_the_hooks_the_refresh_adds(self):
        apply = load("apply_template", APPLY)
        with open(SEED_SETTINGS, encoding="utf-8") as handle:
            seed = json.load(handle)
        self.assertEqual(seed["hooks"]["PreToolUse"], list(apply.SQUAD_HOOKS.values()))
        self.assertIsNone(apply.with_squad_hooks(json.dumps(seed)), "the seed lacks no squad hook")


if __name__ == "__main__":
    unittest.main()
