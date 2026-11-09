"""Unit tests for core/.squad/tools/gate-stamp.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")
CORE = os.path.join(TOOLS, "..", "..")
SETTINGS = {"BASE_REF": "main", "PATCH_MAX_LINES": 30, "COVERAGE_PATHSPECS": ["src/*.py"], "COVERAGE_EXCLUDES": [],
            "COVERAGE_TEST_PATHSPECS": ["tests/*.py"], "FIGURE_TRIVIAL": ["1"], "FIGURE_EXCLUDES": [],
            "SPEC_APPROVAL": "lead"}
SETTINGS_TEXT = "".join(f"{key} = {value!r}\n" for key, value in SETTINGS.items())
STACK = """# Stack

## Commands

| Name | Command |
| ---- | ------- |
| *Format* (in the squad: by the member that changed the files) | `true` |
| *Format check* | `echo format-check` |
| *Test* | `echo test-all` |
| *Test (project)* | `echo test-project <Project>` (the test project of the changed code) |
| *Test with coverage* | `echo test-coverage` |
| *Coverage gate* | `echo coverage-gate` |
| *Analyzer gate* | `echo analyzer` |
"""
PLAN = """# Plan: Fix the check

Source: Issue #5
Tier: {tier} — the change alters the check
Security areas touched: {areas}

## Problem / root cause

The check in `src/a.py:1` is wrong.

## Verified facts

| # | Claim | Evidence | Status |
| - | ----- | -------- | ------ |
| 1 | The check is wrong | src/a.py:1 | confirmed |

## Acceptance criteria

- AC1: The check refuses an expired value.

## Tests per criterion

| AC | Test(s) | Test file |
| -- | ------- | --------- |
| AC1 | {test} | tests/test_a.py |
{without}
## Approach

Fix the check.

## Options considered

one option: the check is the single place.

## Affected projects and types

| Project | Type / file | Change |
| ------- | ----------- | ------ |
| src | a.py | check |

## Signatures (for the Dev's skeleton)

{signatures}

## Test files

tests/test_a.py

## Areas

none

## Documentation updates

{documentation}

## Architecture check

none

## Security considerations

- [x] no limits
- [x] none

## Decision records

- none: no decision beyond the obvious fix

## Out of scope / follow-ups
"""
WITHOUT_TESTS = "\n## Verification without tests\n\n- AC1: check: read the workflow file\n"


def plan_text(tier="standard", areas="none", signatures="- `def check(value) -> bool`", code_free=False,
              documentation="none", test="test_expired_refused"):
    return PLAN.format(tier=tier, areas=areas, signatures=signatures, documentation=documentation,
                       without=WITHOUT_TESTS if code_free else "", test="check: read the workflow" if code_free else test)


def settings_stub():
    return types.SimpleNamespace(**SETTINGS)


def load(name):
    """A tool of core/.squad/tools as a fresh module, with the test settings in place of squad_settings.py."""
    sys.modules.pop("analyzer_common", None)
    sys.modules["squad_settings"] = settings_stub()
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(TOOLS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(step, member, result, tokens=None, launch="opus/medium", continued=None, time="13:00"):
    """A log row; with `tokens`, a launch trailer (`continued`: True, or the step cell it continues)."""
    trailer, mark = "", ""
    if continued is True:
        mark = " · continued"
    elif continued:
        mark = f" · continued from {continued}"
    if tokens is not None:
        trailer = f" ({launch} · {tokens:,} tokens · 3 tool uses · 60 s{mark})"
    return f"| 2026-01-02 {time} | {step} | {member} | {result}{trailer} |\n"


class Repo:
    """A throwaway target: the core tools, the test settings and stack.md on `main`, the work folder on `work`."""

    def __init__(self, directory, folder="issue-5"):
        self.root = os.path.join(directory, "repo")
        self.folder = folder
        os.makedirs(os.path.join(self.root, ".squad", "tools"))
        self.git("init", "-q", "-b", "main")
        for name in os.listdir(TOOLS):
            if name.endswith(".py") or name == ".gitignore":
                shutil.copy(os.path.join(TOOLS, name), os.path.join(self.root, ".squad", "tools", name))
        shutil.copytree(os.path.join(CORE, ".claude", "agents"), os.path.join(self.root, ".claude", "agents"))
        shutil.copytree(os.path.join(CORE, "specs", "_template"), os.path.join(self.root, "specs", "_template"))
        self.write(".squad/tools/squad_settings.py", SETTINGS_TEXT)
        self.write(".squad/stack.md", STACK)
        self.write("src/a.py", "x = 1\n")
        self.write("README.md", "Readme\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "work")
        self.write(f"specs/{folder}/log.md", "# Log: <issue #number | feature name>\n\n| Date | Step | Member | Result |\n"
                                             "| ---- | ---- | ------ | ------ |\n")
        self.commit("intake")

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                              cwd=self.root, capture_output=True, text=True, check=True).stdout.strip()

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as handle:
            return handle.read()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    @property
    def log_path(self):
        return os.path.join(self.root, "specs", self.folder, "log.md")

    def log(self, *rows):
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write("".join(rows))


def run_main(module, argv, stdin=None):
    """(exit code, standard output, standard error) of a tool's main()."""
    out, err = io.StringIO(), io.StringIO()
    stdin_stream = io.TextIOWrapper(io.BytesIO((stdin or "").encode()), encoding="utf-8")
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        saved = sys.stdin
        sys.stdin = stdin_stream
        try:
            code = module.main(argv)
        except SystemExit as stop:
            code = stop.code
        finally:
            sys.stdin = saved
    return code, out.getvalue(), err.getvalue()


