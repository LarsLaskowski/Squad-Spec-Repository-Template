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

## Continue a member, up to a cap (orchestration.md, Continuing a member)

A fresh launch reloads 40 k to 50 k tokens of instructions and code the member already knows (`AGENTS.md`,
`stack.md`, `project.md`, the plan and the code); a continuation keeps that context. But each continuation
reloads the agent's whole conversation, so its cost grows with every round: after five continuations or
300,000 reported tokens a fresh launch with a short hand-over is cheaper than another continuation.

## Hand each member only what it needs (squad-issue, introduction)

Every fresh launch starts with an empty context, so what the orchestrator passes is what the launch costs.

## Batch commits after the PR (orchestration.md, Commits and The stop hook)

After the PR every push re-triggers CI and the code analysis — a full CI cycle — so edits are batched and
committed once per round, and a half-finished tree is never pushed to answer the stop hook.

## Mergeability is read first (orchestration.md, Merge conflicts)

A pull request with a conflict against its base branch gets no merge commit, so CI usually never starts on it:
its checks stay missing or pending, and waiting for them waits forever. `decision-check.py` reports a record
number used twice and a link to a record file that does not exist, so it is the check after a renumbering.

## One build at a time (orchestration.md, Concurrency)

Concurrent builds and test runs share build output and caches and break each other.

## Verbatim documentation fixes need no delta round (orchestration.md, Verbatim documentation fixes)

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

The Tester of a `security` run runs on Opus (orchestration.md, *Launch model*), the Dev stays on Sonnet. Evidence: the working records of 123 issues
in Vandox, Seluna and PlexToJellyfinSync up to 2026-10-25 (107 runs with review rows, 74 with usage per launch:
984 launches, 81 M tokens — Lead 27 %, Tester 25 %, Dev 23 %, Security and Reviewer 9 % each). About 110
blocking review findings: about 55 documentation that contradicted the code, about 30 missing or weak tests and
about 27 implementation defects, the latter in a few runs and in cases neither plan nor tests named (lifecycle,
parser edge cases, error paths). In all 16 runs in which the Dev disputed a Tester's test, the Lead found the
test or a plan fact wrong, not the Dev (e.g. Vandox#286, #279, #278, Seluna#16, #65, #66). So the Dev on Sonnet
implements the plan reliably, a more detailed approach in the plan addresses no measured defect, and the tests
are the weak link: missing and wrong tests outnumber implementation defects. 85 of the 123 runs were tier
`security`, where a missed edge case costs most. The override covers every Tester launch of such a run, not only
`tests-first`, because the missing tests were found after the coverage step.

The override stands in orchestration.md, where the orchestrator reads its launch procedures, and `squad-log.py`
refuses `--agent squad-tester` alone in a run whose plan names tier `security`. Evidence: in the week after the rule
was added to team.md (47 runs in Vandox, Seluna, DockerUpdateGuard and Censio, 2026-10-26 to 2026-11-01, all on
the refreshed template), all 55 Tester launches of security runs were logged as `sonnet/medium`. The skills'
launch step named no model, and `--agent` reads the model from the agent file, so even an applied override
would have been logged as Sonnet; the per-model summary rows that are to measure the override need the
`--launch` the script now asks for.

## Documentation claims are traced (squad-dev.md, Documentation)

Evidence: the same 47 runs. About 34 of about 50 blocking review findings were documentation that contradicted
the code, more than in the runs before, although the Dev has written the documentation against the green code
since 2026-10-25. Most were a claim of completeness, order or number the code did not bear out: "contacts only the
Trivy server and the registries" while the Docker socket is contacted first (DockerUpdateGuard#372), a check
described as automated that was not (Censio, feature 4), a budget one D1 statement short and then a new wrong
figure in the fix (Seluna#110), a step order the code reverses (Censio, feature 9). Naming the line or measurement
a sentence rests on is the check that finds these before the review does.

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

## Anonymized samples replace whole fields (squad-lead.md, mode plan)

In Vandox#33 the Lead anonymized the user's real `/proc/net/tcp6` tables but swapped only the first 32 bits of
each IPv6 address, so two groups of the server's real prefix stayed. The check grepped for the original encoded
strings and missed it; Security caught it only after the commit was on a public branch. Hence whole-field
replacement and a check that decodes each field and compares it with the real values, prefixes included.

## Task groups are a column (specs/_template/tasks.md; plan-check.py)

`squad-spec` runs steps 4–6 per task group, but `tasks.md` had only numbered rows with *Depends on*: in
Vandox#33 and Seluna#15 the orchestrator invented the groups itself (by dependency layer, or one launch per
improvised slice). The Lead now fills a *Group* column and `plan-check.py` checks that every row has one and a
group's rows are consecutive.

## Verbatim fixes are whole sentences (squad-reviewer.md, Hard constraints; orchestration.md, Verbatim documentation fixes)

In Vandox#33 a finding offered a "suggested addition after '…)'": applied literally, the clause attached to
the wrong antecedent and changed the meaning, so the verbatim fix became an ordinary fix round.

## plan-check.py rejects control characters (plan-check.py; scope-check.py)

In Vandox#278 the Write tool turned an escape in `plan.md` into a literal U+202E. `plan-check.py` let it
through steps 2–6, and only `scope-check.py` in the docs step found it, which cost an extra Lead launch during
implementation. Both scripts now share the check (`analyzer_common.py`).

In Seluna#16 (pull request Seluna#79) the Lead's plan table for AC14 contained a literal U+202E, `scope-check.py`
refused it and the orchestrator escaped it by hand: the check only rejects a plan after it is written, and the
Lead's `plan` mode had no instruction to prevent it (Seluna#80, second lesson). The rule now sits in
`.squad/team.md` (*Escapes in files*), and the Lead's `plan` mode points to it, so the first `plan-check.py` run
passes instead of costing a revise round.

## A new mode is a fresh launch (orchestration.md, Continuing a member; squad-issue, steps 6 and 9; squad-log.py)

The rule stood only in *Continuing a member*: in Vandox#278 the orchestrator continued the Dev's `skeleton`
agent for `implement`, in Seluna#15 the Lead's plan agent for `approve-pr`. The steps that start a new mode now
say "fresh launch" themselves, and `squad-log.py` warns when a continuation is logged at another step than its
fresh launch without naming a fix, delta or revise round (a step number alone cannot tell a fix round of step 7
or 8 from a new mode).

## The layout of new output is the Lead's (squad-lead.md, mode plan)

In Vandox#278 the plan named a report section's texts and criteria but not its layout, so the Tester fixed ten
layout choices (heading level, list structure, order, when cap notes appear) in the tests-first step — product
decisions the Lead owns.

## Members read other revisions without a checkout (team.md, Git and GitHub; orchestration.md, Commits)

In Seluna#15 `squad-security` ran `git checkout <sha>` to read the plan commit; HEAD was detached and the
orchestrator's next interim commit landed on it. Every plain form of that command (`-C`, `cd … &&`, `env`, a
variable prefix, an absolute path) was already denied by `git-guard.py` and now has a test, so the hook most
likely did not fire for that call; the one form found to pass it, a command run through `bash -c`, `sh -c` or
`eval`, is checked now too. Since a guard can miss, the rule in *Shared rules* says how to read another
revision, and the orchestrator checks `git symbolic-ref -q HEAD` before every commit.

