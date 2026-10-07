"""Unit tests for core/.squad/tools/coverage-check.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")


def load_script():
    sys.modules["squad_settings"] = types.SimpleNamespace(
        COVERAGE_FORMAT="go", COVERAGE_REPORT_GLOB="coverage.out",
        COVERAGE_PATHSPECS=["*.go"], COVERAGE_EXCLUDES=["*_test.go"])
    sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("coverage_check", os.path.join(TOOLS, "coverage-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


class TestOnlyDiff(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.script.BASE_REF = "main"
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        git("init", "-q", "-b", "main")
        for name in ("a.go", "a_test.go"):
            with open(name, "w") as handle:
                handle.write("package a\n")
        git("add", ".")
        git("commit", "-q", "-m", "base")

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def test_deleted_test_file_counts_as_changed_test_code(self):
        git("rm", "-q", "a_test.go")
        self.assertEqual(self.script.changed_test_files(), ["a_test.go"])
        self.assertEqual(self.script.changed_lines(), {})

    def test_unchanged_tree_has_no_changed_test_files(self):
        self.assertEqual(self.script.changed_test_files(), [])


class TestSeveralReports(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        with open("go.mod", "w") as handle:
            handle.write("module example.com/m\n")
        with open("coverage.out", "w") as handle:
            handle.write("mode: set\nexample.com/m/a.go:1.1,2.2 1 1\nexample.com/m/a.go:3.1,3.9 1 0\n")
        with open("lcov.info", "w") as handle:
            handle.write("SF:web/app.js\nDA:1,1\nDA:2,0\nend_of_record\n")

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def test_reports_of_different_formats_are_merged(self):
        self.script.settings.COVERAGE_REPORTS = [("go", "coverage.out"), ("lcov", "lcov.info")]
        hits = self.script.merged_hits()
        self.assertEqual(hits["a.go"], {1: 1, 2: 1, 3: 0})
        self.assertEqual(hits["web/app.js"], {1: 1, 2: 0})

    def test_single_format_settings_still_work(self):
        hits = self.script.merged_hits()
        self.assertEqual(sorted(hits), ["a.go"])

    def test_unknown_format_is_refused(self):
        self.script.settings.COVERAGE_REPORTS = [("jacoco", "x.xml")]
        with self.assertRaises(SystemExit):
            self.script.report_sources()


if __name__ == "__main__":
    unittest.main()
