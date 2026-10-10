"""Unit tests for tools/apply-template.py (line endings per file): run `python3 -m unittest discover tools`."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apply-template.py")


def load_script():
    spec = importlib.util.spec_from_file_location("apply_template", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, text, newline="\n"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)


class TestLineEndings(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.target = self.dir.name
        subprocess.run(["git", "init", "-q", self.target], check=True)

    def tearDown(self):
        self.dir.cleanup()

    def test_eol_attributes_follow_the_per_pattern_rules(self):
        write(os.path.join(self.target, ".gitattributes"),
              "* text=auto eol=lf\n*.md text eol=crlf\n*.sh text eol=lf\n*.png binary\n")
        eols = self.script.eol_attributes(self.target, ["docs/decisions/README.md", ".squad/tools/x.py",
                                                        ".claude/hooks/session-start.sh", "new/dir/f.md"])
        self.assertEqual(eols, {"docs/decisions/README.md": "crlf", ".squad/tools/x.py": "lf",
                                ".claude/hooks/session-start.sh": "lf", "new/dir/f.md": "crlf"})

    def test_eol_attributes_without_gitattributes_are_empty(self):
        self.assertEqual(self.script.eol_attributes(self.target, ["CLAUDE.md", ".squad/stack.md"]), {})
        self.assertEqual(self.script.eol_attributes(self.target, []), {})

    def test_crlf_for_prefers_the_attribute_over_the_default(self):
        eols = {"a.md": "crlf", "b.py": "lf"}
        self.assertTrue(self.script.crlf_for("a.md", eols, default=False))
        self.assertFalse(self.script.crlf_for("b.py", eols, default=True))
        self.assertTrue(self.script.crlf_for("c.json", eols, default=True))
        self.assertFalse(self.script.crlf_for("c.json", eols, default=False))
        self.assertFalse(self.script.crlf_for("run.sh", {"run.sh": "crlf"}, default=True))

    def test_write_uses_the_files_line_ending_and_reports_renormalized(self):
        rel = "docs/decisions/README.md"
        write(os.path.join(self.target, rel), "# Index\n\nrow\n", newline="\n")
        report = []
        self.script.write(self.target, rel, "# Index\n\nrow\n", True, False, report)
        self.assertEqual(report, [("renormalized", rel)])
        with open(os.path.join(self.target, rel), "rb") as handle:
            self.assertEqual(handle.read(), b"# Index\r\n\r\nrow\r\n")
        report = []
        self.script.write(self.target, rel, "# Index\n\nrow\n", True, False, report)
        self.assertEqual(report, [("unchanged", rel)])
        report = []
        self.script.write(self.target, rel, "# Index\n\nnew row\n", True, False, report)
        self.assertEqual(report, [("updated", rel)])

    def test_dry_run_reports_without_writing(self):
        rel = "CLAUDE.md"
        write(os.path.join(self.target, rel), "old\n")
        report = []
        self.script.write(self.target, rel, "old\n", True, True, report)
        self.assertEqual(report, [("renormalized", rel)])
        with open(os.path.join(self.target, rel), "rb") as handle:
            self.assertEqual(handle.read(), b"old\n")


if __name__ == "__main__":
    unittest.main()
