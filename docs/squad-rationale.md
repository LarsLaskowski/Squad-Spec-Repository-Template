# Squad rationale

Why the squad's rules are the way they are. The rules themselves live once each in `core/` (mostly
`core/.squad/routing.md` and `core/.squad/team.md`) and are rolled out to every target repository; this
document stays in the template repository, so the evidence behind a rule never costs a squad member a word of
its context. Each section names the rule and where it lives. Change a rule there, and record new evidence for
it here.

## Security plan review follows the security areas (routing.md, Tiers)

Security reviews the plan whenever *Security areas touched* is not "none", whatever the tier, and reviews the
diff only on tier `security`. Across the squad's first 75 runs about 80 % were `security`, because nearly every
change touches a security area — while the Security diff review found little that the plan review and the
Reviewer had not. The plan review, in contrast, found real defects in 45–73 % of the runs that had it. So the
plan review follows the security areas, and the diff review stays with the changes to a control itself.

## A patch runs only the gates its files need (routing.md, Gates of a patch)

A `patch` is small by definition — a few exact edits, no logic change — so its step 7 runs the checks its
files need and nothing else. The complete analysis, and for a `patch` without production code the full suite
and the overall coverage figure, are left to CI on the draft pull request.

## No Coverage gate for a change without code (routing.md, Changes without production or test code)

A change that touches no production or test code cannot alter coverage, so the *Coverage gate* is not
applicable; `coverage-check.py` reports only the overall figure for such a diff.

## The image build check, not a full-tree build (routing.md, Criteria verified only in CI)

A build or publish from the full working tree restores with every source present and can hold an output the
image's restore from the project files alone never produces. In Vandox#24 a framework script the plan had seen
in a full-tree publish was missing from the image, and only the CI release build caught it after the PR was
open.

## Untestable files are found in the plan (routing.md, Code a unit test cannot cover)

In Vandox#24 the repository's own browser scripts, without a Node build, counted as new code without coverage
(66.8 %) and failed the CI quality gate after the PR was open. Listing such files in the plan, and excluding
them from the coverage measure in every place that computes it, moves that discovery before the PR.

## Continue a member, up to a cap (routing.md, Continuing a member)

A fresh launch reloads 40 k to 50 k tokens of instructions and code the member already knows (`AGENTS.md`,
`stack.md`, `project.md`, the plan and the code); a continuation keeps that context. But each continuation
reloads the agent's whole conversation, so its cost grows with every round: after five continuations or
300,000 reported tokens a fresh launch with a short hand-over is cheaper than another continuation.

## Hand each member only what it needs (squad-issue, introduction)

Every fresh launch starts with an empty context, so what the orchestrator passes is what the launch costs.

## Batch commits after the PR (routing.md, Commits and The stop hook)

After the PR every push re-triggers CI and the code analysis — a full CI cycle — so edits are batched and
committed once per round, and a half-finished tree is never pushed to answer the stop hook.

## Mergeability is read first (routing.md, Merge conflicts)

A pull request with a conflict against its base branch gets no merge commit, so CI usually never starts on it:
its checks stay missing or pending, and waiting for them waits forever. `decision-check.py` reports a record
number used twice and a link to a record file that does not exist, so it is the check after a renumbering.

## One build at a time (routing.md, Concurrency)

Concurrent builds and test runs share build output and caches and break each other.

## Verbatim documentation fixes need no delta round (routing.md, Verbatim documentation fixes)

The text is the reviewer's own, from the reviewer's own round. Vandox#194 and Vandox#19 each spent an Opus
launch on confirming two commas and one sentence; in the 14 Vandox runs after that, 6 of 8 blocking findings
were such documentation edits, each worked by a Dev launch, a gate run and a delta round.

## Model and effort per role (team.md, Members; the agent files' front matter)

