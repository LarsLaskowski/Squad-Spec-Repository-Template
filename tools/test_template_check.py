"""Unit tests for the word budgets of tools/template-check.py: run `python3 -m unittest discover tools`."""
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


if __name__ == "__main__":
    unittest.main()
