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
Tier: standard — a new user-visible export.
Security areas touched: none

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

| # | Group | Task | Files | Criteria | Depends on | Owner | Done |
| - | ----- | ---- | ----- | -------- | ---------- | ----- | ---- |
| 1 | G1 | Writer | src/Export.cs | AC1, AC2 | — | Dev | [ ] |
"""

BUG_PLAN = """# Plan: Crash on empty title

Source: Issue #34
Tier: trivial — one guard.
Security areas touched: none

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

    def test_security_areas_line_must_be_none_or_the_areas(self):
        for bad in ("", "Security areas touched:\n", "Security areas touched: none | <areas>\n",
                    "Security areas touched: n/a\n", "Security areas touched: none|auth\n",
                    "Security areas touched: none \u2014 UI wording only\n", "Security areas touched: nothing\n"):
            plan = PLAN.replace("Security areas touched: none\n", bad)
            self.assertTrue(any("Security areas touched" in e for e in self.errors(self.feature(plan=plan))), bad)
        listed = PLAN.replace("Security areas touched: none", "Security areas touched: CSV import, `<script>`")
        self.assertEqual(self.errors(self.feature(plan=listed.replace("Tier: standard", "Tier: security"))), [])
        self.assertEqual(self.errors(self.feature(plan=PLAN.replace("touched: none", "touched: `none`"))), [])
        on_security = PLAN.replace("Tier: standard", "Tier: security")
        self.assertTrue(any("cannot be" in e for e in self.errors(self.feature(plan=on_security))))
        write("specs/issue-34/plan.md", BUG_PLAN.replace("Security areas touched: none\n", ""))
        self.assertTrue(any("Security areas touched" in e for e in self.errors("specs/issue-34")))

    def test_tier_must_be_chosen(self):
        plan = PLAN.replace("Tier: standard — a new", "Tier: trivial | standard | security — a new")
        self.assertTrue(any("Tier" in e for e in self.errors(self.feature(plan=plan))))

    def test_plan_over_the_limit_is_a_finding(self):
        errors, warnings = self.script.check(self.feature(plan=PLAN + "\nfiller " * 5000))
        self.assertTrue(any("PLAN_MAX_WORDS" in e for e in errors), errors)
        self.assertEqual(warnings, [])
        errors, _ = self.script.check(self.feature(plan=PLAN + "\nfiller " * 3000))
        self.assertFalse(any("words" in e for e in errors), "a plan within the limit passes")

    def test_skeleton_row_per_group_when_the_plan_lists_api(self):
        plan = (PLAN + "\n## Signatures (for the Dev's skeleton)\n\n- `Options.Kernel string`\n"
                "- `func ReadBootID() (string, error)`\n")
        errors = self.errors(self.feature(plan=plan))
        self.assertTrue(any("group G1 has no *Skeleton* row" in e for e in errors), errors)
        self.assertTrue(any("`Kernel`" in e for e in errors) and any("`ReadBootID`" in e for e in errors), errors)
        skeleton = "| 1 | G1 | Skeleton: Options.Kernel, ReadBootID | src/Export.cs | AC1 | — | Dev | [ ] |\n"
        covered = TASKS.replace("| 1 | G1 | Writer |", skeleton + "| 2 | G1 | Writer |")
        self.assertEqual(self.errors(self.feature(plan=plan, tasks=covered)), [])
        stated = TASKS.replace("| Writer |", "| Writer (no new API) |")
        errors = self.errors(self.feature(plan=plan, tasks=stated))
        self.assertFalse(any("group G1" in e for e in errors), errors)
        self.assertTrue(any("`Kernel`" in e for e in errors), errors)
        none = PLAN + "\n## Signatures (for the Dev's skeleton)\n\nnone\n"
        self.assertEqual(self.errors(self.feature(plan=none)), [])
        docs = TASKS.replace("| Dev |", "| Lead |")
        self.assertFalse(any("group G1" in e for e in self.errors(self.feature(plan=plan, tasks=docs))))

    def test_spec_mode_checks_the_spec_alone(self):
        self.feature(plan=None, tasks=None)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.script.main(["feature-12-export", "--spec"]), 0)
            self.assertEqual(self.script.main(["feature-12-export"]), 1)

    def test_filled_templates_with_their_guidance_left_in_pass(self):
        with open(os.path.join(TEMPLATES, "spec.md"), encoding="utf-8") as handle:
            spec = handle.read()
        spec = (spec.replace("# Spec: <title>", "# Spec: Export").replace("Issue #<number> | the user's description", "Issue #12")
                .replace("- S1: …", "- S1: Given a library, when the user exports it, then a CSV file is written.")
                .replace("- E1: …", "- E1: An empty library writes the header only.")
                .replace("- [ ] AC1: …", "- [ ] AC1: an export writes one row per item (S1, E1)"))
        for heading, text in (("## Problem", "Users cannot export."), ("## Non-functional requirements", "none"),
                              ("## Out of scope", "none"), ("## Open questions", "none"),
                              ("## Area documents", "- docs/areas/export.md: the format.")):
            spec = spec.replace(heading + "\n", heading + "\n\n" + text + "\n", 1)
        with open(os.path.join(TEMPLATES, "tasks.md"), encoding="utf-8") as handle:
            tasks = handle.read().replace("<title>", "Export").replace("| 1 | G1 | … | … | AC1 |",
                                                                       "| 1 | G1 | Writer | src/x.cs | AC1 |")
        plan = PLAN.replace("AC2", "AC1")
        self.assertEqual(self.errors(self.feature(spec=spec, plan=plan, tasks=tasks)), [])

    def test_tasks_in_several_tables_with_ranges_and_emphasis(self):
        tasks = ("# Tasks\n\n## Part 1\n\n| # | Group | Task | Criteria | Owner |\n| - | - | - | - | - |\n"
                 "| 1 | G1 | a | `AC1` | Dev |\n\n## Part 2\n\n| # | Group | Task | Criteria | Owner |\n| - | - | - | - | - |\n"
                 "| 2 | `G2` | b, not AC9 | **AC2** | Dev |\n")
        self.assertEqual(self.errors(self.feature(tasks=tasks)), [])
        ranged = TASKS.replace("AC1, AC2", "AC1–AC2")
        self.assertEqual(self.errors(self.feature(tasks=ranged)), [])

    def test_every_task_names_its_group_and_a_group_is_consecutive(self):
        rows = ("| 1 | G1 | Writer | src/Export.cs | AC1 | — | Dev | [ ] |\n"
                "| 2 | G2 | Reader | src/Import.cs | AC2 | — | Dev | [ ] |\n"
                "| 3 | G1 | Docs | docs/areas/export.md | AC1 | 1 | Dev | [ ] |\n"
                "| 4 | — | Tests | tests/ExportTests.cs | AC2 | 2 | Tester | [ ] |\n")
        tasks = TASKS.replace("| 1 | G1 | Writer | src/Export.cs | AC1, AC2 | — | Dev | [ ] |\n", rows)
        errors = self.errors(self.feature(tasks=tasks))
        self.assertTrue(any("group G1 are not consecutive" in e for e in errors), errors)
        self.assertTrue(any("task without a group: | 4 |" in e for e in errors), errors)
        no_column = TASKS.replace("| # | Group | Task |", "| # | Phase | Task |")
        self.assertTrue(any("without a *Group* column" in e for e in self.errors(self.feature(tasks=no_column))))

    def test_control_character_in_any_markdown_file_of_the_folder_is_reported(self):
        folder = self.feature(plan=PLAN.replace("single worker", "single\u202eworker"))
        write(os.path.join(folder, "log.md"), "# Log\n\nzero\u200bwidth\n")
        errors = self.errors(folder)
        self.assertIn("plan.md: control characters U+202E (write them as text escapes)", errors)
        self.assertIn("log.md: control characters U+200B (write them as text escapes)", errors)
        self.feature(spec=SPEC.replace("Users cannot", "Users\u2028cannot"), plan=None, tasks=None)
        errors = self.script.check_spec_only(folder)[0]
        self.assertIn("spec.md: control characters U+2028 (write them as text escapes)", errors)

    def test_backticked_status_and_crlf_are_accepted(self):
        plan = PLAN.replace("| confirmed |", "| `confirmed` |").replace("to verify:", "`to verify:`")
        self.assertEqual(self.errors(self.feature(plan=plan.replace("\n", "\r\n"))), [])

    def test_empty_markers_are_no_test_and_no_evidence(self):
        plan = PLAN.replace("| ExportWritesOneRowPerItem |", "| — |").replace(
            "src/Jobs/Queue.cs:40 takes a single worker", "n/a")
        errors = self.errors(self.feature(plan=plan))
        self.assertTrue(any("row without a test name" in e for e in errors), errors)
        self.assertTrue(any("claim without evidence" in e for e in errors), errors)

    def test_spec_without_parsable_criterion_or_scenario_fails_early(self):
        spec = SPEC.replace("- [ ] AC1:", "- **AC1**:").replace("- [ ] AC2:", "- AC2:").replace("- S1:", "S1 is").replace(
            "- S2:", "S2 is")
        self.feature(spec=spec, plan=None, tasks=None)
        errors = self.script.check_spec_only(os.path.join("specs", "feature-12-export"))[0]
        for expected in ("no acceptance criterion", "criterion not written", "no scenario"):
            self.assertTrue(any(expected in e for e in errors), (expected, errors))

    def test_plan_without_verified_facts_fails(self):
        plan = PLAN[:PLAN.index("## Verified facts")] + PLAN[PLAN.index("## Tests per criterion"):]
        self.assertTrue(any("*Verified facts* is missing" in e for e in self.errors(self.feature(plan=plan))))

    def test_open_question_variants(self):
        answered = SPEC.replace("- Which delimiter? Answered: comma, as the issue's example shows.",
                                "1. Which delimiter?\n   Answered: comma.\n   - detail\n"
                                "2. Which encoding?\n   - Answered: UTF-8.")
        self.assertEqual(self.errors(self.feature(spec=answered)), [])
        none = SPEC.replace("- Which delimiter? Answered: comma, as the issue's example shows.", "- None.")
        self.assertEqual(self.errors(self.feature(spec=none)), [])
        open_one = SPEC.replace("- Which delimiter? Answered: comma, as the issue's example shows.", "1. Which delimiter?")
        self.assertTrue(any("open question" in e for e in self.errors(self.feature(spec=open_one))))

    def test_trivial_bug_fix_needs_no_test_row(self):
        plan = BUG_PLAN.replace("| AC1 | NfoWriterEmptyTitleWritesNoTitle | tests/NfoWriterTests.cs |",
                                "| AC1 | none (trivial: no tests first) | — |")
        write("specs/issue-34/plan.md", plan)
        self.assertEqual(self.errors("specs/issue-34"), [])

    def test_dash_with_a_number_is_no_range_and_other_columns_are_not_criteria(self):
        spec = SPEC.replace("(E1, E2)", "(E1 \u2013 10 s at most)")
        self.assertTrue(any("E2 is named by no" in e for e in self.errors(self.feature(spec=spec))))
        tasks = TASKS.replace("| # | Task | Files | Criteria |", "| # | Action | Files | Criteria |")
        self.assertEqual(self.errors(self.feature(tasks=tasks)), [])

    def test_sub_bullet_and_prose_questions(self):
        spec = SPEC.replace("- [ ] AC1: an export writes one row per item (S1)",
                            "- [ ] AC1: an export writes one row per item (S1)\n  - complements AC2 for empty input")
        self.assertEqual(self.errors(self.feature(spec=spec)), [])
        prose = SPEC.replace("- Which delimiter? Answered: comma, as the issue's example shows.", "Which delimiter?")
        self.assertTrue(any("Open questions" in e for e in self.errors(self.feature(spec=prose))))

    def test_folder_name_never_becomes_a_path(self):
        self.feature()
        for bad in ("../specs/feature-12-export", "/etc", "_template", "feature-99"):
            self.assertIsNone(self.script.resolve_folder(os.getcwd(), bad), bad)
        self.assertIsNotNone(self.script.resolve_folder(os.getcwd(), "specs/feature-12-export/"))


if __name__ == "__main__":
    unittest.main()
