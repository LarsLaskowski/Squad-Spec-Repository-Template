"""Unit tests for tools/sonar-local.py: run `python3 -m unittest discover tools`."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sonar-local.py")
spec = importlib.util.spec_from_file_location("sonar_local", SCRIPT)
sonar_local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sonar_local)

URL = "https://example.org/file"
HARNESS_OUTPUT = ("RULES\t396\nMISSING\tS9999\n"
                  "ISSUE\tcore/a.py\t53\tS7632\tFix the syntax of this issue suppression comment.\n"
                  "ISSUE\ttools/test_a.py\t4\tS1481\tRemove the unused local variable.\n"
                  "PARSE\tseed/b.py\t2\tParse error at line 2\n"
                  "noise from the JVM\n")


def response(body):
    """A context manager urlopen may return."""
    handle = mock.MagicMock()
    handle.__enter__.return_value.read.return_value = body
    return handle


def http_error(code):
    return urllib.error.HTTPError(URL, code, "error", None, io.BytesIO(b""))


class TestFetch(unittest.TestCase):
    def test_returns_the_body_and_sends_the_headers(self):
        with mock.patch.object(sonar_local.urllib.request, "urlopen", return_value=response(b"body")) as urlopen:
            self.assertEqual(sonar_local.fetch(URL, {"Authorization": "Basic x"}), b"body")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.unredirected_hdrs, {"Authorization": "Basic x"})

    def test_retries_a_rate_limit_and_a_broken_connection_with_backoff(self):
        sleep = mock.Mock()
        outcomes = [http_error(429), urllib.error.URLError("reset"), response(b"ok")]
        with mock.patch.object(sonar_local.urllib.request, "urlopen", side_effect=outcomes):
            self.assertEqual(sonar_local.fetch(URL, sleep=sleep), b"ok")
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])

    def test_gives_up_after_the_last_retry(self):
        sleep = mock.Mock()
        with mock.patch.object(sonar_local.urllib.request, "urlopen", side_effect=http_error(503)), \
                self.assertRaisesRegex(sonar_local.CannotRun, "HTTP 503"):
            sonar_local.fetch(URL, sleep=sleep)
        self.assertEqual(sleep.call_count, sonar_local.RETRIES - 1)
        with mock.patch.object(sonar_local.urllib.request, "urlopen", side_effect=TimeoutError("slow")), \
                self.assertRaisesRegex(sonar_local.CannotRun, "failed: slow"):
            sonar_local.fetch(URL, sleep=sleep)

    def test_does_not_retry_a_client_error(self):
        sleep = mock.Mock()
        with mock.patch.object(sonar_local.urllib.request, "urlopen", side_effect=http_error(404)), \
                self.assertRaisesRegex(sonar_local.CannotRun, "HTTP 404"):
            sonar_local.fetch(URL, sleep=sleep)
        sleep.assert_not_called()

    def test_refuses_a_url_that_is_not_https(self):
        with self.assertRaisesRegex(sonar_local.CannotRun, "non-https"):
            sonar_local.fetch("file:///etc/passwd")


class TestDownload(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.data = {artifact: f"jar of {artifact}".encode() for _, artifact, _, _ in sonar_local.ARTIFACTS}
        pinned = [(group, artifact, version, hashlib.sha256(self.data[artifact]).hexdigest())
                  for group, artifact, version, _ in sonar_local.ARTIFACTS]
        patcher = mock.patch.object(sonar_local, "ARTIFACTS", pinned)
        patcher.start()
        self.addCleanup(patcher.stop)

    def body(self, url, sleep=None):
        return next(data for artifact, data in self.data.items() if f"/{artifact}-" in url)

    def test_downloads_once_and_reuses_the_cache(self):
        with mock.patch.object(sonar_local, "fetch", side_effect=self.body) as fetch:
            paths = sonar_local.download_jars(self.dir.name)
            self.assertEqual(sonar_local.download_jars(self.dir.name), paths)
        self.assertEqual(fetch.call_count, len(sonar_local.ARTIFACTS))
        self.assertIn("/org/sonarsource/python/sonar-python-plugin/", fetch.call_args_list[0].args[0])
        with open(paths[0], "rb") as handle:
            self.assertEqual(handle.read(), self.data["sonar-python-plugin"])

    def test_replaces_a_cached_jar_that_does_not_match_its_sum(self):
        with mock.patch.object(sonar_local, "fetch", side_effect=self.body):
            paths = sonar_local.download_jars(self.dir.name)
        with open(paths[1], "wb") as handle:
            handle.write(b"tampered")
        with mock.patch.object(sonar_local, "fetch", side_effect=self.body) as fetch:
            sonar_local.download_jars(self.dir.name)
        self.assertEqual(fetch.call_count, 1)

    def test_refuses_a_download_that_does_not_match_its_sum(self):
        with mock.patch.object(sonar_local, "fetch", return_value=b"something else"), \
                self.assertRaisesRegex(sonar_local.CannotRun, "pinned SHA-256"):
            sonar_local.download_jars(self.dir.name)
        self.assertEqual(os.listdir(self.dir.name), [])


class TestRules(unittest.TestCase):
    def test_reads_every_page_and_keeps_the_open_python_rules(self):
        pages = [json.dumps({"total": 3, "rules": [{"key": "python:S100"}, {"key": "pythonsecurity:S2076"}]}).encode(),
                 json.dumps({"total": 3, "rules": [{"key": "python:S1192"}]}).encode()]
        with mock.patch.object(sonar_local, "PAGE_SIZE", 2), \
                mock.patch.object(sonar_local, "fetch", side_effect=pages) as fetch:
            self.assertEqual(sonar_local.active_rules("token"), ["S100", "S1192"])
        first, second = fetch.call_args_list
        self.assertIn("qprofile=AZ6SwXCXNtdzQiT7rg_6", first.args[0])
        self.assertIn("p=2", second.args[0])
        self.assertEqual(first.args[1], {"Authorization": "Basic dG9rZW46"})

    def test_sends_no_header_without_a_token(self):
        page = json.dumps({"total": 0, "rules": []}).encode()
        with mock.patch.object(sonar_local, "fetch", return_value=page) as fetch:
            self.assertEqual(sonar_local.active_rules(""), [])
        self.assertEqual(fetch.call_args.args[1], {})

    def test_reads_a_rules_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("python:S1192\n\nS100\nS100\n")
        self.addCleanup(os.unlink, handle.name)
        self.assertEqual(sonar_local.read_rules(handle.name), ["S100", "S1192"])


class TestFiles(unittest.TestCase):
    def test_finds_python_files_in_hidden_directories_and_given_paths(self):
        with tempfile.TemporaryDirectory() as root:
            for path in ("core/.squad/tools/a.py", "core/README.md", "tools/test_b.py", "tools/c.py", "other/d.py"):
                os.makedirs(os.path.dirname(os.path.join(root, path)), exist_ok=True)
                with open(os.path.join(root, path), "w", encoding="utf-8") as handle:
                    handle.write("x = 1\n")
            self.assertEqual(sonar_local.python_files(root=root),
                             [os.path.join("core", ".squad", "tools", "a.py"), os.path.join("tools", "c.py"),
                              os.path.join("tools", "test_b.py")])
            self.assertEqual(sonar_local.python_files(["other/d.py", "core"], root),
                             [os.path.join("core", ".squad", "tools", "a.py"), os.path.join("other", "d.py")])

    def test_test_files_are_named_test_(self):
        self.assertTrue(sonar_local.is_test("tools/test_release.py"))
        self.assertFalse(sonar_local.is_test("tools/release.py"))


class TestHarness(unittest.TestCase):
    def run_with(self, result):
        seen = {}

        def run(command, **kwargs):
            with open(command[-2], encoding="utf-8") as handle:
                seen["rules"] = handle.read()
            with open(command[-1], encoding="utf-8") as handle:
                seen["files"] = handle.read()
            seen["command"], seen["cwd"] = command, kwargs["cwd"]
            return result

        with mock.patch.object(sonar_local.shutil, "which", return_value="/usr/bin/java"), \
                mock.patch.object(sonar_local.subprocess, "run", side_effect=run):
            output = sonar_local.run_harness(["plugin.jar", "api.jar"], ["S1", "S2"], ["a.py", "tools/test_a.py"], "/r")
        return output, seen

    def test_passes_the_rules_and_files_to_the_java_harness(self):
        output, seen = self.run_with(subprocess.CompletedProcess([], 0, "RULES\t2\n", ""))
        self.assertEqual(output, "RULES\t2\n")
        self.assertEqual(seen["command"][:5], ["/usr/bin/java", "-cp", f"plugin.jar{os.pathsep}api.jar",
                                               sonar_local.HARNESS, "plugin.jar"])
        self.assertEqual(seen["rules"], "S1\nS2\n")
        self.assertEqual(seen["files"], "main\ta.py\ntest\ttools/test_a.py\n")
        self.assertEqual(seen["cwd"], "/r")

    def test_a_failing_harness_cannot_run(self):
        failed = subprocess.CompletedProcess([], 1, "", "NoClassDefFoundError")
        with mock.patch.object(sonar_local.shutil, "which", return_value="/usr/bin/java"), \
                mock.patch.object(sonar_local.subprocess, "run", return_value=failed), \
                self.assertRaisesRegex(sonar_local.CannotRun, "exit 1.*NoClassDefFoundError"):
            sonar_local.run_harness(["plugin.jar"], ["S1"], ["a.py"])

    def test_needs_java(self):
        with mock.patch.object(sonar_local.shutil, "which", return_value=None), \
                mock.patch.object(sonar_local.subprocess, "run") as run, \
                self.assertRaisesRegex(sonar_local.CannotRun, "java is not on PATH"):
            sonar_local.run_harness(["plugin.jar"], ["S1"], ["a.py"])
        run.assert_not_called()

    def test_parses_the_output(self):
        loaded, missing, issues = sonar_local.parse_output(HARNESS_OUTPUT)
        self.assertEqual((loaded, missing), (396, ["S9999"]))
        self.assertEqual(issues, [("core/a.py", 53, "python:S7632", "Fix the syntax of this issue suppression comment."),
                                  ("seed/b.py", 2, "parse", "Parse error at line 2"),
                                  ("tools/test_a.py", 4, "python:S1481", "Remove the unused local variable.")])


class TestMain(unittest.TestCase):
    def main(self, output=None, error=None, argv=(), rules=("S1",)):
        out = io.StringIO()
        harness = mock.Mock(return_value=output, side_effect=error)
        with mock.patch.object(sonar_local, "active_rules", return_value=list(rules)) as active, \
                mock.patch.object(sonar_local, "download_jars", return_value=["p.jar"]), \
                mock.patch.object(sonar_local, "run_harness", harness), \
                mock.patch.dict(os.environ, {"SONAR_TOKEN": "t"}), contextlib.redirect_stdout(out):
            code = sonar_local.main(["--cache", "cache", *argv], sleep=mock.Mock())
        return code, out.getvalue(), active, harness

    def test_an_issue_in_a_non_test_file_fails(self):
        code, out, active, harness = self.main(HARNESS_OUTPUT)
        self.assertEqual(code, 1)
        self.assertEqual(active.call_args.args[0], "t")
        self.assertIn("core/a.py:53: python:S7632 Fix the syntax", out)
        self.assertIn("tools/test_a.py:4: python:S1481 Remove the unused local variable.  (test file, not failing)", out)
        self.assertIn("1 active rule(s) have no check in sonar-python-plugin 5.32.0.37250: S9999", out)
        self.assertIn("2 issue(s) in non-test files, 1 in test files: FAIL", out)
        self.assertIn("tools/sonar-local.py", harness.call_args.args[2])

    def test_issues_only_in_test_files_pass(self):
        code, out, _, _ = self.main("RULES\t1\nISSUE\ttools/test_a.py\t4\tS1481\tunused\n")
        self.assertEqual(code, 0)
        self.assertIn("0 issue(s) in non-test files, 1 in test files: PASS", out)

    def test_a_rules_file_replaces_the_profile(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("S7632\n")
        self.addCleanup(os.unlink, handle.name)
        code, _, active, harness = self.main("RULES\t1\n", argv=["--rules", handle.name, "tools/sonar-local.py"])
        self.assertEqual(code, 0)
        active.assert_not_called()
        self.assertEqual(harness.call_args.args[1:3], (["S7632"], [os.path.join("tools", "sonar-local.py")]))

    def test_cannot_run_is_not_checked(self):
        code, out, _, _ = self.main(error=sonar_local.CannotRun("java is not on PATH"))
        self.assertEqual(code, 2)
        self.assertIn("NOT CHECKED: java is not on PATH", out)

    def test_an_empty_profile_is_not_checked(self):
        code, out, _, _ = self.main(rules=())
        self.assertEqual(code, 2)
        self.assertIn("no active 'python:' rule", out)

    def test_no_file_to_analyse(self):
        code, out, _, _ = self.main(argv=["no/such/dir"])
        self.assertEqual(code, 2)
        self.assertIn("No Python file", out)

    def test_default_cache_follows_xdg(self):
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "/c"}):
            self.assertEqual(sonar_local.default_cache(), os.path.join("/c", "squad-sonar-local"))


if __name__ == "__main__":
    unittest.main()
