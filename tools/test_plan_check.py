"""Unit tests for core/.squad/tools/plan-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import types
import unittest

from test_squad_tools import git, load_script, write

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

- N1: An export of 10,000 items finishes within the request timeout.

## Acceptance criteria

- AC1: an export writes one row per item, 10,000 within the request timeout (S1, N1)
- AC2: an empty library writes the header only, titles with commas are quoted (E1, E2)

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

## Options considered

one option: the CSV writer and the job queue exist already.

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

    def test_non_functional_requirements_are_numbered_and_traced(self):
        untraced = SPEC.replace("(S1, N1)", "(S1)")
        self.assertIn("spec.md: N1 is named by no acceptance criterion and not listed under *Out of scope*",
                      self.errors(self.feature(spec=untraced)))
        out_of_scope = untraced.replace("## Out of scope\n", "## Out of scope\n\n- N1: measured in a later issue.\n")
        self.assertEqual(self.errors(self.feature(spec=out_of_scope)), [])
        bullet = SPEC.replace("- N1: An export", "- An export")
        self.assertTrue(any("non-functional requirement not written" in e for e in self.errors(self.feature(spec=bullet))))
        prose = SPEC.replace("- N1: An export", "An export")
        self.assertTrue(any("names no `- N1: …`" in e for e in self.errors(self.feature(spec=prose))))
        none = SPEC.replace("- N1: An export of 10,000 items finishes within the request timeout.", "none")
        self.assertEqual(self.errors(self.feature(spec=none.replace("(S1, N1)", "(S1)"))), [])
        ranged = SPEC.replace("- N1: An export", "- N1: A config value `limit`, default 10.\n- N2: An export").replace(
            "(S1, N1)", "(S1, N1-N2)")
        self.assertEqual(self.errors(self.feature(spec=ranged)), [])

    def test_amendments_record_a_criterion_changed_after_approval(self):
        table = ("\n## Amendments\n\n| Criterion | Change | Reason | Step | Decided by |\n| - | - | - | - | - |\n"
                 "| AC1 | the limit is 5,000 items | the request timeout is 30 s | 6 | Lead |\n")
        self.assertEqual(self.errors(self.feature(spec=SPEC + table)), [])
        self.feature(spec=SPEC + table, plan=None, tasks=None)
        self.assertEqual(self.script.check_spec_only(os.path.join("specs", "feature-12-export"))[0], [])
        dropped = (SPEC.replace("- AC2: an empty library writes the header only, titles with commas are quoted (E1, E2)\n",
                                "").replace("- S2: concurrent", "- E1, E2: in a follow-up issue.\n- S2: concurrent")
                   + table.replace("| AC1 | the limit", "| AC2 | dropped: moved to a follow-up issue; the limit"))
        self.assertEqual(self.errors(self.feature(spec=dropped)), [], "a dropped criterion may stay in plan and tasks")
        still = SPEC + table.replace("| AC1 | the limit", "| AC1 | dropped: the limit")
        self.assertIn("spec.md: *Amendments* drops AC1, which is still a criterion", self.errors(self.feature(spec=still)))
        unknown = SPEC + table.replace("| AC1 |", "| AC9 |")
        self.assertTrue(any("changes AC9, which no criterion" in e for e in self.errors(self.feature(spec=unknown))))
        for bad, expected in ((table.replace("| Lead |", "| Dev |"), "not decided by"),
                              (table.replace("| 6 |", "| — |"), "empty cell"),
                              (table.replace("| Step |", "| When |"), "needs the columns"),
                              ("\n## Amendments\n\nAC1 changed.\n", "holds no table")):
            self.assertTrue(any(expected in e for e in self.errors(self.feature(spec=SPEC + bad))), expected)
        write("specs/issue-34/plan.md", BUG_PLAN + table)
        self.assertEqual(self.errors("specs/issue-34"), [], "a bug fix records its amendments in plan.md")

    def matrix(self, folder):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = self.script.main([os.path.basename(folder), "--matrix"])
        return code, output.getvalue()

    def test_spec_limit_scales_with_the_criteria(self):
        folder = self.feature(plan=None, tasks=None)
        write(os.path.join(folder, "spec.md"), SPEC + "\nfiller " * 600)
        warnings = self.script.check_spec_only(folder)[1]
        self.assertTrue(warnings and "over 700 for 2 criteria" in warnings[0], warnings)
        many = SPEC.replace("- AC2:", "".join(f"- AC{n}: x (S1)\n" for n in range(3, 20)) + "- AC2:")
        write(os.path.join(folder, "spec.md"), many + "\nfiller " * 2000)
        self.assertEqual(self.script.check_spec_only(folder)[1], [], "19 criteria may take up to SPEC_MAX_WORDS")
        write(os.path.join(folder, "spec.md"), many + "\nfiller " * 2500)
        self.assertTrue(self.script.check_spec_only(folder)[1], "SPEC_MAX_WORDS caps the limit")

    def test_small_feature_lets_its_criteria_be_its_scenarios(self):
        small = SPEC.replace("- S1: Given a library, when the user exports it, then a CSV file with one row per item is "
                             "written.\n- S2: Given an export in progress, when another starts, then the second waits.",
                             "none").replace("(S1, N1)", "(N1)").replace("- S2: concurrent exports are serialized by "
                                                                       "the existing job queue.", "none")
        self.assertEqual(self.errors(self.feature(spec=small)), [])
        many = small.replace("- AC2:", "- AC3: x (E1)\n- AC4: y (E2)\n- AC2:")
        tasks = TASKS.replace("AC1, AC2", "AC1\u2013AC4")
        plan = PLAN.replace("| AC2 |", "| AC3, AC4 | T3 | x |\n| AC2 |")
        self.assertTrue(any("only a small feature may" in e for e in self.errors(self.feature(spec=many, plan=plan,
                                                                                               tasks=tasks))))
        secure = PLAN.replace("Security areas touched: none", "Security areas touched: CSV import")
        self.assertTrue(any("touches a security area" in e for e in self.errors(self.feature(spec=small, plan=secure))))

    def challenge(self, plan, on_base=lambda path: False):
        return self.script.challenge_verdict(plan, on_base)

    def test_plan_challenge_trigger(self):
        self.assertEqual(self.challenge(PLAN), (False, "one option and no new decision record"))
        weighed = PLAN.replace("one option: the CSV writer and the job queue exist already.",
                               "- A streaming writer: lost, the files are small.")
        self.assertEqual(self.challenge(weighed), (True, "*Options considered* names an alternative"))
        records = PLAN + "\n## Decision records\n\n- `docs/decisions/0007-csv-export.md` (Proposed)\n"
        self.assertEqual(self.challenge(records), (True, "new decision record docs/decisions/0007-csv-export.md"))
        self.assertFalse(self.challenge(records, on_base=lambda path: True)[0], "an extended record alone is no trigger")
        self.assertTrue(self.challenge(PLAN.replace("Tier: standard", "Tier: security"))[0])
        self.assertFalse(self.challenge(weighed.replace("Tier: standard", "Tier: trivial"))[0])
        no_code = weighed + "\n## Verification without tests\n\n- AC1: CI: the workflow run.\n"
        self.assertEqual(self.challenge(no_code), (False, "no production code (*Verification without tests*)"))
        empty = PLAN.replace("one option: the CSV writer and the job queue exist already.", "")
        self.assertTrue(any("*Options considered* is missing" in e for e in self.errors(self.feature(plan=empty))))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.script.main([os.path.basename(self.feature(plan=weighed))])
        self.assertIn("Plan challenge: due — *Options considered* names an alternative", output.getvalue())

    def test_tier_tests_needs_its_test_rows(self):
        plan = BUG_PLAN.replace("Tier: trivial", "Tier: tests")
        write("specs/issue-34/plan.md", plan)
        self.assertEqual(self.errors("specs/issue-34"), [])
        write("specs/issue-34/plan.md", plan.replace("| NfoWriterEmptyTitleWritesNoTitle |", "| — |"))
        self.assertTrue(any("row without a test name" in e for e in self.errors("specs/issue-34")))

    def test_matrix_finds_tests_by_criterion_id_or_by_name(self):
        folder = self.feature()
        write("tests/ExportTests.cs", '[TestCategory("AC1")]\npublic void ExportWritesRows() {}\n'
                                      "public void ExportQuotesCommas() {}\n")
        code, output = self.matrix(folder)
        self.assertEqual(code, 0, output)
        self.assertIn("| AC1 | unit | ExportWritesOneRowPerItem | pass on `the working tree`: tests/ExportTests.cs |",
                      output, "a renamed test is found by its criterion id")
        self.assertIn("| AC2 | unit | ExportEmptyLibraryWritesHeader, ExportQuotesCommas | pass on", output)
        write("tests/ExportTests.cs", 'public void ExportWritesRows() { Check("AC10"); }\n')
        code, output = self.matrix(folder)
        self.assertEqual(code, 1, output)
        self.assertIn("| AC1 | unit | ExportWritesOneRowPerItem | MISSING: no test file names ExportWritesOneRowPerItem, "
                      "and none its row names or the branch changes carries AC1 |", output, "AC10 is not AC1")
        self.assertIn("FAIL: 2 criterion(s) MISSING", output)
        write("tests/ExportTests.cs", "func TestExport_AC1(t *testing.T) {}\nt.Run(\"AC2 header only\", f)\n")
        self.assertEqual(self.matrix(folder)[0], 0, "a name suffix or a subtest name carries the id")

    def test_matrix_shows_other_verifications_and_amendments(self):
        plan = PLAN.replace("| AC2 | ExportEmptyLibraryWritesHeader, ExportQuotesCommas | tests/ExportTests.cs |",
                            "| AC2 | after merge: the PM imports the file into the target application | — |\n"
                            "| AC3 | CI: the image build check | — |\n| AC4 | manual: the PM on the CI artifact | — |")
        plan += "\n## Verification without tests\n\n- AC5: check: `git diff` holds no other file.\n"
        spec = SPEC.replace("- AC2:", "- AC3: x (S1)\n- AC4: y (S1)\n- AC5: z (S1)\n- AC6: w (S1)\n- AC2:")
        spec += ("\n## Amendments\n\n| Criterion | Change | Reason | Step | Decided by |\n| - | - | - | - | - |\n"
                 "| AC6 | waived: no device to test on | hardware only | 8 | Product Manager |\n"
                 "| AC7 | dropped: in a follow-up issue | scope | 6 | Lead |\n")
        tasks = TASKS.replace("AC1, AC2", "AC1\u2013AC6")
        folder = self.feature(spec=spec, plan=plan, tasks=tasks)
        write("tests/ExportTests.cs", "ExportWritesOneRowPerItem\n")
        self.assertEqual(self.errors(folder), [], "a waived criterion needs no test")
        code, output = self.matrix(folder)
        self.assertEqual(code, 0, output)
        for row in ("| AC2 | after merge | the PM imports the file into the target application | after merge: the "
                    "linked verification issue |", "| AC3 | CI | the image build check | pending: the pull request's CI",
                    "| AC4 | manual | the PM on the CI artifact | to record:",
                    "| AC5 | check | `git diff` holds no other file. | to record:",
                    "| AC6 | waived | \u2014 | waived by the Product Manager", "| AC7 | dropped | \u2014 | dropped"):
            self.assertIn(row, output)
        waived_by_lead = spec.replace("| 8 | Product Manager |", "| 8 | Lead |")
        self.assertTrue(any("did not waive" in e for e in self.errors(self.feature(spec=waived_by_lead))))

    def test_matrix_reads_the_test_paths_of_the_settings_and_needs_a_plan(self):
        subprocess.run(["git", "init", "-q"], check=True)
        write("pkg/export_test.go", "// AC1 and AC2\n")
        self.script.settings = types.SimpleNamespace(COVERAGE_EXCLUDES=["*_test.go"])
        code, output = self.matrix(self.feature(plan=PLAN.replace("| tests/ExportTests.cs |", "| — |")))
        self.assertEqual(code, 0, output)
        self.assertIn("pass on `the working tree`: pkg/export_test.go", output)
        write("specs/issue-35/log.md", "| Date |\n")
        self.assertEqual(self.matrix("specs/issue-35")[0], 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.script.main(["issue-35", "--spec", "--matrix"]), 1)

    def test_matrix_counts_a_bare_criterion_id_only_in_a_file_the_row_names_or_the_branch_changes(self):
        git("init", "-q", "-b", "main")
        write("tests/OldTests.cs", 'it("AC1 retries the outbox")\nit("AC2 drops a stale row")\n')
        write("tests/ExportTests.cs", "// AC2: the header row\n")
        git("add", "-A")
        git("commit", "-q", "-m", "an earlier change")
        git("checkout", "-q", "-b", "work")
        self.script.settings = types.SimpleNamespace(COVERAGE_TEST_PATHSPECS=["tests/*"])
        folder = self.feature()
        code, output = self.matrix(folder)
        self.assertEqual(code, 1, output)
        self.assertIn("| AC1 | unit | ExportWritesOneRowPerItem | MISSING:", output, "an earlier change's test carries AC1")
        self.assertRegex(output, r"\| AC2 \| unit \| [^|]+ \| pass on `\w+`: tests/ExportTests.cs \|", "the file AC2's row names")
        self.assertNotIn("OldTests", output, "a test file the branch leaves alone")
        self.assertNotIn("no merge base", output)
        write("tests/NewTests.cs", 'it("AC1 writes one row per item")\n')
        self.assertRegex(self.matrix(folder)[1], r"\| AC1 \| unit \| ExportWritesOneRowPerItem \| pass on `\w+`: "
                         r"tests/NewTests.cs \|", "an untracked test file is a change of the branch")
        git("add", "-A")
        git("commit", "-q", "-m", "the tests")
        write("tests/OldTests.cs", 'it("AC1 retries the outbox")\nit("AC2 drops a stale row")\nit("AC3")\n')
        code, output = self.matrix(folder)
        self.assertEqual(code, 0, output)
        self.assertIn("tests/NewTests.cs, tests/OldTests.cs |", output, "committed and uncommitted changes count")

    def test_a_criterion_verified_two_ways_or_by_a_pointer_cell_is_reported(self):
        git("init", "-q", "-b", "main")
        write("src/outbox-retry.test.ts", 'it("AC1 retries the outbox")\nit("AC4 keeps the order")\n')
        git("add", "-A")
        git("commit", "-q", "-m", "an earlier change")
        git("checkout", "-q", "-b", "work")
        self.script.settings = types.SimpleNamespace(COVERAGE_TEST_PATHSPECS=["*.test.ts"])
        plan = BUG_PLAN.replace("- [ ] AC1: an empty title writes no title element",
                                "- AC1: every link of the guide opens\n- AC2: the docs build passes\n"
                                "- AC3: only the guide changes\n- AC4: the guide names the order").replace(
            "| AC1 | NfoWriterEmptyTitleWritesNoTitle | tests/NfoWriterTests.cs |",
            "| AC1 | check (below) | \u2014 |\n| AC2 | CI: the docs build | \u2014 |\n| AC3 | none | \u2014 |\n"
            "| AC4 | see below | \u2014 |")
        plan += ("\n## Verification without tests\n\n- AC1: manual: the PM opens every link of the guide\n"
                 "- AC2: CI: the docs build, as AC4 needs no build\n- AC3: check: `git diff` holds only the guide\n")
        write("specs/issue-158/plan.md", plan)
        errors = self.errors("specs/issue-158")
        self.assertEqual(len(errors), 2, errors)
        self.assertIn("AC1 is verified as unit under *Tests per criterion* (check (below)) and as manual under "
                      "*Verification without tests*", errors[0])
        self.assertIn("AC4: the *Tests per criterion* cell `see below` names no kind", errors[1],
                      "a test file that carries AC4 from an earlier change holds no test of that name")
        code, output = self.matrix("specs/issue-158")
        self.assertEqual(code, 1, output)
        for row in ("| AC1 | unit | check (below) | MISSING:", "| AC1 | manual | the PM opens every link of the guide | "
                    "CONFLICT: *Tests per criterion* verifies it as unit", "| AC2 | CI | the docs build | pending:",
                    "| AC3 | check | `git diff` holds only the guide | to record:", "| AC4 | unit | see below | MISSING:"):
            self.assertIn(row, output)
        self.assertNotIn("outbox-retry", output, "an earlier change's AC1 and AC4 are no carriers")
        self.assertIn("FAIL: 2 criterion(s) MISSING", output)
        self.assertIn("1 CONFLICT row(s) — the Lead keeps one verification per criterion", output)

    def test_a_verification_line_names_the_criteria_it_starts_with(self):
        parts = {"Verification without tests": "- AC1-3: manual: the PM on the build\n"
                                                "- AC4, AC5: CI: the image build, unlike AC6\n"}
        found = self.script.without_tests_rows(parts)
        self.assertEqual([criterion for criterion, _ in found], ["AC1", "AC2", "AC3", "AC4", "AC5"],
                         "a range and a list; AC6 in the prose belongs to no verification of the line")
        self.assertEqual(found[0][1][:2], ("manual", "the PM on the build"), "the ids are stripped before the kind")
        self.assertEqual(found[3][1][:2], ("CI", "the image build, unlike AC6"))

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
        write("tests/ExportTests.cs", "public void ExportWritesOneRowPerItem() {}\n")
        self.assertEqual(self.errors(self.feature(plan=plan)), [], "a test that exists already may verify a criterion")
        os.remove("tests/ExportTests.cs")
        errors = self.errors(self.feature(plan=plan))
        self.assertTrue(any("AC1: the *Tests per criterion* cell `ExportWritesOneRowPerItem` names no kind" in e
                            and "the plan writes no test" in e for e in errors), errors)

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

    def test_comment_opener_in_a_code_span_or_fence_hides_nothing(self):
        strip = self.script.strip_comments
        self.assertEqual(strip("a <!-- c --> b"), "a  b")
        self.assertEqual(strip("a `<!--` b\n- [ ] AC1: x"), "a `<!--` b\n- [ ] AC1: x")
        self.assertEqual(strip("```\n<!--\n```\nrest"), "```\n<!--\n```\nrest")
        self.assertEqual(strip("<!-- use `x` -->after"), "after")

    def test_long_spec_is_a_warning_and_guidance_comments_do_not_count(self):
        folder = self.feature()
        spec_path = os.path.join(folder, "spec.md")
        with open(spec_path, encoding="utf-8") as handle:
            spec = handle.read()
        with open(spec_path, "w", encoding="utf-8") as handle:
            handle.write(spec + "\n<!-- " + "guidance " * 3000 + "-->\n")
        self.assertEqual(self.script.check_spec_only(folder)[1], [], "comments are not counted")
        with open(spec_path, "w", encoding="utf-8") as handle:
            handle.write(spec + "\nfiller " * 3000)
        errors, warnings = self.script.check_spec_only(folder)
        self.assertTrue(warnings and "SPEC_MAX_WORDS" in warnings[0], warnings)
        self.assertFalse(any("words" in e for e in errors), "a long spec is no finding")

    def test_plan_over_the_limit_of_its_tier_is_a_finding(self):
        errors, warnings = self.script.check(self.feature(plan=PLAN + "\nfiller " * 3000))
        self.assertTrue(any("PLAN_MAX_WORDS 2500 for tier standard" in e for e in errors), errors)
        self.assertEqual(warnings, [])
        errors, _ = self.script.check(self.feature(plan=PLAN + "\nfiller " * 2000))
        self.assertFalse(any("words" in e for e in errors), "a plan within the limit passes")
        errors, _ = self.script.check(self.feature(plan=PLAN.replace("Tier: standard", "Tier: security")
                                                   + "\nfiller " * 3000))
        self.assertFalse(any("words" in e for e in errors), "tier security allows 4000 words")
        trivial = BUG_PLAN + "\nfiller " * 900
        write("specs/issue-34/plan.md", trivial)
        self.assertTrue(any("PLAN_MAX_WORDS 800 for tier trivial" in e for e in self.errors("specs/issue-34")))
        self.script.PLAN_MAX_WORDS = 4000
        self.assertEqual(self.errors("specs/issue-34"), [], "one number from an older settings file applies to all")
        self.script.PLAN_MAX_WORDS = {"standard": 100}
        self.assertEqual(self.script.plan_limit("trivial"), 800, "a tier the settings lack keeps its default")
        self.assertEqual(self.script.plan_limit(None), 4000, "no tier: the highest limit")

    def test_template_lines_and_comments_do_not_count_against_the_plan_limit(self):
        shutil.copytree(TEMPLATES, os.path.join("specs", "_template"))
        with open(os.path.join(TEMPLATES, "plan.md"), encoding="utf-8") as handle:
            template = handle.read()
        self.assertEqual(self.script.counted_words(template), 0, "the template's own lines are not the Lead's")
        self.assertEqual(self.script.counted_words("<!-- " + "guidance " * 900 + "-->\nOwn words here.\n"), 3)
        errors, _ = self.script.check(self.feature(plan=PLAN + "\n" + template.split("\n## ", 1)[1] * 2))
        self.assertFalse(any("words" in e for e in errors), "guidance kept from the template is not counted")

    def test_appended_notes_do_not_count_against_the_plan_limit(self):
        notes = "\n## Security notes\n\n" + "note " * 5000 + "\n\n## Challenge notes\n\n" + "note " * 5000 + "\n"
        errors, _ = self.script.check(self.feature(plan=PLAN + "\nfiller " * 2000 + notes))
        self.assertFalse(any("words" in e for e in errors), "the appended notes are not counted")
        errors, _ = self.script.check(self.feature(plan=PLAN + notes + "\n## Later\n\n" + "filler " * 5000))
        self.assertTrue(any("PLAN_MAX_WORDS" in e for e in errors), "a section after the notes is counted")

    def test_justified_plan_size_is_a_warning_up_to_the_hard_limit(self):
        justified = PLAN.replace("\n## ", "\nPlan size: eleven task groups across agent and backend\n\n## ", 1)
        errors, warnings = self.script.check(self.feature(plan=justified + "\nfiller " * 4000))
        self.assertFalse(any("words" in e for e in errors), errors)
        self.assertTrue(warnings and "justified: eleven task groups" in warnings[0], warnings)
        placeholder = PLAN.replace("\n## ", "\nPlan size: <why>\n\n## ", 1)
        errors, _ = self.script.check(self.feature(plan=placeholder + "\nfiller " * 4000))
        self.assertTrue(any("PLAN_MAX_WORDS" in e for e in errors), "a placeholder is no reason")
        errors, _ = self.script.check(self.feature(plan=justified + "\nfiller " * 5000))
        self.assertTrue(any("over twice PLAN_MAX_WORDS" in e for e in errors), "beyond twice the limit only a split helps")

    def test_an_approved_plan_is_not_reopened_for_its_size(self):
        folder = self.feature(plan=PLAN + "\nfiller " * 6000)
        errors, _ = self.script.check(folder)
        self.assertTrue(any("over twice PLAN_MAX_WORDS" in e for e in errors), "while the plan is written")
        errors, warnings = self.script.check(folder, approved=True)
        self.assertFalse(any("words" in e for e in errors), errors)
        self.assertTrue(any("approved" in w and "PLAN_MAX_WORDS 2500 for tier standard" in w for w in warnings), warnings)
        errors, _ = self.script.check(self.feature(plan=PLAN.replace("Tier: standard", "Tier: <tier>")), approved=True)
        self.assertTrue(errors, "every other finding still counts on an approved plan")

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
        method = PLAN + "\n## Signatures (for the Dev's skeleton)\n\n- `func (c *Collector) Run(ctx context.Context) error`\n"
        self.assertTrue(any("`Run`" in e for e in self.errors(self.feature(plan=method))),
                        "a Go method is named after the method, not after its receiver")
        self.assertEqual(self.script.signature_names("`func (o *Options) Kernel() string` `func ReadBootID() error`"),
                         ["Kernel", "ReadBootID"])
        none = PLAN + "\n## Signatures (for the Dev's skeleton)\n\nnone\n"
        self.assertEqual(self.errors(self.feature(plan=none)), [])
        docs = TASKS.replace("| src/Export.cs |", "| docs/areas/export.md, README.md |")
        self.assertFalse(any("group G1" in e for e in self.errors(self.feature(plan=plan, tasks=docs))),
                         "a group of documentation rows needs no skeleton")
        noted = TASKS.replace("| src/Export.cs |", "| `docs/areas/export.md` (CSV section) |")
        self.assertFalse(any("group G1" in e for e in self.errors(self.feature(plan=plan, tasks=noted))),
                         "a note in the Files cell is no file")
        dash = TASKS.replace("| src/Export.cs |", "| — |").replace("| Dev |", "| Lead |")
        self.assertFalse(any("owned by the Lead" in e for e in self.errors(self.feature(tasks=dash))),
                         "a Lead row naming no file is no documentation row")
        lead = docs.replace("| Dev |", "| Lead |")
        self.assertTrue(any("owned by the Lead" in e for e in self.errors(self.feature(plan=plan, tasks=lead))))
        record = TASKS.replace("| src/Export.cs |", "| docs/decisions/0007-export.md |").replace("| Dev |", "| Lead |")
        self.assertFalse(any("owned by the Lead" in e for e in self.errors(self.feature(tasks=record))),
                         "a decision record stays the Lead's")

    def test_a_signatures_section_that_states_no_api_lists_none(self):
        for body in ("No public API changes, so no skeleton (step 4): the private `Refresh()` and `Plan.Count` change.",
                     "no public API changes; no skeleton (step 4 skipped) — `RefreshAsync` stays private",
                     "- No new or changed API: `Helper()` is private", "none (only the private `Helper()` changes)",
                     "- None.", "no new APIs"):
            self.assertEqual(self.script.signature_names(body), [], body)
            plan = PLAN + f"\n## Signatures (for the Dev's skeleton)\n\n{body}\n"
            self.assertEqual(self.errors(self.feature(plan=plan)), [], body)
        for body, names in (("- `Foo()` is new; no other API changes", ["Foo"]),
                            ("None of the old members change; new: `Foo()`", ["Foo"]),
                            ("- `def check(value) -> None`", ["check"]),
                            ("- `public void Foo()` (no `API` attribute)", ["Foo", "API"]),
                            ("- `func New() *T`\n- Deleted: `validHost(host string) bool`", ["New"]),
                            ("- `Foo()` is new\n- `Bar(x int)` is removed", ["Foo"])):
            self.assertEqual(self.script.signature_names(body), names, f"{body}: API is listed")
        self.assertEqual(self.script.signature_names("<!-- no skeleton -->\n- `Foo()`"), ["Foo"],
                         "a guidance comment states nothing")
        with open(os.path.join(TEMPLATES, "plan.md"), encoding="utf-8") as handle:
            guidance = self.script.signatures_section(handle.read())
        self.assertEqual(self.script.signature_names(guidance + "\n- `Foo()`"), ["Foo"],
                         "the template's guidance left in states nothing")

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
                .replace("- E1: …", "- E1: An empty library writes the header only.").replace("- N1: …\n", "")
                .replace("- AC1: …", "- AC1: an export writes one row per item (S1, E1)"))
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
        spec = SPEC.replace("- AC1:", "- **AC1**:").replace("- AC2:", "1. AC2:").replace("- S1:", "S1 is").replace(
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
        criterion = "- AC1: an export writes one row per item, 10,000 within the request timeout (S1, N1)"
        spec = SPEC.replace(criterion, criterion + "\n  - complements AC2 for empty input")
        self.assertNotEqual(spec, SPEC)
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