class RepoTest(unittest.TestCase):
    folder = "issue-5"

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Repo(self.directory.name, self.folder)
        cwd = os.getcwd()
        os.chdir(self.repo.root)
        self.addCleanup(os.chdir, cwd)


class TestGatePlanning(unittest.TestCase):
    def setUp(self):
        self.tool = load("gate-stamp")

    def test_stack_commands_take_the_first_code_span_of_every_profile_once(self):
        text = STACK + "\n## Profile go\n\n| Name | Command |\n| - | - |\n| *Format check* | `test -z \"$(gofmt -l .)\"` |\n" \
                       "| *Analyzer gate* | `echo analyzer` |\n"
        commands = self.tool.stack_commands(text)
        self.assertEqual(commands["Format check"], ["echo format-check", 'test -z "$(gofmt -l .)"'])
        self.assertEqual(commands["Analyzer gate"], ["echo analyzer"], "an identical command runs once")
        self.assertEqual(commands["Format"], ["true"], "a note after the name is no part of it")
        self.assertEqual(commands["Test (project)"], ["echo test-project <Project>"])

    def test_a_filled_verification_without_tests_makes_the_plan_code_free(self):
        for plan in ("## Verification without tests\n\n- AC1: read the file\n",
                     "## Tier\n\n## Verification without tests  \n- AC1: read the file\n## Tasks\n\n- T1\n"):
            self.assertTrue(self.tool.code_free(plan), plan)

    def test_an_empty_or_missing_verification_without_tests_is_not_code_free(self):
        for plan in (None, "", "## Tasks\n\n- T1\n", "## Verification without tests\n",
                     "## Verification without tests\n<!-- AC: check -->\n\n## Tasks\n\n- T1\n",
                     "## Verification without tests extra\n- AC1: read\n"):
            self.assertFalse(self.tool.code_free(plan), plan)

    def test_due_gates_follow_the_tier_and_the_rows_of_a_patch(self):
        tool = self.tool
        full = ["Format check", "Analyzer gate", "Test with coverage", "Coverage gate"]
        self.assertEqual(tool.due_gates("standard", plan_text(), {"production"}), (full, [], False, True))
        self.assertFalse(tool.due_gates("security", plan_text(), {"documentation", "test"})[3],
                         "figure-check.py only when a file is neither documentation nor a test")
        self.assertEqual(tool.due_gates("trivial", plan_text(code_free=True), {"lint"})[0], full[:3],
                         "a plan without production or test code drops the Coverage gate")
        self.assertEqual(tool.due_gates("docs", None, {"documentation"}), (["Format check"], ["--tier", "docs"],
                                                                         False, False))
        self.assertEqual(tool.due_gates("tests", plan_text(), {"test"})[:2],
                         (["Format check", "Analyzer gate", "Test (project)"], ["--tier", "tests"]))
        patch = {frozenset({"documentation"}): (["Format check"], False),
                 frozenset({"lint"}): (["Analyzer gate --lint-only"], True),
                 frozenset({"data"}): ([], True),
                 frozenset({"test"}): (["Format check", "Analyzer gate", "Test (project)"], False),
                 frozenset({"test", "production"}): (full, False),
                 frozenset({"lint", "test"}): (["Format check", "Analyzer gate", "Test (project)"], True)}
        for kinds, (gates, check) in patch.items():
            due = tool.due_gates("patch/security", None, set(kinds))
            self.assertEqual((due[0], due[1], due[2]), (gates, ["--tier", "patch"], check), sorted(kinds))

    def test_file_kinds_follow_the_rows_of_gates_of_a_patch(self):
        kind = self.tool.file_kind
        tests, production = {"tests/test_a.py"}, {"src/a.py"}
        self.assertEqual([kind(p, tests, production) for p in ("README.md", "tests/test_a.py", "src/a.py", "run.sh",
                                                               ".github/workflows/ci.yml", "app/Dockerfile",
                                                               "Dockerfile.md", "config.json")],
                         ["documentation", "test", "production", "lint", "lint", "lint", "documentation", "data"])

    def test_test_project_takes_the_project_or_falls_back_to_test(self):
        commands = self.tool.stack_commands(STACK)
        projects = self.tool.parse_projects(["Project=tests/unit", "Project=tests/web"])
        self.assertEqual(self.tool.gate_commands("Test (project)", commands, projects),
                         ("Test (project)", ["echo test-project tests/unit", "echo test-project tests/web"]))
        self.assertEqual(self.tool.gate_commands("Test (project)", commands, {}), ("Test", ["echo test-all"]))
        self.assertEqual(self.tool.gate_commands("Analyzer gate --lint-only", commands, {})[1],
                         ["echo analyzer --lint-only"])
        with self.assertRaises(self.tool.Refusal):
            self.tool.parse_projects(["Project=a b; rm -rf /"])

    def test_a_placeholder_or_a_missing_command_is_refused(self):
        with self.assertRaisesRegex(self.tool.Refusal, "placeholder"):
            self.tool.checked("Build", ["dotnet build {{TODO: Solution}}.slnx"])
        with self.assertRaisesRegex(self.tool.Refusal, "placeholder"):
            self.tool.checked("Sonar gate", ["python3 sonar-check.py pr <number>"])
        with self.assertRaisesRegex(self.tool.Refusal, "not in the Commands table"):
            self.tool.checked("Coverage gate", [])

    def test_the_tier_comes_from_the_plan_or_the_leads_step_2_row(self):
        tool, parse = self.tool, self.tool.squad_log().parse_rows
        self.assertEqual(tool.run_tier(plan_text("security"), []), "security")
        rows = parse(row("1 Intake", "Orchestrator", "bug") + row("2 Plan", "Lead", "RESULT: DONE Tier: patch/security"
                                                                  " — a CI pin", 9000))
        self.assertEqual(tool.run_tier(None, rows), "patch/security")
        self.assertEqual(tool.run_tier(None, parse(row("2a Spec", "squad-lead", "tier `docs`: README only"))), "docs")
        self.assertIsNone(tool.run_tier(None, parse(row("8 Review", "Lead", "tier docs"))), "only step 2 decides")
        self.assertEqual(tool.folder_name("specs/issue-5/"), "issue-5")
        self.assertIsNone(tool.folder_name("../secret"))