## The Git guard runs from the project settings (team.md, Git and GitHub; config-check.py)

Members kept running Git writes the guard denies: `git checkout <sha>` in Seluna#15 and Vandox#286, `git rm` and
`git mv` in Vandox#40, none of them refused. A test in a cloud session (2026-10-25) showed why: a `squad-*` agent
ran `git rm` without a denial, because Claude Code skips the front-matter hooks of a project agent in a folder
without workspace trust, and a cloud or `-p` session never gives that trust. Hooks in `.claude/settings.json` run
there and also inside subagents, with the subagent's `agent_type` in the hook input, so the guard is declared there
and decides only for `squad-*` agents; the orchestrator keeps its Git writes. A second cloud session with the hook
in `.claude/settings.json` confirmed it: the same `git rm` was denied to `squad-code-officer` and allowed to the
main session. The hook now runs before every Bash
call of a session, so a machine without `python3` shows a hook error outside the squad too.

It happened again in Vandox#286 (issue 172 of this repository): after the review round the working tree's
`HEAD` was detached at the reviewed code SHA (reflog `checkout: moving from <branch> to 533be0d`), the
orchestrator's next commits went onto it, and every `git push -q origin <branch>` printed nothing and pushed
nothing, because the branch still pointed at `533be0d`; only the opened PR's old head showed it. The Reviewer
and Security agent files now state the rule themselves, and every push is checked against `origin/<branch>`
without `-q`, so a push that did not move the branch is caught at once. Recovering the detached commits needs
`git merge --ff-only` after the switch, or they are left behind.

## Retired: "Code Officer only" on Format (team.md, Shared rules)

Older seeded `stack.md` files label *Format* "Code Officer only"; the rule is now that the member that changed
the files runs it. A refresh carries the new label into the seeded file (adopt-template, step 1).

## Lead mode docs, interim notifications, test-defect routing, PR body links (squad-lead.md; squad-issue, step 1; routing.md, Loop limits; create-pr, step 8)

Evidence: the squad-spec run of Vandox#35 (38 launches). The plan assigned the area documents and
`docs/ARCHITECTURE.md` to the Lead, but the Lead had no mode for them, so the orchestrator improvised a launch.
A subagent waiting on its own background work produced an interim task notification and a final one with other
numbers (179,088 tokens / 554 s, then 179,882 / 844 s); a row amended from the interim one needed
`--replace-last`. Twice the Dev reproduced a fixture defect (a `/proc/meminfo` fixture without a space after the
colon; a rig that kept `Uptime` constant while the clock advanced) and once a test helper expected the wrong
error text; the orchestrator verified each and sent it straight to the Tester, which is faster than the Lead
round for a disputed expectation. `create_pull_request` and `update_pull_request` rewrote inline Markdown links
in a body into a broken form, relative paths and full URLs alike.

