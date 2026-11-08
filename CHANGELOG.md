# Changelog

What each release of the template brings to the repositories that use it (`consumers.json`). Every pull request that
changes what a target receives adds a line under *Unreleased*; a release turns those lines into a version section and
is tagged (`AGENTS.md`, *Releases*). Changes before the first release are in the history of `main`.

## Unreleased

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
