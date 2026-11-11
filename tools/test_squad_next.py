"""Unit tests for core/.squad/tools/squad-next.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
import sys
import types
import unittest

sys.dont_write_bytecode = True
_SPEC = importlib.util.spec_from_file_location(
    "gate_stamp_tests", os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_gate_stamp.py"))
fixtures = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixtures)
load, plan_text, row, run_main = fixtures.load, fixtures.plan_text, fixtures.row, fixtures.run_main

INTAKE = row("1 Intake", "Orchestrator", "bug: no feature label")
PLANNED = row("2 Plan", "Lead", "RESULT: DONE", 50000)
SKIPPED = row("2 Challenge skipped", "Orchestrator", "challenge skipped — one option and no new decision record")
TEST_FILE = "# AC1 test_expired_refused\n"
SPEC = """# Spec: Export

Source: Issue #7
Status: Approved by Lead

## Problem

Users cannot export.

## Scenarios

- S1: Given a library, when the user exports, then a CSV is written.

## Errors and edge cases

- E1: An empty library writes the header only.

## Non-functional requirements

none

## Acceptance criteria

- AC1: an export writes a CSV (S1)
- AC2: an empty library writes the header only (E1)

## Out of scope

none

## Open questions

none

## Area documents

none
"""
TASKS = """# Tasks: Export

Plan: [plan.md](plan.md)

