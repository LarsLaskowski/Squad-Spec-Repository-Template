# Changelog

What each release of the template brings to the repositories that use it (`consumers.json`). Every pull request that
changes what a target receives adds a line under *Unreleased*; a release turns those lines into a version section and
is tagged (`AGENTS.md`, *Releases*). Changes before the first release are in the history of `main`.

## Unreleased

- [Profile] The `dotnet` profile supports .NET 11: the seed tool manifest lets `reihitsu-format` roll forward to a newer
  runtime, the seed CI takes the SDK version as a placeholder, the seed Dependabot leaves the next major of the
  ASP.NET Core and EF Core packages to the change of the target framework, and the SessionStart hook warns when the
  SDK `global.json` names is not installed (#322)

## v2026.11.4 — 2026-11-10

- [Profile] The `dotnet` profile's *Writing code* names the analyzer rules that refuse a planned name, S2344 and
  Reihitsu's RH2101 and RH2104–RH2108 for nested types of any visibility, instead of CA1034 and CA1724, which no target's
  analysis level reports (#287)
- [Tools] `gate-stamp.py` refuses in a shallow clone before its first gate when it would run `decision-check.py
  --require-history`, and names `git fetch --unshallow --tags origin`; `squad-issue` and `squad-spec` unshallow at
  intake (#294)
- [Tools] A branch of Markdown files only is stamped with *Format check* alone in every tier, and `squad-next.py` says
  to start a stamp that runs *Test with coverage* in the background (#295)
- [Core] An issue that needs the Product Manager's values (measurements on a real system) waits for them before step
  1, and the Lead records them in `measurements.md`, posted with the working record (#296)
- [Core] Trailing whitespace and a final blank line reported by `git diff --check` are verbatim fixes in any file, and
  `gate-stamp.py --verbatim` accepts a file that differs only there (#297)
- [Core] Step 10 may link any document of the working record but the verification matrix by permalink with a summary,
  instead of re-typing it into the comment, and a feature run posts its `measurements.md` too (#298, #296)
- [Core] A member reports a file it staged by mistake instead of unstaging it, and the Dev checks a claim about code it
  did not change, or marks it unverified (#299)
- [Core] The Lead's revision reads *Signatures* against every changed *Approach*, security and resource statement
  (#300)
- [Core] `squad-issue` says how a request for several issues runs: one run per issue by default, one shared run only
  for one `docs` or `patch` change or on the user's request (#301)
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/.squad/stack.md`

## v2026.11.3 — 2026-11-09

- [Tools] `squad-next.py` counts a verbatim row's findings only by the Reviewer's bracketed tags (`[BLOCKING,
  verbatim]`, `[NON-BLOCKING, verbatim]`), so the word "blocking" in its prose clears nothing, and takes a Lead
  decision as ordering a fix only on `FIX:` in capitals with its colon, so "no FIX needed" or "do not fix now" starts
  no fix round (#282)
- [Tools] `squad-next.py` reads `--- ` and `+++ ` lines as file headers only before a file's first hunk, so a removed
  `-- comment` beside a record status no longer passes as a status-only change, and the verdict line it hands over
  says where the member's report puts it (the Reviewer's starts the report, the others' end it) (#282)
- [Tools] `plan-check.py` leaves out only a *Signatures* line that states its member is deleted ("Deleted:", "is
  removed"), so a new member whose description says it "removes" something is still a planned signature; the usage
  examples of `squad-log.py` log a Reviewer verdict line it can read (#282)
- [Tools] `squad-next.py` moves on after an Orchestrator row that skips step 5 for a task group (`5 Tests first skipped
  (G4)`, or one without a group), takes an Orchestrator coverage row without a group as the coverage pass of every
  group implemented before it, and sends a group of documentation rows alone to the Dev's and the Tester's
  documentation launches, without skeleton, tests first and coverage pass (#284)
- [Tools] `squad-log.py` turns its warning for a continuation of another task group's agent of the same mode into a
  note that names the `--continued-from` step to log instead (#284)
- [Tools] Group `PM` in `tasks.md` holds the tasks of the Product Manager and the Lead alone: `plan-check.py` lets its
  rows stand anywhere in the table and needs no skeleton row for it, and `squad-next.py` runs no member for it (#285)
- [Tools] A working-record comment too long for the whole log links `log.md` and starts its log table at step 10:
  `squad-log.py` and `squad-next.py` with `--stdin` read the earlier rows from the commit before the folder's
  removal, and warn when they find none (#286)
- [Core] The Lead checks every new name in *Signatures* against the analyzer's naming rules before step 4; the
  `dotnet` profile's *Writing code* lists the rules a skeleton has hit (S2344, CA1034, CA1724) (#287)
- [Core] The Tester writes Markdown files under the directories of the test paths (a fixture README); an edit under
  `.squad/` the plan lists (*Test doubles* in `.squad/project.md`) is the orchestrator's, written verbatim from the
  member's text (#288)
- [Tools] `squad-next.py` reads a verdict line whose counts carry notes in parentheses (`OBJECTIONS 1 major (…), 5
  minor (…)`, `BLOCKING 2 (…) | NON-BLOCKING 1 (…)`, `APPROVE (…) on <sha>`) instead of stalling on it, and
  `squad-log.py` names a Reviewer line it can read only in part (#289)
- [Tools] `gate-stamp.py` runs `decision-check.py --require-history` whenever the branch changes a decision record or
  an area document: a released record a shallow clone cannot check fails the gate instead of passing with a warning
  (#290)

## v2026.11.2 — 2026-11-08

- [Tools] A non-blocking finding the orchestrator applied verbatim no longer demands a Lead `decide` launch: the
  verbatim row names each finding by the Reviewer's tag (`[BLOCKING, verbatim]`, `[NON-BLOCKING, verbatim]`) and
  `squad-next.py` subtracts both kinds (#276, #278)
- [Tools] A Lead `decide` row that orders a fix (`FIX` in its `RESULT` line, or "fix now") makes `squad-next.py`
  print the fix launches, the gates and a delta round before step 9, and the step-9 record status is stamped with
  `gate-stamp.py --verbatim` and needs no delta round, also after a full stamp (#279)
- [Tools] Every launch `squad-next.py` prints quotes the exact verdict line of the Reviewer (with `on <sha>`), the
  Devil's Advocate, Security and the Lead in mode `decide`; `squad-log.py` warns when such a row carries none, and
  `--replace-last MEMBER --new-result TEXT` corrects the row's result and keeps its trailer, so the launch is not
  logged twice (#277, #278)
- [Tools] `plan-check.py` lists no skeleton signature for a *Signatures* line that says its member is deleted or
  removed (#278)
- [Tools] `decision-check.py` names the fix of a shallow clone (`git fetch --unshallow --tags`) and, while the release
  of the records cannot be told, reports the records past the size limits as one line that says they may all be
  released and exempt, instead of one split warning per record (#275)

## v2026.11.1 — 2026-11-07

- [Tools] `plan-check.py --matrix` counts a criterion id only in a test file the criterion's row names or the branch
  changes, so the test of an earlier change no longer passes a criterion; `plan-check.py` reports a criterion that
  *Tests per criterion* and *Verification without tests* verify as different kinds, which the matrix also shows as a
  `CONFLICT` row, and, in a plan without production or test code, a *Tests per criterion* cell that names no kind
  and no test the test files hold, such as `check (below)` (#272)
- [Core] The Reviewer's verdict line names the code SHA it reviewed, copied from `git rev-parse`, and `squad-next.py`
  continues a Reviewer whose verdict names no SHA or another code than the gate stamp's (#272)
- [Tools] A plan without API no longer demands the skeleton step: `plan-check.py` lists no signatures for a
  *Signatures* section that starts with "none" or states "no new API", "no public API changes" or "no skeleton", and
  `squad-next.py` takes an orchestrator row that logs step 4 as skipped as step 4 done; the plan template keeps
  private members out of *Signatures* (#268)
- [Core] The Reviewer starts its report with one of three exact verdict lines, `BLOCKING 0 | NON-BLOCKING <m>`
  when only non-blocking findings remain, and `squad-next.py` also reads `VERDICT: NON-BLOCKING <m>` as no blocking
  finding instead of a row without a verdict (#267)
- [Core] A dry run's unconfirmed statements are `unverified` facts in `plan.md`, never markers in the published
  document, and a feature spec asks how far a guide may rest on third-party pages; a link or statement on a page the
  session cannot open is reported `unopened` by the Reviewer and confirmed before step 9 by the person the plan names
  (#266)
- [Core] With an early draft PR open, the `specs/` bookkeeping is committed while the run waits on the Product
  Manager, and a PR the user marks ready early is not turned back into a draft: the Product Manager is asked once
  (#266)
- [Tools] After a merge of `main` that changes `.squad/tools/`, `squad-next.py` sends a new `plan-check.py` finding on
  the approved plan to the Lead in mode `revise` with the scope unchanged; an approved plan's size only warns (#266)
- [Core] Members delete or move a file with `rm` or `mv` and `git add`, which `git-guard.py` names when it denies
  `git rm` or `git mv` (#266)
- [Tools] `decision-check.py` and `figure-check.py` pass SonarQube Cloud's python:S7632 and S8786, which #261 left
  in both files: the `noqa` explanation holds no comma, and `figure-check.py` reads numbers without nested
  quantifiers (#263)
- [Tools] `gate-stamp.py`, `figure-check.py`, `decision-check.py` and `squad-log.py` pass SonarQube Cloud's Python
  rules again (python:S6019, S5850, S8786, S7632, S3776), so a refresh no longer fails a target's quality gate (#261)
- [Tools] `squad-log.py --agent-id` reads a launch's model, effort, tokens per kind, tool uses and seconds from the
  subagent's transcript; `--summary` adds a price-weighted table per role with the orchestrator's share, and
  `session-usage.py` a weighted column (#234)
- [Core] Squad lessons are filed in the run's own repository (`squad-upstream` for a template-managed file, `squad`
  for project knowledge); `squad-log.py --summary` requires the step-12 lessons row and lists the lesson candidates
  (#239)
- [Tools] `.squad/template.json` records the template's release tag, and `squad-log.py --summary` prints it (#249)
- [Core] `.squad/project.md` is a pointer file: entries name files and link their area document or record, and
  `config-check.py` warns above `PROJECT_MAX_WORDS`; `decision-check.py` warns about an unreleased record past
  `RECORD_MAX_WORDS` or `RECORD_MAX_OPTIONS` and an area document past `AREA_MAX_WORDS` (new settings in
  `squad_settings.py`), and an unreleased record is extended only for the same decision (#236)
- [Core] The squad's process decisions are the managed `docs/decisions/process.md` instead of numbered records; a
  refresh retires the process records older versions added once (`adopt-template` step 8) (#247)
- [Tools] `figure-check.py` lists the documentation lines that still state a value the diff changed; the Dev runs it
  with the documentation and step 7 runs it again (`FIGURE_TRIVIAL`, `FIGURE_EXCLUDES` in `squad_settings.py`) (#237)
- [Tools] `squad-next.py` prints the orchestrator's next step with its exact launch, and `gate-stamp.py` runs the
  step-7 gates of the tier and logs them with the head SHA; step 9 (`--verify`) and `squad-log.py --summary` (exit 6)
  refuse a head without a passing stamp (#238)
- [Core] The squad's rule files are consolidated without changing a rule: repetitions point to the one place a rule
  lives, and procedure the tools enforce (`squad-next.py`, `gate-stamp.py`, `squad-log.py`, `plan-check.py`, the
  Git and file guards) is a pointer to the tool (#234–#250)
