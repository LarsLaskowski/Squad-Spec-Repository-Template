"""Unit tests for core/.squad/tools/sonar-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import io
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

from test_squad_tools import git, load_script, write

KEY = "org_project"
SENT = object()  # stands for the token; the test checks that every call passes it on


def issue(path, line, rule="go:S1192", message="Define a constant"):
    return {"component": f"{KEY}:{path}", "line": line, "rule": rule, "message": message}


class FakeApi:
    """Answers the endpoints sonar-check.py reads from canned data, and records the calls."""

    def __init__(self, analysed="abc1234def", gate="OK", issues=(), hotspots=()):
        self.analysed, self.gate, self.issues, self.hotspots = analysed, gate, list(issues), list(hotspots)
        self.calls = []

    def __call__(self, path, params, token=None):
        self.calls.append((path, dict(params), token))
        answers = {
            "project_pull_requests/list": lambda: {"pullRequests": [{"key": "7", "commit": {"sha": self.analysed}}]},
            "qualitygates/project_status": lambda: {"projectStatus": {"status": self.gate}},
            "issues/search": lambda: {"issues": self.issues, "paging": {"total": len(self.issues)}},
            "hotspots/search": lambda: {"hotspots": self.hotspots, "paging": {"total": len(self.hotspots)}},
        }
        return answers[path]()


def make_repository():
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


class TestHttpErrors(SonarCheckCase):
    def http_error(self, code=400, body=b'{"errors":[{"msg":"Unknown parameter"}]}'):
        return urllib.error.HTTPError("https://sonarcloud.io/api/x", code, "", {}, io.BytesIO(body))

    def api_error(self, error, path="ce/task", params=None, token=None):
        with mock.patch.object(self.script.urllib.request, "urlopen", side_effect=error), \
                self.assertRaises(self.script.ApiError) as raised:
            self.script.api(path, params or {"id": "1"}, token)
        return str(raised.exception)

    def test_rejected_request_is_named_with_parameters_and_response_but_not_the_token(self):
        message = self.api_error(self.http_error(), "issues/search", {"branch": "work"}, "s3cret")
        self.assertIn("HTTP 400", message)
        self.assertIn("/api/issues/search?branch=work", message)
        self.assertIn("Unknown parameter", message)
        self.assertNotIn("s3cret", message)

    def test_empty_response_body_is_said_so(self):
        self.assertIn("empty response body", self.api_error(self.http_error(502, b"")))

    def test_long_response_body_is_cut(self):
        self.assertLess(len(self.api_error(self.http_error(400, b"x" * 5000))), 700)

    def test_main_prints_the_failing_request_as_not_checked(self):
        make_repository()
        with mock.patch.object(self.script, "api", side_effect=self.script.ApiError("HTTP 400 for GET u: bad")):
            code, output = self.run_quiet(self.script.main, ["pr", "7"])
        self.assertEqual(code, self.script.NOT_CHECKED)
        self.assertIn("HTTP 400 for GET u: bad", output)

class TestRefusedEndpoints(SonarCheckCase):
    """A 403 on the first endpoint falls back to the one a browsing credential may read."""

    def refusing(self, refused, answers):
        def api(path, params, token=None):
            if path in refused:
                raise self.script.ApiError(f"HTTP 403 for GET {path}", 403)
            return answers[path]
        return api

    def test_refused_pull_request_list_reads_the_revision_of_the_analysis(self):
        answers = {"project_analyses/search": {"analyses": [{"revision": "abc1234def"}]}}
        with mock.patch.object(self.script, "api", self.refusing({"project_pull_requests/list"}, answers)):
            self.assertEqual(self.script.analysed_commit(KEY, 7), "abc1234def")
        answers = {"project_analyses/search": {"analyses": []}}
        with mock.patch.object(self.script, "api", self.refusing({"project_pull_requests/list"}, answers)):
            self.assertEqual(self.script.analysed_commit(KEY, 7), "")

    def test_other_http_errors_are_not_swallowed(self):
        error = self.script.ApiError("HTTP 500", 500)
        with mock.patch.object(self.script, "api", side_effect=error), self.assertRaises(self.script.ApiError):
            self.script.analysed_commit(KEY, 7)

    def test_http_error_carries_its_status(self):
        error = urllib.error.HTTPError("https://sonarcloud.io/api/x", 403, "", {}, io.BytesIO(b"no"))
        with mock.patch.object(self.script.urllib.request, "urlopen", side_effect=error), \
                self.assertRaises(self.script.ApiError) as raised:
            self.script.api("ce/task", {"id": "1"})
        self.assertEqual(raised.exception.status, 403)

    def test_pending_says_a_newer_analysis_is_to_come(self):
        with mock.patch.object(self.script, "api", FakeApi(analysed="0ld0000")):
            _, output = self.run_quiet(self.script.check_pr, KEY, 7, "1234567")
        self.assertIn("newer analysis", output)


class TestChangedLines(SonarCheckCase):
    """`changed_line_map` of analyzer_common, which the coverage gate uses."""

    def setUp(self):
        super().setUp()
        self.script = load_script("coverage-check")

    def test_changed_lines_keep_paths_with_spaces(self):
        make_repository()
        lines = self.script.changed_line_map("main")
        self.assertEqual(lines, {"a.go": {4, 5}, "sp ace.go": {1}})

    def test_changed_lines_follow_renames_and_drop_deleted_files(self):
        make_repository()
        write("b.go", "package a\n\nfunc C() {}\n")
        git("add", ".")
        git("commit", "-q", "-m", "b")
        git("mv", "b.go", "c.go")
        os.remove("sp ace.go")
        lines = self.script.changed_line_map("main")
        self.assertEqual(set(lines), {"a.go", "c.go"})
        self.assertEqual(lines["c.go"], {1, 2, 3})