class TestGateStamp(RepoTest):
    def setUp(self):
        super().setUp()
        self.tool = load("gate-stamp")
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.write("src/a.py", "x = 2\n")
        self.head = self.repo.commit("implement")

    def stamp(self, *argv, stdin=None):
        return run_main(self.tool, ["issue-5", *argv], stdin)

    def test_the_stamp_names_the_committed_head_and_verify_checks_it(self):
        self.repo.write("src/b.py", "y = 1\n")
        code, out, _ = self.stamp()
        self.assertEqual(code, 1)
        self.assertIn("Commit first", out)
        self.assertIn("src/b.py", out)
        self.head = self.repo.commit("more")
        code, out, _ = self.stamp()
        self.assertEqual(code, 0, out)
        last = self.repo.read("specs/issue-5/log.md").splitlines()[-1].removesuffix(" |")
        self.assertEqual(last.split(" | ")[1:4], ["7 Gate stamp", "Orchestrator",
                                                   f"PASS on {self.head} (tier standard): Format check pass; Analyzer "
                                                   "gate pass; Test with coverage pass; Coverage gate pass; "
                                                   "scope-check.py pass · figure-check.py 0 hit(s)"])
        self.assertIn("$ echo test-coverage", out)
        self.repo.commit("log")  # a commit of specs/ alone keeps the code
        self.assertEqual(self.stamp("--verify")[0], 0)
        self.repo.write("src/a.py", "x = 3\n")
        self.repo.commit("fix")
        code, out, _ = self.stamp("--verify")
        self.assertEqual(code, 1)
        self.assertIn("the code changed since the gate stamp", out)

    def test_a_failed_gate_is_recorded_and_the_coverage_gate_waits_for_its_report(self):
        self.repo.write(".squad/stack.md", STACK.replace("`echo test-coverage`", "`false`"))
        self.repo.commit("break the tests")
        code, out, _ = self.stamp()
        self.assertEqual(code, 1, out)
        last = self.repo.read("specs/issue-5/log.md").splitlines()[-1]
        self.assertIn("FAIL on ", last)
        self.assertIn("Test with coverage FAIL; Coverage gate not run (Test with coverage failed)", last)
        self.assertNotIn("$ echo coverage-gate", out)
        code, out, _ = self.stamp("--verify")
        self.assertEqual(code, 1)
        self.assertIn("the last gate stamp failed", out)

    def test_verify_needs_the_tier_of_the_run_and_the_base_branch_in_the_head(self):
        self.assertEqual(self.stamp()[0], 0)
        self.repo.commit("log")
        self.repo.write("specs/issue-5/plan.md", plan_text("security", areas="authentication"))
        code, out, _ = self.stamp("--verify")
        self.assertEqual(code, 1)
        self.assertIn("the gate stamp ran for tier standard, the run is tier security now", out)
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.git("checkout", "-q", "main")
        self.repo.write("NOTICE", "moved\n")
        self.repo.commit("main moved")
        self.repo.git("checkout", "-q", "work")
        code, out, _ = self.stamp("--verify")
        self.assertEqual(code, 1)
        self.assertIn("main has commits the head lacks", out)
        rows = self.tool.read_rows(self.repo.log_path)
        self.assertIsNone(self.tool.stamp_problem(self.repo.root, rows, base_check=False), "the summary's check")
        self.assertIsNone(self.tool.summary_problem(self.repo.root, rows))

    def test_a_patch_with_a_script_needs_the_check_the_lead_names(self):
        os.remove(os.path.join(self.repo.root, "specs", "issue-5", "plan.md"))
        self.repo.log(row("2 Plan", "Lead", "RESULT: DONE Tier: patch — a script line", 9000))
        self.repo.write("run.sh", "#!/bin/bash\necho hi\n")
        self.repo.commit("patch")
        code, out, _ = self.stamp()
        self.assertEqual(code, 1)
        self.assertIn("pass the check the Lead's result names", out)
        code, out, _ = self.stamp("--check", "bash -n run.sh", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("Analyzer gate: `echo analyzer`", out, "production code in the diff: the full analyzer gate")
        self.assertIn("check bash -n run.sh: `bash -n run.sh`", out)
        self.assertIn("scope-check.py --tier patch: `python3 .squad/tools/scope-check.py --tier patch`", out)
        self.assertEqual(self.stamp("--check", "bash -n run.sh")[0], 0)
        self.assertIn("(tier patch): ", self.repo.read("specs/issue-5/log.md").splitlines()[-1])

    def test_a_changed_record_or_area_document_runs_decision_check_with_history_required(self):
        code, out, _ = self.stamp("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertNotIn("decision-check.py", out, "no record or area document changed")
        self.repo.write("docs/areas/storage.md", "# Storage\n")
        self.repo.commit("area document")
        code, out, _ = self.stamp("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("decision-check.py: `python3 .squad/tools/decision-check.py --require-history`", out)

    def test_after_step_10_the_stamp_reads_the_log_from_stdin(self):
        log = self.repo.read("specs/issue-5/log.md")
        self.repo.git("rm", "-q", "-r", "specs/issue-5")
        self.repo.commit("Remove squad working record")
        code, out, err = self.stamp("--stdin", stdin=log)
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith("# Log: "), "standard output carries the whole log alone")
        self.assertIn("| 11 Gate stamp | Orchestrator | PASS on ", out.splitlines()[-1])
        self.assertIn("scope-check.py --no-specs pass", out.splitlines()[-1])
        self.assertIn("$ echo format-check", err)
        self.assertEqual(self.stamp("--verify", "--stdin", stdin=out)[0], 0, "plan.md comes from git history")

    def test_a_verbatim_stamp_follows_a_full_one_for_documentation_only(self):
        code, out, _ = self.stamp("--verbatim")
        self.assertEqual(code, 1)
        self.assertIn("--verbatim needs a passing stamp of the full gates", out)
        self.assertEqual(self.stamp()[0], 0)
        self.repo.write("README.md", "Readme, fixed verbatim\n")
        self.repo.commit("verbatim fix")
        code, out, _ = self.stamp("--verbatim")
        self.assertEqual(code, 0, out)
        last = self.repo.read("specs/issue-5/log.md").splitlines()[-1]
        self.assertIn("(tier standard, verbatim): Format check pass; decision-check.py pass; scope-check.py pass", last)
        self.repo.commit("log")
        self.assertEqual(self.stamp("--verify")[0], 0)
        self.repo.write("src/a.py", "x = 9\n")
        self.repo.commit("code")
        code, out, _ = self.stamp("--verbatim")
        self.assertIn("more than documentation", out)
        self.assertEqual(self.stamp("--verify", "--check", "x")[0], 2, "--verify takes no gate options")

    def test_no_stamp_needed_without_a_code_change_or_outside_git(self):
        self.repo.git("reset", "-q", "--hard", "HEAD~1")
        rows = self.tool.read_rows(self.repo.log_path)
        self.assertIsNone(self.tool.summary_problem(self.repo.root, rows), "the work folder alone is no code")
        self.repo.write("src/a.py", "x = 5\n")
        self.repo.commit("code")
        self.assertIn("no gate stamp in the log", self.tool.summary_problem(self.repo.root, rows))
        with tempfile.TemporaryDirectory() as plain:
            self.assertIsNone(self.tool.summary_problem(plain, rows))

    def test_an_unknown_folder_or_tier_is_refused(self):
        self.assertEqual(run_main(self.tool, ["issue-9"])[0], 1)
        self.assertEqual(run_main(self.tool, ["../x"])[0], 2)
        os.remove(os.path.join(self.repo.root, "specs", "issue-5", "plan.md"))
        self.repo.commit("no plan")
        code, out, _ = self.stamp()
        self.assertEqual(code, 1)
        self.assertIn("The tier is unknown", out)


if __name__ == "__main__":
    unittest.main()
