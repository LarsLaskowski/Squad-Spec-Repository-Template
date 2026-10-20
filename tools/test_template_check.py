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
        errors = []
        self.script.check_word_budgets(errors, base=self.dir.name, budgets=budgets)
        return errors

    def test_words_are_counted_like_wc(self):
        self.assertEqual(self.script.word_count(os.path.join(self.dir.name, ".squad", "routing.md")), 10)

    def test_a_file_within_its_budget_passes(self):
        self.assertEqual(self.check({".squad/routing.md": 10}), [])

    def test_a_file_over_its_budget_names_file_count_and_budget(self):
        errors = self.check({".squad/routing.md": 9})
        self.assertEqual(len(errors), 1)
        self.assertIn("core/.squad/routing.md", errors[0])
        self.assertIn("10 words", errors[0])
        self.assertIn("budget of 9", errors[0])

    def test_a_budgeted_file_that_is_missing_fails(self):
        self.assertIn("missing", self.check({".squad/team.md": 100})[0])

    def test_the_core_files_are_within_their_budgets(self):
        errors = []
        self.script.check_word_budgets(errors)
        self.assertEqual(errors, [])


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

    def test_the_distributed_tools_pass(self):
        errors = []
        self.script.check_sonar_rules(errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