The effort is set per role in the agent file so a session's effort setting does not change every role at
once, and no step raises it by default. The plan of a feature ran on `high` until Vandox#19 (1,188 s and
307 k tokens for the plan, and a `CHANGES_REQUIRED` from Security all the same), while the plan of Vandox#20 on
`medium` went through challenge and security review with the same rigor; a run on `xhigh` costs about half the
member time of a feature run (Vandox#17).

The Devil's Advocate runs on Opus because its value is the major objection, and that is what it lost on
Sonnet: on Opus (until 2026-10-10) it raised 0.4 to 0.6 major objections per run and changed 22 of 25 plans; on
Sonnet, with the same plans and the same instructions, 0.05 to 0.3 — the minor objections stayed, the ones
that change a plan disappeared. One challenge costs about 55 k tokens on Sonnet, little against the 0.5 M to
1.5 M of the run it protects. Every run records launches, tokens, tool uses and seconds per role in its
working record (`squad-log.py --summary`), which is the evidence for the next change.

## Run metrics are posted as printed (squad-issue, steps 1 and 12)

Launches, tokens, tool uses and seconds per role are what tunes the squad's models and effort over time, and
the Orchestrator row (wall time, the part no launch covers, the gate runs) shows the orchestrator's own share.
`squad-log.py` refuses what would falsify them: fewer than 1,000 tokens (every launch loads its agent file
first, so a smaller figure is a placeholder), a member cell that names two members (`--amend-last` could not
tell their usage apart), a second amend of the same row.

## Fetch main and the tags at intake (squad-issue and squad-spec, step 1)

A stale local `origin/main` makes `scope-check.py` report files that are not the change's, and a checkout
without the release tags makes every decision record look unreleased. A cloud checkout does not fetch tags,
so an empty local `git tag --list 'v*'` proves nothing; the Lead confirms with `git ls-remote --tags origin`.

## A parser plan needs a real sample (squad-devils-advocate.md, Sample; routing.md, Escalation)

A plan for a reader of an external format built from a description alone lets every reviewer after the plan
find a case the description did not cover: Vandox#20 took two major objections, three Security rounds and three
review rounds for a parser without the real log.

## Verified facts in the plan (squad-lead.md, mode plan)

A plan built on an unchecked claim is the most frequent defect the reviewers find later; hence every claim in
*Verified facts* with its evidence, and `unverified` with its measurement and owner.

## Measured claims (team.md, Test doubles that model a real component)

A test double that copies a real component is only as good as that copy, and every gate and test passes on a
wrong one; a security property resting on an unmeasured claim gets repeated into records and documentation
before anyone measured it. Security reports all bypass classes of a guard in one round so the plan loop needs
no further `CHANGES_REQUIRED` for a sibling form.

## The Tester never implements (squad-tester.md, mode tests-first)

Implementing a feature to see its tests pass is the Dev's step; doing it in the Tester's launch doubles its
cost.

## The integration surface counts as much as the diff (squad-reviewer.md, Round 1)

Most findings that surface late in a review come from a change touching a registration, a documented guarantee
or an instruction file elsewhere, not from a bug in the new lines.

## Logger arguments are checked by name (squad-reviewer.md, The integration surface)

The CI code scanning (e.g. CodeQL) judges a logged value by its name and reports it only after the PR is open,
where no local gate sees it.

## config-check.py on instruction changes (create-pr step 4; squad-reviewer.md, Inputs)

Claude Code silently drops an agent or skill whose front matter does not parse, and the two instruction files
must stay identical from the first `##` heading on.

## Gates before the review are blocking (squad-reviewer.md, The gates)

The format, analyzer and coverage gates run before the pull request, so nothing after the review catches what
they report.

## Later rounds review only the delta (squad-reviewer.md, Round 2 and later; create-pr; review-pr)

A full re-review of an unchanged diff always turns up something new; that is what makes a loop endless — and
turns three findings into four rounds — not evidence that the change is bad. Only blocking findings start a new
round, so the loop converges, while every posted finding is still handled.

## Posted findings are worked now (AGENTS.md, Related skills; create-pr; review-pr)

No "next change that touches this code" is scheduled, and the session holding the context to act on a finding
will not exist later: a deferral drops the finding. A note that only exists in a conversation is lost when the
session ends. Re-running the gates before each push matters because a fix that turns CI red costs more than the
finding did.

## The PR documents the change (AGENTS.md, Related skills; create-pr)

The internal review loop is a working step inside one session, not part of the change's history, and a reader
of the PR has no use for it.

## Retired: "Code Officer only" on Format (team.md, Shared rules)

Older seeded `stack.md` files label *Format* "Code Officer only"; the rule is now that the member that changed
the files runs it. A refresh carries the new label into the seeded file (adopt-template, step 1).
