"""Unit tests for core/.squad/tools/sonar-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import io
import os
import tempfile
import types
import unittest
from unittest import mock

from test_squad_tools import git, load_script, write

KEY = "org_project"
SENT = object()  # stands for the token; the test checks that every call passes it on


def issue(path, line, rule="go:S1192", message="Define a constant"):
    return {"component": f"{KEY}:{path}", "line": line, "rule": rule, "message": message}


class FakeApi:
    """Answers the endpoints sonar-check.py reads from canned data, and records the calls."""

    def __init__(self, analysed="abc1234def", gate="OK", issues=(), hotspots=(), task=None):
        self.analysed, self.gate, self.issues, self.hotspots = analysed, gate, list(issues), list(hotspots)
        self.task = task or {"status": "SUCCESS", "branch": "work"}
        self.calls = []

    def __call__(self, path, params, token=None):
        self.calls.append((path, dict(params), token))
        answers = {
            "project_pull_requests/list": lambda: {"pullRequests": [{"key": "7", "commit": {"sha": self.analysed}}]},
            "qualitygates/project_status": lambda: {"projectStatus": {"status": self.gate}},
            "issues/search": lambda: {"issues": self.issues, "paging": {"total": len(self.issues)}},
            "hotspots/search": lambda: {"hotspots": self.hotspots, "paging": {"total": len(self.hotspots)}},
            "ce/task": lambda: {"task": self.task},
        }
        return answers[path]()


class SonarCheckCase(unittest.TestCase):
    def setUp(self):
        self.script = load_script("sonar-check")
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def run_quiet(self, function, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = function(*args)
            except SystemExit as stop:
                code = stop.code
        return code, output.getvalue()

    def repository(self):
        """A git repository with a commit on `main` and a work branch that changes two files."""
        git("init", "-q", "-b", "main")
        write("sonar-project.properties", "sonar.projectKey=org_project\n")
        write("a.go", "package a\n\nfunc A() {}\n")
        git("add", ".")
        git("commit", "-q", "-m", "base")
        git("checkout", "-q", "-b", "work")
        write("a.go", "package a\n\nfunc A() {}\n\nfunc B() {}\n")
        write("sp ace.go", "package a\n")
        git("add", ".")
        git("commit", "-q", "-m", "work")


class TestPullRequestMode(SonarCheckCase):
    def test_project_key_from_properties_then_workflow_and_never_a_placeholder(self):
        self.assertIsNone(self.script.project_key())
        write(".github/workflows/ci.yml", "run: dotnet-sonarscanner begin /k:\"org_dotnet\" /o:\"org\"\n")
        self.assertEqual(self.script.project_key(), "org_dotnet")
        write("sonar-project.properties", "sonar.projectKey={{TODO: sonar-project-key}}\n")
        self.assertEqual(self.script.project_key(), "org_dotnet")
        write("sonar-project.properties", "sonar.organization=org\nsonar.projectKey=org_ts\n")
        self.assertEqual(self.script.project_key(), "org_ts")

    def test_analysis_of_another_head_is_pending(self):
        with mock.patch.object(self.script, "api", FakeApi(analysed="0ld0000")):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "1234567")
        self.assertEqual(code, self.script.PENDING)
        self.assertIn("PENDING", output)

    def test_analysis_without_a_quality_gate_yet_is_pending(self):
        with mock.patch.object(self.script, "api", FakeApi(gate="NONE")):
            code, _ = self.run_quiet(self.script.check_pr, KEY, 7, "abc1234")
        self.assertEqual(code, self.script.PENDING)

    def test_issues_and_hotspots_of_the_head_fail_and_the_token_is_sent(self):
        fake = FakeApi(issues=[issue("a.go", 3)], hotspots=[{"component": f"{KEY}:b.go", "line": 9,
                                                            "ruleKey": "go:S2068", "message": "Review"}])
        with mock.patch.object(self.script, "api", fake):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "abc1234", SENT)
        self.assertEqual(code, self.script.FINDINGS)
        self.assertIn("go:S1192 a.go:3 Define a constant", output)
        self.assertIn("go:S2068 b.go:9 Review", output)
        self.assertTrue(all(sent is SENT for _, _, sent in fake.calls))

    def test_failed_gate_without_issues_fails(self):
        with mock.patch.object(self.script, "api", FakeApi(gate="ERROR")):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "abc1234")
        self.assertEqual(code, self.script.FINDINGS)
        self.assertIn("Quality gate: ERROR", output)

    def test_clean(self):
        with mock.patch.object(self.script, "api", FakeApi()):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "abc1234")
        self.assertEqual(code, self.script.CLEAN)
        self.assertIn("PASS", output)

    def test_paged_reads_every_page(self):
        pages = {1: {"issues": [1, 2], "paging": {"total": 3}}, 2: {"issues": [3], "paging": {"total": 3}}}
        with mock.patch.object(self.script, "PAGE_SIZE", 2), \
                mock.patch.object(self.script, "api", lambda path, params, token=None: pages[params["p"]]):
            self.assertEqual(self.script.paged("issues/search", {}, "issues"), [1, 2, 3])

    def test_wrong_usage_is_its_own_exit_code(self):
        code, _ = self.run_quiet(self.script.main, ["pr"])
        self.assertEqual(code, self.script.USAGE)
        code, _ = self.run_quiet(self.script.main, ["scan"])
        self.assertEqual(code, self.script.USAGE)


class TestBranchMode(SonarCheckCase):
    def test_changed_lines_keep_paths_with_spaces(self):
        self.repository()
        lines = self.script.changed_line_map("main")
        self.assertEqual(lines, {"a.go": {4, 5}, "sp ace.go": {1}})

    def test_changed_lines_follow_renames_and_drop_deleted_files(self):
        self.repository()
        write("b.go", "package a\n\nfunc C() {}\n")
        git("add", ".")
        git("commit", "-q", "-m", "b")
        git("mv", "b.go", "c.go")
        os.remove("sp ace.go")
        lines = self.script.changed_line_map("main")
        self.assertEqual(set(lines), {"a.go", "c.go"})
        self.assertEqual(lines["c.go"], {1, 2, 3})

    def test_coverage_reports_may_lie_around_untracked(self):
        self.repository()
        write("coverage/lcov.info", "TN:\n")
        settings = types.SimpleNamespace(BASE_REF="main", COVERAGE_FORMAT="lcov",
                                         COVERAGE_REPORT_GLOB="coverage/lcov.info")
        with mock.patch.object(self.script, "settings", settings):
            self.assertEqual(self.script.unexpected_files(), [])
            write("notes.txt", "scratch\n")
            self.assertEqual(self.script.unexpected_files(), ["notes.txt"])

    def test_findings_count_only_on_changed_lines(self):
        lines = {"a.go": {3, 4}, "c.go": set()}
        self.assertTrue(self.script.on_changed_line(issue("a.go", 4), KEY, lines))
        self.assertFalse(self.script.on_changed_line(issue("a.go", 5), KEY, lines))
        self.assertFalse(self.script.on_changed_line(issue("b.go", 3), KEY, lines))
        self.assertTrue(self.script.on_changed_line({"component": f"{KEY}:c.go"}, KEY, lines))

    def test_without_token_is_not_checked(self):
        self.repository()
        with mock.patch.dict(os.environ, {"SONAR_TOKEN": ""}):
            code, output = self.run_quiet(self.script.main, ["branch", "--", "true"])
        self.assertEqual(code, self.script.NOT_CHECKED)
        self.assertIn("SONAR_TOKEN", output)

    def test_dirty_tree_and_base_branch_are_not_scanned(self):
        self.repository()
        write("scratch.txt", "secret\n")
        with mock.patch.dict(os.environ, {"SONAR_TOKEN": "t"}):
            code, output = self.run_quiet(self.script.main, ["branch", "--", "true"])
        self.assertEqual(code, self.script.NOT_CHECKED)
        self.assertIn("uncommitted", output)
        os.remove("scratch.txt")
        git("checkout", "-q", "main")
        with mock.patch.dict(os.environ, {"SONAR_TOKEN": "t"}):
            code, output = self.run_quiet(self.script.main, ["branch", "--", "true"])
        self.assertEqual(code, self.script.NOT_CHECKED)
        self.assertIn("work branch", output)

    def test_failed_or_missing_scanner_is_not_checked_and_leaves_no_output(self):
        self.repository()
        failing = ["python3", "-c", "import os; os.makedirs('.scannerwork'); raise SystemExit(1)"]
        for command in (failing, ["no-such-scanner-binary"]):
            with mock.patch.dict(os.environ, {"SONAR_TOKEN": "t"}):
                code, _ = self.run_quiet(self.script.main, ["branch", "--", *command])
            self.assertEqual(code, self.script.NOT_CHECKED)
            self.assertFalse(os.path.exists(".scannerwork"))

    def test_successful_scan_reports_findings_on_changed_lines_only(self):
        self.repository()
        scanner = ["python3", "-c", "import os; os.makedirs('.scannerwork'); "
                   "open('.scannerwork/report-task.txt', 'w').write('ceTaskId=T1\\n')"]
        fake = FakeApi(issues=[issue("a.go", 5), issue("a.go", 1, rule="go:S100")])
        with mock.patch.dict(os.environ, {"SONAR_TOKEN": "t"}), mock.patch.object(self.script, "api", fake):
            code, output = self.run_quiet(self.script.main, ["branch", "--", *scanner])
        self.assertEqual(code, self.script.FINDINGS)
        self.assertIn("go:S1192 a.go:5", output)
        self.assertNotIn("go:S100", output)
        self.assertFalse(os.path.exists(".scannerwork"))
        searched = [params for path, params, _ in fake.calls if path == "issues/search"]
        self.assertEqual(searched[0]["branch"], "work")
        self.assertEqual(set(searched[0]["componentKeys"].split(",")), {f"{KEY}:a.go", f"{KEY}:sp ace.go"})

    def test_task_that_never_finishes_times_out(self):
        fake = FakeApi(task={"status": "IN_PROGRESS"})
        with mock.patch.object(self.script, "api", fake), mock.patch.object(self.script, "WAIT_SECONDS", 0), \
                mock.patch.object(self.script, "POLL_SECONDS", 0):
            self.assertEqual(self.script.wait_for_task("T1", "t")["status"], "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
