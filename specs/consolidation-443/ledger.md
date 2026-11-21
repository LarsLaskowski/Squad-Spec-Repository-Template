# Consolidation ledger (#443)

Where every removed or reworded sentence of the rule files went, as `template-check.py` asks (AGENTS.md, *Writing
rules*). Rule files: 32,986 → 30,032 words (−9.0 %). Reasons moved out are in `docs/squad-rationale.md`, *Reasons
moved out in the second consolidation (#443)*. Two independent review passes (squad-reviewer discipline) found no
lost or changed rule; their four non-blocking findings are fixed (squad-lead.md documentation updates and CI/manual
criteria; routing.md *Plan challenge* "no stamp"; orchestration.md *Outside authors* comment content).

## First pass (commit 32a1afe)

- squad-issue — POINTER: orchestrator role sentence → routing.md introduction; the follow-up issues kept.
- squad-issue — TOOL: "Follow it, continuing exactly the agent it names (…)" → shortened; squad-next.py names the agent.
- squad-issue — TOOL: `--replace-last …` command → squad-next.py prints it for a row without a verdict line.
- squad-issue — POINTER: step 2 docs/patch route → routing.md *Tiers* rows.
- squad-issue — POINTER: step 6 reasons for the Tester's coverage pass → routing.md *Pipeline* row 6.
- squad-issue — POINTER: step 7 routing of gate results → routing.md *Pipeline* row 7 (Format restore: team.md *Format*).
- squad-issue — POINTER: step 8 blocking/non-blocking routing → *Loop limits*, *Non-blocking findings*.
- squad-issue — POINTER: step 9 checklist and launch condition → routing.md *PR approval*.
- squad-issue — POINTER/TOOL: step 12 lessons and summary exit codes → orchestration.md *Squad lessons*, `squad-log.py --help`.
- squad-issue — REASON: session-model cost, permalink re-typing → rationale.
- orchestration.md — TOOL: Managed/Marked/Seeded lists → summarized; `lesson-label.py` holds MANAGED/MARKED.
- orchestration.md — REASON: continuation token figures, Sonar lag → rationale.
- routing.md — REMOVED: list of orchestration.md section names → "a section named here that this file lacks is one of its sections".
- routing.md — POINTER: no-change comment wording → squad-lead.md *Output format*.
- routing.md — REMOVED: Loop limits "Plan challenge: at most one round, no veto" → stated in *Plan challenge*.
- squad-lead.md — POINTER: tier boundaries (patch/security, tests) → routing.md *Tiers*; no-change cases → *Outcome "no change"*; operator questions → *Operator environments and documented procedures*.
- squad-lead.md — REASON: `wc -w` dash counting → rationale.


## Group routing


No heading, `<!-- -->` marker, bold bullet name (*Manual criterion fails*, *New scope on the open PR*, …), tool name,
step-cell label (`7 Manual test`, `6 Private check`) or section name that another file points to was changed.

## Intro

- core/.squad/routing.md — REWORDED: "The pipeline is the same for bug fixes and features; only the input differs (a bug reported in a GitHub issue for `squad-issue`, a feature — described by the user or in a GitHub issue — plus `spec.md` for `squad-spec`; see *Bug or feature*)."
  → "Bug fixes (`squad-issue`) and features (`squad-spec`, which adds `spec.md`) run the same pipeline (*Bug or feature*)." Where a feature comes from is stated in *Bug or feature*.
- core/.squad/routing.md — REASON: "(subagents cannot talk to each other directly)"
  → The rule (the orchestrator passes documents between members) stays. Rationale (routing.md, intro): "The orchestrator carries every document between members because subagents cannot talk to each other directly."
- core/.squad/routing.md — REWORDED: "records every step and launch" / "Step numbers below are the ones the skills use." → "logs every step and launch" / "Step numbers are the skills'."

## Bug or feature

- core/.squad/routing.md — REWORDED: "A GitHub issue is either a bug fix (`squad-issue`) or a feature (`squad-spec`). The orchestrator decides which before step 1 — before any branch or work folder exists — and the first rule that applies wins:"
  → one sentence, same conditions.
- core/.squad/routing.md — REWORDED: rules 1 and 2 — dropped the repeated "makes it" and "GitHub" (issue type).
- core/.squad/routing.md — REWORDED: "**Otherwise** it is a bug fix with `squad-issue`. The issue text alone does not decide it: a feature request without label is labelled or called a feature by the user."
  → "**Otherwise** it is a bug fix. The issue text alone never makes it a feature: the user labels it or calls it one."
- core/.squad/routing.md — REWORDED: verification issue paragraph ("the skills stop at intake and the orchestrator launches no member … It hands the Product Manager a checklist … prepares what can be automated first … the Lead's result states the results, quoted, never inferred … files a bug issue for it, and the run documents only the result")
  → reordered into one flow; every element kept (label `Manual`, stop at intake, no member launched until results are in, automation prepared, checklist from the criteria, tier `docs` or higher for an area document, results quoted never inferred as exact edits, bug issue for wrong behavior, run documents only the result).
- core/.squad/routing.md — REWORDED: "runs with the skill its kind decides, but the Product Manager supplies the values before step 1; the orchestrator asks for them (*Escalation to the Product Manager*) and creates no branch until they are in."
  → "keeps the skill its kind decides, but the orchestrator asks for the values before step 1 and creates no branch until they are in". The back-pointer to *Escalation* is dropped; *Escalation to the Product Manager* lists this case and points here.

## Work folder

- core/.squad/routing.md — REMOVED: "`main` never contains `specs/` working records."
  → Folded into the preceding bullet ("only on the work branch, never on `main`").

## Scope of a product PR

- core/.squad/routing.md — REWORDED: "An issue or feature PR changes the product and its documentation only. It never touches the squad or the agent instructions: …" → one sentence; "never fixed in the product PR" → "not fixed in the product PR"; "reports any such file … ; a finding is blocking." → "reports such a file … as a blocking finding."
- core/.squad/routing.md — REWORDED: "One exception: … describe the product, not the squad. `.squad/tools/squad_settings.py` is the repository's own settings file and a product PR may change it too, with the files a tool writes from it (`SETTINGS_OUTPUTS` …) (…). A product PR updates them when the change itself makes them untrue — a new build command, a new security area, a new guarantee or coupling point — without an escalation, and the Reviewer treats a stale entry there like stale documentation."
  → "Exceptions: …" — same files, `SETTINGS_OUTPUTS`, the coverage-exclusion example, "a threshold is never lowered", the "without an escalation" update rule and the Reviewer's stale-entry rule all kept.

## Tiers

- core/.squad/routing.md — REWORDED: intro paragraph ("picks the tier on the change, not only on the paths it touches"; "in doubt about what the change does, the higher one … — not in doubt about the definition, which the table settles"; "at any point"; "when step 3 has not run and step 4 has not started — and does not re-run the plan challenge"; "(with the area that made it) and launches the Lead only when it leaves a decision open")
  → tighter wording, every condition kept.
- core/.squad/routing.md — REWORDED: "Security's diff review (step 8) is for tier `security` and for `patch/security` (the `patch` row) alone; below it …" → "Security reviews the diff (step 8) only on tier `security` and `patch/security`; below that …"; "(the `patch` row)" REMOVED (the table row is the next thing the reader sees).
- core/.squad/routing.md — REWORDED: `docs` row, *When*: "The diff changes only product documentation: …, and …" → "Only product documentation changes — …"; "(`scope-check.py --tier docs` checks it)" → "(`scope-check.py --tier docs`)".
- core/.squad/routing.md — TOOL: `docs` row, *Pipeline*: "`result.md` in the work folder, written verbatim with `squad-notes.py <folder> result`"
  → "written verbatim to `result.md` with `squad-notes.py`". `squad-next.py` (`quick_edits`) prints the exact command `python3 .squad/tools/squad-notes.py <folder> result --agent-id <id>`; `squad-notes.py` kind `result` writes `result.md` next to `log.md`. Rest of the cell reworded (orchestrator fixes a blocking finding, checked and delta-reviewed the same way) without change.
- core/.squad/routing.md — REWORDED: `patch` row, *When*: the separate sentence "`scope-check.py --tier patch` checks the line budget; the reviewer confirms that no logic changed and raises the tier otherwise." merged into the budget sentence; "a condition rewritten equivalently" → "an equivalently rewritten condition"; "no new dependency, permission or schema change" → "adds no dependency, permission or schema change".
- core/.squad/routing.md — REWORDED: `patch` row, *Pipeline*: "An edit to production code without one gets the one test the Lead names, written once by `squad-tester` (the only extra launch) on the unfixed head before the edits, its failure confirmed by the orchestrator as in step 5." → active voice, same content; "or on `patch/security`" → "on `patch/security`".
- core/.squad/routing.md — TOOL: `tests` row: "step 7 runs the *test code only* row of *Gates of a patch* and `scope-check.py --tier tests`" → "… of *Gates of a patch* (`gate-stamp.py`)". `gate-stamp.py` runs `scope-check.py --tier tests` for tier `tests` (its docstring and `due_gates`). "(`scope-check.py --tier tests` checks it)" → "(`scope-check.py --tier tests`)".
- core/.squad/routing.md — REMOVED: `trivial` row "(no tests-first)" and "rather than the Dev" → repeat "Steps 4 and 5 skipped" / "names the Tester" in other words.
- core/.squad/routing.md — POINTER (same file): `security` row, *Pipeline*: "the plan challenge (*Plan challenge*) and the Security plan review run in parallel, answered by one Lead revision" → "plan challenge and Security plan review in parallel (*Plan challenge*)". *Plan challenge* (last paragraph) states the single Lead revision and the one delta confirmation completely.

## Gates of a patch

- core/.squad/routing.md — REWORDED: "runs the checks its files need and nothing else; the complete analysis, and for a `patch` without production code the full suite and the overall coverage figure, are CI's job …" → "runs only the checks its files need; the complete analysis — and, without production code, the full suite and the overall coverage figure — is CI's job …".
- core/.squad/routing.md — TOOL: "A gate the row names that the stack does not have (`stack.md` lists no *Test (project)*) is replaced by the next broader one (*Test*)."
  → folded into the `gate-stamp.py` sentence: "and replaces a gate the stack lacks by the next broader one (*Test* for *Test (project)*)". `gate-stamp.py` runs *Test* where `stack.md` lists no *Test (project)* (docstring: "where `stack.md` lists no *Test (project)*, *Test* runs instead, the next broader gate").
- core/.squad/routing.md — TOOL/REASON: production-code row "— not *Test (project)*: it writes no coverage report, and the gate reads the reports of the full run, the overall figure included" → "— not *Test (project)*". `gate-stamp.py` leaves *Test (project)* out where *Test with coverage* runs. Rationale (routing.md, *Gates of a patch*): "A patch with production code runs *Test with coverage*, not *Test (project)*: *Test (project)* writes no coverage report, and the *Coverage gate* reads the reports of the full run, the overall figure included."

## Changes without production or test code

- core/.squad/routing.md — TOOL: "the orchestrator logs the skipped steps with a pointer to it" → "`squad-next.py` prints the row that logs the skipped steps". `squad-next.py` prints "the row to log (… the steps a plan without production or test code skips …)" (docstring).
- core/.squad/routing.md — TOOL: "step 7 runs every gate but the *Coverage gate* (a branch of Markdown files only: *Format check* alone, `gate-stamp.py`)" → "step 7 runs the gates without the *Coverage gate* (`gate-stamp.py`)". `gate-stamp.py`: "a plan with *Verification without tests* leaves out the *Coverage gate*, and a branch that changes only Markdown files outside `specs/` runs *Format check* and `scope-check.py` alone".
- core/.squad/routing.md — REWORDED: "in `plan.md`, under *Verification without tests*," / "a build of the image" / "plus the Tester's share …, in mode `coverage` after the Dev" / "exists, covers every criterion … — otherwise" → same content, tighter order.

## Dry-run artifacts

- core/.squad/routing.md — TOOL: "(`git-guard.py` allows a member only the forms of `git apply` that read a patch)"
  → removed; the rule "checks it with `git apply --check`" stays, and `git-guard.py` refuses any other `git apply` form from a member.

## Criteria verified only in CI

- core/.squad/routing.md — REWORDED: "A criterion that only CI can verify in full — … — is still checked as far as the sandbox allows, before the review. A change that touches an input …" → parentheses instead of dashes, "A change to an input …"; "project or manifest files" → "manifests"; "the plan names it as the criterion's verification with the Dev as its owner" → "…, owned by the Dev".
- core/.squad/routing.md — REASON: "which reproduces the Dockerfile's own order (manifests, restore, then the sources, build without a restore)"
  → what the *Image build check* does is defined by the command in `.squad/stack.md`; the rule that a full-tree build does not count ("it restores with every source present") stays. Rationale (routing.md, *Criteria verified only in CI*): "The *Image build check* reproduces the Dockerfile's own order — manifests, restore, then the sources, a build without a restore — so it fails where the image build fails; a build from the full working tree restores with every source present and hides that failure."
- core/.squad/routing.md — REWORDED: "A criterion tested by hand on a build before the PR approval (step 9) — a Product Manager's manual test of the change, say — names in the plan the build it runs on: …, for which the plan asks for an *Early draft PR* (without one, no CI build of the change exists before step 10)." → "A criterion tested by hand before step 9 (a Product Manager's manual test, say) names in the plan its build: …, which needs an *Early draft PR* (no CI build exists before step 10 otherwise)."
- core/.squad/routing.md — REWORDED: "When the plan asks the Product Manager to build the artifact" → "When the plan has the Product Manager build the artifact"; "(`orchestration.md`, *An artifact …*)" → "(*An artifact …*)" — the intro says a section named here that this file lacks is one of `orchestration.md`'s.
- core/.squad/routing.md — REASON: "so a document it corrects is reviewed once"
  → the rule (manual test on the stamped head before step 8's review set) stays. Rationale (routing.md, *Criteria verified only in CI*): "The manual test runs before the step-8 review set so that a document it corrects is reviewed once, not twice."
- core/.squad/routing.md — REWORDED: "A `manual:` check that names a member of the step-8 review set … runs in that member's round instead" → "… of that review set … runs in that member's round"; "`squad-next.py` names the launch" → "names its launch"; "the input's location is handed over, never committed, copied or quoted" → "… handed over — the input is never committed, copied or quoted" (clarifies that the input, not the location, is never committed).

## Operator environments and documented procedures

- core/.squad/routing.md — REWORDED: "not against the session's" → "not the session's".
- core/.squad/routing.md — REWORDED: Target host: "(tools such as `git`, network access to which hosts, DNS, the console it is used from, the order of steps the operator will paste) … The Devil's Advocate checks the plan against that list." → "(tools such as `git`, the hosts it reaches, DNS, its console, the order in which the operator pastes the steps) … against which the Devil's Advocate checks the plan."
- core/.squad/routing.md — REASON: Third-party pages: "rests on labels and layouts that change without notice"
  → the rule (the spec asks the Product Manager how far the document may rest on them) stays. Rationale (routing.md, *Operator environments and documented procedures*): "A document that leads the operator through another provider's page or console rests on labels and layouts that change without notice, so the Product Manager decides how far it may rest on them."
- core/.squad/routing.md — REWORDED: Dry run: "and lists the hosts and software versions the run needs (for example …)" → "with the hosts and software versions it needs (…, say)"; "Every statement … that no run has shown is a row …, `unverified` with the dry run as its owner — …; the dry run confirms or corrects each, and a statement it could not show is narrowed to what it showed or left out." → "Each statement … no run has shown is a row …, `unverified`, owned by the dry run — …; the dry run confirms or corrects it, or it is narrowed to what the run showed or left out."
- core/.squad/routing.md — POINTER (same file): Dry run: "When an external page cannot be reached from the session, the plan asks the Product Manager to confirm those statements in the earliest real run, not at the end."
  → *Pages the session cannot open* (same file) states it completely: the plan names who opens the pages the session cannot (the Product Manager or a stated stand-in) and when — in the earliest real run when there is a dry run.
- core/.squad/routing.md — REWORDED: Shell procedures: "from that list" → "from it"; "so that a half-finished state can still be run, is a defect of the design" → "leaving a half-finished state that can still be run, is a design defect".

## Pages the session cannot open

- core/.squad/routing.md — REWORDED: "the ones" → "those"; "when there is a dry run" → "if there is a dry run"; "as `unopened`, with the error it got, instead of judging it" → "as `unopened` with the error it got, without judging it".

## Code a unit test cannot cover

- core/.squad/routing.md — REWORDED: "in every place that computes it (… , and `COVERAGE_EXCLUDES` … includes the file — the product PR edits that file itself; …) … and those no local gate reports arrive in step 11" → "everywhere it is computed (…; `COVERAGE_EXCLUDES` … includes the file, edited by the product PR itself; …) … and findings no local gate reports arrive in step 11".

## Early draft PR

- core/.squad/routing.md — REWORDED: "so a PR opened in step 10 comes too late for a change whose **CI-only criteria** or manual test … or **dry run** …" → "so step 10's PR comes too late …"; "For such a change the plan says so" → "Its plan says so".
- core/.squad/routing.md — TOOL: "(`create-pr` step 8, `specs/` still in the diff, no working record comment yet), then waits for CI and reads `sonar-check.py pr <n>` before step 8; findings are worked as in step 11."
  → "`specs/` still in the diff, and works the findings of CI and `sonar-check.py pr <n>` before step 8 as in step 11 (`squad-next.py` prints the steps)". `squad-next.py` (`early_pr`) prints: "open the PR as a draft as create-pr step 8 says, without its review loop (specs/ stays, the working record waits for step 10), subscribe to its activity, wait for CI and run sonar-check.py pr <number> before step 8; findings are worked as in step 11".
- core/.squad/routing.md — REASON: "every push to an open PR runs all of CI again, and step 11 reads the analysis anyway"
  → the rule "The *Sonar gate* alone is no reason for an early PR." stays. Rationale (routing.md, *Early draft PR*): "The *Sonar gate* alone does not justify an early draft PR: every push to an open PR runs all of CI again, and step 11 reads the analysis anyway."
- core/.squad/routing.md — POINTER (same file): "The dry run runs on that head, before the documentation is reviewed." → "The dry run runs on that head." The *Dry run* bullet of *Operator environments and documented procedures* states "**before** the documentation is reviewed".
- core/.squad/routing.md — REWORDED: "additionally" → "also".

## Pipeline

- core/.squad/routing.md — REWORDED: step 2 "where *Spec approval* in `orchestration.md` calls for it" → "where *Spec approval* calls for it" (intro rule); "One plan challenge when *Plan challenge* calls for it, routed as that section says" → "… calls for it" (the section reference already says where).
- core/.squad/routing.md — REWORDED: step 6 "then the plan's doc updates, area documents included, written by the Dev against the code as built" → "then the Dev writes the plan's doc updates, area documents included, against the code as built".
- core/.squad/routing.md — TOOL: step 7 "which runs the tier's gates (*Format check*, *Analyzer gate*, *Test with coverage*, *Coverage gate*, `scope-check.py`; `patch`: *Gates of a patch*) and, in tiers `trivial`, `standard` and `security`, `figure-check.py`, which is no gate,"
  → "which runs the tier's gates (`patch`: *Gates of a patch*) and `figure-check.py` (no gate)". `gate-stamp.py` decides the gate list per tier (`due_gates`; docstring lists *Format check*, *Analyzer gate*, *Test with coverage*, *Coverage gate*, `scope-check.py` for `trivial`/`standard`/`security`) and runs `figure-check.py` only in `FIGURE_TIERS = ("trivial", "standard", "security")`; `squad-next.py` prints "Gates due (tier …)" before the stamp.
- core/.squad/routing.md — TOOL: step 7 "The orchestrator clears a *Format check* failure itself (*Format*, then `git restore` of every file outside the change)"
  → "(`squad-next.py` prints how)". `squad-next.py` (`failed_gates`) prints "run *Format*, git restore -- every file it changed outside the change, commit, stamp again".
- core/.squad/routing.md — POINTER (same file): step 7 "(structural items go to the Dev or Tester)" → "(*Loop limits*)". *Loop limits*, *Code check needs a structural change*, states it completely (edit reverted, item to the Dev or, for tests, the Tester, code check again, not counted).
- core/.squad/routing.md — REWORDED: step 7 "documentation that still states" → "still stating"; step 8 "the code SHA and the gate output of the stamp of step 7 …; later commits during the round" → "the code SHA and gate output of step 7's stamp …; commits during the round".
- core/.squad/routing.md — TOOL: step 12 "Squad lessons checked against the candidates and filed, … the run metrics of `squad-log.py --summary` (exit 0), then the output of `session-usage.py` headed "Session usage", appended …"
  → "Squad lessons filed …; the output of `squad-log.py --summary` (exit 0), then of `session-usage.py`, appended … exactly as printed (`squad-next.py` names the headings) …". `squad-next.py` prints "check the log for the lesson candidates (…*Squad lessons*), file the lessons …" and "append its tables to the working record under "Squad run metrics", then session-usage.py under "Session usage"". The "never a screenshot or a figure typed from `/usage`" rule stays.

## PR approval

- core/.squad/routing.md — TOOL: "runs `decision-check.py`, commits and stamps that commit with `gate-stamp.py --verbatim` (bookkeeping, like `log.md`: no delta round)"
  → "(bookkeeping like `log.md`, no delta round; `squad-next.py` prints the commands, the stamp with `gate-stamp.py --verbatim`)". `squad-next.py` (`approval`) prints "set each Proposed decision record of this change and its index row to Accepted, run decision-check.py, commit, and stamp that commit with gate-stamp.py <folder> --verbatim (the record status needs no delta round)".
- core/.squad/routing.md — REWORDED: "The Lead is launched in mode `approve-pr` only when a decision is open: … The orchestrator lists these points one by one, and they are all the Lead decides there (…)" → "It launches the Lead in mode `approve-pr` only for an open decision — … — listing each point; the Lead decides only those (…)"; "Otherwise "approved by checklist" is logged" → "Otherwise it logs "approved by checklist"".
- core/.squad/routing.md — POINTER (same file): "non-blocking findings are decided in step 8 (*Non-blocking findings*)" → removed; *Non-blocking findings* states "decided by the Lead in step 8 … Step 9 does not take them up again."
- core/.squad/routing.md — REWORDED: "Once that round is clean, the checklist runs again; the Lead's `approve-pr` agent is continued only for a point the fix leaves open, and a point it settled is not listed again." → "…; then the checklist runs again, and the Lead's `approve-pr` agent is continued only for a point the fix left open." "A settled point is not listed again" follows from "continued only for a point left open"; `squad-next.py` prints the same ("once that round is clean the checklist runs again, and the Lead's approve-pr agent is continued only for a point the fix leaves open").

## Plan challenge

- core/.squad/routing.md — REMOVED: "never a plan of tier `docs`, `patch`, `tests` or `trivial`"
  → the preceding clause already limits the challenge to every `security` plan and some `standard` plans; the `docs`, `patch`, `tests` and `trivial` rows of *Tiers* each say "no plan challenge"; `plan-check.py` prints the verdict.
- core/.squad/routing.md — REWORDED: "`plan-check.py` prints the verdict with its reason (…)" → "prints the verdict (…)" — the quoted output (`due — …`) shows the reason.
- core/.squad/routing.md — REASON: "so the orchestrator routes without judgment:" → "and the orchestrator routes by that rank:". Rationale (routing.md, *Plan challenge*): "Objections are ranked `major` or `minor` so that the orchestrator can route them without judgment."
- core/.squad/routing.md — REWORDED: minor objections: "with `squad-notes.py`, which copies them from the member's report, never retyped" → "verbatim … with `squad-notes.py`, never retyped" (`squad-notes.py` copies from the member's report: its docstring).
- core/.squad/routing.md — REWORDED: Security notes: "except a note that leaves the plan a choice (…): the Lead decides it in mode `revise` …; so is a note Security recommends to `fix now`" → "except a note that leaves the plan a choice (…) or that Security recommends to `fix now`: the Lead decides it in mode `revise` …".
- core/.squad/routing.md — REASON: "since Dev and Tester may not edit the plan" (Security notes bullet) and "since Dev and Tester may not edit those documents" (exact-edit bullet)
  → both removed; the routing (Lead decides / orchestrator applies) stays. Rationale (routing.md, *Plan challenge*): "The Lead decides a Security note that leaves a choice or asks to fix now, and the orchestrator applies an exact edit of `plan.md` or `spec.md`, because Dev and Tester may not edit those documents."

## Outcome "no change"

- core/.squad/routing.md — REASON: "(a public statement on the issue)" → removed; the rule (post only after the Product Manager's confirmation) stays. Rationale (routing.md, *Outcome "no change"*): "The proposed comment is a public statement on the issue, so it is posted only after the Product Manager has confirmed it."
- core/.squad/routing.md — REWORDED: "shows the comment to the Product Manager and posts it only after confirmation …. It removes the work folder with a commit and pushes" → "posts the comment only after the Product Manager has confirmed it …, then removes the work folder in a commit and pushes".

## Loop limits

- core/.squad/routing.md — REWORDED: Plan check: "(mode `revise`, …) at most twice per document; findings left after that go to the Lead in mode `decide`" → "in mode `revise` (…) at most twice per document, then to the Lead in mode `decide`".
- core/.squad/routing.md — POINTER (same file): Plan ↔ Security: "when step 3 runs, the first revision answers the plan challenge and the first `CHANGES_REQUIRED` together" → removed; *Plan challenge* (last paragraph) states it completely (one Lead revision answers the major objections and the `CHANGES_REQUIRED` findings together, then one Security delta confirmation).
- core/.squad/routing.md — REWORDED: Plan ↔ Security: "the Lead decides: narrow …, split …, escalate …, or — when the remaining defect is … — accept and fix it without an escalation, followed by exactly one Security delta confirmation of the fix (a further rejection then goes to the Product Manager)" → "the Lead narrows …, splits …, escalates …, or — without an escalation — accepts and fixes the remaining defect if it is …; exactly one Security delta confirmation of the fix follows, and a further rejection goes to the Product Manager." All three defect kinds and the "measured" condition kept.
- core/.squad/routing.md — REWORDED: Review ↔ Dev: "each reviewing only the delta" → "each on the delta only"; "A round counts per review round that returned blocking findings" → "Rounds count per review round with blocking findings".
- core/.squad/routing.md — REWORDED: Existing tests: "these are the only cases in which the Dev edits test code" → "in no other case does the Dev edit test code".
- core/.squad/routing.md — REWORDED: Manual criterion fails: "a manual test that fails" → "failing"; "to the same plan" → "to the plan"; "a further implement round of the Dev and the Tester's coverage pass" → "another Dev implement round and the Tester's coverage pass"; "and ends with" → ", ending with".
- core/.squad/routing.md — REWORDED: Dev ↔ Tester: "not changed silently" → "never changed silently"; "Not counted against a loop limit." → "Neither counts against a loop limit." (the original sentence followed both cases).
- core/.squad/routing.md — REWORDED: Code check / Coverage gate fails: "(or Tester for tests)" → "(tests: the Tester)"; "whose decision is recorded in `log.md`. A whole such file that the plan did not list … is a plan defect the Lead records with the decision." → "its decision recorded in `log.md`; a whole such file the plan did not list … is a plan defect it records with the decision."
- core/.squad/routing.md — REWORDED: New scope: "The Lead decides, recorded in `log.md`: …, or this change grows, and then the spec gets …" → "…, which decides, recorded in `log.md`: …, or the change grows — the spec gets …".

## Escalation to the Product Manager

- core/.squad/routing.md — REWORDED: "The Lead escalates only when it cannot decide responsibly on its own: an ambiguous requirement (a reader of an external format without a real sample … is one — it asks for the sample, …; a sample the PM supplies …), a product decision (…), or a loop limit …" → the three triggers first, then the external-format case as its own sentence ("A reader of an external format without a real sample … is an ambiguous requirement: the Lead asks for the sample, …"). Every element of the sample handling kept.
- core/.squad/routing.md — REWORDED: "Follow-up issues the Lead decides on are created by the orchestrator and listed in the PR under Next Steps." → "The orchestrator creates the follow-up issues the Lead decides on and lists them in the PR under Next Steps."
- core/.squad/routing.md — REWORDED: the list of cases the orchestrator involves the Product Manager in: each case now named by its section first ("*Bug or feature* (an issue labelled both, values only the Product Manager can produce); *Spec approval*; … *A denied measurement* (a download a member was denied); …"); "in `orchestration.md`" dropped (intro rule); "the confirmation of statements no run has shown" → "statements no run has shown". Every case kept.

## Non-blocking findings

- core/.squad/routing.md — REWORDED: "is decided by the Lead in step 8, in mode `decide` (…), before that round's fix round: a fix it orders goes to its owner together with the round's blocking findings, and one delta round covers both; a linked issue is opened by the orchestrator." → "the Lead decides in step 8 in mode `decide` (…), before that round's fix round: a fix it orders goes to its owner with the round's blocking findings, one delta round covering both; the orchestrator opens a linked issue."

## Rationale entries for docs/squad-rationale.md (collected from the REASON lines above)

- routing.md, intro: The orchestrator carries every document between members because subagents cannot talk to each other directly.
- routing.md, *Gates of a patch*: A patch with production code runs *Test with coverage*, not *Test (project)*: *Test (project)* writes no coverage report, and the *Coverage gate* reads the reports of the full run, the overall figure included.
- routing.md, *Criteria verified only in CI*: The *Image build check* reproduces the Dockerfile's own order — manifests, restore, then the sources, a build without a restore — so it fails where the image build fails; a build from the full working tree restores with every source present and hides that failure.
- routing.md, *Criteria verified only in CI*: The manual test runs before the step-8 review set so that a document it corrects is reviewed once, not twice.
- routing.md, *Operator environments and documented procedures*: A document that leads the operator through another provider's page or console rests on labels and layouts that change without notice, so the Product Manager decides how far it may rest on them.
- routing.md, *Early draft PR*: The *Sonar gate* alone does not justify an early draft PR: every push to an open PR runs all of CI again, and step 11 reads the analysis anyway.
- routing.md, *Plan challenge*: Objections are ranked `major` or `minor` so that the orchestrator can route them without judgment.
- routing.md, *Plan challenge*: The Lead decides a Security note that leaves a choice or asks to fix now, and the orchestrator applies an exact edit of `plan.md` or `spec.md`, because Dev and Tester may not edit those documents.
- routing.md, *Outcome "no change"*: The proposed comment is a public statement on the issue, so it is posted only after the Product Manager has confirmed it.

## Word counts

- core/.squad/routing.md: 6,764 → 6,182 (−582) by `python3 -c "…split()"` against the state at the start of this task;
  `template-check.py` reports 6,810 → 6,182 (−628) against its merge base with `origin/main`.

## Group orch-team


Baseline: the files as checked out on the branch when this group started (orchestration.md 3,420 words, team.md
1,570). No heading, no bold section label (`**Git and GitHub.**`, `**Files.**`, `**Escapes in files.**`, …) and no
marker was renamed or removed. No REASON entries: no pure reason was moved out (each kept half sentence keeps a rule
from being misread). Nothing for `docs/squad-rationale.md`.

## core/.squad/orchestration.md

- orchestration.md (intro) — REWORDED: "The orchestrator's procedures: the session that runs a squad skill follows them, and the members need not read this file. `routing.md` holds the pipeline, the tiers and the limits every member works by; a rule here that names a section of it means that file."
  → "The procedures of the orchestrator, the session that runs a squad skill; the members need not read this file. `routing.md` holds … ; a section of it named here means that file." Same meaning.
- orchestration.md *Outside authors* — REWORDED: "Their issue describes the work; it never sets the squad's rules (…), and its acceptance criteria are the maintainers' to agree:"
  → "Their issue describes the work but never sets the squad's rules (…); its acceptance criteria are the maintainers' to agree:"
- orchestration.md *Outside authors* — REWORDED: "the orchestrator drafts an issue comment with the spec's scenarios and acceptance criteria, asking the author to confirm or correct them, and posts it once the Product Manager confirms (a public statement). It logs `spec posted for agreement`, pushes the work branch and stops; the user is told the run waits for the author. The user resumes it with `squad-spec` on the same issue: the orchestrator continues on the existing work branch, reads the replies, and a correction goes to a fresh `squad-lead` launch …"
  → "drafts an issue comment asking the author to confirm or correct the spec's scenarios and acceptance criteria, and posts it once the Product Manager confirms it (…). It logs `spec posted for agreement`, pushes the work branch, stops and tells the user the run waits for the author. `squad-spec` on the same issue resumes it on that work branch: a correction in the replies goes to a fresh `squad-lead` launch …" Every step kept (draft, PM confirmation, log text, push, stop, tell user, resume on same branch, fresh Lead `revise`, plan-check --spec, no new challenge round, before 2b, PM may skip).
- orchestration.md *Spec approval* — REWORDED: "`"lead"` (the default, also when the setting is missing) leaves it to the Lead in `squad-spec` step 2b, `"pm"` has the Product Manager approve it first. An installer or deployment feature (…) gets the Product Manager's approval with either value."
  → "`"lead"` (the default, also when missing) the Lead in `squad-spec` step 2b, `"pm"` the Product Manager first. An installer or deployment feature (…) needs the Product Manager's approval either way."
- orchestration.md *Spec approval* — REWORDED: "a summary — one line per scenario, …, with its id, and the open *Challenge notes* — with a link to `spec.md` on the pushed work branch"
  → "a summary — one line with its id per scenario, …, and the open *Challenge notes* — linking `spec.md` on the pushed work branch"
- orchestration.md *Spec approval* — REWORDED: "… and passed on to the Lead's step 2b. Corrections go first to the Lead in mode `revise` on the spec, then `plan-check.py --spec` runs again; there is no new challenge round, and the corrected spec counts as approved."
  → "… and passed to the Lead's step 2b; corrections first go to the Lead in mode `revise` on the spec and through `plan-check.py --spec` again, with no new challenge round, and the corrected spec counts as approved."
- orchestration.md *Spec approval* — REWORDED: "An answer that cannot come in this session makes the run wait as for an outside author: log `spec waits for approval`, push the work branch and stop; `squad-spec` on the same issue or branch resumes it."
  → "An answer that cannot come in this session: log `spec waits for approval`, push the work branch and stop; `squad-spec` on the same issue or branch resumes the run." ("as for an outside author" dropped: the steps that follow are the whole procedure; the section already says it runs like *Outside authors*.)
- orchestration.md *Spec approval* — REWORDED: "the draft comment of *Outside authors* goes with the summary: an approval without corrections confirms both, and after a correction the comment is drafted again from the revised spec."
  → "the summary goes with the draft comment of *Outside authors*: an approval without corrections confirms both, and a correction has the comment drafted again from the revised spec."
- orchestration.md *Template-managed files* — REWORDED: "come from the template repository and are refreshed with its `adopt-template` skill" → "come from the template repository, refreshed by its `adopt-template` skill".
- orchestration.md *Squad lessons* — REWORDED: "labelled by where it can actually be fixed. The label comes from the files the lesson's fix changes: `python3 .squad/tools/lesson-label.py <path> … --issue <number>` prints it and the title, never chosen by hand."
  → "labelled by where it can actually be fixed: `python3 .squad/tools/lesson-label.py <path> … --issue <number>` prints the label and the title from the files the lesson's fix changes; neither is chosen by hand."
- orchestration.md *Squad lessons* — REWORDED: "Before "no lessons", the orchestrator compares that answer with its log; each of these **candidates** is a lesson unless …"
  → "Before "no lessons", the orchestrator checks its log for these **candidates**; each is a lesson unless …"
- orchestration.md *Continuing a member* — REWORDED: "A fix, delta or `revise` round of the same member within the same run continues that member's last launch (…) with the findings and the new head SHA, instead of a fresh launch; so do … (the member's last agent of the same mode, …)."
  → "A fix, delta or `revise` round of a member within a run continues that member's last launch (…) with the findings and the new head SHA; so do … (the member's last agent of that mode, …)." ("instead of a fresh launch" is what "continues" means.)
- orchestration.md *Continuing a member* — REWORDED: "The first launch of any other mode is fresh, and so is a launch after a session restart (the agent id is gone) or after one that ended on an API error. An agent continued five times or from 250,000 reported tokens on, one that ran on another model than *Launch model* names, or one already continued in another mode, gets a fresh launch with a short hand-over — the plan or task group, what the earlier rounds settled, the open findings and the head SHA."
  → "Fresh are the first launch of any other mode and a launch after a session restart (the agent id is gone) or after one that ended on an API error; so is, with a short hand-over (the plan or task group, what the earlier rounds settled, the open findings and the head SHA), the next launch of an agent continued five times or from 250,000 reported tokens on, run on another model than *Launch model* names, or already continued in another mode." All conditions, the two numbers and the hand-over contents kept; `squad-next.py` decides and prints all of them (CONTINUATION_CAP, FRESH_TOKENS, model and mode checks, restart/API-error note).
- orchestration.md *Continuing a member* — REWORDED: "`squad-next.py` names … or why it is fresh: keep the agent id of every fresh launch, since the agent it names is not always the member's last one. What a continued member may do is in `team.md` (*Shared rules*)."
  → "… or why it is fresh; keep the agent id of every fresh launch, since that agent is not always the member's last one. What a continued member may do: `team.md` (*Shared rules*)."
- orchestration.md *Commits* — REWORDED: "… after every further completed step. They never contain secrets." → "… after every further completed step, never with secrets."
- orchestration.md *Commits* — REWORDED: "a detached HEAD is switched back to it first (`git switch <branch>`, then `git merge --ff-only <sha>` for commits made on the detached HEAD)" → "a detached HEAD is switched back first (`git switch <branch>`, then `git merge --ff-only <sha>` for commits made on it)".
- orchestration.md *Commits* — REMOVED: ", not a success" (in "a push that did not move the branch is a failure, not a success") → repeats "is a failure".
- orchestration.md *Commits* — REWORDED: "so edits are batched and committed once per round, and a tests-first commit … is pushed only together with the implementation" → "so edits are committed once per round, and … is pushed only with the implementation".
- orchestration.md *Commits* — REWORDED: "a document in the middle of a rewrite — ends its subject with `[skip ci]`, so CI and the code analysis do not run on a head that is unfinished by design." → "a document mid-rewrite — … so CI and the code analysis skip a head unfinished by design."
- orchestration.md *Commits* — REWORDED: "The commits that count never carry it: a finished step's commit (`gate-stamp.py` refuses to stamp a code commit that carries it), the commit of a stamp's row, so CI runs on the code a review round reviews, the commit that opens or updates the PR for a fix round, and the head the PR is marked ready on; GitHub reads only the head commit of a push, and a required check never reports on a skipped head, so the last commit before the PR is marked ready runs CI."
  → "The commits that count never carry it (`gate-stamp.py` refuses to stamp a code commit that does): a finished step's commit, the commit of a stamp's row (so CI runs on the code a review round reviews), the commit that opens or updates the PR for a fix round, and the head the PR is marked ready on, since GitHub reads only the head commit of a push and a required check never reports on a skipped head." ("so the last commit before the PR is marked ready runs CI" restated the list item "the head the PR is marked ready on".)
- orchestration.md *The stop hook* — REWORDED: "… unpushed work — and it asks **once per stop**: ending the turn again after answering it is not blocked. The hook never decides when a commit is made:"
  → "… unpushed work, **once per stop** (ending the turn again after answering it is not blocked); it never decides when a commit is made:"
- orchestration.md *The stop hook* — REWORDED: "Outside a review round and a merge, satisfy it with an interim commit (…), also while a PR is open;" → "Outside a review round and a merge, also with a PR open: an interim commit (…);"
- orchestration.md *The stop hook* — REWORDED: "(…; a commit that touches only `specs/` is fine) and while a merge waits for a conflict resolution, do not commit: …" → "(…; a `specs/`-only commit is fine) or a merge waits for a conflict resolution: no commit; …"; "A head that was pushed half-finished … is logged as work in progress, and neither CI …" → "A head pushed half-finished … is logged as work in progress; neither CI …".
- orchestration.md *The stop hook* — REWORDED: "… reclaimed while it waits. The commit touches only `specs/`, so it needs no new stamp or review round." → "… reclaimed while it waits; a `specs/`-only commit needs no new stamp or review round."
- orchestration.md *Draft until green* — REMOVED: "It stays a draft while anything on its head is still to be fixed," → implied by "marked ready … only when all of this holds on the current head", which stays (sentence now: "is opened as a **draft** (`draft: true`) and marked ready for review (…) only when all of this holds on the current head:").
- orchestration.md *Draft until green* — REWORDED: "- the pull request merges cleanly into its base branch (*Merge conflicts* below);" → "- it merges cleanly into its base branch (*Merge conflicts*);".
- orchestration.md *Draft until green* — TOOL: "(a passed gate with new issues is still rework)" → `sonar-check.py` (`report()`) exits 1 (FAIL) on any open issue or hotspot even when the quality gate is OK, and the bullet keeps "exits 0 … with **no new issue** and no hotspot to review".
- orchestration.md *Draft until green* — TOOL/REWORDED: "PENDING (exit 3) means a newer analysis than the shown one is still to come: wait and run it again, …" → "PENDING (exit 3) is no pass: wait and run it again, …" — `sonar-check.py` prints the meaning itself ("PENDING says that a newer analysis than the one shown is still to come, not that the head has a problem: wait and run again. Still PENDING after every CI check of this head finished: the analysis cannot be read, and the PR stays a draft."). The "never read a `Quality Gate passed` comment" and "still PENDING … cannot be read" clauses stay.
- orchestration.md *Draft until green* — REWORDED (moved within section): "A merge or close … whether or not the PR was marked ready." now follows the outside-failure sentence, ending "whether or not the PR was ready".
- orchestration.md *Draft until green* — REWORDED: "Once ready, the PR is not turned back into a draft; review comments and later CI failures are worked as before." + "the orchestrator does not turn it back into a draft: it tells the Product Manager once …"
  → "The orchestrator never turns a ready PR back into a draft; review comments and later CI failures are worked as before. When the user marks it ready before all of this holds (…), the orchestrator tells the Product Manager once …" (the two "not turned back" statements merged into one).
- orchestration.md *Merge conflicts* — REWORDED: "(there is no merge commit), … reads its mergeability first …: … computing it — read it again shortly" → "(no merge commit), … first reads its mergeability …: … computing it: read again shortly".
- orchestration.md *Merge conflicts* — REWORDED: "a conflict in production or test code is resolved by its owner (Dev or Tester) while …" → "its owner (Dev or Tester) resolves a conflict in production or test code while …"; "(the user, outside the squad skills)" → "(outside the squad skills, the user)"; "— the file, its index row and every link to it —" → "(the file, its index row, every link to it),".
- orchestration.md *Merge conflicts* — REWORDED: "the change's security statements" → "the security statements".
- orchestration.md *Merge conflicts* — REWORDED: "never had to pass. `squad-next.py` runs `plan-check.py` after the merge as after every row and sends …" → "never had to pass: `squad-next.py` runs `plan-check.py` after the merge and sends …" ("as after every row" describes the tool, not a step of the orchestrator).
- orchestration.md *Concurrency* — POINTER/REMOVED: "Members experiment only in a scratch `git worktree`, never in the working tree (`team.md`, *Shared rules*)."
  → the rule's one place is `team.md`, *Shared rules* (*Git and GitHub*: "Experiments (mutation tests, trial edits, baselines) run in a scratch `git worktree` (`git stash` is a Git write, too)"), which every member reads; this was already a restatement with a pointer.
- orchestration.md *Verbatim documentation fixes* — TOOL: "passed through *Format check*, `scope-check.py` and `decision-check.py`, and logged with …"
  → "and stamped with `gate-stamp.py --verbatim`, which runs *Format check*, `scope-check.py` and `decision-check.py`. It is logged with …" (`gate-stamp.py`: `--verbatim` "stamps a verbatim documentation fix (… *Verbatim documentation fixes*)", `verbatim_run()` = *Format check*, `decision-check.py`, `scope-check.py`). Same three checks named.
- orchestration.md *Verbatim documentation fixes* — REWORDED: "A review finding — blocking or non-blocking —" → "A review finding, blocking or not,"; "(…naming it `verbatim`); the row names each finding it applied by the Reviewer's tag" → "(…naming it `verbatim`) and each finding it applied by the Reviewer's tag".
- orchestration.md *Verbatim documentation fixes* — REWORDED: "the other lines of that paragraph may be rewrapped: whitespace only, confirmed with `git diff --word-diff`, which then shows the proposed change and nothing else" → "the paragraph's other lines may be rewrapped: whitespace only, confirmed with `git diff --word-diff` to show the proposed change and nothing else".
- orchestration.md *Verbatim documentation fixes* — REWORDED: "without a Lead launch. One exception: a fix that changes … is not applied; the reviewer says so" → "without a Lead launch, but a fix that changes … is not applied: the reviewer says so". Paragraph split in two (no content change).
- orchestration.md *Verbatim documentation fixes* — REMOVED: "by definition" (in "are verbatim fixes by definition, in any file") → adds nothing to "are verbatim fixes … in any file".
- orchestration.md *A denied measurement* — REWORDED: "the orchestrator never passes it on as a result and treats it as not run, so the measurement stays with the owner the plan names." → "the orchestrator treats it as not run, never as a result, and the measurement stays with the owner the plan names."

## core/.squad/team.md

- team.md (intro) — REWORDED: "Squad for this repository, used for both bug reports (`squad-issue` skill) and new features, with or without a GitHub issue (…). The idea follows [bradygaster/squad](…): this file names … and each role's charter is the Claude Code subagent file under `.claude/agents/` (…). The roles run as subagents, driven by the invoking session (the orchestrator)."
  → "The squad of this repository, for bug reports (`squad-issue` skill) and new features with or without a GitHub issue (…), after [bradygaster/squad](…). This file names … and each role's charter is its Claude Code subagent file under `.claude/agents/` (…). The roles run as subagents of the invoking session, the orchestrator."
- team.md (intro) — REWORDED: "… from the Squad-Spec-Repository-Template repository. Everything specific to this repository lives in two files the members read first:" → "… repository; what is specific to this repository lives in two files the members read first:".
- team.md (after *Members*) — REWORDED: "Model and effort are set per role in each agent file's front matter. The orchestrator may override a single launch through its own `model` and `effort` parameters; the overrides it makes by default are in `orchestration.md` (*Launch model*), and `xhigh` is not used. Where production and test code live is defined in `stack.md` (*Layout*)."
  → "Each agent file's front matter sets the role's model and effort; the orchestrator may override them for a single launch (its default overrides: `orchestration.md`, *Launch model*), and `xhigh` is not used. Where production and test code live: `stack.md` (*Layout*)." ("through its own `model` and `effort` parameters" = how a launch override is passed; "override them" keeps it.)
- team.md *Git and GitHub* — REWORDED: "A file the change deletes is removed with plain `rm`, the removal staged with `git add <path>` (…) and named in the report." → "… removed with plain `rm` and the removal staged with `git add <path>` (…), and named in the report."; "never by checking it out in the repository working tree" → "never checked out in the repository working tree".
- team.md *Git and GitHub* — REWORDED: "Session-management tools (`create_session`, `send_message`, `archive_session`, the scheduled-task tools and the other remote-session tools) belong to the orchestrator alone, also for "handing over" work or tidying up: a member never calls one. … The orchestrator commits, pushes and opens the pull request (`routing.md`, *Pipeline*)."
  → "A member never calls a session-management tool (`create_session`, `send_message`, `archive_session`, the scheduled-task and other remote-session tools), not even to hand over work or tidy up: they are the orchestrator's, which commits, pushes and opens the pull request (`routing.md`, *Pipeline*)." (The *Experiments* sentence moved before it, unchanged.)
- team.md *Files* — REWORDED: "(the Code Officer's notes in `.squad/stack.md` excepted)" → "(except the Code Officer's notes in `.squad/stack.md`)"; "every other Write or Edit call" → "every other Write or Edit"; "the member that owns the content" → "the member owning the content".
- team.md *Files* — REWORDED: "Both hooks prevent accidents and are no security boundary: an interpreter or a shell redirect gets past them, and these rules bind there all the same." → "Both hooks prevent accidents and are no security boundary: the rules bind all the same where an interpreter or a shell redirect gets past them."
- team.md *Reporting against a SHA* — REWORDED: "never split across several and sent once" → "sent once and never split".
- team.md *Reading GitHub* — REWORDED: "`gh api` and the GitHub MCP tools answer 403 for repositories outside the session (a third-party action): resolve a tag …" → "For a repository outside the session (a third-party action), where `gh api` and the GitHub MCP tools answer 403, resolve a tag …".
- team.md *Test doubles that model a real component* — REWORDED: "by a scratch measurement in a scratch `git worktree`" → "by a measurement in a scratch `git worktree`".
- team.md *Escapes in files* — REWORDED (the escapes were written through a script with chr(92) and checked on disk with grep: `A`, `'\\u'`, `\\u202E` are byte-identical to before):
  "so a plan table or a test fixture whose cases are about escapes silently loses them" → "so a plan table or test fixture about escapes silently loses them";
  "write each such escape … or generate the file with a script; either way check the bytes on disk (`grep -n '\\u' <file>`) and confirm every escape is there exactly as the case needs" → "write such an escape … or generate the file with a script, and check on disk (`grep -n '\\u' <file>`) that every escape is there exactly as the case needs";
  "again after *Format*, since a formatter may do the same to string literals" → "again after *Format*, which may do the same to string literals";
  "so a lost escape fails the run instead of testing the wrong input" → "so a lost escape fails the run";
  "is never written as the character itself into `plan.md`, … working record: it stands there as a text escape (…), because `plan-check.py` and `scope-check.py` reject the character." → "never stands as itself in `plan.md`, … working record but as a text escape (…): `plan-check.py` and `scope-check.py` reject the character."

## Word counts (python3 -c "...split()")

- core/.squad/orchestration.md: 3,420 → 3,219 (−201)
- core/.squad/team.md: 1,570 → 1,522 (−48)
- together: 4,990 → 4,741 (−249); target was about −450.

template-check.py: PASS (no FAIL/ERROR; no shared 20-word run involving these files). `python3 -m unittest discover tools`: 646 tests OK.

## Group skills-squad


Files: `core/.claude/skills/squad-issue/SKILL.md`, `core/.claude/skills/squad-spec/SKILL.md`.

## squad-issue/SKILL.md

- squad-issue — REMOVED: "A feature runs through `squad-spec` instead (`.squad/routing.md`, *Bug or feature*)."
  → duplicate within the file: step 1 says a feature switches to `squad-spec` (*Bug or feature*); also the skill's
  `description:`.
- squad-issue — REWORDED: "You are the **orchestrator** its first paragraph describes: the tiers and loop limits of
  [`.squad/routing.md`]… " → "the **orchestrator** the first paragraph of [`.squad/routing.md`] describes: its tiers
  and loop limits and the procedures of [`.squad/orchestration.md`] …" (same content; both markdown links kept, which
  `template-check.py` reads via SKILL_LINK).
- squad-issue — TOOL: "with `python3 .squad/tools/squad-notes.py <folder> challenge|security --agent-id <id>`
  (`--spec` for `spec.md`; …)" → "with the `squad-notes.py` command `squad-next.py` prints (`--stdin` …)".
  `squad-next.py` prints the exact `squad-notes.py … challenge|security --agent-id` command for plan notes
  (`confirmation()`), `challenge --spec` for spec notes (`spec_challenge()`) and `result` for docs/patch.
  The `--stdin` outside-Claude-Code variant is not printed, so it stays.
- squad-issue — TOOL/REWORDED: "it prints the next step with its exact launch — agent, mode, model, fresh or continued
  (*Continuing a member*), hand-over and log command — or your own row, and the gates and review set the tier calls
  for" → "it prints the next step — its exact launch (agent, mode, model, fresh or continued, hand-over, verdict line,
  log command) or your own row — and the gates and review set due". Added "verdict line" (printed by `launch()`:
  "Verdict line: quote it in the prompt, exactly as here"), which replaces the Logging bullet's "Every launch prompt
  quotes the *Verdict line* `squad-next.py` prints for it".
- squad-issue — REMOVED: "ignored paths are skipped anyway, and" (in "Stage with plain `git add -A`: …")
  → general Git behaviour; the reason that keeps the rule from being worked around ("an exclusion pathspec for an
  ignored path makes `git add` fail and stage nothing") stays.
- squad-issue — POINTER: "**Scope:** a product PR touches neither the squad nor the instruction files outside their
  project blocks (*Scope of a product PR*, which `scope-check.py` enforces)." → "**Scope:** as *Scope of a product
  PR* says, which `scope-check.py` enforces." `routing.md`, *Scope of a product PR*, states the rule completely
  (squad files, `.claude/`, `CLAUDE.md`, `AGENTS.md`/copilot-instructions outside project blocks, plus exceptions).
- squad-issue — REMOVED: "It opens as a draft and is marked ready in step 11 (*Draft until green*)." (Pull request
  bullet) → step 10 (`create-pr` step 8; `draft: true` on update), step 11 ("then mark it ready"), `routing.md`
  *Pipeline* row 10 ("PR opened **as a draft**") and `orchestration.md` *Draft until green* ("Every pull request … is
  opened as a draft").
- squad-issue — REWORDED: Session-model bullet: "Gate output stays …" joined onto the previous line (wrap only).
- squad-issue — POINTER: "decide bug or feature first (*Bug or feature*): a feature switches to `squad-spec` now,
  before any branch or work folder exists; a verification issue stops here (*Bug or feature*)" → "…: a feature
  switches to `squad-spec`, a verification issue stops here". `routing.md` *Bug or feature*: "The orchestrator decides
  which before step 1 — before any branch or work folder exists"; "switch to it now".
- squad-issue — REWORDED: "Note the reported environment …" moved after "A closed issue: stop and report that."
  (order only).
- squad-issue — REWORDED: "(in a shallow clone, `git rev-parse --is-shallow-repository` prints `true`: `git fetch
  --unshallow --tags origin`; a stamp that checks the decision records refuses a shallow clone)" → "(`git fetch
  --unshallow --tags origin` when `git rev-parse --is-shallow-repository` prints `true`: a stamp that checks the
  decision records refuses a shallow clone)". Both commands and the reason kept.
- squad-issue — REWORDED: "e.g. `fix-issue-<number>-<short-slug>` (or the branch the session prescribes). A prescribed
  branch whose pull request is already merged is not reused: start a new branch off `main` without a force-push and
  name it in the intake row." → "e.g. `fix-issue-<number>-<short-slug>`, or the branch the session prescribes —
  unless its pull request is already merged: then a new branch off `main`, without a force-push, named in the intake
  row." Same conditions.
- squad-issue — REWORDED (*Several issues in one request*): "intake then starts with the lowest number (its work
  folder) and its row lists every issue; when the Lead's step-2 result does not cover them all in one tier `docs` or
  `patch` change and the user did not ask for one pull request, the others go back to runs of their own" → "intake
  starts with the lowest number (its work folder), and its row lists every issue; unless the Lead's step-2 result
  covers them all in one tier `docs` or `patch` change or the user asked for one pull request, the others go back to
  runs of their own" (not A and not B = unless A or B).
- squad-issue — REWORDED: "A shared run's pull request carries one `Closes #<number>` per issue, and the working
  record goes to the first issue with a one-line pointer on each other." → "…per issue; its working record goes to
  the first issue, with a one-line pointer on each other."
- squad-issue — REWORDED: "`gate-stamp.py --verify` and `squad-log.py` read the checked-out branch, `sonar-check.py pr`
  its `HEAD` unless `--head <sha>` is given: while one run waits … in a worktree of its branch (`git worktree add
  ../<repository>-<number> <branch>`), and remove it once that pull request is merged." → rule first, reason after:
  "While one run waits … in a worktree of its branch (`git worktree add ../<repository>-<number> <branch>`, removed
  once that pull request is merged): `gate-stamp.py --verify` and `squad-log.py` read the checked-out branch,
  `sonar-check.py pr` its `HEAD` unless `--head <sha>` is given."
- squad-issue — REWORDED: "either share one run or are stacked on purpose, … targets it, the last pull request repeats
  …, and once the previous pull request is merged, `main` is merged into the next branch and its pull request
  retargeted to `main` before its own merge." → "share one run or are stacked, …; the last pull request repeats …;
  once the previous pull request is merged, merge `main` into the next branch and retarget its pull request to `main`
  before its own merge."
- squad-issue — TOOL: "Write a launch's row as soon as its report is in, with `--agent-id <id>` (the agent id the
  Agent tool returned): the script reads the launch's figures from its transcript; never type a number yourself."
  + "Log with the step cell and the continuation option (`--continued`, `--continued-from`) `squad-next.py` prints"
  → one bullet: "log a launch as soon as its report is in, with the command `squad-next.py` printed for it (step
  cell, `--agent-id <id>` the Agent tool returned, continuation option): the script reads the launch's figures from
  its transcript; never type a number yourself". `squad-next.py` `log_command()` prints the full command with the
  step cell, member cell, `--agent-id <id>` and `--continued` / `--continued-from "<step>"`.
- squad-issue — TOOL: "Every launch prompt quotes the *Verdict line* `squad-next.py` prints for it" → `squad-next.py`
  `launch()` prints "Verdict line: quote it in the prompt, exactly as here; …" (and the Next-step bullet now lists
  "verdict line" among what it prints).
- squad-issue — REWORDED: "start the result with the member's `VERDICT:` or `RESULT:` line: the script reads them back.
  … a row logged without that line is corrected as `squad-next.py` then prints (`--replace-last`), never with a
  second row of the same launch." → "start the result with the member's `VERDICT:` or `RESULT:` line, which the
  script reads back; a row without it is corrected as `squad-next.py` then prints (`--replace-last`), never with a
  second row of the same launch".
- squad-issue — REWORDED: Logging bullets lower-cased into one list after "— never by hand:" (no content change).
- squad-issue — REWORDED: "`RESULT: DONE` with `plan.md`: `squad-next.py` runs `plan-check.py` before anyone else reads
  it and after every Lead write, and sends findings back as *Loop limits* (Plan check) says. Then the steps the tier
  requires." → "`RESULT: DONE` with `plan.md`: the steps its tier requires; `squad-next.py` runs `plan-check.py`
  after every Lead write, before anyone else reads the plan, and sends findings back as *Loop limits* (Plan check)
  says."
- squad-issue — POINTER: "together with step 3 on the same plan commit when that runs" (Plan challenge paragraph,
  step 2) → step 3 of the same skill ("in parallel with the plan challenge") and `routing.md` *Plan challenge* ("When
  step 3 runs, the challenge and Security's plan review run **in parallel** on the same plan commit").
- squad-issue — TOOL: "the tests it hands back as **deferred** go into its log row as its `Deferred:` line
  (`Deferred: none` without one), which `squad-next.py` holds the coverage pass open on" → "…go into its log row as
  `squad-next.py` says". `squad-next.py` prints for step 5: "log its `Deferred: <test names>` line (`Deferred: none`)
  in the row" and holds the coverage pass open on it (`deferred_tests()`).
- squad-issue — REWORDED: step 6 "Then, when the plan lists documentation updates not written yet, continue the Dev's
  `implement` agent for them" → "Then continue the Dev's `implement` agent for the plan's documentation updates not
  written yet". Rewrapped (the step had broken line lengths).
- squad-issue — TOOL: "Before step 7, `squad-next.py` runs `plan-check.py --matrix` and sends a `MISSING` criterion to
  `squad-tester` in mode `coverage`." → `squad-next.py` `matrix_check()` runs the matrix before step 7 and prints the
  launch `squad-tester`, mode `coverage`, "6 Coverage (matrix)" for MISSING criteria; the orchestrator only follows
  the Next-step output. (Also `routing.md` / squad-next docstring: "without a passing stamp … step 7
  (`plan-check.py --matrix` first, a `MISSING` criterion to the Tester)".)
- squad-issue — TOOL: "— in the background (Bash `run_in_background`) when it runs *Test with coverage*, which can
  outlast a foreground command's time limit — (`patch`: with `--check "<command>"` for the check the Lead's result
  names; `--project NAME=VALUE` for the test project of *Test (project)*)" → "as `squad-next.py`'s *Gates due* lines
  say (in the background, `--check`, `--project`)". `squad-next.py` `gates_due()` prints: "Start the stamp in the
  background (Bash run_in_background): the full suite can outlast a foreground command's time limit"; "pass the check
  the Lead's result names with --check \"<command>\""; "*Test (project)*: pass the test project of the changed code
  as --project NAME=VALUE".
- squad-issue — TOOL/POINTER: "When the plan asks for an *Early draft PR*, open it once the stamp passes, as that
  section says (`create-pr` step 8 without its review loop), and subscribe to its activity." → "An *Early draft PR*
  the plan asks for opens once the stamp passes, as that section and `squad-next.py` say." `routing.md` *Early draft
  PR* ("opens the PR as a draft right after step 7 (`create-pr` step 8 …)"); `squad-next.py` `early_pr()` prints
  "open the PR as a draft as create-pr step 8 says, without its review loop …, subscribe to its activity, wait for CI
  and run sonar-check.py pr <number> before step 8".
- squad-issue — TOOL: "A report for another code head is a stale round (`squad-next.py` compares the SHA of the
  Reviewer's verdict line with the stamp)." → `squad-next.py` ties a Reviewer verdict whose SHA differs from the
  stamp's code to no stamp and prints the Reviewer's continuation on the stamp's SHA (module docstring: "one that
  names none, or a commit whose code differs from the stamp of its round … ties the round to no stamp, and the
  Reviewer is continued on the stamp's SHA").
- squad-issue — POINTER/TOOL: "With an *Early draft PR* the open PR is updated as below instead of opened." (step 10)
  → `routing.md` *Early draft PR* ("step 10 then only posts the working record, removes `specs/` and marks nothing
  ready"), `squad-next.py` `pull_request()` prints "update the early draft PR" after an early PR, and step 10's own
  "a PR the session already has for the branch … gets its title and body updated instead".
- squad-issue — TOOL: "(a `MISSING` row sends the change back to step 6)" (step 10) → `squad-next.py`
  `pull_request()` prints "plan-check.py --matrix reports MISSING criteria: back to step 6" with the Tester's launch.
- squad-issue — REWORDED: step 10 working-record sentence "Post the matrix, not collapsed, then `plan.md` …, and
  `log.md` as one comment on the issue, headed "Squad working record", each inside a collapsed `<details>` block — or
  …" → "Post as one comment on the issue, headed "Squad working record", the matrix, not collapsed, then `plan.md` …
  and `log.md`, each in a collapsed `<details>` block — or …" (same content).
- squad-issue — REWORDED: "A `log.md` that does not fit the comment (GitHub takes 65,536 characters) must be linked
  this way; a linked `log.md` makes the comment's log table start with the step-10 row: `squad-log.py` and
  `squad-next.py` with `--stdin` read the earlier rows from that commit." → "A `log.md` too long for the comment
  (GitHub takes 65,536 characters) must be linked; the comment's log table then starts with the step-10 row, and
  `--stdin` reads the earlier rows from that commit."
- squad-issue — TOOL: "Then `git rm -r specs/issue-<number>/`, confirm with `python3 .squad/tools/scope-check.py
  --no-specs`, commit ("Remove squad working record") and push." → "Then remove the work folder as `squad-next.py`
  prints (`git rm -r`, `scope-check.py --no-specs`, commit "Remove squad working record", push)." `squad-next.py`
  `pull_request()` prints "git rm -r specs/<name>/, scope-check.py --no-specs, commit \"Remove squad working
  record\", push". Commit subject kept verbatim.
- squad-issue — REWORDED: step 11 "Subscribe to the PR's activity right away (…) — a session that ends …" → "at once
  (…): a session that ends …"; the four routing bullets folded into one sentence with the same targets: merge
  conflict first (*Merge conflicts*); code-analysis findings (`sonar-check.py pr <number>`) → `squad-code-officer`,
  structural → `squad-dev`; failing build or test → `squad-dev`, test defects → `squad-tester`; review comments
  (human, automated, `review-pr`) → `squad-dev`, worked in this PR, blocking or not.
- squad-issue — REWORDED: "logged at step 11 like every launch (`squad-next.py --launch squad-<role> <mode>` prints the
  exact launch), within the limit of *Loop limits*" → "within *Loop limits*, logged at step 11 with the launch
  `squad-next.py --launch squad-<role> <mode>` prints".
- squad-issue — REWORDED: "give the Reviewer, Security and the Lead the plan (…; for a feature also …)" → "hand … (…;
  a feature also …)".
- squad-issue — REWORDED: step 12 "Append the tables exactly as printed (a run without them is not wrapped up) to the
  comment under "Squad run metrics", then the output of `python3 .squad/tools/session-usage.py` as printed under
  "Session usage"." → "append its tables, then the output of `python3 .squad/tools/session-usage.py`, exactly as
  printed to the comment under "Squad run metrics" and "Session usage" (a run without them is not wrapped up)." Both
  headings and the command kept (`tools/squad-report.py` reads the headings).
- squad-issue — REWORDED: Notes "Prefer non-interactive commands only." → "Use non-interactive commands only." ("Prefer
  … only" was self-contradictory; meaning kept.)

## squad-spec/SKILL.md

- squad-spec — POINTER: "— the user calling it a feature or invoking this skill settles it" (step 1) → `routing.md`
  *Bug or feature*, rule 1 ("Calling it a feature … or invoking `squad-spec` makes it a feature … whatever the
  issue's labels or text say").
- squad-spec — REWORDED: "a bug fix switches to `squad-issue` now; a verification issue stops here (*Bug or
  feature*). A closed issue: stop and report that." → "a bug fix switches to `squad-issue`, a verification issue
  stops here; a closed issue: stop and report that." (*Bug or feature* named once, as in the step.)
- squad-spec — POINTER: "Run `git fetch origin main --tags` (unshallowing a shallow clone as `squad-issue` step 1
  says), create the branch off the latest `main` (or the branch the session prescribes, unless its pull request is
  merged: `squad-issue` step 1)" → "Otherwise fetch and branch off the latest `main` as `squad-issue` step 1 says (the
  branch the session prescribes included)". `squad-issue` step 1 holds the fetch command, the unshallow command and
  the prescribed-branch exception in full; the orchestrator of `squad-spec` reads `squad-issue` first.
- squad-spec — REMOVED: "(the feature exists already or contradicts an accepted decision: …)" (step 2a, on `RESULT: NO
  CHANGE`) → when the Lead returns it is the Lead's rule (`squad-lead.md`, mode `spec`: "feature that already exists
  or contradicts an accepted decision record is `RESULT: NO CHANGE`"); the orchestrator's routing of it ("with an
  issue, as *Outcome "no change"*; otherwise report it to the user") stays.
- squad-spec — TOOL/REWORDED: "`squad-next.py` runs `plan-check.py --spec` after every Lead write and sends findings back
  as *Loop limits* (Plan check) says, and its size warning once: the Lead shortens the spec, or keeps it and gives the
  reason in its result, which you log." → "`squad-next.py` runs `plan-check.py --spec` after every Lead write and
  sends its findings (*Loop limits*, Plan check) and, once, its size warning back to the Lead; when the Lead keeps the
  spec's size, log the reason its result gives." The Lead's two options are printed in the hand-over by
  `squad-next.py` ("the size warning: shorten the spec, or keep it and give the reason in the result").
- squad-spec — TOOL: "(`squad-notes.py <folder> challenge --spec --agent-id <id>`)" (Spec challenge) → "routed as
  `squad-next.py` prints"; `spec_challenge()` prints the exact command `python3 … squad-notes.py <name> challenge
  --spec --agent-id <the Devil's Advocate's id>` and the major/minor routing. The `squad-issue` intro bullet also
  names the command as printed by `squad-next.py`.
- squad-spec — REWORDED: "Minor objections only: append them verbatim to `spec.md` as a *Challenge notes* section …;
  the Lead answers them while it plans. A major objection: continue `squad-lead` in mode `revise` on the spec with
  all objections; it answers each … One round, no veto (*Loop limits*)." → "one round, no veto (*Loop limits*),
  routed as `squad-next.py` prints. Minor objections only go verbatim into `spec.md` as *Challenge notes*, which the
  Lead answers while it plans. A major objection: continue `squad-lead` in mode `revise` …; it answers each in the
  spec's *Challenge* section and may narrow the scope, escalate or return `RESULT: NO CHANGE`." (all conditions kept)
- squad-spec — POINTER: "with the value of `SPEC_APPROVAL` in `.squad/tools/squad_settings.py`" (Spec approval) →
  `orchestration.md` *Spec approval* opens with "`SPEC_APPROVAL` in `.squad/tools/squad_settings.py` says who
  approves a feature's spec …", values and default included.
- squad-spec — POINTER: step 2b "`squad-next.py` runs `plan-check.py` after every Lead write, before anyone else reads
  the plan; findings as *Loop limits* says. Then the **plan challenge** with `squad-devils-advocate` in mode `plan`
  when *Plan challenge* calls for it (the verdict `plan-check.py` prints), routed as `squad-issue` step 2 says." →
  "The plan check and the **plan challenge** run as `squad-issue` step 2 says." `squad-issue` step 2 states the
  plan-check run (after every Lead write, before anyone reads the plan, *Loop limits* Plan check) and the challenge
  (`squad-devils-advocate` mode `plan` when *Plan challenge* calls for it, routed as that section says);
  `routing.md` *Plan challenge* says `plan-check.py` prints the verdict and that the same holds for a feature.
- squad-spec — REWORDED: "Continue the Lead's last launch in mode `plan`" kept as is.
- squad-spec — POINTER: step 3 "whenever *Security areas touched* is not "none": `squad-security` in mode `plan` reviews
  `spec.md` and `plan.md` together, in parallel with the plan challenge, and the loop of `squad-issue` step 3
  applies." → "**Plan security review** as `squad-issue` step 3 says, with `squad-security` reviewing `spec.md` and
  `plan.md` together." `squad-issue` step 3 holds the condition, the mode, the parallel run and the loop.
- squad-spec — REWORDED: Steps 4–6 bullet "`squad-next.py` prints each group's launches; the step cell names the group
  (`4 Skeleton (G2)`), also for a group a Lead decision adds in step 7 or 8, whose launches are never logged as `8
  Fix`." → "`squad-next.py` prints each group's launches with step cells that name the group (`4 Skeleton (G2)`) —
  also for a group a Lead decision adds in step 7 or 8, never logged as `8 Fix`."
- squad-spec — REMOVED: "Any document but the verification matrix may go as a permalink to the commit before the
  removal, with a summary, as `squad-issue` step 10 says." (Step 10 bullet) → `squad-issue` step 10, which
  `squad-spec` follows for steps 4–12 ("for any document but the matrix, a permalink to the last commit that contains
  it … with a summary"); `squad-next.py` `pull_request()` also prints "a part too long for it as a permalink …
  squad-issue step 10".

## REASON entries

None. (The one reason already removed in the first pass — the session's context re-read cost — is in
`docs/squad-rationale.md`.)

## Word counts (`python3 -c "…split()"`)

| File | Before (HEAD~1 state given) | After |
| ---- | ---------------------------: | ----: |
| core/.claude/skills/squad-issue/SKILL.md | 3,019 | 2,750 |
| core/.claude/skills/squad-spec/SKILL.md | 1,057 | 925 |
| Together | 4,076 | 3,675 (−401) |

## Group lead


Baseline for "before": the working tree at the start of this task (= commit 32a1afe). Note: `template-check.py`
compares against the merge base with `origin/main`, so its "sentence removed" warnings for `squad-lead.md` also list
sentences the earlier branch commit 32a1afe already removed (e.g. "A few exact edits without a logic change are
`patch` …", "… `wc -w`, which counts a stand-alone dash differently", "If no code change is warranted (duplicate, not
reproducible …"). Those are not in this ledger; they belong to that commit's ledger.

## core/.claude/agents/squad-lead.md

- squad-lead.md — POINTER: "It says what the feature does for its users, never how it is built;"
  → kept as a parenthetical "(what the feature does for its users, never how it is built)" after "and nothing else";
  the spec template's opening comment states the same ("What the feature does for its users, before anyone decides
  how to build it").
- squad-lead.md — POINTER: "a small feature gets a short spec: with at most `SMALL_FEATURE_CRITERIA` criteria
  (`squad_settings.py`) and no security area of `.squad/project.md` touched, *Scenarios* may say "none" and each
  criterion is then written as its own scenario (given, when, then)"
  → "a small feature gets a short spec (the *Scenarios* comment)". `specs/_template/spec.md`, *Scenarios* comment,
  states it in full ("A small feature (at most SMALL_FEATURE_CRITERIA criteria in `squad_settings.py`, no security
  area) may write "none" here and each criterion as its own scenario"; the scenario form "Given …, when …, then …" is
  in the same comment); `plan-check.py` (`check_small_spec`) enforces it. The Lead writes the spec "each section as
  its comment says".
- squad-lead.md — REWORDED: "For an installer or deployment feature, or a document that leads the operator through
  another provider's page, ask the Product Manager what *Operator environments and documented procedures*
  (`.squad/routing.md`) has the spec ask (`RESULT: ESCALATE`), and record the answers as that section says."
  → same content, `RESULT: ESCALATE` moved next to "ask the Product Manager".
- squad-lead.md — POINTER: "return the tier with its justification, the files and the exact edits, and the
  acceptance criteria in your result; for `patch` also, per edit, the existing test or check that covers it (an edit
  to production code without one gets the name of the single test the Tester adds)"
  → "your result holds what their rows of *Tiers* name". `.squad/routing.md`, *Tiers*: justification ("justifies it
  in `plan.md` (`docs`, `patch`: in its result)"), `docs` row "the Lead's result (tier, exact edits, acceptance
  criteria)", `patch` row "the result also naming per edit the test or check that covers it. For an edit to
  production code without one, `squad-tester` writes the one test the Lead names". The Lead reads routing.md in full.
- squad-lead.md — POINTER: "(accepted — what changed; or rejected — why)" (closing the spec's *Challenge notes*,
  mode `plan`) → "(its template's comment)": the spec template's *Challenge* comment states the answer form.
- squad-lead.md — REMOVED: "`plan-check.py` checks its structure."
  → changes nothing the Lead does; `.squad/routing.md`, *Pipeline* step 2 and *Loop limits* (Plan check) state that
  `plan-check.py` runs after every Lead write.
- squad-lead.md — POINTER: "for a bug, name the root cause with file and line"
  → "(a bug's root cause: the template's *Problem / root cause*)"; `specs/_template/plan.md` says "For a bug: the
  cause, with file and line."
- squad-lead.md — POINTER: "state which claims were confirmed or refuted"
  → the bullet "every factual claim the plan rests on in *Verified facts*, with its evidence and status (the
  template)" two paragraphs below; the template's *Status* column is `confirmed / refuted / unverified`.
- squad-lead.md — REMOVED: "so a plan of a few edits stays far below it"
  → repeats "a ceiling for its largest changes, not a target" in other words.
- squad-lead.md — POINTER: "- the **tier** with a one-sentence justification, and *Security areas touched* in every
  plan: a change that touches a security area without creating, changing or removing a security control is not
  `security`;"
  → "- the **tier** with a one-sentence justification and *Security areas touched* (*Tiers*);". `.squad/routing.md`,
  *Tiers*: "Every `plan.md` names its **Security areas touched** …" and the `standard` row "A behavior change that
  creates, changes or removes no security control … — also when it touches a security area".
- squad-lead.md — POINTER: "(a feature's are the spec's: never copy them), … — the Tester writes exactly those first
  — or, for one no unit test can verify, its kind and check (`CI:`, `manual:` with who runs it, `after merge:`; the
  template)"
  → "and for every criterion its tests, or its kind and check, in *Tests per criterion* (the template)". Template
  *Acceptance criteria*: "a feature's criteria live in `spec.md` … do not copy them here"; *Tests per criterion*:
  "the tests the Tester writes first … `CI: <the check>`, `manual: <who, on which build>` or `after merge: …`";
  routing *Pipeline* step 5: "Only the tests the plan names".
- squad-lead.md — POINTER + REWORDED: documentation-updates bullet. Removed "its owner reports the exact text, which
  the orchestrator writes in" → "(an edit of `.squad/stack.md` or `.squad/project.md` too: `.squad/team.md`,
  *Files*)"; team.md *Files*: "An edit of `.squad/project.md` or `.squad/stack.md` the plan lists is the
  orchestrator's: the member that owns the content … reports the exact text, and the orchestrator writes it
  verbatim". Rest reordered (owner and timing first, then the sweep) with every condition kept: sweep of area
  documents and `docs/ARCHITECTURE.md`, enumerations / "only these …" (routes, rules, settings, tables, limits),
  each hit listed, every list and sentence of an altered set found by its members' names, not only the first, the
  documents already known, the PR-template checklist incl. its project block, changelog example, Dev / Tester owner,
  never the orchestrator, written once green against that code, exact wording only where a criterion fixes it.
- squad-lead.md — REWORDED: "for every area document the change extends, the words it has now and the words the
  change adds, on the line of *Areas* (`docs/areas/<name>.md (+N words)`): `plan-check.py` warns when the sum passes
  `AREA_MAX_WORDS`, and a split into a new area document is then planned now and in the spec's *Area documents*, not
  left to `decision-check.py` after the documentation is written;"
  → "its words now and the words the change adds, on its *Areas* line (…): past `AREA_MAX_WORDS` (`plan-check.py`
  warns) a split … is planned now, also in the spec's *Area documents*, not left to `decision-check.py` afterwards;".
- squad-lead.md — POINTER: "- for a feature, `tasks.md`: task groups in build order, each naming the spec's criteria
  it delivers, the tasks it waits for and a skeleton row for its *Signatures* (or "no new API");"
  → "- for a feature, `tasks.md` as its template says, task groups in build order;". `specs/_template/tasks.md`:
  "Each task names its criteria, the tasks it waits for and its group … A group has a "Skeleton" row for its API in
  *Signatures*, or says "no new API""; `plan-check.py` checks both.
- squad-lead.md — POINTER: "(for the Dev's skeleton; no private member, and no backticks in a plan without API: the
  template's *Signatures*)" → "(the template's *Signatures*)"; the template's *Signatures* text: "Each backticked
  declaration here is one the Dev's skeleton adds (step 4), so a private member is described in *Approach*, and a
  plan without API writes this section in plain prose."
- squad-lead.md — POINTER: "- the **test files**, named strictly by *Layout* in `.squad/stack.md` and
  `docs/UNIT_TESTS.md`, and the existing test call sites a changed signature affects, with who adapts them (*Loop
  limits*);" → "- the **test files** and the existing test call sites a changed signature affects, with who adapts
  them (the template's *Test files*);". Template *Test files*: "named strictly by the convention in *Layout* of
  `.squad/stack.md` and UNIT_TESTS.md … Existing test code that calls a changed signature …: the call sites and who
  adapts them (`.squad/routing.md`, *Loop limits*)". The sentence "a test kept unchanged has no input …" stays.
- squad-lead.md — POINTER: "- for a change without production or test code: the declaration and its *Verification
  without tests* (*Changes without production or test code*); for an input the image build is sensitive to: the
  *Image build check* as the criterion's verification, run by the Dev, and for a criterion tested by hand on a build
  the build it runs on (*Criteria verified only in CI*); the files no unit test can cover, each with the reason, or
  "none" (*Code a unit test cannot cover*);"
  → "- what the template asks for a change without production or test code (*Verification without tests*), a
  criterion verified only in CI or by hand on a build, and files no unit test can cover;". Template: *Verification
  without tests* section (pointing to routing *Changes without production or test code*); *Acceptance criteria*: "one
  about a container image, or tested by hand before step 9, names its verification as *Criteria verified only in
  CI* (`.squad/routing.md`) says" (routing states the *Image build check*, the Dev as owner, the build a hand test
  runs on); *Test files*: "Files of the change no unit test can cover …, each with the reason … — or "none""
  (routing *Code a unit test cannot cover*).
- squad-lead.md — REWORDED: "marked *unverified*" → "*unverified*" (test-double / security-property claim bullet).
- squad-lead.md — POINTER: "and a control character a case is about is written as a text escape" → dropped; the
  pointer `(.squad/team.md, *Escapes in files*)` stays on the sentence, and team.md states it in full ("A control
  character a case is about … is never written as the character itself into `plan.md`, `spec.md`, `tasks.md` …: it
  stands there as a text escape"). The escape-guard criterion clause stays.
- squad-lead.md — POINTER: "extend an existing unreleased record only when it records the same decision, never
  because it shares the topic, and split a record the extension would take past the size limits instead
  (`docs/decisions/README.md`, *Size*)."; "A record you delete takes its index row with it."; "Keep the record to
  the why: the behavior it leads to is written once in the area document, which the record links and names in its
  `Area:` field."
  → "when to extend, split or delete a record and what it holds is the README's (*Rules*)". `docs/decisions/README.md`,
  *Rules*: "look for an unreleased record of the same decision and extend it instead …; another decision on a topic
  that already has a record gets a record of its own"; *Size* bullet (split); "deleted … together with its index row
  and every link to it"; "The record states the decision … and does not restate behavior … belong in the area
  document and are linked from the record"; the `Area:` field bullet. The Lead reads that README first.
  The `git ls-remote --tags origin` check and the ARCHITECTURE.md update sentence stay.
- squad-lead.md — POINTER: "(accepted — what changed; or rejected — why)" (mode `revise`, spec challenge) → dropped;
  the spec template's *Challenge* comment states the answer form.
- squad-lead.md — REWORDED: "fold an existing *Challenge notes* section into *Challenge*, and decide every choice a
  *Security notes* entry leaves (the option taken and why), folding the section into *Security review*."
  → "folding *Challenge notes* into *Challenge* and *Security notes* into *Security review*, where you decide every
  choice a *Security notes* entry leaves (the option taken and why)."
- squad-lead.md — REWORDED: "In every other launch (`decide`, a revise for `plan-check.py` findings or the size,
  `approve-pr`) you leave the *Challenge* and *Security review* sections exactly as they are: they count toward no
  size limit (`plan-check.py`)." → "In every other launch, a revise for `plan-check.py` findings or the size
  included, leave … exactly as they are: no size limit counts them (`plan-check.py`)." (`decide` and `approve-pr`
  are "every other launch" without naming.)
- squad-lead.md — REWORDED: "a signature that still contradicts one (…) is changed in the same revision" → "and
  change in the same revision a signature that still contradicts one (…)".
- squad-lead.md — POINTER: "a waiver of one no one can verify is the Product Manager's" and "the template names the
  columns" → "(… the spec template's *Amendments* comment)". The comment says "waives (`waived: …`, a criterion no
  one can verify, only by the Product Manager)" and names the columns; `plan-check.py` rejects a `waived` row not
  decided by the Product Manager.
- squad-lead.md — REMOVED: "`plan-check.py` checks the folder before the next launch." → TOOL / changes nothing the
  Lead does: routing *Loop limits* (Plan check) — `plan-check.py` runs after every Lead write.
- squad-lead.md — REWORDED: "launched only when the orchestrator's checklist (`.squad/routing.md`, *PR approval*)
  passed and left decisions open." → "after the checklist of *PR approval* (`.squad/routing.md`) left decisions
  open:" (a checklist that leaves decisions open has passed; routing *PR approval* states the launch condition).
- squad-lead.md — POINTER: "— a plan deviation, one of your earlier decisions to confirm against what was built, a
  change to `docs/ARCHITECTURE.md` or `.squad/project.md` the plan does not name or the Reviewer did not find
  consistent —" → "(an earlier decision of yours is confirmed against what was built)". `.squad/routing.md`, *PR
  approval*, lists the kinds: "a plan deviation in a member's report, a Lead decision recorded during steps 3–8 …, or
  a change to `docs/ARCHITECTURE.md` or `.squad/project.md` that the plan does not name or the Reviewer did not find
  consistent. The orchestrator lists these points one by one". The confirm-against-what-was-built nuance is kept.
- squad-lead.md — REWORDED: "You may write only under `specs/` and `docs/decisions/` — never a squad or instruction
  file (*Scope of a product PR*), never production or test code, never `log.md`." → "You write only under … — never
  a squad or instruction file (*Scope of a product PR*), never `log.md`." ("never production or test code" repeats
  "only under `specs/` and `docs/decisions/`"; also team.md *Files* and the charter's description.)

## core/.claude/agents/squad-devils-advocate.md

- squad-devils-advocate.md — REWORDED: "Check each against the code and the documents, with file and line." → "Check
  each against the code and the documents (evidence: *Rules*)."; the *Rules* bullet "Every objection cites
  evidence: the plan passage, or file and line plus what you read or ran" states the file-and-line requirement for
  both modes.
- squad-devils-advocate.md — REMOVED: "Rank and report exactly as below." → repeats the next paragraph's "The *Rules*
  below apply to both modes." (ranking and report are *Rules* bullets and the final `VERDICT` line).
- squad-devils-advocate.md — REWORDED: "Your job is to find what the plan got wrong **before** it is built, not to
  review code style or security (Security and the Reviewer do that later). Question the plan on:" → "Question what
  the plan got wrong **before** it is built, not code style or security (Security and the Reviewer do that later):".
- squad-devils-advocate.md — REWORDED: "The orchestrator routes on that rank alone (*Plan challenge*): minor
  objections go verbatim into the *Challenge notes* of the document you challenged (…)" → "The orchestrator routes
  on that rank alone: minor objections go verbatim into the *Challenge notes* of the challenged document (…)". The
  pointer *Plan challenge* went because the Devil's Advocate reads only routing's *Tiers* (its *Read first*); the
  routing facts it needs stay in the sentence.

## core/specs/_template/plan.md

- plan.md — POINTER: comment "Each security area of `.squad/project.md`, Docker/CI or build configuration and
  dependency the change touches, or "none" — in every plan (`.squad/routing.md`, *Tiers*)."
  → "Security areas touched: as *Tiers* in `.squad/routing.md` defines them, or "none"."; routing *Tiers*: "Every
  `plan.md` names its **Security areas touched**: each security area of `.squad/project.md`, Docker/CI or build
  configuration and dependency the change touches, or exactly "none"". Only the Lead writes the plan and reads
  routing in full. The "Plan size:" sentence stays unchanged.
- plan.md — REMOVED (TOOL): "`.squad/tools/plan-check.py` rejects a row without evidence or status." → changes
  nothing the writer does (the preceding sentences already require evidence and status); `plan-check.py`
  (`check_verified_facts`) rejects such a row.
- plan.md — REMOVED (TOOL): "; `--matrix` shows each one's result" → information for the orchestrator (step 10,
  `plan-check.py --matrix`, documented in the tool's docstring); changes nothing the Lead writes.
- plan.md — POINTER: "steps 4, 5 and the *Coverage gate* are not applicable" and the examples "(workflow step, PR
  dry run, read-only check)" → `.squad/routing.md`, *Changes without production or test code*, already pointed to
  in the same sentence: "may declare steps 4 (*Skeleton*), 5 (*Tests first*) and the *Coverage gate* **not
  applicable** … (a workflow step, a PR dry run, a build of the image, a read-only check)".
- plan.md — POINTER: "A change in behavior updates its area document in this pull request." → `AGENTS.md`
  ("What holds today … is written once in the area document of the change in `docs/areas/`, which the same pull
  request updates"), routing *Work folder* (the *what* in the area documents the plan names under *Areas*) and
  routing *Pipeline* step 6 (the plan's doc updates, area documents included).

## core/specs/_template/spec.md

- spec.md — REMOVED: "Written by the Lead in mode `spec`, challenged once by the Devil's Advocate, and from then
  on" → "Once challenged,". Who writes and challenges the spec is in `squad-lead.md` (mode `spec`), routing
  *Pipeline* step 2 and *Loop limits* (Spec challenge); the comment keeps that from the challenge on the spec is the
  only source of the criteria.

## Not changed

- `core/specs/_template/tasks.md`, `core/specs/_template/log.md`: no restatement or removable sentence found (every
  sentence of tasks.md states a rule `plan-check.py`/`squad-next.py` depends on or that exists nowhere else).
- No heading, table header, `<!-- … -->` marker, placeholder text `plan-check.py` matches (`<title>`,
  `Issue #<number>`, `<one-sentence justification>`, `NNNN-title`, `one option: <why`, `AC1: ...`), front matter
  or *Read first* line was changed.

## Word counts (before → after)

| File | Before | After |
| ---- | ------ | ----- |
| core/.claude/agents/squad-lead.md | 3181 | 2768 |
| core/.claude/agents/squad-devils-advocate.md | 804 | 784 |
| core/specs/_template/plan.md | 1123 | 1069 |
| core/specs/_template/spec.md | 599 | 584 |
| core/specs/_template/tasks.md | 173 | 173 |
| core/specs/_template/log.md | 47 | 47 |
| **Total** | **5927** | **5425** (−502) |

## Group members


## core/.claude/agents/squad-reviewer.md

- squad-reviewer.md — REMOVED: "You are a reviewer, not an implementer."
  → repeats the sentence before it and *Hard constraints* ("Never edit files. You report; the calling session decides and fixes.").
- squad-reviewer.md — POINTER/REWORDED: "**Your experiments, builds and test runs** (when a squad session invoked you) happen in a scratch worktree: `git worktree add --detach <scratchpad>/review <head>` (a worktree, not a plain file copy: the squad scripts need git), plus any uncommitted changes you were asked to review copied over; remove it with `git worktree remove --force <scratchpad>/review` when done. The head you review is never checked out in the repository working tree, not by a command, a script or a tool you run: the orchestrator commits there (`.squad/team.md`, *Shared rules*)."
  → same rule, tighter; the reason "the orchestrator commits there" dropped: `team.md`, *Shared rules* (*Git and GitHub*: another revision is read in a scratch worktree, never checked out in the working tree; *Reporting against a SHA*: the orchestrator commits while members work). Pointer now names *Git and GitHub*. Commands, paths and "not a plain file copy: the squad scripts need git" kept.
- squad-reviewer.md — REWORDED: "Back every finding with something you ran or read: a test run, … a throwaway snippet in the scratchpad directory. Quote the evidence. A claim you cannot back up is not a finding — drop it."
  → one sentence, same content ("… and quote it; a claim you cannot back up is not a finding").
- squad-reviewer.md — REMOVED: "Your time goes to what nobody has checked yet."
  → summary of the preceding rule (re-run only the one case you doubt or the report is silent on); changes nothing a reviewer does.
- squad-reviewer.md — REWORDED: "… is evidence; read it against the diff and re-run only the one case you doubt …"
  → "… is evidence: check it against the diff, re-run only the one case you doubt …" (also breaks the 20-word run shared with squad-security.md).
- squad-reviewer.md — REWORDED: "a checklist item that passes, formatting the formatter fixes, or praise is left out of the report." + Severity: "A nit that would not change what gets merged stays out of the report."
  → merged into *Hard constraints*: "a checklist item that passes, formatting the formatter fixes, praise or a nit that would not change what gets merged is left out."
- squad-reviewer.md — REWORDED: "When the fix changes a behavior statement an acceptance criterion or a guarantee in `.squad/project.md` relies on, say so: the Lead decides."
  → same sentence joined to the previous one ("…; say so when the fix changes a behavior statement … relies on: the Lead decides.").
- squad-reviewer.md — REASON: "because records are the Lead's and any other form costs a Lead launch"
  → rationale entry (below). Rule kept: every wording finding on a decision record is stated verbatim.
- squad-reviewer.md — REWORDED: "Trailing whitespace or a blank line at the end of a file (`git diff --check`), in any file, is marked `verbatim` too, with the file and line."
  → "Trailing whitespace or a blank line at the end of any file (`git diff --check`) is marked `verbatim` too, with file and line."
- squad-reviewer.md — REWORDED: "The calling session gives you: the base ref and the head to review, the round number, and — from round 2 on — the previous round's findings and the commits that were supposed to fix them. If no round number is given, assume round 1."
  → "The calling session gives you the base ref, the head to review, the round number (none given: round 1) and, from round 2 on, the previous round's findings and the commits meant to fix them."
- squad-reviewer.md — REWORDED: "The head is a code SHA: commits after it that touch only `specs/` …" → "later commits that touch only `specs/` …".
- squad-reviewer.md — REWORDED: "Then additionally read the folder's `plan.md` …" → "Then read the folder's `plan.md` …"; "For `docs` the review reads the diff only" and "After step 10 the plan comes from …" joined into one paragraph (text unchanged).
- squad-reviewer.md — REWORDED: "A full review covers three things: the integration surface, the conventions and the gates — the surface counts as much as the diff."
  → "A full review covers the integration surface, which counts as much as the diff, the conventions and the gates."
- squad-reviewer.md — REWORDED: "Then check these, which hold in every repository:" → "Then, in every repository:".
- squad-reviewer.md — REWORDED: "a diff that changes one without saying so in the PR description is a finding, and so is a diff that leaves the corresponding sentence in `README.md` or `docs/` standing while making it untrue."
  → "a diff that changes one is a finding when the PR description does not say so, or when it leaves the corresponding sentence in `README.md` or `docs/` standing while making it untrue."
- squad-reviewer.md — REWORDED: "A match is a blocking finding even when … (the CI code scanning judges by the name). The remedy is the one that section names …"
  → "A match is blocking even when … (the CI code scanning judges by the name); the remedy is the one that section names …" (reason kept: it stops the "only a harmless label" workaround).
- squad-reviewer.md — REWORDED: "**A change to project conventions** touches `AGENTS.md`, …, the skill files under `.claude/skills/` and `docs/`, which are meant to stay in sync with each other. Updating only one of them is a finding."
  → "**A change to project conventions** keeps `AGENTS.md`, … and `docs/` in sync; updating only one of them is a finding."
- squad-reviewer.md — REWORDED: "… a long-running loop or, worse, silently produce wrong data?" → "or silently produce wrong data?".
- squad-reviewer.md — REMOVED: "- **Test coverage**: new or changed logic must have tests — a hard requirement, not a preference."
  → "a hard requirement, not a preference" repeats "A missing test on new behavior is blocking" (kept); bullet now "new or changed logic must have tests; a missing test on new behavior is blocking. Check them against …".
- squad-reviewer.md — REMOVED: "Check the claims, don't read past them."
  → repeats the question before it ("does every sentence the diff adds or leaves standing still describe what the code does?").
- squad-reviewer.md — REWORDED: "Report failures as blocking findings, and quote the failing line. A formatter diff, any diagnostic the analyzer gate reports in a changed file, and a failed *Coverage gate* are all blocking."
  → "Report every failure as a blocking finding and quote the failing line; a formatter diff, any diagnostic the analyzer gate reports in a changed file and a failed *Coverage gate* are all failures."
- squad-reviewer.md — REWORDED: "A later round answers two questions: 1. Does each fix actually resolve the finding it claims to resolve? 2. Did the fix commits introduce a defect — **including in the prose they wrote**? Text added to fix a documentation finding is under review like any other change: check each new claim against the running code. Do **not** re-review parts of the diff the fix commits did not touch."
  → "A later round reviews only what the fix commits touched and answers two questions: does each fix resolve the finding it claims to resolve, and did the fix commits introduce a defect — **including in the prose they wrote**, whose every new claim you check against the running code?" (gates sentence unchanged).
- squad-reviewer.md — REWORDED: "Report it once with a recommendation and mark it clearly. It does not gate the pull request and it does not earn another review round."
  → "Report it once, clearly marked, with a recommendation; it neither gates the pull request nor earns another review round."
- squad-reviewer.md — REMOVED: "A `verbatim` finding's fix is the complete replacement text, nothing to interpret."
  → repeats *Hard constraints* (*State a documentation fix verbatim*: "the whole sentence as it stands and as it should read (never an insertion point …)") and the example in *Output*.

## core/.claude/agents/squad-security.md

- squad-security.md — REWORDED: "— and the diff review (mode `diff`) of a change made outside the squad that touches a security area (`AGENTS.md`, golden rules), launched by `create-pr` or `review-pr` with no plan: review the diff against `.squad/project.md` and the issue or PR description instead."
  → "— and, launched by `create-pr` or `review-pr` with no plan, the diff review (mode `diff`) of a change made outside the squad that touches a security area (`AGENTS.md`, golden rules), against `.squad/project.md` and the issue or PR description."
- squad-security.md — REWORDED: "The Devil's Advocate challenges the same plan at the same time, so stay with security."
  → "Stay with security: the Devil's Advocate challenges the same plan in parallel."
- squad-security.md — REWORDED: "A second `plan` launch confirms the Lead's revision: review the plan's change since your round plus whether your findings are resolved." + "Mode `diff`: … ; from round 2 on, review only the delta since the previous round plus whether your earlier findings are resolved."
  → one sentence for both: "A second `plan` launch (confirming the Lead's revision) and a `diff` round from round 2 on review only the change since your previous round plus whether your findings are resolved."; the mode `diff` sentence keeps base ref/head, `patch/security` against `result.md`, "as the only review of the change".
- squad-security.md — POINTER: "on the changed log calls: a name that matches the stack's sensitive-name list is a blocking finding."
  → the clause after the colon goes: the Reviewer's *Logger arguments* check (`.claude/agents/squad-reviewer.md`, which this sentence already points to) states that a match is blocking.
- squad-security.md — REWORDED: "A verification the Dev reported with its cases and output is evidence: read it against the diff and re-run only what bears on a security area and you doubt, instead of repeating the whole comparison."
  → "Check a verification the Dev reported with its cases and output against the diff instead of repeating it; re-run only what bears on a security area and you doubt." (breaks the 20-word run shared with squad-reviewer.md).
- squad-security.md — POINTER: "(a deadline that interrupts a query step, a limit a parser enforces, a server's flush semantics)"
  → the examples are in `.squad/team.md`, *Test doubles that model a real component* (same three examples), which the sentence points to and Security reads.
- squad-security.md — REWORDED: "an unverified claim of that kind is a blocking finding." → "is blocking."
- squad-security.md — REWORDED/REMOVED: "If the measurement cannot run because a download or tool is denied, report it as not run and name what it needs; the orchestrator handles it (`.squad/orchestration.md`, *A denied measurement*)."
  → merged into the previous sentence: "one without them, or one a denied download or tool stopped, is reported as not run, the latter naming what it needs." The clause "the orchestrator handles it (`.squad/orchestration.md`, *A denied measurement*)" goes: it changes nothing Security does, and the orchestrator's step lives in `orchestration.md`, *A denied measurement*, which members do not read.
- squad-security.md — REWORDED: "- In mode `diff`, take the code SHA … (`.claude/agents/squad-reviewer.md`). Never edit files, and never check out the code SHA or another revision in the repository working tree (`.squad/team.md`, *Shared rules*)." + "- In mode `diff`, write each finding in the Reviewer's shape and tags (…; its *Output*), and wrap a proposed replacement to the width of the paragraph it replaces."
  → the two mode-`diff` bullets merged ("… (`.claude/agents/squad-reviewer.md`), and write each finding in its shape and tags (…; its *Output*), a proposed replacement wrapped to the width of the paragraph it replaces."); the edit/checkout rule is its own bullet "Never edit files or check out the code SHA or another revision in the repository working tree (`.squad/team.md`, *Git and GitHub*)."

## core/.claude/agents/squad-code-officer.md

- squad-code-officer.md — REMOVED: "CI does not replace this step."
  → changes nothing the Code Officer does (it is launched by the orchestrator); the front-matter description already says the pass exists "so nothing is left for CI or the code analysis to find".
- squad-code-officer.md — REWORDED: "Nothing else: the plan, the issue and the project's documentation are not needed for format and analyzer fixes."
  → "Nothing else: format and analyzer fixes need no plan, issue or project documentation."
- squad-code-officer.md — REWORDED: "3. Run the *Analyzer gate*. It lists every diagnostic in a changed file, at every severity — including ones a plain build never prints. Do not rely on grepping console build output. Fix every listed diagnostic within the limits below; … as not analysed locally, so the orchestrator knows step 11 may still bring findings."
  → "3. Run the *Analyzer gate*: it lists every diagnostic in a changed file at every severity, including ones a plain build never prints, which grepping console build output misses. Fix every one within the limits below; … as not analysed locally: step 11 may still bring findings."
- squad-code-officer.md — REWORDED: "counts as structural: do not make it, hand it back with file, line and rule id …"
  → "counts as structural: hand it back with file, line and rule id …" (the *Limits* sentence before it already forbids the change).
- squad-code-officer.md — REMOVED: "(*Scope of a product PR* in `.squad/routing.md`, *Squad lessons* in `.squad/orchestration.md`)"
  → citation only; the Code Officer reads neither file, and the rule it needs ("in the product PR") stays. The permission lives in `routing.md`, *Scope of a product PR*.
- (unchanged) "A finding that contradicts a documented style rule … is reported as a conflict with that rule …" — `team.md` does not state it; kept here, the Dev's copy reworded so the two no longer share a 20-word run.

## core/.claude/agents/squad-tester.md

- squad-tester.md — REWORDED: "Write **only** the tests the plan names for its acceptance criteria — one or a few per criterion — in the test location from *Layout*, in the test files the plan names, reusing the existing test doubles. Each one fails on the current code or on the skeleton."
  → one sentence, same content.
- squad-tester.md — TOOL: "…, which the orchestrator's log row carries; it launches mode `coverage` for them even when the *Coverage gate* already passes."
  → "…, from which `squad-next.py` launches mode `coverage` for them even when the *Coverage gate* already passes." (verified: `squad-next.py` `DEFERRED`, `deferred_tests()`, `coverage_pass(…, deferred_tests(run, group))`).
- squad-tester.md — REWORDED: "If the plan assigns you existing test call sites of a signature whose old form still exists, move them to the new signature as the plan says."
  → "Move the existing test call sites the plan assigns you (of a signature whose old form still exists) to the new signature as the plan says."
- squad-tester.md — REWORDED: "For each existing test the plan keeps unchanged, check its input and expectation against every new criterion and report a contradiction in the hand-back."
  → "Check the input and expectation of each existing test the plan keeps unchanged against every new criterion and report a contradiction."
- squad-tester.md — REWORDED: "A plan's claim of a bound … fails when the claim is false. A time bound … never as an absolute duration; the limit is at least three times the highest ratio you measured, with the instrumentation of *Test with coverage* included (`docs/UNIT_TESTS.md`)."
  → one sentence, every number and condition kept ("…, with a limit of at least three times the highest ratio you measured, the instrumentation of *Test with coverage* included"). Not replaced by a pointer: `docs/UNIT_TESTS.md` is a seed a target may have rewritten.
- squad-tester.md — REWORDED: "Build and run the new tests. They must compile … and fail on the current code; …" → "Build and run the new tests: they compile … and fail on the current code; …".
- squad-tester.md — POINTER: "Confirming the failure on the current code or the skeleton is all this mode checks: never implement the feature to see your tests pass — not in the working tree and not in a scratch `git worktree` or copy either; …"
  → "Confirming that failure is all this mode checks: never implement the feature to see your tests pass, not even in a scratch copy (*Rules*); …" — the tester's own *Rules* bullet says "Never write production code (also not in a scratch copy; the one exception is the throwaway mutation of mode `coverage`)".
- squad-tester.md — REWORDED: "…, or name a file it misses or one you can cover after all, in your report." → "in your report" dropped (the whole step reports).
- squad-tester.md — REWORDED: "Write every test the hand-back of mode `tests-first` listed as deferred …" → "Write every test the `tests-first` hand-back listed as deferred …".
- squad-tester.md — POINTER/REMOVED: "apply that mutation once in a scratch `git worktree` (never in the working tree), …, and remove the worktree: a throwaway mutation is a check of your test, not production code."
  → "(never in the working tree)" becomes the pointer "(`.squad/team.md`, *Git and GitHub*)" — team.md: "Experiments (mutation tests, trial edits, baselines) run in a scratch `git worktree`"; the closing clause repeats the tester's *Rules* exception ("the one exception is the throwaway mutation of mode `coverage`").
- squad-tester.md — REWORDED: "Tests that only execute lines without asserting behavior do not count." → "A test that only executes lines without asserting behavior does not count."
- squad-tester.md — REWORDED: "Report lines you believe cannot be covered by a unit test, …" → "Report lines you believe no unit test can cover, …".
- squad-tester.md — REWORDED: "Write tests the analyzers accept from the start — these are test-design rules the Code Officer cannot fix without handing them back — and run the *Analyzer gate* …"
  → "Write tests the analyzers accept from the start (the Code Officer hands test-design findings back to you) and run the *Analyzer gate* …" (half-sentence reason kept, shorter).

## core/.claude/agents/squad-dev.md

- squad-dev.md — REWORDED: "The plan already carries the guarantees and integration points that apply; `.squad/project.md` is the Lead's and the Reviewer's reading."
  → "…; not `.squad/project.md`, since the plan carries the guarantees and integration points that apply." (joined to the *Read first* sentence).
- squad-dev.md — REWORDED: "Constructors store their arguments and never throw — a test harness builds these types, and a throwing constructor fails every test at construction instead of at its assertion; only member bodies fail."
  → "Constructors store their arguments and never throw (a throwing constructor fails every test at construction, not at its assertion); only member bodies fail."
- squad-dev.md — REWORDED: "…, so the suite builds. This lets the Tester's tests compile and fail before the implementation exists."
  → "…, so the suite builds and the Tester's tests compile." (that the tests fail before the implementation is the Tester's tests-first mode).
- squad-dev.md — POINTER/REWORDED: "Stage every new file you created, in every launch — skeleton, implementation, documentation or fix round — before you hand back (`git add <file>` is the one Git operation you may run, and staging is yours, not the orchestrator's: the *Coverage gate* only counts files Git tracks); a file the plan deletes is removed and staged as …; where the permission check denies `git add`, …"
  → "Stage every new file you created with `git add <file>` before you hand back, in every launch (…): staging is yours, not the orchestrator's, since the *Coverage gate* only counts files Git tracks; where the permission check denies `git add`, … A file the plan deletes is removed and staged as *Git and GitHub* in `.squad/team.md` says." — "is the one Git operation you may run" goes: which Git commands a member may run is `team.md`, *Git and GitHub* (read-only Git, `git add`, a scratch `git worktree`).
- squad-dev.md — REWORDED: "Run *Build*, *Test with coverage* and the *Coverage gate* from `stack.md`. When the change touches an input the container image's build is sensitive to, also run the *Image build check* and report its result (*Criteria verified only in CI* in `.squad/routing.md`). Report the coverage result; uncovered changed lines … (code that is hard to test is a design signal …"
  → "Run *Build*, *Test with coverage* and the *Coverage gate* from `stack.md`, and, when the change touches an input the container image's build is sensitive to, the *Image build check* (*Criteria verified only in CI* in `.squad/routing.md`); report their results. Uncovered changed lines … (hard-to-test code is a design signal …".
- squad-dev.md — REWORDED: "A finding that contradicts a documented style rule (`AGENTS.md`, *Code style*; `.squad/stack.md`) is not worked around: report it as a conflict with that rule, name the `.editorconfig` severity as the proposed fix, and leave the code as the rule has it."
  → "Do not work around a finding a documented style rule (`AGENTS.md`, *Code style*; `.squad/stack.md`) contradicts: leave the code as the rule has it and report the conflict, the `.editorconfig` severity as the proposed fix." (`team.md` does not state this rule, so both charters keep it; reworded so it no longer shares a 20-word run with squad-code-officer.md.)
- squad-dev.md — rewrap only of the *Documentation* paragraph's figure-check sentences (no word changed).

## Rationale entries (for docs/squad-rationale.md)

- Reviewer, *Hard constraints*, *State a documentation fix verbatim* (`core/.claude/agents/squad-reviewer.md`):
  "A wording finding on a decision record is always stated verbatim because records are the Lead's: any other form
  of the finding costs a Lead launch just to reword a name, link, number or sentence."

## Checks of the brief's known shared runs

- code-officer/dev "a finding that contradicts a documented style rule": `team.md` does not state it; both members
  must follow it and neither reads the other's charter, so both keep it; the Dev's sentence is reworded (no shared
  20-word run any more).
- reviewer/security "is evidence, read it against the diff": `team.md` does not state it; Security's version has its
  own condition (only what bears on a security area), so both stay, reworded apart.
- tester/orchestration "in a scratch git worktree, never in the": `team.md`, *Git and GitHub*, states it
  ("Experiments (mutation tests, trial edits, baselines) run in a scratch `git worktree`"); the Tester's
  "(never in the working tree)" became a pointer to it.

`template-check.py` reports no 20-word run shared by these files after the edit; it exits 0.
`python3 -m unittest discover tools`: 646 tests OK.

## Word counts (python split)

| File | Before | After | Change |
| --- | ---: | ---: | ---: |
| core/.claude/agents/squad-reviewer.md | 2283 | 2147 | −136 |
| core/.claude/agents/squad-security.md | 840 | 764 | −76 |
| core/.claude/agents/squad-code-officer.md | 560 | 526 | −34 |
| core/.claude/agents/squad-tester.md | 1313 | 1261 | −52 |
| core/.claude/agents/squad-dev.md | 1197 | 1149 | −48 |
| **Total** | 6193 | 5847 | −346 |

## Group skills-other


Files: `core/.claude/skills/create-pr/SKILL.md`, `core/.claude/skills/review-pr/SKILL.md`,
`core/.claude/skills/decision-consolidate/SKILL.md`, `core/AGENTS.md`, `core/docs/ARCHITECTURE.md`.
No heading, marker, `{{TODO}}` placeholder, project block or front matter changed. create-pr step numbers (step 4, 8, 9
are referenced from `routing.md`, `squad-issue`) are unchanged. Profiles only fill the `stack:` blocks of AGENTS.md
(untouched); `apply-template.py` / `config-check.py` only cut AGENTS.md at its first `## ` heading and compare bodies.

## core/.claude/skills/create-pr/SKILL.md

- create-pr — REMOVED: "Use this skill to prepare and open a pull request for changes made in this repository."
  → repeats the skill's `description:` front matter; changes nothing a session does.
- create-pr — REWORDED: "**Verify the working tree**: run `git status --short --branch` and `git diff` to confirm what will be
  included, and confirm the `origin` remote exists. Do not include unrelated or uncommitted work the user didn't ask
  for. If there are no relevant local changes and no unpushed commits, stop and say so plainly."
  → same step, tighter: both commands, the `origin` check, leaving out unasked work and the stop condition kept.
- create-pr — REWORDED: "**Create a branch** if you are still on `main` (or another base branch) — never commit directly to it.
  Derive a short kebab-case name from the work (e.g. `add-season-aggregates`, `fix-path-mapping`), or use the name the
  user supplied. If you are already on a feature branch, stay on it."
  → one sentence with every condition; one of the two name examples dropped (`fix-path-mapping` kept).
- create-pr — REWORDED: "**Verify tests exist** for what the diff changes: … before the PR opens."
  → "for what the diff changes" repeats "logic the diff adds or changes"; "before the PR opens" is given by the step
  order (step 3 of 10, before the push).
- create-pr — REWORDED: "Fix any failures before proceeding — do not open a PR with failing checks, unformatted code or
  outstanding analyzer diagnostics. This step is the gate before the PR; CI is not meant to find anything here."
  → "Fix every failure before going on: this step is the gate before the PR, CI is not meant to find anything here."
  The enumeration (checks, formatting, analyzer) is the list of gates directly above it.
- create-pr — REWORDED: "**Run the internal review loop** (see below) and resolve what it finds. This happens *before* the
  push, so the pull request opens on a reviewed change instead of collecting review rounds afterwards."
  → "… resolve what it finds, before the push: the pull request opens on a reviewed change." Rule (before the push)
  and its half-sentence reason kept; "instead of collecting review rounds afterwards" goes (see REASON below).
- create-pr — POINTER: "title `[area] Description` per CONTRIBUTING.md — area is one of the areas CONTRIBUTING lists,
  capitalized, no period at the end, no issue number in the description, under 70 characters"
  → "title `[area] Description` as CONTRIBUTING.md says, under 70 characters". `docs/CONTRIBUTING.md`, *Submitting a
  pull request*, states the area from its list, capitalized, no period at the end, no issue number; the 70-character
  limit is not there and stays.
- create-pr — REWORDED: "fill in Description, Issues (link the related issue if one exists, with `Closes #<number>`),
  Reviewer Notes and Test Plan, and check off the checklist items that are actually true (don't check items you
  haven't verified) — including the unit-test, formatting, analyzer, coverage, documentation and dependency items, not
  just the general ones"
  → "fill in Description, Issues (`Closes #<number>` for a related issue), Reviewer Notes and Test Plan, and check off
  only the checklist items you verified, the unit-test, formatting, analyzer, coverage, documentation and dependency
  items included". Every section, item group and the "only what you verified" condition kept.
- create-pr — REWORDED: "Mark the PR ready for review only when *Draft until green* holds; otherwise leave it a draft and
  tell the user what blocks it."
  → "Mark it ready for review only when *Draft until green* holds; otherwise tell the user what blocks it." "leave it a
  draft" is the same as not marking it ready (`orchestration.md`, *Draft until green*: stays a draft until all holds).
- create-pr — REWORDED: "The review happens here, in this session, against the local branch — not as a round trip through
  pull request comments. Each pass is delegated to the `squad-reviewer` subagent; its checklist and round semantics
  live in `.claude/agents/squad-reviewer.md`."
  → "Each pass runs the `squad-reviewer` subagent in this session against the local branch, not through pull request
  comments; its checklist and round semantics are in `.claude/agents/squad-reviewer.md`." (pointer to the agent file
  as a whole, as before)
- create-pr — REWORDED: "Blocking findings → fix each one minimally and commit. Do not widen the change beyond what the
  finding requires."
  → "Blocking findings → fix each one minimally, no wider than the finding requires, and commit."
- create-pr — REWORDED: "If push or PR creation fails, stop and report the failure clearly instead of continuing as if it
  succeeded."
  → "If push or PR creation fails, stop and report the failure." "Stop" already excludes continuing.
- create-pr — REWORDED: "… make sure the corresponding documentation — README.md, ARCHITECTURE.md, SECURITY.md — was
  updated in the same PR (see the template checklist)."
  → "… the same PR updates the corresponding documentation (README.md, ARCHITECTURE.md, SECURITY.md; see the template
  checklist)." All triggers, the three files and the checklist pointer kept.
- create-pr — POINTER: "See [`CONTRIBUTING.md`](../../../docs/CONTRIBUTING.md) for the full workflow and stability policy
  this skill follows."
  → `AGENTS.md`, *Pull requests, contributing and architecture* ("Follow CONTRIBUTING.md for branch/PR naming, the PR
  checklist … and the stability policy"), which every Claude Code session reads through the `@AGENTS.md` import; step
  8 of the skill still links CONTRIBUTING.md for the title.
- create-pr — REASON: "instead of collecting review rounds afterwards" (step 6)
  → rationale for `docs/squad-rationale.md` (create-pr, step 6 / *The internal review loop*): "create-pr reviews the
  change before the push so the pull request opens on a reviewed change instead of collecting review rounds as PR
  comment threads afterwards; a pass in the session is cheaper than a round trip through GitHub."

## core/.claude/skills/review-pr/SKILL.md

- review-pr — REWORDED: "Use this skill to review a pull request on GitHub — someone else's, or your own when you
  deliberately want a second opinion after it is open."
  → "For a pull request on GitHub — someone else's, or your own for a second opinion once it is open."
- review-pr — REWORDED: "For a change that has not been pushed yet, do not use this skill: the internal review loop in
  `create-pr` reviews the local branch before the pull request exists, which is cheaper and does not fill the PR with
  comment threads."
  → "A change not pushed yet goes through the internal review loop of `create-pr` instead: it reviews the local
  branch before the pull request exists, cheaper and without comment threads." Rule and its half-sentence reason kept.
- review-pr — REWORDED: "Delegate the review itself to the `squad-reviewer` subagent (subagent_type `squad-reviewer`)."
  + "Give it the base ref, the head SHA, and the round number — … the commits that were meant to fix them."
  → merged with the next sentence; every input (base ref, head SHA, round, previous findings, fix commits) kept.
- review-pr — REASON/POINTER: "The review checklist, the integration-surface sweep, the severity model and the round
  semantics all live in that agent's definition (`.claude/agents/squad-reviewer.md`), so they stay identical whether
  the review runs before or after the push."
  → kept as a parenthesis "(…; its checklist, integration-surface sweep, severity model and round semantics are in
  `.claude/agents/squad-reviewer.md`)"; the clause "so they stay identical whether the review runs before or after the
  push" goes. Rationale for `docs/squad-rationale.md` (review-pr, step 2): "create-pr and review-pr both delegate to
  the same squad-reviewer agent so the checklist, severity model and round semantics are identical before and after
  the push."
- review-pr — REWORDED: "**Only genuine findings.** No positive remarks, no confirmation that checklist items pass, no
  "looks good" filler, no formatting the formatter already fixes."
  → "**Only genuine findings**: no praise or "looks good" filler, no confirmation that checklist items pass, no
  formatting the formatter already fixes." ("positive remarks" → "praise", every exclusion kept)
- review-pr — REASON: "Lead the review body with the verdict line the subagent produced (`APPROVE`, or the
  blocking/non-blocking counts), so the author can see whether anything is required of them without reading every
  thread."
  → rule kept as "Lead the review body with the subagent's verdict line (`APPROVE`, or the blocking/non-blocking
  counts)." Rationale for `docs/squad-rationale.md` (review-pr, step 3): "The verdict line leads the review body so
  the author sees whether anything is required without reading every thread."
- review-pr — REWORDED: "**Only blocking findings justify another review round.** A non-blocking finding is still
  worked, but does not earn a round."
  → "**Only blocking findings justify another review round**; a non-blocking one is still worked." ("does not earn a
  round" is the bold sentence itself.)
- review-pr — REMOVED: "The rounds are capped, the handled findings are not: every open thread is answered before the PR
  is done."
  → stated in the same file, *Every posted finding gets worked*: "Every posted finding — blocking or not … is worked
  … and its thread is answered and resolved before the PR is done."
- review-pr — REWORDED: "Fix the finding, push, then keep the reply to one line: `Fixed in <sha>: <what changed>`."
  + "The reasoning belongs in the commit message, where it stays with the code; the reviewer verifies the commit, not
  the reply."
  → "Fix the finding, push, then reply in one line: `Fixed in <sha>: <what changed>`. The reasoning goes in the commit
  message; the reviewer verifies the commit, not the reply." Clause "where it stays with the code" goes (REASON,
  rationale: "Fix reasoning goes into the commit message rather than the review reply, so it stays with the code.").
- review-pr — REWORDED: "This skill reviews; it does not silently rewrite the PR. Fixing findings on your own PR is the
  author's step above, and it is explicit — never edit someone else's branch without being asked."
  → "This skill reviews, it does not rewrite the PR: never edit someone else's branch without being asked (on your own
  PR, fixing is the author's step above)."

## core/.claude/skills/decision-consolidate/SKILL.md

- decision-consolidate — REWORDED: "Unreleased decision records are edited in place (`docs/decisions/README.md`), so a
  `Superseded by` chain or several records of one decision that never shipped can be folded into one, and a record
  that grew into several decisions can be split. Released records are never touched."
  → "Unreleased decision records are edited in place (`docs/decisions/README.md`), so they can be folded and split;
  released records are never touched." What is folded and split (chains, records of one decision, oversized records) is
  stated in full in step 3 and in the `description:`.
- decision-consolidate — POINTER: "All output you create — branch name, commit message, PR title and body — is written in
  **English**."
  → `AGENTS.md`, *Commit messages and pull requests*: "Everything written to the repository or to GitHub — code,
  comments, documentation, commit messages, PR titles and descriptions, review comments — is in **English**", which
  every Claude Code session reads through the `@AGENTS.md` import in `CLAUDE.md`. (Branch names are not named there
  explicitly; doubt noted below.)

## core/AGENTS.md

- AGENTS.md — REWORDED: "Project guidance for AI coding agents working in this repository. This one file holds the rules
  for all of them: Codex, … read it directly, …"
  → "The rules for every AI coding agent working in this repository: Codex, … read this file directly, …". Intro only
  (before the first `##`, not part of the Copilot mirror body); all readers, the generation rule and the config-check
  sentence kept.
- AGENTS.md — POINTER: "In the squad skills the member that changed the files runs it on them before handing back
  (`.squad/team.md`, *Shared rules*)."
  → "(in the squad skills: `.squad/team.md`, *Shared rules*)" — `team.md`, *Shared rules*, **Format.** states that the
  member that changed files runs *Format* before handing back, completely.
- AGENTS.md — REWORDED: "including info-level ones that never show up as build warnings but that the CI code analysis
  (e.g. SonarQube Cloud) reports. Check with the *Analyzer gate* … before considering the work done"
  → "including info-level ones the build never shows as warnings but the CI code analysis (e.g. SonarQube Cloud)
  reports. Check with the *Analyzer gate* … before the work is done".
- AGENTS.md — POINTER: "`squad-issue` — fix a bug reported in a GitHub issue with the squad: the Lead plans and picks a
  tier (`docs` / `patch` / `tests` / `trivial` / `standard` / `security`), the Devil's Advocate challenges a plan once
  when `.squad/routing.md` calls for it, Security reviews the plan whenever a security area is touched and the diff of
  a change to a security control, … once the PR is approved by checklist (the Lead decides what is open) a PR
  referencing the issue opens."
  → "`squad-issue` — fix a bug reported in a GitHub issue with the squad pipeline of `.squad/routing.md`: the Lead plans
  and picks a tier, the Devil's Advocate and Security join where routing calls for them, the Tester …, the Dev …, the
  Code Officer …, the Reviewer …, and once the PR is approved by checklist a PR referencing the issue opens." The tier
  list, when the DA challenges, when Security reviews and who decides at PR approval are owned by `routing.md`
  (*Tiers*, *Plan challenge*, step 3 / step 8, *PR approval*); this is a one-line skill summary.
- AGENTS.md — REWORDED: "`decision-consolidate` — merge unreleased decision records (Superseded chains, records of one
  decision) into one record each, split a record that holds several decisions, delete the obsolete ones, lift behavior
  that sits in records into the area documents and fix links and index; released records stay untouched."
  → "`decision-consolidate` — fold, split and delete unreleased decision records, lift the behavior they state into the
  area documents and fix links and index; released records stay untouched." The skill's own `description:` and steps
  carry the detail.
