# Changelog

What each release of the template brings to the repositories that use it (`consumers.json`). Every pull request that
changes what a target receives adds a line under *Unreleased*; a release turns those lines into a version section and
is tagged (`AGENTS.md`, *Releases*). Changes before the first release are in the history of `main`.

## Unreleased

- [Skill] `adopt-template` opens the target's pull request labelled `ignore-for-release`, creating the label where it
  is missing, so a squad update no longer reaches the target's release notes; `rollout-check.py` fails when a
  target's `.github/release.yml` does not exclude the label (#336)
- [Core] `create-pr` labels a change of the squad alone (`.squad/`, `.claude/`, the instruction files)
  `ignore-for-release` (#336)
- [Skill] `adopt-template` keeps the seed's Dependabot `docker` entry only for a Dockerfile whose `FROM` lines name
  the image itself, which is all Dependabot reads; the seeded `stack.md` says how images named through a build
  argument stay current instead (#335)
- [Profile] The `dotnet` profile seeds `Directory.Build.props` (the target framework and the required switches once,
  the analyzers for every project, MSTest and coverage for every `*.Tests` project) and `Directory.Packages.props`
  (central versions), the structure `dotnet_config.py` checks; the seeded tool manifest names `reihitsu.cli` 1.2.0,
  the version of Reihitsu.Analyzer (#340)
- [Profile] The `dotnet` *Analyzer gate* runs the new managed `dotnet_config.py`: the target framework and the
  required build switches only in `Directory.Build.props`, central package versions, the tool manifest under
  `.config/` at the analyzer's Reihitsu version, CRLF for C# files, no rule set, no rule in `NoWarn`, no assembly-wide
  `SuppressMessage`, the dotnet-rules blocks current and no rule set outside them; a refresh fixes what it reports (#342)
- [Profile] The `dotnet` profile's new managed `dotnet-rules.py` writes the template's rule baseline
  (`.squad/dotnet-rules.editorconfig`, the stricter setting of the .NET repositories winning) into the
  `squad:dotnet-rules` blocks of `.editorconfig`, so every .NET repository builds with the same analyzer rules; it
  refuses a block under a section of a path, and `adopt-template` runs it on every refresh (#341)
- [Profile] A rule the code does not meet yet goes into `DOTNET_RULES_PENDING` of `squad_settings.py` with its issue;
  `dotnet-rules.py` and `sonar-rules.py` write it as `suggestion`, which the *Analyzer gate* still reports (#341)
- [Profile] `sonar-rules.py` writes the rules of the project's SonarQube Cloud profile at `error`;
  `SONAR_RULES_SEVERITY` is gone (#341)

## v2026.11.6 — 2026-11-11

- [Core] `git-guard.py` allows a member `git apply` only with `--check`, `--stat`, `--numstat` or `--summary` and
  otherwise options that write no file, so `--build-fake-ancestor=.git/index` can no longer replace the index (#328)
- [Core] `git-guard.py` denies a member `git apply --3way` also beside `--check`, which stores the merged blob in
  `.git/objects` (#328)
- [Profile] `sonar-rules.py` leaves a rule out of its block only when `.editorconfig` sets it for every C# file; one
  set in a section of a path (`[tests/**.cs]`, `[**/Migrations/*.cs]`) keeps its line in the block (#330)
- [Profile] `sonar-rules.py` reads a section's glob to decide whether it applies to every C# file: `[*]` sets the
  project's own choice, `[*.g.cs]` or `[*Tests.cs]` only that of some files; it warns when such a section comes before
  the block, whose line then wins there too (#333)
- [Profile] The `dotnet` seed Dependabot holds back the next major of `Microsoft.Extensions.*` too, whose 11.0.0 also
  restores into a `net10.0` project (#328)
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/.github/dependabot.yml`, `profiles/dotnet/seed/.squad/stack.md`

## v2026.11.5 — 2026-11-11

- [Profile] The `dotnet` profile's new managed `sonar-rules.py` writes the rules of the project's SonarQube Cloud C#
  profile beyond *Sonar way core* into a marked `.editorconfig` block (severity `SONAR_RULES_SEVERITY`), so the
  *Analyzer gate* reports S3776, S1192, S107 and the rest locally; `adopt-template` runs it on every refresh (#312)
- [Profile] The `dotnet` *Skeleton* names the diagnostics a skeleton raises by construction (S1144, S1172, S4487,
  S2325, CS0067, CS0649, RH2003) for its removable pragma, and the Dev leaves a DI registration a criterion's test
  asserts to the implementation (#306)
- [Tools] `squad-next.py` holds the Tester's coverage pass open for the tests a step-5 row names after `Deferred:`
  (#307), launches the Tester for its share of a plan without production or test code (#314), reads the step-9
  approval from the Lead's `RESULT:` line and the checklist row's first words, so a fix ordered in `approve-pr` ends
  with the checklist (#319), takes a logged or folded *Challenge notes* append as done (#318), never continues an
  agent already continued in another mode (#320), and keeps step 12 due after a merge or close (#311)
- [Tools] `plan-check.py --matrix` names only the files of the tests a criterion's row names, falling back to its id
  in the row's files, and keeps the cell's code spans (#308)
- [Tools] `gate-stamp.py` writes each gate's whole output to a file outside the repository and prints a summary with
  the tail of a failure; `session-usage.py` prints the orchestrator's share and names its model above half (#313)
- [Tools] `git-guard.py` allows a member `git apply --check` (and `--stat`, `--numstat`, `--summary`) for a dry-run
  patch the orchestrator commits and reverts (*Dry-run artifacts*) (#315)
- [Core] A merge or close of the PR ends the watching, never the run: step 12 runs at once (#311); the orchestrator
  keeps every fresh launch's agent id and continues exactly the agent `squad-next.py` names (#320)
- [Core] Every documentation update of a plan has a member as owner, an edit of `stack.md` or `project.md` too, whose
  exact text the orchestrator writes in (#316); the Lead's proposed no-change comment thanks no one when the issue's
  author posts it (#317); the Lead leaves the verbatim *Challenge notes* and *Security notes* alone outside a challenge
  revision (#318)
- [Profile] The `dotnet` profile keeps a repository on one .NET major while 10 and 11 are installed side by side: the
  new managed `dotnet_major.py`, run by the *Analyzer gate*, fails a target framework, `global.json` or .NET image of
  another major; a seeded `global.json` fixes the SDK (newest feature band of its major, `10.0.404`), which the seed CI
  installs and a refresh creates in a target without one, whose environments then need that SDK or a later one of its
  band; the seed tool manifest lets `reihitsu-format` roll forward only where .NET 10 is missing; the seed Dependabot
  keeps the SDK (`dotnet-sdk`), the packages and the images current within the major; and the SessionStart hook warns
  about a missing SDK or target runtime (#322)
- [Tools] `squad-next.py` warns in every output while a member's last launch continued an agent past the continuation
  cap, and its fresh launch says it is a new agent, not a `SendMessage`; `squad-issue` says a launch it names fresh is
  fresh, a fix round too (#324)
- [Profile] The `dotnet` SessionStart hook warns when no installed SDK of the `global.json` version's major and minor
  is at least that version (an older 10.0 band beside a pin of 10.0.404), not only when the major is missing (#322)
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/.config/dotnet-tools.json`, `profiles/dotnet/seed/.editorconfig`, `profiles/dotnet/seed/.github/dependabot.yml`, `profiles/dotnet/seed/.github/workflows/ci.yml`, `profiles/dotnet/seed/.squad/stack.md`, `profiles/dotnet/seed/.squad/tools/squad_settings.py`, `profiles/dotnet/seed/global.json`

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
