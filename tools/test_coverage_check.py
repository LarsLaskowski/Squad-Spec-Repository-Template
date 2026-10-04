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


if __name__ == "__main__":
    unittest.main()