- AGENTS.md — REWORDED: "The reasoning behind code decisions — why something was built the way it was — is recorded by
  the Lead as one decision record per decision …"
  → "Why something was built the way it was is recorded by the Lead as one decision record per decision …".
- AGENTS.md — REWORDED: "… gets worked in that pull request**, blocking or not, now, in that pull request — never
  deferred …"
  → "… gets worked in that pull request**, blocking or not, now — never deferred …" (duplicate "in that pull request").
- AGENTS.md — re-wrapped only (no word change): the intro's reference list, the security-area golden rule, the "product
  PR never changes the squad" sentence and the decision-record paragraph had lines over 120 characters.

## core/docs/ARCHITECTURE.md (*Development process*, outside the project block)

- ARCHITECTURE.md — POINTER: "The squad skills (`squad-issue`, `squad-spec`) wrap that review in a bounded pipeline
  described in `.squad/routing.md`: a Lead plans, picks the tier …; a Devil's Advocate challenges a feature's spec and,
  when routing says so, the plan; Security reviews the plan when a security area is touched; tests come first, …"
  → "… wrap that review in the bounded pipeline of `.squad/routing.md`: a Lead plans, picks the tier that decides how
  much of the pipeline runs and owns every decision, tests come first, …". When the Devil's Advocate and Security run
  is owned by `routing.md` (*Spec challenge*/*Plan challenge*, step 3) and each member's charter; this paragraph is an
  overview.
- ARCHITECTURE.md — REWORDED: "The reasoning behind individual choices is kept out of this document and recorded instead
  as decision records in `docs/decisions/`; this document describes how the system works and links a record where a
  guarantee or flow is the result of one."
  → "The reasoning behind individual choices is recorded as decision records in `docs/decisions/`, not here; this
  document describes how the system works and links a record where a guarantee or flow results from one."

## Rationale entries for docs/squad-rationale.md

1. create-pr, step 6 / *The internal review loop*: create-pr reviews the change before the push so the pull request
   opens on a reviewed change instead of collecting review rounds as PR comment threads afterwards.
2. review-pr, step 2: create-pr and review-pr delegate to the same `squad-reviewer` agent, so the checklist, severity
   model and round semantics are identical whether the review runs before or after the push.
3. review-pr, step 3: the verdict line leads the review body so the author sees whether anything is required of them
   without reading every thread.
4. review-pr, *Answering findings on your own PR*: the reasoning of a fix goes into the commit message rather than the
   reply, so it stays with the code.

## Word counts (before → after)

| File | Before | After | Δ |
|---|---|---|---|
| core/.claude/skills/create-pr/SKILL.md | 1,347 | 1,194 | −153 |
| core/.claude/skills/review-pr/SKILL.md | 802 | 700 | −102 |
| core/.claude/skills/decision-consolidate/SKILL.md | 591 | 550 | −41 |
| core/AGENTS.md | 1,487 | 1,399 | −88 |
| core/docs/ARCHITECTURE.md | 317 | 285 | −32 |
| **Total** | 4,544 | 4,128 | **−416** |

Checks: `python3 tools/template-check.py` exits 0, no FAIL/ERROR/shared-run line from these files (only the expected
"sentence removed" warnings, answered above); `python3 -m unittest discover tools`: 646 tests OK.
