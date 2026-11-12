"""Unit tests for core/.squad/tools/coverage-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import glob
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")


def load_script():
    sys.modules.pop("analyzer_common", None)  # it reads squad_settings once, at import
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


class TestExcludeMatchingNoFile(unittest.TestCase):
    """An exclude that matches no tracked file (`*.d.ts` without declaration files under `src/`) must not
    empty the production file list: `git ls-files` with such an `:(exclude)` pathspec lists nothing."""

    def setUp(self):
        self.script = load_script()
        self.script.settings.COVERAGE_PATHSPECS = ["src/*.ts"]
        self.script.settings.COVERAGE_EXCLUDES = ["*.test.ts", "*.d.ts"]
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        os.makedirs("src/setup")
        for name in ("src/a.ts", "src/a.test.ts", "src/setup/cookies.ts", "worker.d.ts"):
            with open(name, "w") as handle:
                handle.write("export {};\n")
        git("init", "-q", "-b", "main")
        git("add", ".")
        git("commit", "-q", "-m", "base")

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def test_tracked_production_files_are_listed(self):
        self.assertEqual(self.script.production_files(), {"src/a.ts", "src/setup/cookies.ts"})

    def test_overall_coverage_measures_the_tracked_files(self):
        hits = {"src/a.ts": {1: 1, 2: 0}, "src/setup/cookies.ts": {1: 1}, "src/a.test.ts": {1: 1}}
        self.assertEqual(self.script.overall_coverage(hits), (2 / 3 * 100, 2, 3))

    def test_untracked_production_files_are_listed(self):
        for name in ("src/new.ts", "src/new.test.ts"):
            with open(name, "w") as handle:
                handle.write("export {};\n")
        self.assertEqual(self.script.production_files("--others", "--exclude-standard"), {"src/new.ts"})


class TestStaleReport(unittest.TestCase):
    """A report older than the last change of a tracked production or test file (a merge, a formatter, an edit after
    the test run) counts lines that have moved: the gate refuses it and asks for *Test with coverage* again."""

    def setUp(self):
        self.script = load_script()
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        git("init", "-q", "-b", "main")
        for name in ("a.go", "a_test.go", "coverage.out"):
            with open(name, "w") as handle:
                handle.write("package a\n")
        git("add", "a.go", "a_test.go")
        git("commit", "-q", "-m", "base")
        self.start = time.time() - 1000
        for name, age in (("a.go", 0), ("a_test.go", 0), ("coverage.out", 10)):
            self.touch(name, age)

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def touch(self, name, seconds):
        os.utime(name, (self.start + seconds, self.start + seconds))

    def assert_refused(self, newest):
        with self.assertRaises(SystemExit) as raised:
            self.script.refuse_stale_reports()
        self.assertIn(f"last change of {newest}", str(raised.exception.code))
        self.assertIn("Run *Test with coverage*", str(raised.exception.code))

    def test_report_written_after_the_last_change_is_accepted(self):
        self.assertIsNone(self.script.refuse_stale_reports())

    def test_production_file_changed_after_the_report_is_refused(self):
        self.touch("a.go", 20)
        self.assert_refused("a.go")

    def test_test_file_changed_after_the_report_is_refused(self):
        self.touch("a_test.go", 20)
        self.assert_refused("a_test.go")

    def test_untracked_and_unmeasured_files_do_not_count(self):
        for name in ("b.go", "README.md"):
            with open(name, "w") as handle:
                handle.write("package a\n")
        git("add", "README.md")
        self.touch("b.go", 20)
        self.touch("README.md", 20)
        self.assertIsNone(self.script.refuse_stale_reports())

    def test_oldest_of_several_reports_decides(self):
        with open("lcov.info", "w") as handle:
            handle.write("SF:a.go\nDA:1,1\nend_of_record\n")
        self.touch("lcov.info", 2)
        self.touch("a.go", 5)  # older than coverage.out, newer than lcov.info
        self.script.settings.COVERAGE_REPORTS = [("go", "coverage.out"), ("lcov", "lcov.info")]
        self.assert_refused("a.go")


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


class TestConditions(unittest.TestCase):
    """Branch conditions count on changed lines as SonarQube counts them (DockerUpdateGuard#430)."""

    def setUp(self):
        self.script = load_script()
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        with open("coverage.cobertura.xml", "w") as handle:
            handle.write('<coverage><sources><source>.</source></sources><packages><package><classes>'
                         '<class filename="src/Map.cs"><lines>'
                         '<line number="1" hits="1" branch="False" />'
                         '<line number="2" hits="1" branch="True" condition-coverage="25% (1/4)" />'
                         '<line number="3" hits="0" branch="False" />'
                         '</lines></class></classes></package></packages></coverage>')
        with open("lcov.info", "w") as handle:
            handle.write("SF:web/app.js\nDA:1,1\nBRDA:1,0,0,1\nBRDA:1,0,1,0\nBRDA:1,0,2,-\nend_of_record\n")

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def test_conditions_are_read_from_cobertura_and_lcov(self):
        self.script.settings.COVERAGE_REPORTS = [("cobertura", "*.xml"), ("lcov", "lcov.info"), ("go", "none.out")]
        self.script.run_reports = lambda pattern: [] if pattern == "none.out" else sorted(glob.glob(pattern))
        self.assertEqual(self.script.merged_conditions(), {"src/Map.cs": {2: (1, 4)}, "web/app.js": {1: (1, 3)}})
        self.script.settings.COVERAGE_CONDITIONS = False
        self.assertEqual(self.script.merged_conditions(), {})

    def test_new_code_counts_lines_and_conditions_together(self):
        self.script.changed_lines = lambda: {"src/Map.cs": {1, 2, 3}}
        hits = {"src/Map.cs": {1: 1, 2: 1, 3: 0}}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            lines_only = self.script.new_code_coverage(hits)
            both = self.script.new_code_coverage(hits, {"src/Map.cs": {2: (1, 4)}})
        self.assertEqual(lines_only, (2 / 3 * 100, 2, 3, 0, 0))
        self.assertEqual(both, (3 / 7 * 100, 2, 3, 1, 4), "2 of 3 lines and 1 of 4 conditions: 3 of 7")
        self.assertIn("2/3 + 1/4 conditions  src/Map.cs  uncovered: [3]  conditions not covered: [2]",
                      output.getvalue())


if __name__ == "__main__":
    unittest.main()
