"""Unit tests for core/.squad/tools/lesson-label.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import sys
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools", "lesson-label.py")
_SPEC = importlib.util.spec_from_file_location("lesson_label", SCRIPT)
tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tool)


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = tool.main(list(argv))
    return code, out.getvalue()


class TestLessonLabel(unittest.TestCase):
    def test_managed_files_go_upstream(self):
        # Template#388: lessons about .squad/tools/ were filed as squad, since .squad/ reads like project knowledge.
        for path in (".squad/tools/squad-next.py", "./.squad/tools/analyzer-check-go.py", ".squad/routing.md",
                     ".claude/agents/squad-tester.md", ".claude/hooks/git-guard.py", ".claude/skills/squad-spec/SKILL.md",
                     "specs/_template/plan.md", "docs/decisions/process.md", ".squad/dotnet-rules.editorconfig"):
            self.assertEqual(tool.kind(path), "managed", path)
        code, out = run(".squad/tools/squad-next.py", "--issue", "213")
        self.assertEqual(code, 0)
        self.assertIn("Label: squad-upstream", out)
        self.assertIn("(from ", out)
        self.assertIn("#213)`", out)

    def test_seeded_and_own_files_stay_here(self):
        for path in (".squad/stack.md", ".squad/project.md", ".squad/tools/squad_settings.py", "docs/UNIT_TESTS.md",
                     "src/a.py", ".claude/skills/own-skill/SKILL.md", ".claude/agents/helper.md",
                     ".squad/tools/sub/x.py", "docs/areas/pipe.md"):
            self.assertEqual(tool.kind(path), "seeded", path)
        self.assertIn("Label: squad\n", run(".squad/stack.md")[1])

    def test_a_repository_owned_tool_under_squad_tools_stays_here(self):
        # Template#395: Vandox's own coverage converter was labelled squad-upstream, where it cannot be fixed.
        self.assertEqual(tool.kind(".squad/tools/go-coverage-to-cobertura.py"), "seeded")
        self.assertEqual(tool.kind(".squad/tools/dotnet-rules.py"), "managed")
        self.assertIn("Label: squad\n", run(".squad/tools/go-coverage-to-cobertura.py")[1])

    def test_editorconfig_is_marked(self):
        self.assertEqual(tool.kind(".editorconfig"), "marked")

    def test_a_marked_file_needs_its_part_and_both_kinds_make_two_issues(self):
        code, out = run("AGENTS.md")
        self.assertEqual(code, 2)
        self.assertIn(":template", out)
        self.assertIn("Label: squad\n", run("AGENTS.md:project")[1])
        self.assertIn("Label: squad-upstream", run("docs/CONTRIBUTING.md:template")[1])
        code, out = run(".squad/tools/squad-log.py", ".squad/stack.md")
        self.assertEqual(code, 0)
        self.assertIn("Labels: squad-upstream and squad — two issues", out)
        self.assertIn("Title (squad-upstream)", out)
        self.assertIn("Title (squad)", out)


if __name__ == "__main__":
    unittest.main()
