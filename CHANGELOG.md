# Changelog

What each release of the template brings to the repositories that use it (`consumers.json`). Every pull request that
changes what a target receives adds a line under *Unreleased*; a release turns those lines into a version section and
is tagged (`AGENTS.md`, *Releases*). Changes before the first release are in the history of `main`.

## Unreleased

- [Core] A `manual:` check that names the Reviewer or Security runs in its step-8 round, not as a step-7 test, and
  `plan-check.py` refuses one that names a member outside the tier's review round; a Product Manager's manual check
  named only in the plan's prose holds the review, and an Orchestrator `7 Manual test` row records a stand-in's (#396)
- [Core] A member's report re-sent word for word after a task notification is part of its round, not a continued
  launch; members send their report once, with no background command left running (#397)
- [Core] `squad-log.py` names `--round 1` when a round is logged late; `squad-next.py` asks for the verbatim row before
  stamping a documentation-only fix of an open review round that no Dev or Tester fix followed (#398)
- [Core] `plan-check.py` skips appended challenge and security notes in its placeholder check; notes the Lead answered
  in *Challenge* are not asked for again (the template's own *Challenge* text answers none) (#401)
- [Core] Security's diff verdict counts its non-blocking findings (`VERDICT: APPROVED | NON-BLOCKING n`, else its
  tags), so tiers `docs` and `patch` decide them before the PR; the `patch` test is written on the unfixed head before
  the edits (#402)
- [Core] `squad-notes.py` writes a report's control characters as text escapes, so appended notes never fail
  `plan-check.py` (#400)
- [Core] The Dev's skeleton report lists the changed files from `git status` and only members read back from disk, and
  `squad-next.py` sends a file a skeleton task row names but the branch has not changed back to the Dev before tests
  first; a plan names the test seam of a resource bound over an external system (#399)
- [Core] `lesson-label.py` counts only the tools the template ships to `.squad/tools/` as managed, so a repository's
  own tool there is labelled `squad`; *Template-managed files* names the template blocks of `.editorconfig` as marked
  (#395)
- [Core] `result.md` is listed in the work folder (`specs/README.md`, *Work folder*) and posted in the working record
  of tiers `docs` and `patch` (#394)
- [Profile] The seeded CI of every profile runs `decision-check.py --require-history --tags-fetched` in a job
  `decision-records`, so a changed released record cannot merge, and a refresh adds the job to an existing CI; a CI
  merged from several profiles runs it once and renames a prefixed job in `needs:` too (#403)
- [Profile] dotnet: the shared global analyzer config sets MSTEST0001, a rule reported without a location that no
  `.editorconfig` section reaches, to `error`; `dotnet-rules.py` writes a pending entry for such a rule into
  `.squad/dotnet-rules-pending.globalconfig` at a higher `global_level`, and `dotnet_config.py` checks that
  `Directory.Build.props`, Dockerfiles and `.dockerignore` carry both global configs (#393)
- [Seed] The seeded CI workflows gain the `decision-records` job; dotnet `Directory.Build.props` names
  `.squad/dotnet-rules-pending.globalconfig`, and dotnet `stack.md` says the *Analyzer gate* also reports a diagnostic
  without a location of a project with a changed file (#393, #403)

## v2026.11.10 — 2026-11-13

- [Skill] `adopt-template` asks for the *Fork scope* repository settings only in the pull request that adds
  `fork-scope.yml`, not on every refresh
- [Core] New `lesson-label.py` names a squad lesson's label from the files its fix changes (`squad-upstream` for a
  managed file, `squad` for the repository's own), split into two issues when both; `squad-upstream` is the default
  for a lesson about the squad's rules, agents, skills or tools; `squad-report.py --upstream` also lists the open
  `squad` issues that name a managed file (#388)
- [Core] `squad-next.py` reads a non-blocking count in the verdict clause only, so "no blocking or non-blocking
  findings" after `APPROVE` is prose (#385)
- [Core] `session-usage.py` counts the harness's reply to a `SubagentHandback` call as part of the same round, so one
  launch is no longer logged as continued; `squad-log.py --round N` logs a round written late (#386, #390)
- [Core] One Lead revision logged as the plan-check revise answers a challenge and a CHANGES_REQUIRED that came back
  with it; its hand-over names them (#387)
- [Core] `squad-next.py` names the fresh Lead `decide` launch of step 6; a member's report is one final reply (#383)
- [Core] A Reviewer verdict on a later head that adds only documentation to the stamped code counts; a criterion
  verified `manual:` runs as `7 Manual test` before the review set (#382)
- [Core] Tier `trivial` keeps a task group's order when `tasks.md` puts the Tester first; a reason for the spec's
  length in the Lead's result settles the size warning; `squad-log.py --stdin` keeps a new row off the last line of
  a table pasted without its line break (#390)
- [Core] The Lead's result of tiers `docs` and `patch` is written verbatim to `result.md` with `squad-notes.py
  <folder> result`, and the Reviewer and Security read the diff against it (#389)
- [Core] The Tester keeps test code, table tests included, under the analyzer's cognitive-complexity limit (#384)
- [Profile] dotnet: the *Analyzer gate* reports a diagnostic without a location (MSTEST0001) for its project when a
  file of it changed; the shared baseline sets MSTEST0001 to `error` (a test project without `[assembly: Parallelize]`
  or `DoNotParallelize` goes to `DOTNET_RULES_PENDING` until it states one) (#379)
- [Seed] dotnet `UNIT_TESTS.md` names the branch conditions the *Coverage gate* prints; go `stack.md` says `gocognit`
  covers `_test.go` files too (#380, #384)
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/docs/UNIT_TESTS.md`, `profiles/go/seed/.squad/stack.md`

## v2026.11.9 — 2026-11-12

- [Profile] The seeded `codeql.yml` grants nothing at the workflow level (`permissions: {}`) and, like the seeded
  `ci.yml`, checks out with `persist-credentials: false` (#360, #372)
- [Core] The generated release notes leave out Dependabot's GitHub Actions updates (label `github_actions`) (#363)
- [Core] `scope-check.py` escapes control characters in what it prints, so a fork's file name cannot start a GitHub
  Actions workflow command in the *Fork scope* log (#361)
- [Core] The *Coverage gate* counts branch conditions on new and changed lines together with the lines, as SonarQube
  Cloud does, where the report records them (Cobertura, lcov; not a Go coverprofile; `COVERAGE_CONDITIONS = False`:
  lines only); overall coverage stays line coverage (#368)
- [Core] `plan-check.py --matrix` reads a file name in a *Tests or check* cell as that file and a call (`Read(...)`)
  by its name, instead of matching every test file (#373)
- [Core] `plan-check.py` leaves the *Challenge* and *Security review* sections out of the plan's size, as the Lead's
  instructions say; the Lead measures a size with the checking script, never `wc -w` (#375)
- [Core] `squad-log.py` checks the verdict line of the row as written and quotes the result it read in its warning
  (#369)
- [Core] New `squad-notes.py` appends *Challenge notes* and *Security notes* from the member's transcript (the
  report a cloud session's subagent hands back included; a text without a `VERDICT:` line is refused), never retyped,
  and `squad-next.py` names it; a session branch whose pull request is merged is not reused (#370)
- [Core] `squad-next.py` accepts `6 Implement skipped (<group>)`, and a non-blocking finding the plan already orders
  (`NON-BLOCKING 2 (1 plan)`) goes to its owner without a Lead decision (#371)
- [Core] `squad-issue` says how dependent issues are stacked (one shared run, or each pull request on the previous
  branch with every `Closes` on the last) (#367)
- [Core] A manual check on an artifact the Product Manager builds names the fallback; `orchestration.md` holds the
  recipe for a Docker image built in a cloud session (#366)
- [Profile] `dotnet_major.py` also checks the `net<N>.0` monikers of shell and PowerShell scripts and workflows, their
  comments left out (#374)
- [Profile] `dotnet_config.py` reports a Dockerfile building .NET code that does not bring
  `.squad/dotnet-rules.globalconfig` into its build, and a `.dockerignore` that leaves it out; `adopt-template` and
  the seeded `stack.md` say so (#357)
- [Skill] `adopt-template` splits a seeded process record the project extended in place: a new record keeps the
  project's own rules, the seeded one is retired; `apply-template.py` marks such a record "also names …" (#356)
- [Core] `plan-check.py --matrix` takes a test's name only from the listed code spans of its cell, not from the
  description after it; `squad-issue` checks a pull request that waits while another run works in the same clone
  from a worktree of its branch (#351)
- [Core] A Security note or a minor objection of the plan challenge whose fix is an exact edit of `plan.md` or
  `spec.md` is applied by the orchestrator when it appends the note, like a verbatim documentation fix (#350)
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/.github/workflows/ci.yml`, `profiles/dotnet/seed/.github/workflows/codeql.yml`, `profiles/dotnet/seed/.squad/stack.md`, `profiles/dotnet/seed/.squad/tools/squad_settings.py`, `profiles/dotnet/seed/docs/UNIT_TESTS.md`, `profiles/go/seed/.github/workflows/ci.yml`, `profiles/go/seed/.github/workflows/codeql.yml`, `profiles/node/seed/.github/workflows/ci.yml`, `profiles/node/seed/.github/workflows/codeql.yml`, `profiles/node/seed/.squad/tools/squad_settings.py`, `profiles/node/seed/docs/UNIT_TESTS.md`, `profiles/typescript/seed/.github/workflows/ci.yml`, `profiles/typescript/seed/.github/workflows/codeql.yml`, `profiles/typescript/seed/.squad/tools/squad_settings.py`, `profiles/typescript/seed/docs/UNIT_TESTS.md`, `seed/.github/release.yml`

## v2026.11.8 — 2026-11-12

- [Profile] `dotnet-rules.py` lowers a pending rule the baseline does not set as well (one on only through
  `AnalysisLevel`, CA1848, or one it sets only for test code, BL0016), so `TreatWarningsAsErrors` no longer fails on it (#337)
- [Profile] The managed global analyzer config `.squad/dotnet-rules.globalconfig` switches the baseline's switched-off
  rules off in generated code too (S1125 in `.razor` markup, which `.editorconfig` does not reach); the seeded
  `Directory.Build.props` names it in `GlobalAnalyzerConfigFiles` and `dotnet_config.py` asks for it (#337)
- [Profile] The baseline turns IDE0061 (expression-bodied local functions) and IDE0045 (conditional assignment)
  silent: `reihitsu-format` writes local functions with block bodies, and IDE0045 nests ternaries S3358 rejects (#337)
- [Skill] `adopt-template` turns C# files to CRLF by a fresh checkout (`git add --renormalize .` alone changes no file
  Git stores with LF) and carries over build-file items the seeds gained (#337)
- [Tools] `apply-template.py` lists a decision record as an old process record only when its source is the seeds'
  "Squad adopted/refreshed from" line, not when it merely cites the template (#337)
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/.squad/stack.md`, `profiles/dotnet/seed/Directory.Build.props`

## v2026.11.7 — 2026-11-12

- [Profile] `sonar-rules.py` puts a new block right after the dotnet-rules block, never into the paths block, and names
  a leftover `SONAR_RULES_SEVERITY`; `dotnet-rules.py` refuses a pending entry for a rule the baseline switches off or
  a lower-case rule id; `dotnet_config.py` reads every form of an assembly-wide suppression and the build files below
  the root, and no longer reports a `[*]` value the dotnet-rules block overrides for C# files; the baseline has no
  trailing whitespace (#337)
- [Profile] The rule baseline keeps CA2007 (`ConfigureAwait`) at `warning` for production code and turns it off for
  test code, where MSTest runs without a synchronization context (#337)
- [Skill] `adopt-template` brings a `dotnet` target onto the shared baseline on its first refresh to it: the target
  framework and the required switches into `Directory.Build.props`, versions into `Directory.Packages.props`, the
  rules out of `.editorconfig`, rule sets, `NoWarn` and assembly-wide suppressions, the tool manifest under `.config/`,
  CRLF for C# files; values stay the target's (#343)
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
- [Seed] Seeded files changed; existing targets keep their own copy, so the refresh carries these changes over by hand: `profiles/dotnet/seed/.config/dotnet-tools.json`, `profiles/dotnet/seed/.editorconfig`, `profiles/dotnet/seed/.github/dependabot.yml`, `profiles/dotnet/seed/.squad/stack.md`, `profiles/dotnet/seed/.squad/tools/squad_settings.py`, `profiles/dotnet/seed/Directory.Build.props`, `profiles/dotnet/seed/Directory.Packages.props`

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
