---
name: squad-spec
description: Use when the user wants to develop a new feature in this repository spec-driven with the squad — from a description, or from a GitHub issue the user calls a feature (implement feature 12) or that carries a feature/enhancement label (.squad/routing.md, Bug or feature). The Lead writes the spec first and the Devil's Advocate challenges it before any plan exists; then the Lead writes plan and tasks against the spec's acceptance criteria and picks a tier, Security reviews plan and diff of security-tier changes, Tester writes failing tests first, Dev implements until the Coverage gate passes, each member formats its files, Code Officer clears analyzer findings, Reviewer reviews, the PR is approved by checklist with the Lead deciding what is open, then a PR is opened.
---

# Squad Spec

Build a feature with the squad defined in `.squad/`, **spec first**: what the feature does for its users is
written, challenged and settled in `spec.md` before anyone plans how to build it. The spec is the only
source of the acceptance criteria; `plan.md` and `tasks.md` refer to them by id, and
`python3 .squad/tools/plan-check.py <folder>` checks that nothing is lost on the way. You are the
**orchestrator**, with the same role and rules as in the `squad-issue` skill (its introduction: you never do a
member's work, hand each member only what it needs, continue members for their next round, commits and
pushes, GitHub access, the Product Manager) — read it first. Steps 1–3 below replace its steps 1–3; steps
4–12 follow `squad-issue` with the changes listed after them.

## Steps 1–3

1. **Intake.** With a GitHub issue, read it in full, including comments and labels, and decide bug or feature
   as `.squad/routing.md`, *Bug or feature*, says — the user calling it a feature or invoking this skill
   settles it; a bug fix switches to `squad-issue` now. A closed issue: stop and report that. Run
   `git fetch origin main --tags` (`scope-check.py` compares against the local `origin/main`; the release tags
   tell `decision-check.py` and the Lead which decision records are released), then create the branch off the
   latest `main` (or the branch the session prescribes) and the work folder `specs/feature-<short-slug>/`
   (from an issue `specs/feature-<number>-<short-slug>/`) with `log.md` from `specs/_template/log.md`; commit
   and push. Log every row exactly as `squad-issue` step 1 says (`squad-log.py`, a launch row without metric
   options until its task notification is in).
2. **Spec.** Launch `squad-lead` in mode `spec` with the issue text (or the user's description) and the work
   folder. It writes `spec.md` from `specs/_template/spec.md` — problem, numbered scenarios and edge cases,
   non-functional requirements, the acceptance criteria, out of scope, open questions with their answers, the
   area documents the behavior will live in — and nothing about the implementation. It returns
   `RESULT: DONE`, `RESULT: NO CHANGE` (the feature exists already or contradicts an accepted decision: with an
   issue, handle it as `squad-issue` step 2 says — a proposed comment posted only after the user's
   confirmation; otherwise report it to the user) or `RESULT: ESCALATE` (an open question only the Product
   Manager can answer: relay it verbatim, then relaunch the Lead with the answer). Then run
   `python3 .squad/tools/plan-check.py <folder> --spec`; a finding goes back to the Lead (mode `revise`, the
   findings only), without a challenge.

   **Spec challenge.** Launch `squad-devils-advocate` in mode `spec` with the issue text and the work folder,
   for every feature. It challenges what the feature will do — a scenario or edge case the issue implies but
   the spec misses, a criterion that would not catch a wrong build, an answer to an open question that
   contradicts the code or an accepted record, a requirement that cannot be met as written, scope that is
   too wide — not how it is built. Minor objections only: append them verbatim to `spec.md` as a *Challenge
   notes* section; the Lead folds them in while it plans. A major objection: launch `squad-lead` in mode
   `revise` on the spec with all objections; it answers each in the spec's *Challenge* section and may narrow
   the scope, escalate or switch to `RESULT: NO CHANGE`. Run `plan-check.py --spec` again after a revision.
   One round, no veto. The spec's status becomes `Approved by Lead`, or `Approved by Product Manager` when an
   escalation settled it.
3. **Plan.** Launch `squad-lead` in mode `plan` with the work folder: it writes `plan.md` (the tier, the
   *Verified facts* with their evidence, the *Tests per criterion* for every criterion of the spec — never a
   copy of the criteria —, signatures, options, areas, documentation updates, decision records) and
   `tasks.md` (task groups, each naming the criteria it delivers and the tasks it waits for), with the agent
   file's model and effort like every other Lead launch (`--agent squad-lead`). A feature is never `docs` or
   `patch` and rarely `trivial`. Run `python3 .squad/tools/plan-check.py <folder>`; a finding goes back to the
   Lead (mode `revise`, the findings only) before anyone else reads the plan. Then:
   - **Plan challenge** only when the plan weighs options (its *Options considered* names an alternative, or
     it adds or extends a decision record): `squad-devils-advocate` in mode `plan` as `squad-issue` step 2
     says. The spec challenge already questioned what is built; a `security` plan without options gets its
     scrutiny from Security.
   - **Plan security review** on `security`: `squad-security` in mode `plan` reviews `spec.md` and `plan.md`
     together, in parallel with the plan challenge when there is one, and the loop of `squad-issue` step 3
     applies. Run `plan-check.py` again after every Lead revision.

## Steps 4–12: as in `squad-issue`, with these changes

- **Steps 4–6** run per task group from `tasks.md`, in the order its *Depends on* column allows; tick tasks off
  as they are done. Run Tester and Dev one after another, never in parallel (*Concurrency* in
  `.squad/routing.md`). Continue a member for the fix and delta rounds of its task group (*Continue a member*
  in `squad-issue`); the next task group starts with a fresh launch, so a member's context does not grow over
  the whole feature. A fix round for an earlier task group whose agent is no longer the member's last fresh
  launch is logged with `--continued-from "<step cell of that group's launch>"`. The Tester's tests first
  are the tests *Tests per criterion* names for the group's criteria.
- **Code-free changes:** a plan may declare steps 4, 5 and the *Coverage gate* not applicable as described in
  *Changes without production or test code* in `.squad/routing.md`; its *Verification without tests* section
  then says where each criterion of the spec is verified, and you log the skipped steps.
- **Decision records:** features usually involve real design choices, so expect a record in
  `docs/decisions/` (extend an existing unreleased record on the topic rather than adding a new one). The
  behavior the feature adds belongs in the area documents the spec names (`docs/areas/`), user-facing
  configuration in `README.md`, and a changed flow or guarantee in `docs/ARCHITECTURE.md` — not in `spec.md`,
  which leaves with the working record, nor in a decision record, which keeps only the why.
- **Step 8:** the Reviewer checks the diff against the spec's scenarios, edge cases and criteria, and that the
  area documents now say what the spec's *Area documents* section promised.
- **Step 10 — pull request:** the working record (`spec.md`, `plan.md`, `tasks.md`, `log.md`) is posted to
  the feature request issue if one exists (`Closes #<n>` in the PR), otherwise as the first comment on the PR
  right after opening it; the folder is removed before the PR as in `squad-issue`. The PR opens as a draft
  and is marked ready for review in step 11 as in `squad-issue` (*Draft until green*).