## Skeleton per task group, plan size limit, log after step 10, interim usage (plan-check.py; squad-log.py; squad-issue, steps 1 and 10; tasks.md template)

Evidence: the squad-spec run of Vandox#36 (72 launches, 11 task groups). Group G7 had no new type, but the plan's
*Signatures* listed `Options.Kernel`, `Options.StateDir` and six constants, and `tasks.md` had no skeleton row for
it: the Tester wrote tests against code that did not compile (the whole package failed to build, old tests
included) and had to ask for a skeleton step; G9 (`procstats.ReadBootID`) went the same way in small. The plan
grew to about 11,300 words through challenge rounds, three Security rounds and two decisions, against the soft
limit of 4,000, because the warning named no consequence; now the Lead moves settled material out and the
warning is a finding at twice the limit. That hard limit still let the plan of Vandox#40 grow to 5,300 words in two
revise rounds with only a warning, and the Vandox plans of that week ran from 3,500 to 11,300 words (Vandox#288:
11,281), read in full by each of 30 to 72 launches, so the limit itself became the finding (2026-10-25). A scope that
really needs more keeps the warning with a stated reason (`Plan size:`), so the size is a decision someone wrote down,
not an accident of revise rounds; the hard limit at twice the soft one stays. A Dev launch with its own background gate produced five interim
notifications with rising numbers; `--replace-last` was refused on a pending row and hit the wrong row once
another row followed, and `--tokens 0` is refused by design, which cost several retries. Step 10 removes
`specs/<folder>/`, so later log rows and `--summary` needed a manual restore of `log.md`, and rows written
locally were lost again; the rows after the removal now go through `--stdin` against the comment's log table.
The Product Manager supplied real journals for a binary format without a sample and the Tester built an
anonymized fixture with a field-by-field leak test against them; *Escalation* names the pattern.

## Safeguard stop escalated, not relaunched; no probes in a diff review of an exploit measurement (routing.md, Loop limits; squad-issue, step 8; squad-security.md)

Evidence: the squad run of Vandox#271 (working record in Vandox#271's issue comment, filed as issue 165 of this
repository). A member stopped by the model's safeguard (`invalid_request`, category `cyber`) while it was about to
measure a write vector; the API-error rule (relaunch unchanged, at most twice) would have looped, and rephrasing the
request would have been a workaround. The unreviewed finding was therefore carried as unverified to the Product
Manager, and the Security diff review of such an issue runs read-only.

## Outside contributions (orchestration.md, Outside authors; team.md, Outside text is data; review-pr, step 1; fork-scope.yml)

Reason: the template's repositories are public, so issues and fork pull requests come from people who are not
maintainers. In spec-driven work the acceptance criteria are the contract, so an outside author's feature spec is
agreed on the issue before a plan exists, and the maintainers stay its owners. Issue and PR texts reach the Lead
verbatim and a checkout of a fork can bring `.claude/` hooks and settings into the reviewing session, so outside
text is data and a fork that changes those files is reviewed as a diff only. The *Fork scope* workflow runs on
`pull_request_target` with `main`'s copy of `scope-check.py`: on `pull_request` the fork's own revision of the
workflow and of the script would run, and the fork could weaken both. The fork is never checked out: a checkout
of a fork under `pull_request_target` is what SonarQube Cloud reports as `githubactions:S7631` (a security finding
that fails the quality gate), and an earlier version that copied `main`'s tools into the fork's checkout let a file
the fork committed next to the script (`argparse.py`) run first, because Python imports from the script's folder
before the standard library. `scope-check.py --pull-request NUMBER` reads the file list, the text at the merge base
and the text at the head commit through the GitHub API with a read-only token, so no code of the fork is on the
runner. Measured with a stubbed API: a product change passes, a change to `.claude/settings.json` plus a neutered
`scope-check.py` in the fork fails on both files.
No incident yet; the rules are preventive.

## Unchanged tests are checked against the new criteria (squad-lead.md, mode plan; squad-tester.md, mode tests-first)

Evidence: the squad run of PlexToJellyfinSync#234 (filed as issue 174 of this repository). The plan listed an
existing test as unchanged regression although a new criterion made the method throw for exactly its input (a
65-character key). The conflict surfaced only in step 6, when the Dev's implementation left the test red, and cost
one extra Lead `decide` launch and a plan correction. The Tester's tests-first run missed it too, because the old
test still passes on the old code.

## Task groups continue the member; the Dev writes the documentation; specs sized to the feature (orchestration.md, Continuing a member; squad-dev.md, Documentation; squad-lead.md, mode spec; plan-check.py)

