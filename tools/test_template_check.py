"""Unit tests for the word budgets and Sonar rules of tools/template-check.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template-check.py")


def load_script():
    spec = importlib.util.spec_from_file_location("template_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestWordBudgets(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.dir.name, ".squad"))
        with open(os.path.join(self.dir.name, ".squad", "routing.md"), "w", encoding="utf-8") as handle:
            handle.write("# Routing\n\nOne rule — in  two\tlines,\nwith  `code`.\n")

    def tearDown(self):
        self.dir.cleanup()

    def check(self, budgets):
        errors, warnings = [], []
        self.script.check_word_budgets(errors, base=self.dir.name, budgets=budgets, warnings=warnings)
        return errors + warnings

    def test_words_are_counted_like_wc(self):
        self.assertEqual(self.script.word_count(os.path.join(self.dir.name, ".squad", "routing.md")), 10)

    def test_a_file_within_its_budget_passes(self):
        self.assertEqual(self.check({".squad/routing.md": 10}), [])

    def test_a_file_over_its_budget_names_file_count_and_budget(self):
        errors = self.check({".squad/routing.md": 9})
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("WARNING"))
        self.assertIn("core/.squad/routing.md", errors[0])
        self.assertIn("10 words", errors[0])
        self.assertIn("budget of 9", errors[0])

    def test_a_file_over_its_budget_is_no_error(self):
        errors = []
        self.script.check_word_budgets(errors, base=self.dir.name, budgets={".squad/routing.md": 9}, warnings=[])
        self.assertEqual(errors, [])

    def test_a_budgeted_file_that_is_missing_fails(self):
        self.assertIn("missing", self.check({".squad/team.md": 100})[0])

    def test_the_budgeted_core_files_exist(self):
        errors = []
        self.script.check_word_budgets(errors)
        self.assertEqual(errors, [])


class TestRepeatedRules(unittest.TestCase):
    RULE = " ".join(f"word{i}" for i in range(25))

    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.budgets = {"a.md": 1000, "b.md": 1000}

    def tearDown(self):
        self.dir.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.dir.name, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def check(self):
        warnings = []
        self.script.check_repeated_rules(warnings, base=self.dir.name, budgets=self.budgets)
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

    def test_the_checked_files_hold_the_distributed_tools_and_the_templates_own(self):
        names = {os.path.relpath(path, self.script.ROOT) for path in self.script.checked_python_files()}
        self.assertIn(os.path.join("tools", "template-check.py"), names)
        self.assertIn(os.path.join("core", ".squad", "tools", "scope-check.py"), names)

    def test_the_checked_tools_pass(self):
        errors = []
        self.script.check_sonar_rules(errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
