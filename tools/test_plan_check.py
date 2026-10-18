"""Unit tests for core/.squad/tools/plan-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import io
import os
import shutil
import tempfile
import unittest

from test_squad_tools import load_script, write

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", "specs", "_template")

SPEC = """# Spec: Export

Source: Issue #12
Status: Approved by Lead

## Problem

Users cannot take their watch history elsewhere.

## Scenarios

- S1: Given a library, when the user exports it, then a CSV file with one row per item is written.
- S2: Given an export in progress, when another starts, then the second waits.

## Errors and edge cases

- E1: An empty library writes the header only.
- E2: A title with a comma is quoted.

## Non-functional requirements

- An export of 10,000 items finishes within the request timeout.

## Acceptance criteria

- [ ] AC1: an export writes one row per item (S1)
- [ ] AC2: an empty library writes the header only, titles with commas are quoted (E1, E2)

## Out of scope

- S2: concurrent exports are serialized by the existing job queue.

## Open questions

- Which delimiter? Answered: comma, as the issue's example shows.

## Area documents

- docs/areas/export.md: the CSV format and its columns.
"""

PLAN = """# Plan: Export

Source: [spec.md](spec.md)
Status: Draft
Tier: standard — a new user-visible export, no security area.

## Problem / root cause

See spec.md.

## Verified facts

| # | Claim | Evidence | Status |
| - | ----- | -------- | ------ |
| 1 | The job queue serializes jobs | src/Jobs/Queue.cs:40 takes a single worker | confirmed |
| 2 | The CSV writer quotes commas | to verify: Dev runs the writer on "a,b" before step 6 | unverified |

## Tests per criterion

| AC | Test(s) | Test file |
| -- | ------- | --------- |
| AC1 | ExportWritesOneRowPerItem | tests/ExportTests.cs |
| AC2 | ExportEmptyLibraryWritesHeader, ExportQuotesCommas | tests/ExportTests.cs |
"""

TASKS = """# Tasks: Export

| # | Task | Files | Criteria | Depends on | Owner | Done |
| - | ---- | ----- | -------- | ---------- | ----- | ---- |
| 1 | Writer | src/Export.cs | AC1, AC2 | — | Dev | [ ] |
"""

BUG_PLAN = """# Plan: Crash on empty title

Source: Issue #34
Tier: trivial — one guard.

## Verified facts

| # | Claim | Evidence | Status |
| - | ----- | -------- | ------ |
| 1 | An empty title throws | src/Nfo.cs:12 indexes title[0] | confirmed |

## Acceptance criteria

- [ ] AC1: an empty title writes no title element

## Tests per criterion

| AC | Test(s) | Test file |
| -- | ------- | --------- |
| AC1 | NfoWriterEmptyTitleWritesNoTitle | tests/NfoWriterTests.cs |
"""


class TestPlanCheck(unittest.TestCase):
    def setUp(self):
        self.script = load_script("plan-check")
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def feature(self, spec=SPEC, plan=PLAN, tasks=TASKS):
        for name, text in (("spec.md", spec), ("plan.md", plan), ("tasks.md", tasks)):
            if text is not None:
                write(os.path.join("specs", "feature-12-export", name), text)
        return os.path.join("specs", "feature-12-export")

    def errors(self, folder):
        return self.script.check(folder)[0]

    def test_complete_feature_and_bug_fix_pass(self):
        self.assertEqual(self.errors(self.feature()), [])
        write("specs/issue-34/plan.md", BUG_PLAN)
        self.assertEqual(self.errors("specs/issue-34"), [])

    def test_untouched_templates_fail(self):
        folder = os.path.join("specs", "feature-1-new")
        shutil.copytree(TEMPLATES, folder)
        errors = self.errors(folder)
        for expected in ("section *Problem*", "template placeholder", "Tier", "defines AC1", "status must be"):
            self.assertTrue(any(expected in e for e in errors), (expected, errors))

    def test_case_without_criterion_and_open_question_are_reported(self):
        spec = SPEC.replace("(E1, E2)", "(E1)").replace(" Answered: comma, as the issue's example shows.", "")
        errors = self.errors(self.feature(spec=spec))
        self.assertTrue(any("E2 is named by no acceptance criterion" in e for e in errors), errors)
        self.assertTrue(any("open question without" in e for e in errors), errors)

    def test_criteria_live_in_the_spec_only_and_each_needs_a_test_and_a_task(self):
        plan = PLAN + "\n## Acceptance criteria\n\n- [ ] AC3: copied from the spec\n"
        plan = plan.replace("| AC2 | ExportEmptyLibraryWritesHeader, ExportQuotesCommas | tests/ExportTests.cs |\n", "")
        tasks = TASKS.replace("AC1, AC2", "AC1, AC7")
        errors = self.errors(self.feature(plan=plan, tasks=tasks))
        for expected in ("defines AC3", "AC2 has no row", "AC2 is covered by no task", "names AC7"):
            self.assertTrue(any(expected in e for e in errors), (expected, errors))

    def test_criterion_verified_without_tests_needs_no_test_row(self):
        plan = PLAN.replace("| AC2 | ExportEmptyLibraryWritesHeader, ExportQuotesCommas | tests/ExportTests.cs |\n", "")
        plan += "\n## Verification without tests\n\n- AC2: checked by the workflow's dry run.\n"
        self.assertEqual(self.errors(self.feature(plan=plan)), [])

    def test_facts_need_evidence_and_unverified_ones_a_measurement(self):
        plan = PLAN.replace("to verify: Dev runs", "Dev runs").replace(
            "src/Jobs/Queue.cs:40 takes a single worker", "-")
        errors = self.errors(self.feature(plan=plan))
        self.assertTrue(any("claim without evidence" in e for e in errors), errors)
        self.assertTrue(any("unverified claim without `to verify:`" in e for e in errors), errors)

    def test_tier_must_be_chosen(self):
        plan = PLAN.replace("Tier: standard — a new", "Tier: trivial | standard | security — a new")
        self.assertTrue(any("Tier" in e for e in self.errors(self.feature(plan=plan))))

    def test_long_plan_is_a_warning_not_an_error(self):
        plan = PLAN + "\nfiller " * 5000
        errors, warnings = self.script.check(self.feature(plan=plan))
        self.assertEqual(errors, [])
        self.assertTrue(warnings and "words" in warnings[0])

    def test_spec_mode_checks_the_spec_alone(self):
        self.feature(plan=None, tasks=None)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.script.main(["feature-12-export", "--spec"]), 0)
            self.assertEqual(self.script.main(["feature-12-export"]), 1)

    def test_folder_name_never_becomes_a_path(self):
        self.feature()
        for bad in ("../specs/feature-12-export", "/etc", "_template", "feature-99"):
            self.assertIsNone(self.script.resolve_folder(os.getcwd(), bad), bad)
        self.assertIsNotNone(self.script.resolve_folder(os.getcwd(), "specs/feature-12-export/"))


if __name__ == "__main__":
    unittest.main()