| # | Group | Task | Files | Criteria | Depends on | Owner | Done |
| - | ----- | ---- | ----- | -------- | ---------- | ----- | ---- |
| 1 | G1 | Skeleton of export | src/e.py | AC1 | — | Dev | [ ] |
| 2 | G1 | export | src/e.py | AC1 | 1 | Dev | [ ] |
| 3 | G2 | Skeleton of header | src/e.py | AC2 | 2 | Dev | [ ] |
| 4 | G2 | header | src/e.py | AC2 | 3 | Dev | [ ] |
"""


def feature_plan():
    text = plan_text(signatures="- `def export(library) -> str`\n- `def header() -> str`")
    text = text.replace("Source: Issue #5", "Source: [spec.md](spec.md)")
    text = text.replace("- AC1: The check refuses an expired value.", "The criteria are the spec's.")
    return text.replace("| AC1 | test_expired_refused | tests/test_a.py |",
                        "| AC1 | test_export | tests/test_e.py |\n| AC2 | test_empty | tests/test_e.py |")


class NextTest(fixtures.RepoTest):
    def setUp(self):
        super().setUp()
        self.tool = load("squad-next")

    def next(self, *argv, stdin=None):
        code, out, err = run_main(self.tool, [self.folder, *argv], stdin)
        self.assertEqual(code, 0, out + err)
        return out

    def reviewed(self, step, verdict, tokens, **kwargs):
        """A Reviewer row whose verdict line names the code SHA it reviewed: the head."""
        return row(step, "Reviewer", f"{verdict} on {self.repo.git('rev-parse', 'HEAD')}", tokens, **kwargs)

    def stamp(self, *argv):
        code, out, _ = run_main(load("gate-stamp"), [self.folder, *argv])
        self.assertEqual(code, 0, out)
        self.repo.commit("stamp")

    def implemented(self, tier="standard", areas="none", **plan):
        """A bug fix through step 6 on the given tier, its code committed."""
        self.repo.write(f"specs/{self.folder}/plan.md", plan_text(tier, areas, **plan))
        if tier == "security":
            self.repo.log(row("2 Plan challenge", "Devil's Advocate", "VERDICT: NO OBJECTIONS", 9000),
                          row("3 Plan security", "Security", "VERDICT: APPROVED", 9000))
        self.repo.log(INTAKE, PLANNED, SKIPPED, row("4 Skeleton", "Dev", "done", 30000, "sonnet/medium"),
                      row("5 Tests first", "Tester", "red", 30000, "sonnet/medium"),
                      row("6 Implement", "Dev", "green", 30000, "sonnet/medium"),
                      row("6 Coverage skipped", "Orchestrator", "the gate passes"))
        self.repo.write("src/a.py", "x = 2\n")
        self.repo.write("tests/test_a.py", TEST_FILE)
        self.repo.commit("implement")


class TestPlanSteps(NextTest):
    def test_a_security_run_starts_challenge_and_review_in_parallel_with_the_tester_on_opus(self):
        self.assertIn("Next: step 1 — Intake", self.next())
        self.repo.log(INTAKE)
        self.assertIn("Launch: squad-lead, mode plan\n  Model: opus/medium", self.next())
        self.repo.write("specs/issue-5/plan.md", plan_text("security", "authentication"))
        self.repo.log(PLANNED)
        out = self.next()
        self.assertIn("tier security · review set: squad-reviewer (review) + squad-security (diff) · Tester model "
                      "opus/medium", out)
        self.assertIn("Next: step 2 — Plan challenge (tier security)", out)
        self.assertIn("Next: step 3 — Plan security review (Security areas touched: authentication)", out)
        self.assertIn("the two run in parallel on the same plan commit", out)
        self.repo.log(row("2 Plan challenge", "Devil's Advocate", "VERDICT: OBJECTIONS 1 major, 1 minor", 40000),
                      row("3 Plan security", "Security", "VERDICT: CHANGES_REQUIRED", 40000))
        out = self.next()
        self.assertIn("Next: step 2 — Lead revision", out)
        self.assertIn('continue the agent of "2 Plan" (0 continuation(s), 50,000 tokens)', out)
        self.assertIn('"2 Plan revise" "Lead" "<its RESULT line>, then the result" --agent-id <id> --continued', out)
        self.repo.log(row("2 Plan revise", "Lead", "RESULT: DONE", 20000, continued=True))
        self.assertIn("Next: step 3 — Security delta confirmation", self.next())
        self.repo.log(row("3 Plan security delta", "Security", "VERDICT: CHANGES_REQUIRED", 20000, continued=True))
        out = self.next()
        self.assertIn("the 2nd CHANGES_REQUIRED", out)
        self.assertIn("Launch: squad-lead, mode decide", out)
        self.assertIn("Agent: fresh launch — the first launch of mode decide", out)
        self.repo.log(row("3 Decide", "Lead", "RESULT: DECIDED — accept the complete fix", 20000))
        self.assertIn("Security delta confirmation", self.next(), "one confirmation of the accepted fix")
        self.repo.log(row("3 Plan security delta", "Security", "VERDICT: CHANGES_REQUIRED", 20000, continued=True))
        self.assertIn("escalate to the Product Manager", self.next())
        self.repo.log(row("3 Answer", "Product Manager", "narrow the scope"),
                      row("3 Plan security delta", "Security", "VERDICT: APPROVED", 20000, continued=True))
        out = self.next()
        self.assertIn("Next: step 4 — Skeleton", out)
        self.repo.log(row("4 Skeleton", "Dev", "done", 30000, "sonnet/medium"))
        out = self.next()
        self.assertIn("Launch: squad-tester, mode tests-first\n  Model: opus/medium (*Launch model*", out)
        self.assertIn("pass it explicitly on this launch", out)

    def test_plan_check_findings_go_to_the_lead_twice_then_to_decide(self):
        self.repo.write("specs/issue-5/plan.md", "# Plan: <title>\n\nTier: standard\n")
        self.repo.log(INTAKE, PLANNED)
        out = self.next()
        self.assertIn("Next: step 2 — plan-check.py findings", out)
        self.assertIn("  Finding: ", out)
        self.assertIn('"2 Plan revise (plan-check)"', out)
        self.repo.log(row("2 Plan revise (plan-check)", "Lead", "RESULT: DONE", 9000, continued=True),
                      row("2 Plan revise (plan-check)", "Lead", "RESULT: DONE", 9000, continued=True))
        out = self.next()
        self.assertIn("Launch: squad-lead, mode decide", out)
        self.assertIn('"2 Decide (plan-check)"', out)

    def test_an_approved_plan_gets_new_findings_as_a_revise_and_its_size_as_a_warning(self):
        self.implemented()
        self.repo.write("specs/issue-5/plan.md", plan_text() + "\nfiller " * 6000)
        out = self.next()
        self.assertNotIn("plan-check.py findings", out, "a merge's lower limit does not reopen an approved plan")
        self.repo.write("specs/issue-5/plan.md", plan_text().replace("src/a.py:1 | confirmed |", "src/a.py:1 |  |")
                        + "\nfiller " * 6000)
        out = self.next()
        self.assertIn("Next: step 2 — plan-check.py findings on the approved plan", out)
        self.assertIn("  Warning: plan.md has", out)
        self.assertIn("Launch: squad-lead, mode revise", out)
        self.assertIn("Hand over: the findings only, the approved scope unchanged (no challenge round)", out)
        self.repo.log(row("2 Plan revise (plan-check)", "Lead", "RESULT: DONE", 9000, continued=True),
                      row("2 Plan revise (plan-check)", "Lead", "RESULT: DONE", 9000, continued=True))
        self.assertIn('"2 Decide (plan-check)"', self.next(), "two revisions after the approval, then decide")

    def test_a_skipped_challenge_and_minor_objections_are_the_orchestrators(self):
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.log(INTAKE, PLANNED)
        out = self.next()
        self.assertIn('"2 Challenge skipped" Orchestrator "challenge skipped — one option and no new decision record"',
                      out)
        self.repo.write("specs/issue-5/plan.md", plan_text("security", "authentication"))
        self.repo.log(row("2 Plan challenge", "Devil's Advocate", "VERDICT: OBJECTIONS 0 major, 2 minor", 9000),
                      row("3 Plan security", "Security", "VERDICT: APPROVED", 9000))
        self.assertIn("append the minor objections verbatim to plan.md as *Challenge notes*", self.next())
        self.repo.log(row("2 Challenge notes", "Orchestrator", "minor objections appended verbatim to plan.md"))
        self.assertNotIn("append the minor objections", self.next(), "the logged append settles the notes")
        self.repo.log(row("2 Plan challenge", "Devil's Advocate", "objections in the report", 9000))
        out = self.next()
        self.assertIn('the row "2 Plan challenge · Devil\'s Advocate" carries no VERDICT line', out)

    def test_escalation_no_change_and_a_waiting_run(self):
        self.repo.log(INTAKE, row("2 Plan", "Lead", "RESULT: ESCALATE — which format?", 9000))
        self.assertIn("relay the Lead's question verbatim", self.next())
        self.repo.log(row("2 Answer", "Product Manager", "CSV"))
        out = self.next()
        self.assertIn("the Product Manager answered", out)
        self.assertIn('"2 Plan (answer)"', out)
        self.repo.log(row("2 Plan (answer)", "Lead", "RESULT: NO CHANGE — a duplicate of #4", 9000, continued=True))
        self.assertIn("Outcome \"no change\"", self.next())
        self.repo.log(row("2 No change", "Orchestrator", "comment posted"))
        self.assertIn("Next: step 12 — Wrap-up", self.next())
        self.repo.log(row("2 Waits", "Orchestrator", "spec waits for approval"))
        self.assertIn("the run waits", self.next())


class TestCodeSteps(NextTest):
    def test_a_bug_fix_runs_steps_4_to_6_then_the_code_check(self):
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.log(INTAKE, PLANNED, SKIPPED)
        self.assertIn("Next: step 4 — Skeleton", self.next())
        self.repo.log(row("4 Skeleton", "Dev", "done", 30000, "sonnet/medium"))
        out = self.next()
        self.assertIn("Next: step 5 — Tests first", out)
        self.assertIn("Model: sonnet/medium (.claude/agents/squad-tester.md)", out, "no override below tier security")
        self.repo.log(row("5 Tests first", "Tester", "red", 30000, "sonnet/medium"))
        out = self.next()
        self.assertIn("Launch: squad-dev, mode implement", out)
        self.assertIn("Agent: fresh launch — the first launch of mode implement", out, "never the skeleton agent")
        self.repo.log(row("6 Implement", "Dev", "green", 30000, "sonnet/medium"))
        out = self.next()
        self.assertIn("run *Test with coverage* and the *Coverage gate* from .squad/stack.md yourself", out)
        self.assertIn('"6 Coverage skipped" Orchestrator', out)
        self.repo.log(row("6 Coverage skipped", "Orchestrator", "the gate passes"))
        self.assertIn("plan-check.py --matrix reports MISSING criteria", self.next())
        self.repo.write("tests/test_a.py", TEST_FILE)
        self.repo.write("src/a.py", "x = 2\n")
        out = self.next()
        self.assertIn("Commit first, these files outside specs/ are uncommitted: src/a.py, tests/", out)
        self.repo.commit("implement")
        out = self.next()
        self.assertIn("Next: step 7 — Code check: no gate stamp in the log", out)
        self.assertIn("Gates due (tier standard): Format check, Analyzer gate, Test with coverage, Coverage gate, "
                      "scope-check.py + figure-check.py (no gate)", out)
        self.assertIn("Start the stamp in the background (Bash run_in_background)", out)
        self.assertNotIn("The clone is shallow", out, "no record or area document changed")
        self.repo.write("docs/areas/storage.md", "# Storage\n")
        self.repo.commit("area document")
        self.tool.stamp_tool().shallow = lambda root: True
        self.assertIn("The clone is shallow: run 'git fetch --unshallow --tags origin' before the stamp", self.next())

    def test_the_orchestrators_skip_row_ends_step_4(self):
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.log(INTAKE, PLANNED, SKIPPED)
        out = self.next()
        self.assertIn("Next: step 4 — Skeleton", out)
        self.assertIn('"4 Skeleton skipped" Orchestrator "skipped — <where the plan says it adds no API>"', out)
        self.repo.log(row("4 Skeleton", "Orchestrator", "Skipped: the plan adds only a private method"))
        self.assertIn("Next: step 5 — Tests first", self.next(), "the skip record is step 4")

    def test_a_plan_whose_signatures_state_no_api_needs_no_skeleton(self):
        signatures = "No public API changes, so no skeleton (step 4): the private `Refresh()` changes."
        self.repo.write("specs/issue-5/plan.md", plan_text(signatures=signatures))
        self.repo.log(INTAKE, PLANNED, SKIPPED)
        out = self.next()
        self.assertNotIn("Next: step 4", out)
        self.assertIn("Next: step 5 — Tests first", out)

    def test_documentation_updates_come_after_the_code(self):
        self.implemented(documentation="- README.md: the new flag")
        out = self.next()
        self.assertIn("Next: step 6 — Documentation updates", out)
        self.assertIn('continue the agent of "6 Implement"', out)

    def test_a_plan_without_code_skips_steps_4_and_5_and_the_tests_tier_has_no_dev(self):
        self.repo.write("specs/issue-5/plan.md", plan_text("trivial", code_free=True))
        self.repo.log(INTAKE, PLANNED, SKIPPED)
        out = self.next()
        self.assertIn("steps 4–5 — not applicable", out)
        self.repo.log(row("4-5 Skipped", "Orchestrator", "no production or test code"))
        self.assertIn("the Dev's edits (no Tester's share in the plan)", self.next())
        self.repo.log(row("6 Implement", "Dev", "done", 9000, "sonnet/medium"))
        self.assertNotIn("Tester's share", self.next())
        self.repo.write("specs/issue-5/plan.md", plan_text("tests"))
        out = self.next()
        self.assertIn("the Tester writes the plan's tests (tier tests: no Dev)", out)

    def test_a_plan_without_code_launches_the_tester_for_the_share_the_plan_names(self):
        # Vandox#410: the plan gave the test documentation and a dry-run test to the Tester.
        plan = plan_text("trivial", code_free=True, documentation="- docs/UNIT_TESTS.md: the Tester adds the limit")
        self.repo.write("specs/issue-5/plan.md", plan)
        self.repo.log(INTAKE, PLANNED, SKIPPED, row("4-5 Skipped", "Orchestrator", "no production or test code"))
        self.assertIn("the Dev's edits; then the Tester's share the plan names", self.next())
        self.repo.log(row("6 Implement", "Dev", "done", 9000, "sonnet/medium"))
        out = self.next()
        self.assertIn("the Tester's share of a plan without production or test code", out)
        self.assertIn("Launch: squad-tester, mode coverage", out)
        self.assertIn("git apply --check", out)
        self.repo.log(row("6 Tester share", "Tester", "done", 9000, "sonnet/medium"))
        self.assertNotIn("Tester's share", self.next())

    def test_deferred_tests_keep_the_coverage_pass_due_until_the_tester_ran(self):
        # Censio#137: the gate passed, the orchestrator went on to step 7 with four deferred tests open.
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.log(INTAKE, PLANNED, SKIPPED, row("4 Skeleton", "Dev", "done", 30000, "sonnet/medium"),
                      row("5 Tests first", "Tester", "red; Deferred: `test_a`, `test_b`", 30000, "sonnet/medium"),
                      row("6 Implement", "Dev", "green", 30000, "sonnet/medium"),
                      row("6 Coverage skipped", "Orchestrator", "the gate passes"))
        out = self.next()
        self.assertIn("the Tester's pass is due for the deferred tests", out)
        self.assertIn("the deferred tests (`test_a`, `test_b`)", out)
        self.repo.log(row("6 Coverage", "Tester", "deferred tests written", 9000, "sonnet/medium"))
        self.assertNotIn("deferred tests", self.next())

    def test_no_deferred_tests_leave_the_skip_row_in_force(self):
        self.repo.write("specs/issue-5/plan.md", plan_text())
        self.repo.log(INTAKE, PLANNED, SKIPPED, row("4 Skeleton", "Dev", "done", 30000, "sonnet/medium"),
                      row("5 Tests first", "Tester", "red; Deferred: none", 30000, "sonnet/medium"),
                      row("6 Implement", "Dev", "green", 30000, "sonnet/medium"),
                      row("6 Coverage skipped", "Orchestrator", "the gate passes"))
        self.assertNotIn("Next: step 6", self.next())

    def test_an_agent_continued_in_another_mode_is_never_continued_again(self):
        # Censio#140: the Tester's coverage agent was continued for tests first of the next group.
        self.repo.git("mv", "specs/issue-5", "specs/feature-7-export")
        self.folder = "feature-7-export"
        self.repo.folder = self.folder
        self.repo.write("specs/feature-7-export/spec.md", SPEC)
        self.repo.write("specs/feature-7-export/plan.md", feature_plan())
        self.repo.write("specs/feature-7-export/tasks.md", TASKS)
        self.repo.log(row("1 Intake", "Orchestrator", "feature: label enhancement"),
                      row("2a Spec", "Lead", "RESULT: DONE", 50000),
                      row("2a Spec challenge", "Devil's Advocate", "VERDICT: NO OBJECTIONS", 9000),
                      row("2b Plan", "Lead", "RESULT: DONE", 9000, continued=True),
                      row("2b Challenge skipped", "Orchestrator", "challenge skipped — one option"),
                      row("4 Skeleton (G1)", "Dev", "done", 30000, "sonnet/medium"),
                      row("5 Tests first (G1)", "Tester", "red", 30000, "sonnet/medium"),
                      row("6 Implement (G1)", "Dev", "green", 30000, "sonnet/medium"),
                      row("6 Coverage (G1)", "Tester", "covered", 30000, "sonnet/medium"),
                      row("4 Skeleton (G2)", "Dev", "done", 9000, "sonnet/medium", continued="4 Skeleton (G1)"),
                      row("5 Tests first (G2)", "Tester", "red", 9000, "sonnet/medium", continued=True),
                      row("6 Implement (G2)", "Dev", "green", 9000, "sonnet/medium", continued="6 Implement (G1)"))
        out = self.next()
        self.assertIn("Next: step 6 — Coverage (G2)", out)
        self.assertIn('the agent of "6 Coverage (G1)" was continued in another mode at "5 Tests first (G2)"', out)
        self.assertIn("short: the plan or task group", out)

    def test_task_groups_continue_the_agent_of_the_same_mode(self):
        self.repo.git("mv", "specs/issue-5", "specs/feature-7-export")
        self.folder = "feature-7-export"
        self.repo.folder = self.folder
        self.repo.write("specs/feature-7-export/spec.md", SPEC)
        self.repo.write("specs/feature-7-export/plan.md", feature_plan())
        self.repo.write("specs/feature-7-export/tasks.md", TASKS)
        self.repo.log(row("1 Intake", "Orchestrator", "feature: label enhancement"),
                      row("2a Spec", "Lead", "RESULT: DONE", 50000),
                      row("2a Spec challenge", "Devil's Advocate", "VERDICT: NO OBJECTIONS", 9000))
        out = self.next()
        self.assertIn("Next: step 2b — Plan", out)
        self.assertIn('continue the agent of "2a Spec"', out)
        self.repo.log(row("2b Plan", "Lead", "RESULT: DONE", 9000, continued=True),
                      row("2b Challenge skipped", "Orchestrator", "challenge skipped — one option"),
                      row("4 Skeleton (G1)", "Dev", "done", 30000, "sonnet/medium"),
                      row("5 Tests first (G1)", "Tester", "red", 30000, "sonnet/medium"),
                      row("6 Implement (G1)", "Dev", "green", 30000, "sonnet/medium"),
                      row("6 Coverage skipped (G1)", "Orchestrator", "passes"))
        out = self.next()
        self.assertIn("Next: step 4 — Skeleton (G2)", out)
        self.assertIn('--agent-id <id> --continued-from "4 Skeleton (G1)"', out)
        self.repo.log(row("4 Skeleton (G2)", "Dev", "done", 9000, "sonnet/medium", continued="4 Skeleton (G1)"))
        out = self.next()
        self.assertIn("Next: step 5 — Tests first (G2)", out)
        self.assertIn('"5 Tests first (G2)" "Tester" "<the result>" --agent-id <id> --continued\n', out)

    def test_a_skip_row_ends_step_4_for_its_group_and_one_without_a_group_for_every_group(self):
        self.repo.git("mv", "specs/issue-5", "specs/feature-7-export")
        self.folder = self.repo.folder = "feature-7-export"
        self.repo.write("specs/feature-7-export/spec.md", SPEC)
        self.repo.write("specs/feature-7-export/plan.md", feature_plan())
        self.repo.write("specs/feature-7-export/tasks.md", TASKS)
        self.repo.log(row("1 Intake", "Orchestrator", "feature: label enhancement"),
                      row("2a Spec", "Lead", "RESULT: DONE", 50000),
                      row("2a Spec challenge", "Devil's Advocate", "VERDICT: NO OBJECTIONS", 9000),
                      row("2b Plan", "Lead", "RESULT: DONE", 9000, continued=True),
                      row("2b Challenge skipped", "Orchestrator", "challenge skipped — one option"))
        self.assertIn('"4 Skeleton skipped (G1)" Orchestrator', self.next())
        self.repo.log(row("4 Skeleton skipped (G2)", "Orchestrator", "the group adds no API"))
        self.assertIn("Next: step 4 — Skeleton (G1)", self.next(), "a skip of G2 leaves G1's skeleton due")
        self.repo.log(row("4 Skeleton skipped", "Orchestrator", "the plan adds no API"))
        self.assertIn("Next: step 5 — Tests first (G1)", self.next())


    def feature(self, tasks):
        """A feature through the plan (no challenge) with the given tasks.md."""
        self.repo.git("mv", "specs/issue-5", "specs/feature-7-export")
        self.folder = self.repo.folder = "feature-7-export"
        self.repo.write("specs/feature-7-export/spec.md", SPEC)
        self.repo.write("specs/feature-7-export/plan.md", feature_plan())
        self.repo.write("specs/feature-7-export/tasks.md", tasks)
        self.repo.log(row("1 Intake", "Orchestrator", "feature: label enhancement"),
                      row("2a Spec", "Lead", "RESULT: DONE", 50000),
                      row("2a Spec challenge", "Devil's Advocate", "VERDICT: NO OBJECTIONS", 9000),
                      row("2b Plan", "Lead", "RESULT: DONE", 9000, continued=True),
                      row("2b Challenge skipped", "Orchestrator", "challenge skipped — one option"))

    def group_one_done(self):
        self.repo.log(row("4 Skeleton (G1)", "Dev", "done", 30000, "sonnet/medium"),
                      row("5 Tests first (G1)", "Tester", "red", 30000, "sonnet/medium"),
                      row("6 Implement (G1)", "Dev", "green", 30000, "sonnet/medium"),
                      row("6 Coverage skipped (G1)", "Orchestrator", "passes"))

    def test_an_orchestrator_row_of_step_5_ends_tests_first_for_its_group(self):
        self.feature(TASKS)
        self.group_one_done()
        self.repo.log(row("4 Skeleton (G2)", "Dev", "done", 9000, "sonnet/medium", continued="4 Skeleton (G1)"))
        out = self.next()
        self.assertIn("Next: step 5 — Tests first (G2)", out)
        self.assertIn('"5 Tests first skipped (G2)" Orchestrator', out, "the skip row is offered")
        self.repo.log(row("5 Tests first (G2)", "Orchestrator", "Tester launch denied, relaunching"))
        self.assertIn("Next: step 5 — Tests first (G2)", self.next(), "a row that does not say it skipped ends nothing")
        self.repo.log(row("5 Tests first (G2)", "Orchestrator", "skipped — G2 adds no production behaviour"))
        self.assertIn("Next: step 6 — Implement (G2)", self.next(), "an orchestrator skip row of step 5 ends it")

    def test_a_skip_row_of_step_5_without_a_group_ends_it_for_every_group(self):
        self.feature(TASKS)
        self.repo.log(row("4 Skeleton skipped", "Orchestrator", "the plan adds no API"),
                      row("5 Tests first skipped", "Orchestrator", "skipped — documentation only"))
        self.assertIn("Next: step 6 — Implement (G1)", self.next())

    def test_a_coverage_row_without_a_group_ends_the_coverage_pass_of_every_group(self):
        self.feature(TASKS)
        self.group_one_done()
        self.repo.log(row("4 Skeleton (G2)", "Dev", "done", 9000, "sonnet/medium", continued="4 Skeleton (G1)"),
                      row("5 Tests first (G2)", "Tester", "red", 9000, "sonnet/medium", continued=True),
                      row("6 Implement (G2)", "Dev", "green", 9000, "sonnet/medium", continued="6 Implement (G1)"))
        self.assertIn("Next: step 6 — Coverage (G2)", self.next())
        self.repo.log(row("6 Coverage gate (all groups)", "Orchestrator", "PASS"))
        self.assertNotIn("Coverage (G2)", self.next())

    def test_a_coverage_row_without_a_group_before_a_groups_implementation_leaves_its_pass_due(self):
        self.feature(TASKS)
        self.group_one_done()
        self.repo.log(row("6 Coverage gate", "Orchestrator", "PASS"),
                      row("4 Skeleton (G2)", "Dev", "done", 9000, "sonnet/medium", continued="4 Skeleton (G1)"),
                      row("5 Tests first (G2)", "Tester", "red", 9000, "sonnet/medium", continued=True),
                      row("6 Implement (G2)", "Dev", "green", 9000, "sonnet/medium", continued="6 Implement (G1)"))
        self.assertIn("Next: step 6 — Coverage (G2)", self.next())

    def test_a_documentation_group_needs_no_skeleton_and_no_tests_first(self):
        self.feature(TASKS + "| 5 | G3 | Area document | `docs/areas/export.md` | AC1 | 4 | Dev | [ ] |\n"
                     "| 6 | G3 | Test doubles | `tests/fixtures/README.md` | AC2 | 4 | Tester | [ ] |\n")
        self.group_one_done()
        self.repo.log(row("4 Skeleton (G2)", "Dev", "done", 9000, "sonnet/medium", continued="4 Skeleton (G1)"),
                      row("5 Tests first (G2)", "Tester", "red", 9000, "sonnet/medium", continued=True),
                      row("6 Implement (G2)", "Dev", "green", 9000, "sonnet/medium", continued="6 Implement (G1)"),
                      row("6 Coverage skipped (G2)", "Orchestrator", "passes"))
        out = self.next()
        self.assertIn("Next: step 6 — Documentation (G3)", out)
        self.assertNotIn("Tests first (G3)", out)
        self.repo.log(row("6 Documentation (G3)", "Dev", "written", 9000, "sonnet/medium", continued=True))
        out = self.next()
        self.assertIn("Launch: squad-tester, mode coverage", out, "the Tester writes the group's test documentation")
        self.assertIn('"6 Test documentation (G3)"', out)
        self.repo.log(row("6 Test documentation (G3)", "Tester", "written", 9000, "sonnet/medium"))
        self.assertNotIn("Next: step 6 — Documentation (G3)", self.next(), "the group is done after both rows")

    def test_a_note_in_parentheses_naming_code_keeps_a_group_out_of_documentation(self):
        self.feature(TASKS + "| 5 | G3 | Setting | `README.md` (read in `src/Settings.py`) | AC1 | 4 | Dev | [ ] |\n")
        self.assertFalse(self.tool.documentation_cell("`README.md` (read in `src/Settings.py`)"))
        self.assertTrue(self.tool.documentation_cell("`docs/areas/a.md`, `tests/Fixtures/README.md`"))

    def test_the_pm_group_runs_no_member(self):
        self.feature(TASKS.replace("| 1 | G1 |", "| 0 | PM | Layout probe | `specs/x/log.md` | AC1 | — | "
                                   "Product Manager | [ ] |\n| 1 | G1 |"))
        out = self.next()
        self.assertIn("Next: step 4 — Skeleton (G1)", out)
        self.assertNotIn("(PM)", out)


class TestVerdictLines(NextTest):
    def test_objections_with_notes_in_parentheses_are_counted(self):
        tool = self.tool
        line = ("VERDICT: OBJECTIONS 1 major (N3/AC3 unsatisfiable: small integers, delta (sum) relations), 5 minor "
                "(E8 vs N4/AC7, time shift bounds)")
        self.assertEqual(tool.objections(tool.Row(0, "2a Spec challenge", "2a", tool.ADVOCATE, line)), (1, 5))
        self.assertIsNone(tool.verdict_problem(tool.ADVOCATE, line))

    def test_review_counts_with_notes_in_parentheses_are_counted(self):
        tool = self.tool
        line = "VERDICT: BLOCKING 2 (S1, S2) | NON-BLOCKING 1 (wording) on 0123456789abcdef"
        found = tool.REVIEW.search(line)
        self.assertEqual((found.group("blocking"), found.group("nonblocking"), found.group("sha")),
                         ("2", "1", "0123456789abcdef"))

    def test_an_approval_with_a_note_keeps_its_sha_and_a_cut_short_line_is_named(self):
        tool = self.tool
        self.assertEqual(tool.REVIEW.search("VERDICT: APPROVE (no findings) on 0123456789abcdef").group("sha"),
                         "0123456789abcdef")
        cut = "VERDICT: BLOCKING 0 (a (b (c))) | NON-BLOCKING 2 on 0123456789abcdef"
        self.assertIsNotNone(tool.verdict_problem(tool.REVIEWER, cut), "a line read only in part is named")
        self.assertIsNone(tool.verdict_problem(tool.REVIEWER, "VERDICT: BLOCKING 1 | NON-BLOCKING 0 on 0123456789ab"))

    def test_a_spec_challenge_with_notes_moves_on_to_the_lead_revision(self):
        self.repo.git("mv", "specs/issue-5", "specs/feature-7-export")
        self.folder = self.repo.folder = "feature-7-export"
        self.repo.write("specs/feature-7-export/spec.md", SPEC)
        self.repo.log(row("1 Intake", "Orchestrator", "feature: label enhancement"),
                      row("2a Spec", "Lead", "RESULT: DONE", 50000),
                      row("2a Spec challenge", "Devil's Advocate", "VERDICT: OBJECTIONS 1 major (N3 unsatisfiable), "
                          "5 minor (E8 vs N4, AC7 name match)", 9000))
        out = self.next()
        self.assertIn("Next: step 2a — a major spec objection", out)
        self.repo.log(row("2a Spec challenge (revise)", "Lead", "RESULT: DONE — all objections answered", 9000,
                          continued=True))
        self.assertNotIn("step 2a", self.next())


class TestReviewAndAfter(NextTest):
    def test_the_review_set_follows_the_tier_and_a_round_follows_a_stamp(self):
        self.implemented()
        self.stamp()
        out = self.next()
        self.assertIn("Next: step 8 — Review, round 1 (full): squad-reviewer (mode review)", out)
        self.assertIn("No Security diff review on tier standard", out)
        self.assertNotIn("squad-security", out)
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 60000))
        out = self.next()
        self.assertIn("Launch: squad-dev, mode fix — code and documentation", out)
        self.assertIn('"8 Fix" "Dev" "<the result>" --agent-id <id> --continued', out)
        for round_number in (1, 2):
            self.repo.log(row("8 Fix", "Dev", "fixed", 9000, "sonnet/medium", continued=True))
            self.repo.write("src/a.py", f"x = {round_number + 2}\n")
            self.repo.commit("fix")
            self.assertIn("the code changed since the gate stamp", self.next())
            self.stamp()
            out = self.next()
            self.assertIn("Review, delta round", out)
            self.assertIn('continue the agent of "8 Review"', out)
            self.repo.log(self.reviewed("8 Review delta", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 9000,
                              continued=True))
        out = self.next()
        self.assertIn("blocking findings after two delta rounds", out)
        self.assertIn('"8 Decide (loop limit)"', out)

    def test_a_security_tier_reviews_with_both_and_non_blocking_findings_go_to_the_lead_first(self):
        self.implemented("security", "authentication")
        self.stamp()
        out = self.next()
        self.assertIn("squad-reviewer (mode review), squad-security (mode diff)", out)
        self.assertIn('"8 Security diff" "Security"', out)
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 0 \\| NON-BLOCKING 2", 60000),
                      row("8 Security diff", "Security", "VERDICT: APPROVED", 60000))
        out = self.next()
        self.assertIn("non-blocking findings (*Non-blocking findings*)", out)
        self.repo.log(row("8 Decide", "Lead", "RESULT: DECIDED — linked issues", 9000))
        out = self.next()
        self.assertIn("Next: step 9 — PR approval", out)
        self.assertIn('"9 PR approval" Orchestrator "approved by checklist"', out)

    def test_a_delta_round_with_only_non_blocking_findings_is_read_without_a_blocking_count(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 60000),
                      row("8 Fix", "Dev", "fixed", 9000, "sonnet/medium", continued=True))
        self.repo.write("src/a.py", "x = 3\n")
        self.repo.commit("fix")
        self.stamp()
        self.repo.log(self.reviewed("8 Review delta", "VERDICT: NON-BLOCKING 1", 9000, continued=True))
        out = self.next()
        self.assertNotIn("carries no VERDICT line", out)
        self.assertIn("non-blocking findings (*Non-blocking findings*)", out)

    def test_the_verdict_line_must_name_the_stamped_code(self):
        self.implemented()
        self.stamp()
        stamped = self.repo.git("rev-parse", "HEAD~1")
        self.repo.log(row("8 Review", "Reviewer", "VERDICT: APPROVE", 60000))
        out = self.next()
        self.assertIn("the Reviewer's verdict line names no code SHA: the round cannot be matched to the stamp on "
                      f"{stamped[:12]}", out)
        self.assertIn('continue the agent of "8 Review"', out)
        self.assertIn(f"the stamp's code SHA {stamped}: it reviews that SHA", out)
        self.assertIn('"8 Review (stamp SHA)" "Reviewer"', out)
        garbled = stamped[:9] + ("0" if stamped[9] != "0" else "1") + stamped[10:]
        self.repo.log(row("8 Review (stamp SHA)", "Reviewer", f"VERDICT: APPROVE on {garbled}", 9000, continued=True))
        self.assertIn(f"names {garbled[:12]}, not the stamped code {stamped[:12]}: a stale round", self.next())
        self.repo.log(row("8 Review (stamp SHA)", "Reviewer", f"VERDICT: APPROVE on {stamped[:7]}", 9000,
                          continued=True))
        self.assertIn("Next: step 9 — PR approval", self.next(), "a short SHA of the stamp")
        self.repo.write("src/a.py", "x = 5\n")
        self.repo.commit("fix")
        self.stamp()
        self.repo.log(row("8 Review delta", "Reviewer", f"VERDICT: APPROVE on {stamped}", 9000, continued=True))
        self.assertIn("a stale round", self.next(), "the code of the stamp before")
        self.repo.log(self.reviewed("8 Review delta", "VERDICT: APPROVE", 9000, continued=True))
        self.assertIn("Next: step 9 — PR approval", self.next(), "a commit that touched only specs/ after the stamp")

    def test_failed_gates_go_to_their_owner(self):
        self.implemented()
        head = self.repo.git("rev-parse", "HEAD")
        self.repo.log(row("7 Gate stamp", "Orchestrator", f"FAIL on {head} (tier standard): Format check FAIL; "
                          "Analyzer gate FAIL; Test with coverage FAIL; Coverage gate not run (Test with coverage "
                          "failed); scope-check.py pass"))
        out = self.next()
        self.assertIn("run *Format*, git restore -- every file it changed outside the change", out)
        self.assertIn("Launch: squad-code-officer, mode code-check", out)
        self.assertIn("Launch: squad-dev, mode fix", out)
        self.assertNotIn("Launch: squad-tester", out)
        self.repo.log(row("7 Gate stamp", "Orchestrator", f"FAIL on {head} (tier standard): Format check pass; "
                          "Coverage gate FAIL; scope-check.py FAIL"))
        out = self.next()
        self.assertIn("Launch: squad-tester, mode coverage", out)
        self.assertIn("a scope finding goes to the owner of the file", out)

    def test_approval_pull_request_after_the_pr_and_wrap_up(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: APPROVE", 60000))
        self.repo.commit("log")
        self.repo.git("checkout", "-q", "main")
        self.repo.write("NOTICE", "moved\n")
        self.repo.commit("main moved")
        self.repo.git("checkout", "-q", "work")
        self.assertIn("gate-stamp.py --verify fails", self.next())
        self.repo.git("merge", "-q", "--no-edit", "main")
        self.assertIn("the code changed since the gate stamp", self.next())
        self.stamp()
        self.assertIn("Next: step 9 — PR approval", self.next(), "a clean merge of main needs no new review round")
        self.repo.write("src/a.py", "x = 6\n")
        self.repo.commit("fix after the review")
        self.stamp()
        self.assertIn("Review, delta round", self.next(), "a commit of its own does")
        self.repo.log(self.reviewed("8 Review delta", "VERDICT: APPROVE", 9000, continued=True))
        self.assertIn("Next: step 9 — PR approval", self.next())
        self.repo.log(row("9 PR approval", "Orchestrator", "approved by checklist"))
        out = self.next()
        self.assertIn("Next: step 10 — Pull request", out)
        self.assertIn("Matrix: plan-check.py --matrix passes", out)
        self.repo.commit("log")
        log = self.repo.read("specs/issue-5/log.md")
        self.repo.git("rm", "-q", "-r", "specs/issue-5")
        self.repo.commit("Remove squad working record")
        out = self.next("--stdin", stdin=log)
        self.assertIn("after step 10 (log from --stdin)", out)
        self.assertIn("Next: step 11 — After the PR", out)
        self.repo.write("src/a.py", "x = 7\n")
        self.repo.commit("ci fix")
        out = self.next("--stdin", stdin=log)
        self.assertIn("Next: step 11 — Code check", out)
        self.assertIn("gate-stamp.py issue-5 --stdin < log.md > log-updated.md", out)
        code, log, _ = run_main(load("gate-stamp"), ["issue-5", "--stdin"], log)
        self.assertEqual(code, 0)
        out = self.next("--stdin", stdin=log)
        self.assertIn("Next: step 11 — Review, delta round", out)
        log += self.reviewed("11 Review delta", "VERDICT: APPROVE", 9000, continued=True)
        self.assertIn("Next: step 9 — PR approval", self.next("--stdin", stdin=log), "the re-approval")
        log += row("11 PR approval", "Orchestrator", "approved by checklist")
        out = self.next("--stdin", stdin=log)
        self.assertIn("Step 12 is still due: a merge or close notification ends the watching, never the run", out)
        self.assertIn("Next: step 12 — Wrap-up", self.next("--stdin", stdin=log + row("11 Merged", "Orchestrator",
                                                                                   "merged at 10:00")),
                      "Censio#127: a merge before the PR was marked ready still leaves step 12")
        log += row("11 Ready for review", "Orchestrator", "marked ready for review")
        self.assertIn("Next: step 12 — Wrap-up", self.next("--stdin", stdin=log))
        log += row("12 Wrap-up", "Orchestrator", "no lessons")
        self.assertIn("squad-log.py --summary --stdin until it exits 0", self.next("--stdin", stdin=log))

    def test_a_fix_ordered_in_approve_pr_ends_with_the_checklist(self):
        # Censio#140: the checklist row named the Lead's earlier NOT APPROVED, and step 9 asked for a fix again.
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: APPROVE", 60000))
        self.repo.commit("log")
        self.repo.log(row("9 PR approval", "Lead", "RESULT: NOT APPROVED — FIX: (1) Dev — the region icon", 9000))
        out = self.next()
        self.assertIn("Next: step 9 — NOT APPROVED with a fix", out)
        self.assertIn("Launch: squad-dev, mode fix", out)
        self.repo.log(row("9 Fix", "Dev", "fixed", 9000, "sonnet/medium", continued=True))
        self.repo.write("src/a.py", "x = 8\n")
        self.repo.commit("fix")
        self.stamp()
        self.repo.log(self.reviewed("8 Review delta", "VERDICT: APPROVE", 9000, continued=True))
        self.assertIn("Next: step 9 — PR approval", self.next())
        self.repo.log(row("9 PR approval", "Orchestrator", "approved by checklist; the Lead's NOT APPROVED fix done"))
        self.assertIn("Next: step 10 — Pull request", self.next())

    def test_not_approved_without_a_fix_goes_to_the_lead(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: APPROVE", 60000))
        self.repo.commit("log")
        self.repo.log(row("9 PR approval", "Lead", "RESULT: NOT APPROVED — the guarantee needs the PM", 9000))
        out = self.next()
        self.assertIn("NOT APPROVED without a fix", out)
        self.assertIn("Launch: squad-lead, mode decide", out)

    def test_a_verbatim_fix_needs_the_light_stamp_and_no_delta_round(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 60000),
                      row("8 Verbatim fix", "Orchestrator", "verbatim: README.md line 1"))
        self.repo.write("README.md", "Readme, fixed\n")
        self.repo.commit("verbatim fix")
        self.assertIn("add --verbatim", self.next())
        self.stamp("--verbatim")
        self.assertIn("Next: step 9 — PR approval", self.next())

    def test_docs_and_patch_routes(self):
        self.repo.log(INTAKE, row("2 Plan", "Lead", "RESULT: DONE Tier: patch/security — a pin in CI", 9000))
        out = self.next()
        self.assertIn("tier patch/security · review set: squad-security (diff)", out)
        self.assertIn("apply the Lead's exact edits", out)
        self.assertIn("launch squad-tester once", out)
        self.repo.write("README.md", "Readme 2\n")
        self.repo.commit("edit")
        out = self.next()
        self.assertIn("Gates due (tier patch/security): Format check, scope-check.py --tier patch", out)
        self.assertNotIn("run_in_background", out, "only a stamp that runs the full suite")
        self.stamp()
        out = self.next()
        self.assertIn("Launch: squad-security, mode diff", out)
        self.assertIn("the first log.md row", out)
        self.repo.log(row("8 Security diff", "Security", "VERDICT: APPROVED", 9000))
        self.assertIn("Next: step 10 — Pull request", self.next(), "no step 9 on tiers docs and patch")


RECORD = ("# 0001: Topic\n\n- **Status:** {status}\n- **Date:** 2026-01-01\n- **Supersedes:** —\n\n## Context\n\n"
          "Why.\n\n## Decision\n\nThis.\n")
RECORD_INDEX = ("# Decision records\n\n<!-- project:begin index -->\n| # | Title | Status | Date |\n| - | ----- | ------ "
                "| ---- |\n| 0001 | Topic | {status} | 2026-01-01 |\n<!-- project:end index -->\n")


class TestReviewFollowUps(NextTest):
    def test_verbatim_fixes_clear_the_non_blocking_findings_they_name(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 1", 60000),
                      row("8 Verbatim", "Orchestrator", "verbatim: [BLOCKING, verbatim] README.md line 1; "
                          "[NON-BLOCKING, verbatim] README.md line 2"))
        self.repo.write("README.md", "Readme, fixed\nand more\n")
        self.repo.commit("verbatim fixes")
        self.stamp("--verbatim")
        out = self.next()
        self.assertNotIn("mode decide", out, "a non-blocking finding applied verbatim needs no Lead decide launch")
        self.assertIn("Next: step 9 — PR approval", out)

    def test_a_non_blocking_finding_not_applied_verbatim_still_goes_to_the_lead(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 1", 60000),
                      row("8 Verbatim", "Orchestrator", "verbatim: [BLOCKING, verbatim] README.md line 1"))
        self.repo.write("README.md", "Readme, fixed\n")
        self.repo.commit("verbatim fix")
        self.stamp("--verbatim")
        out = self.next()
        self.assertIn("non-blocking findings (*Non-blocking findings*)", out)
        self.assertIn("Verdict line: quote it in the prompt, exactly as here; it ends the report", out)
        self.assertIn("`FIX:` in capitals whenever it orders a change", out)

    def test_a_fix_the_lead_orders_on_a_non_blocking_finding_comes_before_step_9(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 0 \\| NON-BLOCKING 1", 60000),
                      row("8 Decide", "Lead", "RESULT: DECIDED — FIX: Dev src/a.py names the constant", 9000))
        out = self.next()
        self.assertIn("Next: step 8 — the Lead ordered fixes: their owner, then steps 6–7 and a mandatory delta round",
                      out)
        self.assertIn("Launch: squad-dev, mode fix — when the Lead names the Dev", out)
        self.assertNotIn("step 9", out)
        self.repo.log(row("8 Fix", "Dev", "fixed", 9000, "sonnet/medium", continued=True))
        self.repo.write("src/a.py", "x = 3\n")
        self.repo.commit("fix")
        self.assertIn("the code changed since the gate stamp", self.next())
        self.stamp()
        self.assertIn("Review, delta round", self.next())

    def test_a_decision_without_a_fix_goes_on_to_step_9(self):
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: BLOCKING 0 \\| NON-BLOCKING 1", 60000),
                      row("8 Decide", "Lead", "RESULT: DECIDED — ISSUE: rename the constant later", 9000))
        self.assertIn("Next: step 9 — PR approval", self.next())

    def test_the_record_status_of_step_9_needs_no_delta_round(self):
        self.repo.write("docs/decisions/0001-topic.md", RECORD.format(status="Proposed"))
        self.repo.write("docs/decisions/README.md", RECORD_INDEX.format(status="Proposed"))
        self.implemented()
        self.stamp()
        self.repo.log(self.reviewed("8 Review", "VERDICT: APPROVE", 60000))
        self.assertIn("--verbatim (the record status needs no delta round)", self.next())
        self.repo.write("docs/decisions/0001-topic.md", RECORD.format(status="Accepted"))
        self.repo.write("docs/decisions/README.md", RECORD_INDEX.format(status="Accepted"))
        self.repo.commit("accept the record")
        out = self.next()
        self.assertIn("Only decision-record status lines and index rows changed since the stamp", out)
        self.stamp("--verbatim")
        self.assertIn("Next: step 9 — PR approval", self.next())
        self.stamp()
        self.assertIn("Next: step 9 — PR approval", self.next(), "a full stamp of the status alone needs none either")
        self.repo.write("docs/decisions/0001-topic.md", RECORD.format(status="Accepted").replace("This.", "That."))
        self.repo.commit("change the decision")
        self.stamp()
        self.assertIn("Review, delta round", self.next(), "a change beyond the status does")

    def test_a_removed_comment_line_that_looks_like_a_diff_header_is_no_status_change(self):
        self.repo.write("docs/decisions/0001-topic.md", RECORD.format(status="Proposed"))
        self.repo.write("src/a.sql", "select 1;\n-- drop me\n")
        old = self.repo.commit("record and query")
        self.repo.write("docs/decisions/0001-topic.md", RECORD.format(status="Accepted"))
        self.repo.write("src/a.sql", "select 1;\n")
        self.repo.write("src/b.sql", "select 2;\n++ kept\n")
        new = self.repo.commit("status and two comment lines")
        run = self.tool.Run(self.repo.root, self.folder, [], False)
        self.assertFalse(self.tool.record_status_only(run, old, new), "`--- drop me` is content, not a file header")
        self.assertIn("it starts the report", "\n".join(self.tool.launch(run, "squad-reviewer", "review", "8 Review", "x")))

    def test_a_row_without_a_verdict_line_names_the_format_and_the_correction(self):
        self.implemented()
        self.stamp()
        self.repo.log(row("8 Review", "Reviewer", "one non-blocking finding", 60000))
        out = self.next()
        self.assertIn("carries no VERDICT line", out)
        self.assertIn('--replace-last "Reviewer" --step "8 Review" --new-result', out)
        self.assertIn("`VERDICT: BLOCKING <n> | NON-BLOCKING <m> on <sha>`", out)
        tool = self.tool
        self.assertIsNone(tool.verdict_problem("squad-reviewer", "VERDICT: APPROVE on abc1234"))
        self.assertIn("on <sha>", tool.verdict_problem("squad-reviewer", "approve"))
        self.assertIn("OBJECTIONS <n> major", tool.verdict_problem("squad-devils-advocate", "two objections"))
        self.assertIsNone(tool.verdict_problem("squad-dev", "fixed"))
        self.assertIn("RESULT:", tool.verdict_problem("squad-lead", "decided"))
        self.assertTrue(tool.fix_ordered("RESULT: DECIDED — FIX: Dev src/a.py; ISSUE: none"))
        for declined in ("RESULT: DECIDED — no FIX needed, ISSUE: #3", "RESULT: DECIDED — do not fix now; ISSUE: #4",
                         "RESULT: DECIDED — accept, the prefix stays; a fix is not needed"):
            self.assertFalse(tool.fix_ordered(declined), declined)
        run = types.SimpleNamespace()
        prose = [tool.Row(5, "8 Verbatim", "8", "orchestrator", "verbatim: [BLOCKING, verbatim] docs/a.md — the "
                          "blocking sentence corrected; [NON-BLOCKING, verbatim] README.md, non-blocking wording")]
        run.of = lambda who, after=-1: prose
        self.assertEqual(tool.verbatim_findings(run, 0), (1, 1), "the word blocking in prose counts nothing")


class TestLaunches(NextTest):
    def test_the_cap_and_another_model_make_a_fresh_launch(self):
        self.implemented()
        self.repo.log(*[row("8 Fix", "Dev", "fixed", 9000, "sonnet/medium", continued=True) for _ in range(5)],
                      row("8 Review", "Reviewer", "VERDICT: APPROVE", 9000, launch="sonnet/medium"))
        out = self.next("--launch", "squad-dev", "fix")
        self.assertIn('the agent of "6 Implement" was continued 5 time(s) at 75,000 tokens', out)
        self.assertIn("short: the plan or task group", out)
        self.assertIn('"7 Fix" "Dev" "<the result>" --agent-id <id>\n', out, "logged without --continued")
        out = self.next("--launch", "squad-reviewer", "review")
        self.assertIn('ran on sonnet/medium, not opus/medium: never continued', out)
        self.assertEqual(run_main(self.tool, ["issue-5", "--launch", "squad-dev", "dance"])[0], 2)
        self.assertEqual(run_main(self.tool, ["issue-9"])[0], 1)

    def test_verdicts_are_read_from_the_logged_lines(self):
        tool, row_of = self.tool, self.tool.Row
        review = tool.review_verdict
        self.assertEqual(review(row_of(0, "8", "8", "squad-reviewer", "VERDICT: BLOCKING 2 \\| NON-BLOCKING 1")), (2, 1))
        logged = "VERDICT: BLOCKING 2 \\| NON-BLOCKING 1 on 0123456789abcdef0123456789abcdef01234567 — two defects"
        self.assertEqual(review(row_of(0, "8", "8", "squad-reviewer", logged)), (2, 1))
        self.assertEqual(tool.REVIEW.search(logged).group("sha"), "0123456789abcdef0123456789abcdef01234567")
        self.assertIsNone(tool.REVIEW.search("VERDICT: APPROVE; found on 0123abc").group("sha"))
        self.assertEqual(review(row_of(0, "8", "8", "squad-reviewer", "VERDICT: APPROVE all good")), (0, 0))
        self.assertEqual(review(row_of(0, "8", "8", "squad-reviewer", "VERDICT: NON-BLOCKING 3")), (0, 3))
        self.assertIsNone(review(row_of(0, "8", "8", "squad-reviewer", "VERDICT: APPROVED")))
        self.assertEqual(review(row_of(0, "8", "8", "squad-security", "VERDICT: CHANGES_REQUIRED")), (1, 0))
        self.assertEqual(tool.objections(row_of(0, "2", "2", "x", "VERDICT: OBJECTIONS 2 major, 0 minor")), (2, 0))
        self.assertEqual(tool.objections(row_of(0, "2", "2", "x", "VERDICT: NO OBJECTIONS")), (0, 0))
        self.assertEqual(tool.lead_result(row_of(0, "9", "9", "squad-lead", "RESULT: NOT APPROVED — x")), "NOT APPROVED")
        self.assertEqual(tool.mode_of("squad-lead", "2a", "2a Spec"), "spec")
        self.assertEqual(tool.mode_of("squad-tester", "8", "8 Fix tests"), "coverage")
        self.assertEqual(tool.mode_of("squad-security", "3", "3 Plan security"), "plan")


if __name__ == "__main__":
    unittest.main()
