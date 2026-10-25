"""Unit tests for tools/apply-template.py (line endings, Copilot mirror, rules moved out of CLAUDE.md, references to
retired files):
run `python3 -m unittest discover tools`."""
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


class TestCopilotMirror(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_instruction_body_starts_at_the_first_section_and_drops_import_lines(self):
        rules = ("# AGENTS.md\n\nIntro.\n\n## Code style\n\n<!-- project:begin code-style -->\n"
                 "@.github/instructions/csharp.instructions.md\nUse tabs; mail @someone.\n"
                 "<!-- project:end code-style -->\n")
        self.assertEqual(self.script.instruction_body(rules),
                         "\n## Code style\n\n<!-- project:begin code-style -->\nUse tabs; mail @someone.\n"
                         "<!-- project:end code-style -->\n")

    def test_generated_mirror_is_the_core_introduction_plus_the_rules_body(self):
        with tempfile.TemporaryDirectory() as folder:
            header = os.path.join(folder, "copilot.md")
            write(header, "# Copilot instructions\n\nFor Copilot.\n")
            generated = self.script.generated_files({".github/copilot-instructions.md": header},
                                                    "# AGENTS.md\n\nFor agents.\n\n## Rules\n\nRule.\n")
        self.assertEqual(generated, {".github/copilot-instructions.md":
                                     "# Copilot instructions\n\nFor Copilot.\n\n## Rules\n\nRule.\n"})


class TestLegacyRules(unittest.TestCase):
    TEMPLATE = "# CLAUDE.md\n\n@AGENTS.md\n"

    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.target = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def legacy(self, text=None):
        if text is not None:
            write(os.path.join(self.target, "CLAUDE.md"), text, newline="\r\n")
        report = []
        return self.script.legacy_rules(self.target, self.TEMPLATE, False, report), report

    def test_project_blocks_of_a_claude_md_holding_the_rules_are_carried_over(self):
        project, report = self.legacy("# CLAUDE.md\n\n## What\n\n<!-- project:begin overview -->\nOurs.\n"
                                      "<!-- project:end overview -->\n")
        self.assertEqual(project, {"overview": "Ours.\n"})
        self.assertEqual(report, [])

    def test_hand_written_claude_md_is_backed_up_and_the_template_one_is_not(self):
        project, report = self.legacy("# Our notes\n\nUse tabs.\n")
        self.assertEqual(project, {})
        self.assertEqual([status for status, _ in report], ["backed-up"])
        self.assertTrue(os.path.isfile(os.path.join(self.target, ".git", "adopt-template", "backup", "CLAUDE.md")))
        self.assertEqual(self.legacy(self.TEMPLATE), ({}, []))

    def test_no_claude_md_carries_nothing(self):
        self.assertEqual(self.legacy(), ({}, []))


class TestRetiredReferences(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.target = self.dir.name
        subprocess.run(["git", "init", "-q", self.target], check=True)

    def tearDown(self):
        self.dir.cleanup()

    def test_lists_lines_naming_a_retired_file_and_ignores_longer_names(self):
        write(os.path.join(self.target, "docs", "ARCHITECTURE.md"),
              "# A\n\nDecisions: [decisions.md](/.squad/decisions.md).\n")
        write(os.path.join(self.target, "App.slnx"), '<File Path=".squad/agents/lead/charter.md" />\n')
        write(os.path.join(self.target, "README.md"), "See my.squad/decisions.md, AGENTS.md and "
                                                      ".github/copilot-instructions.md.\n")
        write(os.path.join(self.target, ".squad", "decisions.md"), "See .squad/decisions.md\n")
        hits = self.script.retired_references(self.target)
        self.assertEqual([(path, number) for path, number, _ in hits], [("App.slnx", 1), ("docs/ARCHITECTURE.md", 3)])



class TestGitGuardSetting(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_existing_settings_get_the_guard_once_and_keep_their_hooks(self):
        import json
        text = json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "start.sh"}]}],
                                     "PreToolUse": [{"matcher": "Read", "hooks": [{"command": "secrets.ps1"}]}]},
                           "permissions": {"allow": ["Bash(ls)"]}})
        merged = json.loads(self.script.with_git_guard(text))
        self.assertEqual(merged["permissions"], {"allow": ["Bash(ls)"]}, "other settings stay")
        self.assertEqual(len(merged["hooks"]["SessionStart"]), 1, "other hooks stay")
        self.assertEqual(merged["hooks"]["PreToolUse"][-1], self.script.GIT_GUARD_HOOK)
        self.assertIsNone(self.script.with_git_guard(json.dumps(merged)), "a second refresh adds nothing")
        self.assertIn("git-guard.py", json.dumps(json.loads(self.script.with_git_guard("{}"))))

    def test_odd_hook_groups_and_non_ascii_text_survive(self):
        import json
        text = json.dumps({"hooks": {"PreToolUse": [{"matcher": "Read", "hooks": 5}]}, "note": "Grüße"},
                          ensure_ascii=False)
        merged = self.script.with_git_guard(text)
        self.assertIn("Grüße", merged, "non-ASCII text is kept as written")
        self.assertIn("git-guard.py", merged)

    def test_write_seeds_merges_an_existing_settings_file(self):
        with tempfile.TemporaryDirectory() as target:
            write(os.path.join(target, ".claude", "settings.json"), '{"hooks": {}}\n')
            emitted, report = {}, []
            seeds = {".claude/settings.json": "{}", "SECURITY.md": "x"}
            self.script.write_seeds(target, seeds, ["go"], False, emitted.__setitem__, report)
            self.assertIn("git-guard.py", emitted[".claude/settings.json"], "the existing file gets the guard")
            self.assertEqual(emitted["SECURITY.md"], "x", "a missing seed is still written")

    def test_settings_that_are_no_object_are_left_to_a_person(self):
        for text in ("[]", '{"hooks": []}', '{"hooks": {"PreToolUse": {}}}', "not json"):
            with self.assertRaises(ValueError, msg=text):
                self.script.with_git_guard(text)

    def test_refresh_adds_the_guard_to_an_existing_settings_file(self):
        with tempfile.TemporaryDirectory() as target:
            write(os.path.join(target, ".claude", "settings.json"), '{"hooks": {"SessionStart": []}}\n')
            emitted, report = {}, []
            self.script.merge_git_guard(target, emitted.__setitem__, report)
            self.assertIn("git-guard.py", emitted[".claude/settings.json"])
            write(os.path.join(target, ".claude", "settings.json"), emitted[".claude/settings.json"])
            emitted.clear()
            self.script.merge_git_guard(target, emitted.__setitem__, report)
            self.assertEqual((emitted, report[-1]), ({}, ("kept", ".claude/settings.json")))


if __name__ == "__main__":
    unittest.main()
