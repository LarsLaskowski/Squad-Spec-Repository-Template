"""Unit tests for tools/apply-template.py (line endings, Copilot mirror, rules moved out of CLAUDE.md, references to
retired files, process records to retire, merged settings):
run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
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



class TestSquadHookSettings(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_existing_settings_get_the_guards_once_and_keep_their_hooks(self):
        import json
        text = json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "start.sh"}]}],
                                     "PreToolUse": [{"matcher": "Read", "hooks": [{"command": "secrets.ps1"}]}]},
                           "permissions": {"allow": ["Bash(ls)"]}})
        merged = json.loads(self.script.with_squad_hooks(text))
        self.assertEqual(merged["permissions"], {"allow": ["Bash(ls)"]}, "other settings stay")
        self.assertEqual(len(merged["hooks"]["SessionStart"]), 1, "other hooks stay")
        self.assertEqual(merged["hooks"]["PreToolUse"][1:], [self.script.GIT_GUARD_HOOK, self.script.FILE_GUARD_HOOK])
        self.assertIsNone(self.script.with_squad_hooks(json.dumps(merged)), "a second refresh adds nothing")
        empty = json.dumps(json.loads(self.script.with_squad_hooks("{}")))
        self.assertIn("git-guard.py", empty)
        self.assertIn("file-guard.py", empty)

    def test_settings_with_the_git_guard_only_get_the_file_guard(self):
        import json
        text = json.dumps({"hooks": {"PreToolUse": [self.script.GIT_GUARD_HOOK]}})
        merged = json.loads(self.script.with_squad_hooks(text))
        self.assertEqual(merged["hooks"]["PreToolUse"], [self.script.GIT_GUARD_HOOK, self.script.FILE_GUARD_HOOK])
        own = json.dumps({"hooks": {"PreToolUse": [{"matcher": "Write|Edit", "hooks": [
            {"type": "command", "command": "py .claude/hooks/file-guard.py --strict"}]}]}})
        merged = json.loads(self.script.with_squad_hooks(own))
        self.assertEqual(len(merged["hooks"]["PreToolUse"]), 2, "a file guard entry of the target's own is kept as is")

    def test_odd_hook_groups_and_non_ascii_text_survive(self):
        import json
        text = json.dumps({"hooks": {"PreToolUse": [{"matcher": "Read", "hooks": 5}]}, "note": "Grüße"},
                          ensure_ascii=False)
        merged = self.script.with_squad_hooks(text)
        self.assertIn("Grüße", merged, "non-ASCII text is kept as written")
        self.assertIn("git-guard.py", merged)
        self.assertIn("file-guard.py", merged)

    def test_write_seeds_merges_an_existing_settings_file(self):
        with tempfile.TemporaryDirectory() as target:
            write(os.path.join(target, ".claude", "settings.json"), '{"hooks": {}}\n')
            emitted, report = {}, []
            seeds = {".claude/settings.json": "{}", "SECURITY.md": "x"}
            self.script.write_seeds(target, seeds, ["go"], False, emitted.__setitem__, report)
            self.assertIn("git-guard.py", emitted[".claude/settings.json"], "the existing file gets the guards")
            self.assertIn("file-guard.py", emitted[".claude/settings.json"], "the existing file gets the guards")
            self.assertEqual(emitted["SECURITY.md"], "x", "a missing seed is still written")

    def test_settings_that_are_no_object_are_left_to_a_person(self):
        for text in ("[]", '{"hooks": []}', '{"hooks": {"PreToolUse": {}}}', "not json"):
            with self.assertRaises(ValueError, msg=text):
                self.script.with_squad_hooks(text)
        with tempfile.TemporaryDirectory() as target:
            write(os.path.join(target, ".claude", "settings.json"), "[]\n")
            emitted, report = {}, []
            self.script.merge_squad_hooks(target, emitted.__setitem__, report)
            self.assertEqual(emitted, {})
            self.assertEqual(report[-1][0], "conflict")
            self.assertIn("file-guard.py", report[-1][1], "the report names both hooks to add by hand")

    def test_refresh_adds_the_guards_to_an_existing_settings_file(self):
        with tempfile.TemporaryDirectory() as target:
            write(os.path.join(target, ".claude", "settings.json"), '{"hooks": {"SessionStart": []}}\n')
            emitted, report = {}, []
            self.script.merge_squad_hooks(target, emitted.__setitem__, report)
            self.assertIn("git-guard.py", emitted[".claude/settings.json"])
            self.assertIn("file-guard.py", emitted[".claude/settings.json"])
            write(os.path.join(target, ".claude", "settings.json"), emitted[".claude/settings.json"])
            emitted.clear()
            self.script.merge_squad_hooks(target, emitted.__setitem__, report)
            self.assertEqual((emitted, report[-1]), ({}, ("kept", ".claude/settings.json")))


def process_record(number, title, status="Accepted", source="Issue #1", supersedes="—"):
    return (f"# {number}: {title}\n\n- **Status:** {status}\n- **Date:** 2026-01-01\n- **Area:** —\n"
            f"- **Source:** {source}\n- **Supersedes:** {supersedes}\n\n## Decision\n\nIt holds.\n")


class TestProcessRecords(unittest.TestCase):
    """The numbered process records of an older template version, still in force, are listed for step 8."""

    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.target = self.dir.name
        self.decisions = os.path.join(self.target, "docs", "decisions")

    def tearDown(self):
        self.dir.cleanup()

    def record(self, name, text):
        write(os.path.join(self.decisions, name), text)

    def test_no_decisions_folder_lists_nothing(self):
        self.assertEqual(self.script.process_records(self.target), [])

    def test_seeded_records_and_their_successors_still_in_force(self):
        adopted = "Squad adopted from Squad-Spec-Repository-Template"
        title = "Squad working records stay off main, and product PRs never change the squad"
        self.record("0002-off-main.md", process_record("0002", title, "Superseded by 0022", adopted))
        self.record("0022-off-main.md", process_record("0022", title, "Superseded by [0037](0037-off-main.md)", adopted,
                                                       "0002"))
        self.record("0037-off-main.md", process_record("0037", title, source=adopted, supersedes="0022"))
        self.record("0044-settings.md", process_record("0044", "Product PRs may change the squad settings file",
                                                       supersedes="[0037](0037-off-main.md) (amends it)"))
        self.record("0045-squash.md", process_record("0045", "squash-merge pull requests"))
        self.record("0046-product.md", process_record("0046", "Cache entries expire", supersedes="0001"))
        self.record("README.md", "# Decision records\n")
        self.record("process.md", "# Process decisions\n")
        self.assertEqual(self.script.process_records(self.target), [
            ("docs/decisions/0037-off-main.md", "Accepted", ""),
            ("docs/decisions/0044-settings.md", "Accepted", "supersedes or amends 0037"),
            ("docs/decisions/0045-squash.md", "Accepted", "")])
        self.record("0050-moved.md", process_record("0050", "The squad\u2019s process decisions live in process.md",
                                                    source="Squad refreshed from Squad-Spec-Repository-Template",
                                                    supersedes="0037, 0044, 0045"))
        for name in ("0037-off-main.md", "0044-settings.md", "0045-squash.md"):
            path = os.path.join(self.decisions, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            write(path, text.replace("- **Status:** Accepted", "- **Status:** Superseded by 0050"))
        self.assertEqual(self.script.process_records(self.target), [], "retired once by the record that moved them")

    def test_the_report_names_them(self):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.script.print_report([], [], [], False, [("docs/decisions/0037-off-main.md", "Accepted", ""),
                                                         ("docs/decisions/0044-x.md", "", "supersedes or amends 0037")])
        self.assertIn("Process records of an older template version, now in docs/decisions/process.md", printed.getvalue())
        self.assertIn("  docs/decisions/0037-off-main.md (Accepted)\n", printed.getvalue())
        self.assertIn("  docs/decisions/0044-x.md (no status; supersedes or amends 0037)\n", printed.getvalue())

    def test_a_record_that_is_no_utf_8_is_read(self):
        os.makedirs(self.decisions, exist_ok=True)
        with open(os.path.join(self.decisions, "0001-latin.md"), "wb") as handle:
            handle.write(process_record("0001", "Squash-merge pull requests").encode("utf-8") + b"Gr\xf6\xdfe\n")
        self.assertEqual(self.script.process_records(self.target), [("docs/decisions/0001-latin.md", "Accepted", "")])

    def test_a_record_linking_process_md_is_the_move_record(self):
        self.record("0003-squash.md", process_record("0003", "Squash-merge pull requests", "Superseded by 0009"))
        self.record("0009-moved.md", process_record("0009", "Process decisions now in a file", supersedes="0003")
                    + "See [process.md](process.md).\n")
        self.assertEqual(self.script.process_records(self.target), [])


class TestMergedSettings(unittest.TestCase):
    """squad_settings.py of a repository with several profiles carries the size limits and the stale-figure settings
    like a single profile's seed."""

    def test_the_size_limits_are_those_of_every_seed(self):
        script = load_script()
        root = os.path.dirname(os.path.dirname(SCRIPT))
        seed = script.load_settings(os.path.join(root, "profiles", "go", "seed", ".squad", "tools", "squad_settings.py"))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "squad_settings.py")
            write(path, script.merge_settings([os.path.join(root, "profiles", name) for name in ("go", "dotnet")]))
            merged = script.load_settings(path)
        for name, (default, _) in script.SIZE_SETTINGS.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(merged, name), getattr(seed, name))
                self.assertEqual(getattr(merged, name), default)
        self.assertEqual(merged.FIGURE_TRIVIAL, seed.FIGURE_TRIVIAL)
        self.assertEqual(merged.FIGURE_EXCLUDES, ["go.sum", "*.svg", "packages.lock.json"], "every profile's, once")


if __name__ == "__main__":
    unittest.main()
