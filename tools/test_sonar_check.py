"""Unit tests for core/.squad/tools/sonar-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from test_squad_tools import load_script, write

KEY = "org_project"


def issue(path, line, rule="go:S1192", message="Define a constant"):
    return {"component": f"{KEY}:{path}", "line": line, "rule": rule, "message": message}


class FakeApi:
    """Answers the endpoints sonar-check.py reads from canned data."""

    def __init__(self, analysed="abc", gate="OK", issues=(), hotspots=()):
        self.analysed, self.gate, self.issues, self.hotspots = analysed, gate, list(issues), list(hotspots)

    def __call__(self, path, params, token=None):
        if path == "project_pull_requests/list":
            return {"pullRequests": [{"key": "7", "commit": {"sha": self.analysed}}]}
        if path == "qualitygates/project_status":
            return {"projectStatus": {"status": self.gate}}
        if path == "issues/search":
            return {"issues": self.issues, "paging": {"total": len(self.issues)}}
        if path == "hotspots/search":
            return {"hotspots": self.hotspots, "paging": {"total": len(self.hotspots)}}
        raise AssertionError(path)


class TestSonarCheck(unittest.TestCase):
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
        with contextlib.redirect_stdout(output):
            code = function(*args)
        return code, output.getvalue()

    def test_project_key_from_properties_then_workflow_and_never_a_placeholder(self):
        self.assertIsNone(self.script.project_key())
        write(".github/workflows/ci.yml", "run: dotnet-sonarscanner begin /k:\"org_dotnet\" /o:\"org\"\n")
        self.assertEqual(self.script.project_key(), "org_dotnet")
        write("sonar-project.properties", "sonar.projectKey={{TODO: sonar-project-key}}\n")
        self.assertEqual(self.script.project_key(), "org_dotnet")
        write("sonar-project.properties", "sonar.organization=org\nsonar.projectKey=org_ts\n")
        self.assertEqual(self.script.project_key(), "org_ts")

    def test_pr_analysis_of_another_head_is_pending(self):
        with mock.patch.object(self.script, "api", FakeApi(analysed="old")):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "new")
        self.assertEqual(code, self.script.PENDING)
        self.assertIn("PENDING", output)

    def test_pr_lists_issues_and_hotspots_of_the_head(self):
        fake = FakeApi(issues=[issue("a.go", 3)], hotspots=[{"component": f"{KEY}:b.go", "line": 9,
                                                            "ruleKey": "go:S2068", "message": "Review"}])
        with mock.patch.object(self.script, "api", fake):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "abc")
        self.assertEqual(code, self.script.FINDINGS)
        self.assertIn("go:S1192 a.go:3 Define a constant", output)
        self.assertIn("go:S2068 b.go:9 Review", output)

    def test_pr_failed_gate_without_issues_fails(self):
        with mock.patch.object(self.script, "api", FakeApi(gate="ERROR")):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "abc")
        self.assertEqual(code, self.script.FINDINGS)
        self.assertIn("Quality gate: ERROR", output)

    def test_pr_clean(self):
        with mock.patch.object(self.script, "api", FakeApi()):
            code, output = self.run_quiet(self.script.check_pr, KEY, 7, "abc")
        self.assertEqual(code, self.script.CLEAN)
        self.assertIn("PASS", output)

    def test_branch_findings_count_only_on_changed_lines(self):
        lines = {"a.go": {3, 4}, "c.go": set()}
        self.assertTrue(self.script.on_changed_line(issue("a.go", 4), KEY, lines))
        self.assertFalse(self.script.on_changed_line(issue("a.go", 5), KEY, lines))
        self.assertFalse(self.script.on_changed_line(issue("b.go", 3), KEY, lines))
        self.assertTrue(self.script.on_changed_line({"component": f"{KEY}:c.go"}, KEY, lines))

    def test_branch_without_token_is_not_checked(self):
        write("sonar-project.properties", "sonar.projectKey=org_ts\n")
        with mock.patch.dict(os.environ, {"SONAR_TOKEN": ""}):
            code, output = self.run_quiet(self.script.main, ["branch", "--", "true"])
        self.assertEqual(code, self.script.NOT_CHECKED)
        self.assertIn("SONAR_TOKEN", output)

    def test_failed_scan_is_not_checked_and_leaves_no_scanner_output(self):
        write("sonar-project.properties", "sonar.projectKey=org_ts\n")
        command = ["python3", "-c", "import os; os.makedirs('.scannerwork'); raise SystemExit(1)"]
        with mock.patch.dict(os.environ, {"SONAR_TOKEN": "t"}):
            code, _ = self.run_quiet(self.script.main, ["branch", "--", *command])
        self.assertEqual(code, self.script.NOT_CHECKED)
        self.assertFalse(os.path.exists(".scannerwork"))


if __name__ == "__main__":
    unittest.main()
