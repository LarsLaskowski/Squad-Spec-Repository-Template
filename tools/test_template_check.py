"""Unit tests for the rule-file checks and Sonar rules of tools/template-check.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template-check.py")


def load_script():
    spec = importlib.util.spec_from_file_location("template_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRuleFiles(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.dir.name, ".squad"))
        with open(os.path.join(self.dir.name, ".squad", "routing.md"), "w", encoding="utf-8") as handle:
            handle.write("# Routing\n\nOne rule — in  two\tlines,\nwith  `code`.\n")

    def tearDown(self):
        self.dir.cleanup()

    def test_words_are_counted_like_wc(self):
        self.assertEqual(self.script.word_count(os.path.join(self.dir.name, ".squad", "routing.md")), 10)

    def test_a_listed_file_that_is_missing_fails(self):
        errors = []
        self.script.check_rule_files(errors, base=self.dir.name, files=[".squad/routing.md", ".squad/team.md"])
        self.assertEqual(len(errors), 1)
        self.assertIn("core/.squad/team.md", errors[0])

    def test_the_listed_core_files_exist(self):
        errors = []
        self.script.check_rule_files(errors)
        self.assertEqual(errors, [])

    def test_growth_is_information_until_the_consolidation_threshold(self):
        old = {"a.md": "one two three four", "b.md": "x"}
        new = {"a.md": "one two three four five six", "b.md": "x"}
        info, warnings = self.script.rule_growth(old, new, baseline=7)
        self.assertIn("INFO core/a.md: 4 -> 6 words (+2)", info)
        self.assertFalse(any("b.md" in line for line in info), "an unchanged file is not listed")
        self.assertEqual(warnings, [], "7 words against a baseline of 7 is no growth")
        _, warnings = self.script.rule_growth(old, new, baseline=6)
        self.assertEqual(len(warnings), 1, "7 words are 16.7% over a baseline of 6")
        _, warnings = self.script.rule_growth(old, {"a.md": "w " * 20}, baseline=10)
        self.assertTrue(warnings and "consolidation" in warnings[0], warnings)

    def test_a_removed_sentence_is_named_and_a_moved_one_is_not(self):
        old = {"a.md": "# A\n\nThe Dev writes the documentation after the code. The Lead keeps the records and the plans.\n",
               "b.md": "Short line.\n"}
        new = {"a.md": "# A\n\nThe Lead keeps the records and the plans.\n",
               "b.md": "Short line.\nThe  Dev writes the\ndocumentation after the code.\n"}
        self.assertEqual(self.script.removed_sentences(old, new), [])
        new["b.md"] = "Short line.\n"
        removed = self.script.removed_sentences(old, new)
        self.assertEqual(removed, [("a.md", "The Dev writes the documentation after the code.", None)])

    def test_a_reworded_sentence_is_information_naming_the_dropped_words(self):
        old = {"a.md": "The Dev writes the documentation after the code is green and the gate passes.\n"}
        new = {"a.md": "The Dev writes the documentation after the code is green and the coverage gate passes.\n"}
        (rel, sentence, rewording), = self.script.removed_sentences(old, new)
        self.assertIsNotNone(rewording, "one word changed is a rewording")
        self.assertEqual(self.script.dropped_words(sentence, rewording), [], "a word was only added")
        new = {"a.md": "The Dev writes the documentation after the code is green and the review passes.\n"}
        (_, sentence, rewording), = self.script.removed_sentences(old, new)
        self.assertEqual(self.script.dropped_words(sentence, rewording), ["gate"])
        warnings, info = [], []
        self.script.check_rule_changes(warnings, info, old=old, new=new)
        self.assertFalse(any("sentence removed" in w for w in warnings), warnings)
        self.assertTrue(any("reworded" in line and "gate" in line for line in info), info)

    def test_blocks_split_headings_list_items_and_table_rows(self):
        text = ("---\nname: x\ndescription: front matter is left out entirely here\n---\n# A heading\n"
                "First sentence of a wrapped\nparagraph goes on here. Second one of the same paragraph here.\n"
                "- a list item that is long enough to count\n1. a numbered item that is long enough to count\n"
                "| a | table | row | with | enough | cells |\n| - | - | - | - | - | - |\n")
        found = self.script.sentences(text)
        self.assertIn("First sentence of a wrapped paragraph goes on here.", found)
        self.assertIn("- a list item that is long enough to count", found)
        self.assertFalse(any("front matter" in s for s in found))
        self.assertFalse(any(set(s) <= set("|- ") for s in found), "a separator row is no sentence")

    def test_base_texts_come_from_the_merge_base_and_name_new_files(self):
        root = self.dir.name
        def git(*args):
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                           cwd=root, check=True, capture_output=True)
        os.makedirs(os.path.join(root, "core", ".squad"))
        with open(os.path.join(root, "core", ".squad", "routing.md"), "w", encoding="utf-8") as handle:
            handle.write("old rule text\n")
        git("init", "-q", "-b", "main")
        git("add", ".")
        git("commit", "-q", "-m", "base")
        git("update-ref", "refs/remotes/origin/main", "HEAD")
        texts = self.script.base_rule_texts(files=[".squad/routing.md", ".squad/new.md"], root=root)
        self.assertEqual(texts[".squad/routing.md"], "old rule text\n")
        self.assertIsNone(texts[".squad/new.md"], "a file new since the base has no base text")
        git("update-ref", "-d", "refs/remotes/origin/main")
        self.assertIsNone(self.script.base_rule_texts(files=[".squad/routing.md"], root=root), "no origin/main")

    def test_without_a_base_nothing_is_compared(self):
        warnings, info = [], []
        with unittest.mock.patch.object(self.script, "base_rule_texts", return_value=None):
            self.script.check_rule_changes(warnings, info)
        self.assertEqual(warnings, [])
        self.assertIn("no merge base", info[0])


class TestRepeatedRules(unittest.TestCase):
    RULE = " ".join(f"word{i}" for i in range(25))

    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.files = ["a.md", "b.md"]

    def tearDown(self):
        self.dir.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.dir.name, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def check(self):
        warnings = []
        self.script.check_repeated_rules(warnings, base=self.dir.name, files=self.files)
        return warnings

    def test_a_long_shared_run_is_a_warning_naming_both_files_and_its_length(self):
        self.write("a.md", "# A\n\nFirst. " + self.RULE + "\n")
        self.write("b.md", "# B\n\n" + self.RULE.upper() + " Other.\n")
        warnings = self.check()
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].startswith("WARNING"))
        self.assertIn("core/a.md and core/b.md share 25 words", warnings[0])

    def test_a_short_shared_run_passes(self):
        self.write("a.md", "one two three four five six seven eight nine ten\n")
        self.write("b.md", "one two three four five six seven eight nine ten\n")
        self.assertEqual(self.check(), [])

    def test_front_matter_is_ignored(self):
        self.write("a.md", "---\ndescription: " + self.RULE + "\n---\nText a.\n")
        self.write("b.md", "---\ndescription: " + self.RULE + "\n---\nText b.\n")
        self.assertEqual(self.check(), [])

    def test_a_rule_repeated_inside_one_file_is_not_reported(self):
        self.write("a.md", self.RULE + "\n\n" + self.RULE + "\n")
        self.write("b.md", "Nothing shared.\n")
        self.assertEqual(self.check(), [])

    def test_the_core_files_state_each_rule_once(self):
        warnings = []
        self.script.check_repeated_rules(warnings)
        self.assertEqual(warnings, [])


class TestSonarRules(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def rules(self, source, path="tool.py"):
        return [rule for _, rule, _ in self.script.sonar_findings(path, source)]

    def test_a_nested_conditional_expression_is_reported(self):
        self.assertEqual(self.rules("x = a if b else (c if d else e)\n"), ["python:S3358"])

    def test_a_nested_conditional_in_a_comprehension_passes(self):
        self.assertEqual(self.rules("x = [a if b else (c if d else e) for a in f]\n"), [])

    def test_a_literal_three_times_is_reported(self):
        self.assertEqual(self.rules("a = 'spec.md'\nb = 'spec.md'\nc = 'spec.md'\n"), ["python:S1192"])

    def test_literals_sonar_leaves_out_pass(self):
        source = ('"""spec.md"""\n' * 3 + "a = b = c = None\n" + "".join(f"x{i} = 'plain_word'\n" for i in range(3))
                  + "".join(f"y{i} = f'{{z}} spec.md'\n" for i in range(3)) + "w = 'spec.md', 'spec.md'\n")
        self.assertEqual(self.rules(source), [])

    def test_duplicated_literals_in_a_test_file_pass(self):
        self.assertEqual(self.rules("a = 'spec.md'\nb = 'spec.md'\nc = 'spec.md'\n", "test_tool.py"), [])

    def test_anchored_alternatives_without_a_group_are_reported(self):
        self.assertEqual(self.rules("import re\nX = re.compile(r'^[`*_]+|[`*_]+$')\n"), ["python:S5850"])

    def test_grouped_or_fully_anchored_alternatives_pass(self):
        for pattern in (r"(?:^a)|(?:b$)", r"^(?:a|b)$", r"^a$|^b$", r"[|^]a|b", r"\\^a|b"):
            self.assertEqual(self.rules(f"import re\nX = re.compile(r'{pattern}')\n"), [], pattern)

    def test_several_spaces_in_a_regex_are_reported(self):
        self.assertEqual(self.rules("import re\nX = re.compile(r'^  ([a-z]+):')\n"), ["python:S6326"])

    def test_single_spaces_quantifiers_and_classes_pass(self):
        for pattern in (r"^ {2}([a-z]+):", r"a b", r"[ ]{2}", r"[  ]x"):
            self.assertEqual(self.rules(f"import re\nX = re.compile(r'{pattern}')\n"), [], pattern)

    def test_an_assertion_with_a_more_specific_one_is_reported(self):
        for call in ("self.assertTrue(a == b)", "self.assertFalse(a in b)", "self.assertTrue(a < b)",
                     "self.assertTrue(isinstance(a, int))", "self.assertEqual(a, None)", "self.assertIsNot(None, a)",
                     "self.assertEqual(a, round(b, 2))", 'self.assertEqual(a.new, None, "message")',
                     "self.assertEqual(a[3], False)", "self.assertIs(True, a)"):
            self.assertEqual(self.rules(f"{call}\n", "test_tool.py"), ["python:S5906"], call)

    def test_specific_assertions_pass(self):
        for call in ("self.assertTrue(a)", "self.assertFalse(a < b)", "self.assertTrue(a == b == c)",
                     "self.assertEqual(a, b)", "self.assertIsNone(a)", "self.assertIn(a, b)", "self.assertEqual(a, 0)",
                     "self.assertTrue(f(a == b))", "assertTrue(a == b)"):
            self.assertEqual(self.rules(f"{call}\n", "test_tool.py"), [], call)

    def test_a_function_that_always_returns_the_same_value_is_reported(self):
        self.assertEqual(self.rules("def f(a):\n    if a:\n        return 0\n    return 0\n"), ["python:S3516"])

    def test_varying_returns_nested_functions_and_none_pass(self):
        sources = ("def f(a):\n    if a:\n        return 0\n    return 1\n",
                   "def f(a):\n    if a:\n        return 0\n    return a\n",
                   "def f(a):\n    if a:\n        return None\n    return None\n",
                   "def f(a):\n    if a:\n        return 'x'\n    return None\n",
                   "def f():\n    def g():\n        return 0\n    return 0\n")
        for source in sources:
            self.assertEqual(self.rules(source), [], source)

    def test_a_mock_lambda_that_ignores_its_arguments_is_reported(self):
        source = ("import unittest.mock as mock\nmock.patch.object(m, 'f', lambda path, stop=None: [1])\n"
                  "mock.patch('m.f', lambda: 1)\nmock.patch.object(m, 'g', lambda path: d[path])\n"
                  "mock.patch.object(m, 'h', return_value=[1])\n")
        self.assertEqual(self.rules(source, "test_tool.py"), ["python:S9081", "python:S9081"])

    def test_the_checked_files_hold_the_distributed_tools_and_the_templates_own(self):
        names = {os.path.relpath(path, self.script.ROOT) for path in self.script.checked_python_files()}
        self.assertIn(os.path.join("tools", "template-check.py"), names)
        self.assertIn(os.path.join("core", ".squad", "tools", "scope-check.py"), names)

    def test_the_checked_tools_pass(self):
        errors = []
        self.script.check_sonar_rules(errors)
        self.assertEqual(errors, [])



class TestWordsPerLaunch(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_read_first_names_files_and_their_sections(self):
        charter = ("---\nname: x\n---\n\nRead first: `.squad/team.md` (*Shared rules*), the *Code style* and *Architecture*\n"
                   "sections of `AGENTS.md`, `.squad/stack.md` (commands, *Writing\ntests*) and the plan.\n\nMore.\n")
        self.assertEqual(self.script.read_first(charter), [(".squad/team.md", ["Shared rules"]),
                                                           ("AGENTS.md", ["Code style", "Architecture"]),
                                                           (".squad/stack.md", ["Writing tests"])])

    def test_a_section_runs_to_the_next_heading_of_its_level(self):
        text = "# T\n\n## A one\n\nx y\n\n### Sub\n\nz\n\n## B\n\nw\n"
        self.assertEqual(self.script.section_text(text, "A"), "## A one\n\nx y\n\n### Sub\n\nz\n")
        self.assertEqual(self.script.read_words(text, ["B"]), 3)
        self.assertEqual(self.script.read_words(text, ["Missing"]), len(text.split()), "unknown names count it all")

    def test_every_role_and_both_orchestrators_are_reported(self):
        lines = self.script.words_per_launch()
        for name in ("squad-lead", "squad-tester", "orchestrator (squad-issue)", "orchestrator (squad-spec)"):
            self.assertTrue(any(line.startswith(f"INFO   {name}: ") for line in lines), name)
        tester = next(line for line in lines if line.startswith("INFO   squad-tester: "))
        self.assertIn(".squad/team.md (Shared rules)", tester)
        self.assertIn("seeded", tester, "stack.md and UNIT_TESTS.md come from the seeds")


class TestConsumersAndChangelog(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, rel, text):
        path = os.path.join(self.dir.name, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_the_repository_consumers_pass_and_bad_entries_fail(self):
        errors = []
        self.script.check_consumers(errors, ["dotnet", "go", "node", "typescript"])
        self.assertEqual(errors, [])
        path = self.write("consumers.json", '{"consumers": [{"repository": "o/a", "profiles": ["cobol"], "sonar": null, '
                                            '"status": "active"}, {"repository": "o/a", "profiles": ["go"], "sonar": "a b", '
                                            '"status": "gone"}, {"repository": "noslash"}]}')
        self.script.check_consumers(errors, ["go"], path)
        for finding in ("o/a needs 'profiles'", "o/a is listed twice", "invalid 'sonar'", "needs 'status'",
                        "without a valid 'repository'"):
            self.assertTrue(any(finding in error for error in errors), finding)

    def git(self, *args):
        subprocess.run(["git", "-C", self.dir.name, "-c", "user.name=t", "-c", "user.email=t@t", "-c",
                        "commit.gpgsign=false", *args], check=True, capture_output=True)

    def test_a_change_that_reaches_the_targets_needs_a_changelog_line(self):
        self.git("init", "-q")
        self.write("CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- [Core] Earlier (#1)\n")
        self.write("core/a.md", "a\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        errors, info = [], []
        self.write("docs/x.md", "x\n")
        self.script.check_changelog(errors, info, root=self.dir.name)
        self.assertEqual(errors, [], "a change that no target receives needs no line")
        self.write("core/a.md", "b\n")
        self.script.check_changelog(errors, info, root=self.dir.name)
        self.assertEqual(len(errors), 1)
        self.assertIn("core/a.md", errors[0])
        errors.clear()
        self.write("CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- [Core] Earlier (#1)\n- [Core] This one (#2)\n")
        self.script.check_changelog(errors, info, root=self.dir.name)
        self.assertEqual(errors, [])

    def test_without_a_merge_base_the_entry_is_not_checked(self):
        self.write("CHANGELOG.md", "# Changelog\n\n## Unreleased\n")
        errors, info = [], []
        self.script.check_changelog(errors, info, root=self.dir.name)
        self.assertEqual(errors, [])
        self.assertIn("not checked", info[0])


if __name__ == "__main__":
    unittest.main()