Evidence: the squad runs of 2026-10-18 to 2026-10-25. The Vandox features cost about 400 tokens per added line
against about 245 before, with 30 to 72 launches a run: steps 4–6 launched the Dev and the Tester fresh for every
task group (Vandox#288 had 9 to 11 groups), and each fresh launch first read the rules, the spec and the plan —
about 60,000 to 100,000 tokens, a skeleton stub in Vandox#288 58,646 tokens in 16 seconds — while a continued launch
cost 1,000 to 20,000. The Lead (Opus) wrote the area documents and `docs/ARCHITECTURE.md` in its own launches of
150,000 to 300,000 tokens, written against the plan's strings: documentation that contradicted the code was the most
frequent blocking review finding (five of six in DockerUpdateGuard, seven of twelve in PlexToJellyfinSync). The
specs of PlexToJellyfinSync ran to 2,000 to 5,250 words for changes of 21 production lines in the median, and every
later launch reads the spec in full.

## Security areas of manual changes, the guard of the security tier, AGENTS.md project blocks (AGENTS.md, golden rules; routing.md, Tiers and Scope of a product PR; scope-check.py)

Evidence: the squad runs and manual pull requests of 2026-10-18 to 2026-10-25. Manual pull requests changed a dependency (Seluna#92, npm
`overrides` for eight Dependabot alerts) and workflow token permissions (DockerUpdateGuard#327, #328) without a
review, because the rule for changes outside the squad named only the list in `.squad/project.md`, while the squad's
own routing counts CI, build configuration and dependencies too. Leads read "a guard whose purpose is to stop an
attacker" to cover any bounded parser of untrusted input and "in doubt the higher one" as doubt about the definition
(Seluna#82, Vandox#282, #308): the extra Security diff review found nothing blocking in those runs. Seluna#106: the `docs`
tier allowed the project blocks of `AGENTS.md`, but *Scope of a product PR* forbade the file, so a stale project
block could be fixed only in a squad-maintenance PR. A pull request from a fork still changes neither file:
those blocks are text every agent reads.

## No word budget; removed sentences are reported; the orchestrator's procedures in their own file (AGENTS.md, Writing rules; template-check.py; orchestration.md)

The word budgets of the 2026-10-18 consolidation were met more than once by shortening another rule, and a rule or
its reason got lost on the way: the consolidation itself lost five rules its review had to restore, and later
lessons were written shorter than they needed to be to fit. Budgets became warnings (#181), but the pressure to
justify a larger file stayed. What costs a run is reading, not writing: the Lead reads `routing.md` in full on every
launch, and about 2,100 of its 6,300 words were procedures only the orchestrator follows (commits, the stop hook,
draft until green, merge conflicts and the like). So size is now information, a removed sentence must be answered in
the pull request, cuts happen only in a consolidation of their own (decided 2026-10-25), and those procedures moved to
`orchestration.md`, which the members need not read.


## New scope on an open PR, no deliberately red head, continuation cap reported (routing.md, Loop limits; orchestration.md, Commits; squad-log.py)

Vandox#324 (feature 42) took 57 commits and 70 failed CI runs over 58 hours after it was opened. Most of it was no
defect: after the PR opened, the Product Manager asked for an install bundle instead of a repository checkout, then
for single-command installs and a manifest, and the run built each request on the open PR with "work in progress"
commits. Its tests-first skeletons were pushed red on purpose, so CI failed by design on several heads. A request
that adds behavior now goes to the Lead first (a follow-up issue by default), and a red tests-first commit is
pushed only with the implementation that makes it pass. In the week of 2026-10-25 several runs also continued one
agent 9 to 12 times and up to 590,000 tokens (Seluna#123 and #130, Vandox#322, #324 and #349) although
*Continuing a member* asks for a fresh launch after 5 continuations or 300,000 tokens; Seluna#123 reported it as an
orchestrator miss. `squad-log.py` now warns when such a continuation is logged and lists it in the summary.

## A code convention binds only its own language (team.md, Shared rules)

In Vandox#346 the Dev applied the .NET profile's `== false` instead of `!` to Go code: in a repository with two
profiles, `AGENTS.md` lists both profiles' conventions next to each other, and nothing said that one profile's rule
stops at its language.

## The Sonar gate reads the pull request only (routing.md, Pipeline step 7 and Early draft PR; sonar-check.py)

In the week of 2026-10-25 the branch scan of step 7 ran in every squad run across five repositories and never
produced a result. With the network secret the scan uploaded, but reading it back failed: SonarQube Cloud answered
HTTP 403 ("not allowed to access data from non main branches") for the organization, and before #203 also HTTP 400
on mixed file qualifiers; where no `dotnet-sonarscanner` was restored it did not start at all. Every real finding
(Seluna `text:S6389`, Vandox `S5332`, `S1192` and `S7684`, Censio `S7020`, `S8233` and `S8431`) came from the
analysis of the pull request in step 11. #211 had made a Sonar gate that could not run a reason to open the draft
pull request right after step 7, but every later push then runs all of CI again, so the Product Manager decided
(2026-11-01) to drop the branch scan and that trigger: `sonar-check.py` keeps only its `pr` mode, read in step 11.

## Session usage from the transcripts, not from `/usage` (routing.md, Pipeline step 12; session-usage.py)

`/usage` cannot be run by the agent, and copying its panel gives only the "What's contributing" text; the cost and
token table exists on screen only. #223 and #224 had the orchestrator ask for a screenshot and transcribe it, which
the Product Manager found impractical for every run (2026-11-03). Claude Code writes the same figures to its
session transcripts: every API response carries its model and token usage, every subagent has its own transcript
under `<session>/subagents/` with its agent type in a `.meta.json` (its tokens are not in the session's
transcript), and a `cost-state` record holds cost, API time and lines. That record is written only when the
session pauses (five times in a two-day session), and it alone includes Claude Code's background calls. Compared
with `/usage` on 2026-11-03, the transcripts matched output and cache-write tokens within a few percent (Haiku
exactly: subagent plus background calls), but showed 15-20 % fewer input and cache-read tokens, and the snapshot
said $1.33 where `/usage` said $3.85, because it predated the day's work. The Product Manager decided to drop the
cost entirely: `session-usage.py` prints the transcript tokens as a lower bound, and costs are calculated from
them with the prices given when they are needed. The format is Claude Code's internal one; a record the script
cannot read is skipped.

## Pending continuations, Tester model, manual-test build, skeleton body, changelog row, clock exceptions (squad-log.py; orchestration.md, Launch model and Continuing a member; routing.md, Criteria verified only in CI; squad-dev.md, mode skeleton; squad-lead.md, mode plan; profile testing blocks)

In LarsLaskowski/Censio#11 (#222) `squad-log.py` refused `--continued-from` on a pending row, so a continued
launch's row could only be written once its notification arrived; the same run passed the agent-file model of
a first Tester launch in a tier-`security` run on to every continuation, and a plan asked for a manual test by
the Product Manager before step 9 that only worked from a local publish of the branch head, since no CI build
exists before step 10 without an *Early draft PR*. In LarsLaskowski/Seluna#140 (#228) the first Tester launch
of a `security` run again omitted `model: opus` (only `squad-log.py` caught it, after the launch), the Dev wrote
`return false` stubs without having read *Skeleton* in `stack.md`, and the plan left out the `CHANGELOG.md` entry
the project's PR checklist asks for, which cost a fix round and a delta review after the PR approval. In
LarsLaskowski/Vandox#315 (#229) the project added a second real-clock exception to its `docs/UNIT_TESTS.md`
(library timers without an injectable clock), which made the template-owned testing block's "the one exception"
false in its `AGENTS.md`.

## Measurements with command and output; prescribed assertions checked (squad-security.md; orchestration.md, A denied measurement; squad-devils-advocate.md, Rules)

In LarsLaskowski/Seluna#141 (PR LarsLaskowski/Seluna#148, filed as LarsLaskowski/Seluna#149 and #231 here)
Security's plan review reported a fact as "measured in the local workerd pool, in a throwaway worktree" with a
results table, while its task notification showed 10 tool uses in 76 s, too few for a worktree, an install and a
test run; the orchestrator could not tell a real measurement from a claimed one and fell back to the Tester's
planned measurement. In the same run the Devil's Advocate told the Tester to assert "exactly one `outbox` row, the
notice" in a concurrency test where the counted delivery also writes its own row, so the instruction could not
hold; the Tester deviated and the Lead had to decide it in step 9.

## Coverage launch fresh, verbatim rewrap, dotnet skeleton pragmas and surrogate escapes (squad-issue step 6; orchestration.md, Verbatim documentation fixes; dotnet stack.md seed, Skeleton and Known pitfalls)

From the DockerUpdateGuard runs for #358 and #363 (DockerUpdateGuard#392, #397, #398). The orchestrator continued
the Tester's `tests-first` agent for the coverage pass: *Continuing a member* already makes the first launch of
another mode fresh, but step 6 named that only for the Dev, so it now names it for the Tester too; `squad-log.py`
warns on the pending row of such a continuation since the pending-continuation change. A Reviewer's verbatim
sentence that is longer than the original inside a hard-wrapped paragraph cannot be applied without rewrapping;
the rewrap is whitespace only and shows as such in `git diff --word-diff`, so it needs no delta round. A .NET
skeleton with private helpers nothing calls yet failed the Release build on S1144 and S1172, and the Dev
improvised pragmas; the seed now names the sanctioned pragma and its removal. `reihitsu-format` also rewrote a
surrogate-pair escape (`\uD83D\uDE00`) into the emoji; the Tester rebuilt the input at run time. The run of #363
(DockerUpdateGuard#392) launched the tier-`security` Tester on Sonnet; the explicit `model: opus` at steps 5
and 6 came with the pending-continuation change.

## The report reads the run's own total row (squad-report.py)

Since #225 the wrap-up appends the output of `session-usage.py` under a "Session usage" heading below the run
metrics, and its per-model table ends in a `| **Total** | … |` row as well. `squad-report.py` took the last total
row of the record, so from then on it read that one (#235): the launches became the leading digit group of the
session's output tokens and the tokens its cache-read tokens. LarsLaskowski/Seluna#144 was reported with 256
launches and 36,619,921 tokens for a run whose own metrics say 24 launches and 1,070,203 tokens; Seluna#148
(141 / 21,205,367), Seluna#150 (107 / 17,217,521) and LarsLaskowski/Censio#99 (359 / 56,874,701) were read the same
way, and the weekly medians from 2026-W45 on were wrong (Censio `security` 29.51 M, Vandox `security` 20.76 M,
Seluna `standard` 21.21 M). The report now reads launches and tokens only above the "Session usage" heading and
only from a total row of `squad-log.py`'s shape, whose Model/effort cell is empty, so a session table posted without
its heading is not taken either. For merges from 2026-11-03 to 2026-11-05 it reads Seluna#144 as 24 / 1,070,203,
Seluna#148 as 9 / 817,445, Seluna#150 as 11 / 529,734 and Censio#99 as 25 / 1,400,838, with the medians Seluna
`standard` 0.82 M and Censio `security` 1.77 M. The session figures count the whole session, the orchestrator and
the cache reads included (#234), so they get four columns of their own (input, output, cache read, cache write)
instead of standing in for the run metrics.

## config-check.py without PyYAML, decision-check.py before the first release, seed text without braces (config-check.py; decision-check.py)

Found in the review of 2026-11-05 against the five consumers (#234, #250). `create-pr` step 4, `squad-reviewer.md`
(*Inputs*) and `adopt-template` step 9 run `config-check.py`, which stopped with "PyYAML is required" on a plain
Python 3.12 in every consumer; only its docstring named the dependency, no `stack.md` seed, SessionStart hook or
README. Installing PyYAML from the hooks would add a network step to every session start and still fail where pip
cannot reach its index, so the script reads the front matter itself when PyYAML is missing: the agents and skills
use `key: value` lines, quoted values, block scalars and lists, and the built-in parser still refuses what made
Claude Code drop a file, above all an unquoted value with `: `. PyYAML stays the parser where it is installed;
a test applies the template and compares the findings of both. `decision-check.py` warned "no local 'v*' tags
although a remote is configured" in every repository before its first release and then treated each record as
possibly released, which LarsLaskowski/Censio met until its first tag on 2026-11-05 (LarsLaskowski/Censio#58);
it now asks the remotes with `git ls-remote --tags` and warns only when one has a release tag or cannot be asked.
Censio's `.squad/project.md` kept the seed's integration-surface bullets with their braces removed ("its
interface", "registration and lifetime", "the test double in the test project", "the component list in
`docs/ARCHITECTURE.md`"), which `config-check.py` found only by the braces; it now also reports a bullet of a
seeded file that reads like a seed bullet's placeholder. Censio's *Guarantees* section said "None recorded yet"
although accepted records such as 0019 state deliberate behavior; no text comparison can tell that, so it stays
with `adopt-template` step 6, which fills the guarantees from the decision records.

## Aliases, every gh write and file ownership in the guards; no security boundary (team.md, Git and GitHub and Files; git-guard.py; file-guard.py; config-check.py)

Found in the review of 2026-11-05 against the five consumers (#248, scope in #234). Hook inputs with `agent_type:
squad-dev` fed to `git-guard.py` at 7571677 let through `git -c alias.ci=commit ci -m x` and `git -c alias.p=push p
origin HEAD` (`-c` was skipped as an option with a value, so the alias's command was never checked), `gh api -XPOST
repos/o/r/issues` (only `-X POST`, `--method POST` and `--method=POST` were read), `gh workflow run`, `gh run
rerun`, `gh secret set`, `gh variable set` and `gh gist create` (groups missing from the list), a `python3 -c` that
runs `git push`, and `echo x > .git/HEAD`. Checking the list against `gh help reference` of gh 2.102 found more that
passed: the command aliases `gh pr new`, `gh issue new`, `gh repo new`, `gh release new` and `gh pr co`, `gh pr
checkout` (a checkout of the working tree), `gh pr update-branch`, `gh issue develop`, `gh repo set-default`, a `-R
<repo>` before the subcommand (`gh pr -R o/r create`), an attached field (`gh api … -ftitle=x`), and `gh alias set`,
the `gh` form of the alias bypass. `gh ruleset` has only `check`, `list` and `view`; a ruleset is written through `gh
api`, which the method check covers. An interpreter, a script, an alias from the user's own configuration or a shell
redirect still reaches Git and every file, and closing that would mean reading every language a member can run, so
the guards are stated to prevent accidents, not to be a boundary.

Which files a member may write was stated only in the agent files and `team.md`; no hook checked it, and every
writing member could edit `.claude/` or `.squad/`. The read-only roles have no Write or Edit tool, but they have
Bash, which the file guard does not read. `NotebookEdit` is guarded with Write, Edit and MultiEdit, so a notebook is
no way around it. The Tester's paths are the ones the coverage gate already reads as tests (`COVERAGE_TEST_PATHSPECS`,
by default `COVERAGE_EXCLUDES`), so one list says what a test file is; a fixture outside it (Go `testdata/`, a .NET
test project file) is reported to the orchestrator or added to that list. Files outside the repository's directory
stay unchecked, because the Tester's throwaway mutation of production code (mode `coverage`) and the Reviewer's
builds run in scratch worktrees there; a worktree nested in the repository (Claude Code's `.claude/worktrees/`) is
judged by its own paths, so working in one is not refused by the `.claude/` rule. The hook runs before every file
write of a session, the orchestrator's included, so a machine without `python3` shows a hook error there too.

## The code check measures coverage again; a stale report is refused (routing.md, Pipeline step 7; squad-issue, step 7; coverage-check.py)

Found in the review of 2026-11-05 against the five consumers (#234, #245). Step 7 ran *Test*, which writes no
coverage report, so its *Coverage gate* judged the report of step 6, and `coverage-check.py` did not check the
report's age. Between the two runs step 7 merges `main` when it moved, and the Code Officer may edit the changed
files (regions, documentation comments, formatting): the report's line numbers then no longer match the files,
and changed lines are counted as covered or as uncovered by mistake. The Reviewer's gate list and the
production-code row of *Gates of a patch* already ran *Test with coverage*. `coverage-check.py` compares the
modification times of the reports with those of the tracked production and test files rather than with the HEAD
commit time: the Code Officer's edits are still uncommitted when the gates run, and a test changed after the run
makes the report stale as well.

## Members never commit, when the Product Manager is asked, area documents outside the squad, the early draft PR in the skill, the Lead reads records by topic (AGENTS.md, Golden rules and Related skills; routing.md, Tiers and Escalation to the Product Manager; create-pr, Notes; pull_request_template.md; squad-issue, introduction and steps 7 and 10; squad-lead.md, Read first)

Found in the review of 2026-11-05 against the five consumers (#234, #246), each item checked against template
commit 7571677. `AGENTS.md` told every agent to commit and push to a feature branch without asking, and `team.md`
makes `AGENTS.md` binding for every member, who never runs a Git write: members kept trying the writes the guard then
denies (*The Git guard runs from the project settings*). `AGENTS.md` and the introduction of `squad-issue` said the
user is asked only when the Lead escalates (the skill: or to confirm a *no change* comment), although *Bug or
feature*, *Outside authors*, *A denied measurement*, *Loop limits* (Plan ↔ Security and the safeguard stop), the dry
run and the manual test involve the Product Manager as well; the cases are now listed once, in *Escalation to the
Product Manager*, the section `team.md` already points to. *Tiers* named a `patch/security` row the table does not
have; it is part of the `patch` row. The checklist of the pull request template and the *Notes* of `create-pr` named
`README.md` and `ARCHITECTURE.md` (`create-pr` also `SECURITY.md`) but neither the area documents nor the decision
records, so a change made outside the squad was not told that a change in behavior updates its area document in the
same pull request (`docs/areas/README.md`). *Early draft PR* stood only in `routing.md`, not in the procedure the
orchestrator follows step by step: LarsLaskowski/Vandox#337 posted the working record and removed `specs/` on its
early draft pull request before the review, and logged that as improvised. The Lead read every decision record
(110 records of about 98,000 words in Vandox, #236), the Devil's Advocate only the index and the records of the
topic; the Lead now reads them the same way, the first step of #236.

## Project knowledge as pointers, size warnings, one record per decision (seed project.md; config-check.py; decision-check.py; squad_settings.py seeds; docs/decisions/README.md, Rules and Size; docs/areas/README.md, Size; squad-lead.md, mode plan; squad-security.md; squad-spec and decision-consolidate; adopt-template, steps 1 and 6)

Found in the review of 2026-11-05 against the five consumers (#234, #236). `.squad/project.md`, which five members
read on every launch, had 15,541 words in LarsLaskowski/Vandox (*Security areas* alone 11,861), 3,725 in
LarsLaskowski/Seluna and 1,911 in LarsLaskowski/Censio (*Test doubles* 1,097). The largest area documents were
Vandox `agent.md` with 42,996 words, Seluna `setup-wizard.md` with 13,304 (a copy of the UI strings of
`src/setup/texts.ts`), Censio `pipe.md` with 5,125 and LarsLaskowski/DockerUpdateGuard `registries.md` with 4,722.
Vandox had 110 records of about 98,000 words; 0088 weighs 38 options with about 19 marked chosen, 0131 34. Seluna 0043
grew to 2,968 words over four issues and DockerUpdateGuard 0014 was extended by three runs (#348, #355, #364).

The cost is stale copies: one fact with several homes goes stale in all but one. Stale documentation was about 22
of 23 blocking review findings in Seluna's 12 latest runs, 10 of 17 in Vandox's 13 latest and 9 of 9 in the sampled
DockerUpdateGuard runs; LarsLaskowski/Vandox#305 repeated one memory figure in `project.md`, `web-ui.md`,
`README.md` and record 0116 (four blocking findings), LarsLaskowski/Seluna#110 a budget figure in record 0041 and the
area document. The causes in the template: the seed's *Security areas* asked to "name the concrete types, files or
endpoints" without bounding an entry, so entries took over limits, drain sequences and token regexes from the area
documents; "extend an existing unreleased record on the same topic" stood in three places, and with releases rare
(Vandox one tag, Censio its first on 2026-11-05) the records stayed unreleased and grew into topic bundles; and no
tool checked the area size rule, "one decision per file" or "the record does not restate behavior". The Lead read
every record until #246 narrowed its *Read first* to the index and the records of the change's topic.

The seed now says that every entry points (files, types or endpoints, and a link) and that values live in the area
document; its placeholder bullets stay as they were, so `config-check.py` still recognizes them, and the guarantee
bullet gains its area link (its earlier form, braces removed, is still reported in repositories adopted before). Security reads the linked area documents of the areas a change touches, since the rules
no longer stand in `project.md`. The limits are warnings, not errors: a repository past them cannot shrink inside a
product pull request, and a failing `config-check.py` would block every run of Vandox until a large rewrite. The
defaults follow the issue (1,500 words for `project.md` and a record, 8 options, 5,000 words for an area document),
are set in `squad_settings.py` and checked only on unreleased records, because a released one is never split. No
tool can tell whether a record restates behavior; its size is the proxy, and `decision-consolidate` lifts the
behavior into the area documents. `decision-consolidate` grouped records "on one topic", the same bundling, and now
groups by decision and splits what the warning names. Seeded files are not refreshed, so `adopt-template` step 1
carries the new structure and settings over, and the shortening itself is a squad-maintenance pull request in the
target.

## The squad's process decisions in one managed file (docs/decisions/process.md; decision-seeds/; decision-check.py; apply-template.py; adopt-template, step 8; orchestration.md, Template-managed files; CONTRIBUTING.md)

Found in the review of 2026-11-05 against the five consumers (#234, #247). `adopt-template` step 8 numbered the
three records of `decision-seeds/` into each product's `docs/decisions/`, and every refresh that changed one of
their rules edited the seeded record in place (unreleased) or added a record that superseded or amended it
(released). LarsLaskowski/Seluna carries the chain 0002 "Squad working records stay off main, and product PRs never
change the squad" (2026-10-14, adopted, superseded by 0022), 0022 with the same title (2026-10-17, superseded by
0037), 0037 (2026-10-25, accepted) and 0044 "Product PRs may change the squad settings file" (2026-11-01, refreshed,
amends 0037). They are decisions of the template, not of the product, yet they take numbers in its log, and every
reader of the index walks past them.

The process decisions are now `docs/decisions/process.md`, a managed file under `core/` that every refresh
overwrites: no number, no status, no index row, so a template change never adds a record to a product's log again.
It sits next to the records rather than in `docs/CONTRIBUTING.md`, whose template text every contributor reads, and
`decision-check.py` already reads only `NNNN-*.md` files, so it ignores the file; the docstring and a test now say so.
The records the seeds left behind are retired once: `apply-template.py` lists those still in force — a source naming
the template, a title of a `process.md` section, or a record that supersedes or amends one, which catches Seluna's
0044 — and leaves out the record that moved them, so the list is empty after the migration. An unreleased one is
deleted; the released ones are superseded together by the one record left in `decision-seeds/`, which names the
file. A released record whose `Superseded by` named a deleted unreleased record gets the new record as its successor
(a released record's status may still change to another `Superseded by`), so no link points at nothing.

## Documentation that still states a changed value (figure-check.py; routing.md, Pipeline step 7; squad-issue, step 7; squad-dev.md, Documentation; squad_settings.py seeds)

Found in the review of 2026-11-05 against the five consumers (#234, #237; evidence in #236). The most frequent
blocking review finding was a sentence in another file that still stated a number, limit or default the change had
made untrue. Neither sweep caught it: the Lead's plan sweep looks for enumerations and "only these …" statements,
and the Dev's documentation rule traces the sentences the Dev writes, so a sentence in an untouched file kept the old
value until the Reviewer found it, at the cost of a fix round and a delta round. LarsLaskowski/Vandox#305 repeated
one memory figure in four files, LarsLaskowski/Seluna#110 fixed a budget figure to a new wrong value, and
LarsLaskowski/Seluna#140 left the old value in the option text of record 0043.

`figure-check.py` is a tool of its own rather than a part of `scope-check.py`, whose findings are blocking and which
runs on fork pull requests through the API: a hit here is only a candidate (an equal number can state another
quantity), so it warns and never fails. It reads the old values per file — what the removed lines hold and the added
lines of the same file do not — so a value moved within a file is no hit, and renames are compared with their old
version. Released decision records state what held when they were released and cannot be edited, so they are not
searched; neither are changelogs, which name old values on purpose, nor the template text of marked files and the
managed `process.md` and `_template.md` files, which a product change cannot fix. The trivial values default to the
single digits, 10 and 100 rather than the issue's 0, 1, 2 and 100: prose numbers its steps, list items and counts with
single digits, and every such line would otherwise be a hit. The Dev runs the tool before handing back the
documentation, when the hits are cheapest; step 7 runs it again after the merge of `main` and the Code Officer's
edits, sends a hit the Dev did not confirm back to the Dev and the rest to the Reviewer. It runs in every tier whose
diff changes production code or configuration, a `patch` included, because it is no gate and costs no build.
