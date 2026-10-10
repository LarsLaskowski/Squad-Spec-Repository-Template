"""Unit tests for core/.squad/tools/squad-log.py and scope-check.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")


def load_script(name):
    sys.modules["squad_settings"] = types.SimpleNamespace(BASE_REF="main")
    sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(TOOLS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


def write(path, text, newline="\n"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)


class TestSquadLog(unittest.TestCase):
    def setUp(self):
        self.script = load_script("squad-log")
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "log.md")

    def tearDown(self):
        self.dir.cleanup()

    def test_row_follows_the_files_line_ending(self):
        write(self.path, "| Date | Step | Member | Result |\r\n| - | - | - | - |", newline="")
        self.script.append_row(self.path, "1 Intake", "Orchestrator", "branch created", today="2026-01-02")
        with open(self.path, "rb") as handle:
            data = handle.read()
        self.assertTrue(data.endswith(b"| - | - | - | - |\r\n| 2026-01-02 | 1 Intake | Orchestrator | branch created |\r\n"))

    def test_launch_trailer_and_summary(self):
        write(self.path, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        self.script.append_row(self.path, "2 Plan", "Lead", "plan written", today="2026-01-02",
                               launch=("opus/high", 37445, 6, 57))
        self.script.append_row(self.path, "2 Plan", "Devil's Advocate", "2 objections | 1 minor", today="2026-01-02",
                               launch=("sonnet/high", 12000, 3, 20))
        self.script.append_row(self.path, "2 Plan", "Lead", "revised", today="2026-01-02", launch=("opus/high", 8000, 2, 10))
        self.script.append_row(self.path, "7 Code check", "Orchestrator", "gates pass", today="2026-01-02")
        table = self.script.summary(self.path)
        self.assertIn("| Devil's Advocate | sonnet/high | 1 | 12,000 | 3 | 20 |", table)
        self.assertIn("| Lead | opus/high | 2 | 45,445 | 8 | 67 |", table)
        self.assertIn("| **Total** | | 3 | 57,445 | 11 | 87 |", table)

    def test_controls_pipes_and_newlines_are_escaped(self):
        write(self.path, "| Date |\n")
        row = self.script.append_row(self.path, "2 Plan", "Lead", "a|b\nsecond \u202e line\tend", today="2026-01-02")
        self.assertEqual(row, "| 2026-01-02 | 2 Plan | Lead | a\\|b<br>second U+202E line end |")


class TestScopeCheck(unittest.TestCase):
    def setUp(self):
        self.script = load_script("scope-check")
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        git("init", "-q", "-b", "main")
        write("docs/CONTRIBUTING.md", "# Contributing\n\ntemplate text\n<!-- project:begin areas -->\nold\n"
              "<!-- project:end areas -->\nmore template text\n")
        write("README.md", "# Readme\n")
        write("src/a.go", "package a\n")
        write(".squad/stack.md", "# Stack\n")
        git("add", ".")
        git("commit", "-q", "-m", "base")
        git("checkout", "-q", "-b", "work")

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def errors(self, tier=None, no_specs=False):
        base = self.script.merge_base()
        return self.script.check(self.script.changed_files(base), base, tier, no_specs)

    def test_clean_product_change_passes(self):
        write("src/a.go", "package a\n\nvar X = 1\n")
        write("specs/issue-1/log.md", "| Date |\n")
        self.assertEqual(self.errors(tier="standard"), [])

    def test_squad_files_are_reported_but_stack_and_project_are_allowed(self):
        write(".squad/routing.md", "# Routing\n")
        write(".squad/stack.md", "# Stack\n\nchanged\n")
        write("CLAUDE.md", "# x\n")
        found = self.errors()
        self.assertEqual([e.split(":")[0] for e in found], [".squad/routing.md", "CLAUDE.md"])

    def test_marked_file_edit_inside_project_block_passes_outside_fails(self):
        write("docs/CONTRIBUTING.md", "# Contributing\n\ntemplate text\n<!-- project:begin areas -->\nnew\n"
              "<!-- project:end areas -->\nmore template text\n")
        self.assertEqual(self.errors(), [])
        write("docs/CONTRIBUTING.md", "# Contributing\n\nedited template text\n<!-- project:begin areas -->\nnew\n"
              "<!-- project:end areas -->\nmore template text\n")
        self.assertIn("outside its <!-- project:", self.errors()[0])

    def test_control_character_in_markdown_is_reported(self):
        write("docs/decisions/0001-x.md", "# 0001\n\ntext \u202e here\n")
        self.assertIn("U+202E", self.errors()[0])

    def test_working_record_after_step_10_is_reported(self):
        write("specs/issue-1/plan.md", "# Plan\n")
        self.assertEqual(self.errors(no_specs=False), [])
        self.assertIn("working record still in the diff", self.errors(no_specs=True)[0])

    def test_docs_tier_allows_only_product_documentation(self):
        write("README.md", "# Readme\n\nmore\n")
        write("docs/guide.md", "# Guide\n")
        write("specs/issue-1/log.md", "| Date |\n")
        self.assertEqual(self.errors(tier="docs"), [])
        write("docs/areas/core.md", "# Core\n")
        write("src/a.go", "package a\n// comment\n")
        found = self.errors(tier="docs")
        self.assertEqual([e.split(":")[0] for e in found], ["docs/areas/core.md", "src/a.go"])


if __name__ == "__main__":
    unittest.main()
