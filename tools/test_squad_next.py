"""Unit tests for core/.squad/tools/squad-next.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
import sys
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
        self.assertIn("the Dev's edits alone", self.next())
        self.repo.write("specs/issue-5/plan.md", plan_text("tests"))
        out = self.next()
        self.assertIn("the Tester writes the plan's tests (tier tests: no Dev)", out)

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


class TestReviewAndAfter(NextTest):
    def test_the_review_set_follows_the_tier_and_a_round_follows_a_stamp(self):
        self.implemented()
        self.stamp()
        out = self.next()
        self.assertIn("Next: step 8 — Review, round 1 (full): squad-reviewer (mode review)", out)
        self.assertIn("No Security diff review on tier standard", out)
        self.assertNotIn("squad-security", out)
        self.repo.log(row("8 Review", "Reviewer", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 60000))
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
            self.repo.log(row("8 Review delta", "Reviewer", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 9000,
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
        self.repo.log(row("8 Review", "Reviewer", "VERDICT: BLOCKING 0 \\| NON-BLOCKING 2", 60000),
                      row("8 Security diff", "Security", "VERDICT: APPROVED", 60000))
        out = self.next()
        self.assertIn("non-blocking findings (*Non-blocking findings*)", out)
        self.repo.log(row("8 Decide", "Lead", "RESULT: DECIDED — linked issues", 9000))
        out = self.next()
        self.assertIn("Next: step 9 — PR approval", out)
        self.assertIn('"9 PR approval" Orchestrator "approved by checklist"', out)

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
        self.repo.log(row("8 Review", "Reviewer", "VERDICT: APPROVE", 60000))
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
        self.repo.log(row("8 Review delta", "Reviewer", "VERDICT: APPROVE", 9000, continued=True))
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
        log += row("11 Review delta", "Reviewer", "VERDICT: APPROVE", 9000, continued=True)
        self.assertIn("Next: step 9 — PR approval", self.next("--stdin", stdin=log), "the re-approval")
        log += row("11 PR approval", "Orchestrator", "approved by checklist")
        log += row("11 Ready for review", "Orchestrator", "marked ready for review")
        self.assertIn("Next: step 12 — Wrap-up", self.next("--stdin", stdin=log))
        log += row("12 Wrap-up", "Orchestrator", "no lessons")
        self.assertIn("squad-log.py --summary --stdin until it exits 0", self.next("--stdin", stdin=log))

    def test_a_verbatim_fix_needs_the_light_stamp_and_no_delta_round(self):
        self.implemented()
        self.stamp()
        self.repo.log(row("8 Review", "Reviewer", "VERDICT: BLOCKING 1 \\| NON-BLOCKING 0", 60000),
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
        self.assertIn("Gates due (tier patch/security): Format check, scope-check.py --tier patch", self.next())
        self.stamp()
        out = self.next()
        self.assertIn("Launch: squad-security, mode diff", out)
        self.assertIn("the first log.md row", out)
        self.repo.log(row("8 Security diff", "Security", "VERDICT: APPROVED", 9000))
        self.assertIn("Next: step 10 — Pull request", self.next(), "no step 9 on tiers docs and patch")


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
        self.assertEqual(review(row_of(0, "8", "8", "squad-reviewer", "VERDICT: APPROVE all good")), (0, 0))
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
