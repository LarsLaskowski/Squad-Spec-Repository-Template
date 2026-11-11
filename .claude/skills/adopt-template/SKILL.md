---
name: adopt-template
description: Use when the user wants to bring the Squad-Spec-Repository-Template squad and Claude Code rules into another repository, or to refresh a repository that already uses them. Detects the stack profile, applies the template with tools/apply-template.py, moves the repository's own knowledge into the project sections, .squad/stack.md and .squad/project.md, replaces old skills, verifies everything and opens a pull request in the target repository.
---

# Adopt Template

Bring Squad-Spec-Repository-Template into a **target repository**, or refresh it there. You run in a session
that has both this repository and the target cloned. Invoking this skill is the user's approval for opening
the pull request in the target repository at the end (step 10) — nothing else.

Rules that hold throughout:

- **Never commit to `main`** of the target. Work on a new branch off its latest `main`
  (`adopt-project-template`, or `update-project-template` for a refresh — or the branch the session
  prescribes). Commit and push to that branch after every completed step.
- **Never lose the target's knowledge.** Everything project-specific in the files the template replaces —
  overview, architecture, commands, conventions, guarantees, security notes, review checklists in old
  skills or agents — ends up in a project block, `.squad/stack.md`, `.squad/project.md`, `docs/` or a kept
  file. Deleting is only allowed for content the template now covers word for word in meaning.
- **Template-managed files are not edited in the target** (`.squad/orchestration.md`, *Template-managed files*).
  If one does not fit the target, stop and fix it here in Squad-Spec-Repository-Template first, then re-apply.
- Everything written into the target is in **English**.

## Steps

1. **Target and branch.** Clone the target if needed, `git fetch origin main`, and create the work branch
   off `origin/main`. Read its `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `README.md`, `docs/`, `SECURITY.md`, `.claude/`, `.agents/`, `.github/` and its build
   files before changing anything.
   If `.squad/template.json` exists, this is a **refresh**: note its `tag`, `commit` and `profile`/`profiles` (older
   records without `repository` or `tag` get them on this run), move the target's open `squad-upstream` issues here
   (*Updating the template itself*) and continue with step 3. Seeded files are not
   refreshed, so on a refresh compare the target's `.squad/stack.md`, `.squad/project.md` and `squad_settings.py`
   with the seeds (`git -C <template> diff <old commit>..<tag> -- seed profiles/<profile>/seed`; the `[Seed]` line of
   each release section since the recorded tag names the files) and carry over
   changed commands, settings and rule sentences by hand (a *Format* row still labelled "Code Officer only"
   becomes "in the squad: by the member that changed the files, `.squad/team.md`"). A setting the target's
   `squad_settings.py` lacks is added with the seed's comment and default: `SPEC_APPROVAL = "lead"` (who approves a
   feature's spec) unless the user asks for `"pm"`, the size limits `PLAN_MAX_WORDS` per tier, `SPEC_*`,
   `SMALL_FEATURE_CRITERIA`, `PROJECT_MAX_WORDS`, `AREA_MAX_WORDS`, `RECORD_MAX_WORDS` and `RECORD_MAX_OPTIONS`, and
   `FIGURE_TRIVIAL` and `FIGURE_EXCLUDES` of `figure-check.py`; a value the target already sets stays. The same holds
   for `docs/UNIT_TESTS.md`: a section the seed gained (e.g. *Criterion ids*) is added to the target's test document,
   adapted to its test framework; and for the structure of `project.md`, a pointer file: its introduction and the
   section texts that say what an entry holds. The size warnings of `config-check.py` are not worked in the refresh;
   list them in the PR description. Shortening the target's existing `project.md` entries to pointers is a
   squad-maintenance pull request in that repository (file it there as a `squad` issue); splitting the records and
   area documents the warnings name is a documentation change of the product (file an issue for it). The same diff
   covers
   `seed/.claude/settings.json`: the apply step adds each squad `PreToolUse` hook the target's
   `.claude/settings.json` lacks (`git-guard.py`, and `file-guard.py` for targets adopted before it; step 8), and any
   other change to the seed's hooks is carried over by hand.
2. **Profile.** Detect the stack: `*.slnx`/`*.sln`/`*.csproj` → `dotnet`, `go.mod` → `go`,
   `tsconfig.json` → `typescript`, `package.json` without `tsconfig.json` → `node` (a repository already on
   `node` keeps it on a refresh). If several match and each is product code (e.g. a Go agent and a .NET
   backend), use all of them — pass `--profile` once per profile, the main product code first; a profile
   that only builds tooling or a client the main profile already covers stays out. Say which you chose and
   why. On a refresh keep the recorded `profiles`: run without `--profile`. If none matches, stop: a new
   profile has to be added to Squad-Spec-Repository-Template first (see `README.md`, *Adding a stack*).
3. **Apply.** First, on a first adoption, move documents the template expects under `docs/` but the target
   keeps elsewhere (e.g. a root-level `ARCHITECTURE.md` or `CONTRIBUTING.md`) there with `git mv` and fix
   every link to them: the apply step then backs them up like any other marked file, and their content
   lands in the template's file instead of living twice. Then, from the template repository's root, on a checkout
   of its latest release tag (`git fetch origin --tags`, `git checkout <tag>`: the tag and its commit are recorded in
   `.squad/template.json`, and a change not yet released waits for its release, `AGENTS.md` there, *Releases*;
   before the template's first release, an up-to-date `main`, recorded with `"tag": null`), run
   `python3 tools/apply-template.py --target <path> [--profile <profile> …] --dry-run`, read the list, then run
   it without `--dry-run`. Keep the output: it names the backed-up files, the skipped seeds (name them in
   the PR description — e.g. a `.gitattributes` an existing repository should get in a change of its own)
   and the files in template-owned folders the template does not know, the retired files it removed (the
   skill copies an older template version wrote) and the *Process records* step 8 retires. The rules live in `AGENTS.md`; `CLAUDE.md` is managed and only
   imports it. A `CLAUDE.md` that still holds the rules (it has project blocks: an older template version) has
   its project blocks carried into `AGENTS.md`; a hand-written `CLAUDE.md` or `AGENTS.md` without project markers
   is backed up like a marked file (step 4). With several profiles it also lists `conflict` seeds (a file two profiles both seed that the merge cannot combine, e.g. `sonar-project.properties`): merge those by hand.
   `.github/copilot-instructions.md` is generated from the rebuilt `AGENTS.md` (its own title and introduction,
   then the body of `AGENTS.md` without Claude Code `@` import lines); a target whose file was removed by an
   earlier refresh gets it back, and a hand-written one without project markers is backed up like a marked file
   (step 4). After step 4 changed a project block of `AGENTS.md`, run the apply step once more (or make the same
   change in `.github/copilot-instructions.md`) so the two bodies stay identical.
   The output ends with **References to removed files**: every line of the target (project blocks, `README.md`,
   `docs/`, `*.sln`/`*.slnx`/`*.csproj`, workflows, …) that still names a retired file. The apply step never
   rewrites those files (decision records under `docs/decisions/` are not listed: they state history, and a
   released one is append-only), so fix every listed line by hand — link the replacement (`AGENTS.md`,
   `.claude/agents/squad-*.md`, `docs/decisions/`) or drop it — and rerun the apply step until the list is
   empty; step 9 is not reached before.
4. **Move the knowledge into the project blocks** (first adoption; on a refresh only check that nothing
   new needs a block). For every file backed up under `.git/adopt-template/backup/` in the target, move its
   project-specific content into the matching `<!-- project:begin … -->` block of the new file:
   - instruction files (a backed-up `CLAUDE.md`, `AGENTS.md` or `.github/copilot-instructions.md`), all into
     `AGENTS.md`: *overview*, *architecture*, *configuration*, *code-style* (only what goes beyond the stack
     block); a Claude Code `@path` import line moves along — Claude Code follows it through `CLAUDE.md`'s import,
     and the Copilot mirror leaves it out;
   - `docs/CONTRIBUTING.md`: *getting-started*, *areas* (the PR title areas), *releases*, *stability*,
     *license*;
   - `docs/ARCHITECTURE.md`: *architecture* (normally the whole former document, minus a former
     "development process" section the template now provides);
   - `.github/ISSUE_TEMPLATE/bug_report.md`: *environment*, *logs*;
   - `.github/pull_request_template.md`: *checklist* (project-specific checklist items, e.g. a UI section);
   - `docs/decisions/README.md`: *index* (the existing table rows);
   - `docs/areas/README.md`: *area-index* (the areas of the project, one row each; empty on a first adoption —
     the areas are defined with the project, see `docs/areas/README.md`).
   `SECURITY.md` is seeded, not rebuilt: an existing one stays as it is; a new one gets its placeholders
   filled; on a refresh, remove `<!-- project:… -->` markers left in it from older template versions. A pull
   request or issue template under another name or case (e.g. `.github/PULL_REQUEST_TEMPLATE.md`) is merged
   into the template's file and removed — GitHub would otherwise pick one at random, and the two names
   collide on case-insensitive file systems.
   Links in `AGENTS.md` are repository-rooted (`/docs/ARCHITECTURE.md`, `/.squad/stack.md`); write the project
   blocks the same way.
   Replace every `{{TODO: …}}` placeholder — they only occur inside project blocks and seeded files, so a
   refresh never brings them back. Rules that the stack or core sections already state are dropped from
   the project blocks rather than kept twice.
5. **Fill `.squad/stack.md` and `.squad/tools/squad_settings.py`** from the target's real build: versions,
   solution or module name, layout, every command, coverage paths, and the generated files whose values
   `figure-check.py` should not read (`FIGURE_EXCLUDES`). Run each command once to prove it
   works. Where the profile expects a tool the target does not have yet (e.g. ESLint with
   eslint-plugin-sonarjs, Prettier and the npm scripts `format`, `format:check`, `lint`, `typecheck`,
   `coverage:lcov` for `node`; the same scripts with typescript-eslint's type-aware configs, Vitest and
   `@vitest/coverage-v8` for `typescript`; Reihitsu or SonarAnalyzer.CSharp for `dotnet`), add it — a new dev
   dependency is part of this PR and is named in its description. If adding it would change a lot of
   unrelated code (a formatter's first run), keep the gate limited to changed files and say so in the PR.
   With the `dotnet` profile, run `python3 .squad/tools/sonar-rules.py` on adoption and on every refresh: it writes the
   `squad:sonar-rules` block of `.editorconfig` from the project's SonarQube Cloud C# profile (a target without the
   markers gets them; rules the target set by hand for the same purpose move into the block, and a sentence of its
   `stack.md` that calls such a rule one "no local analyzer reports" is corrected). NOT CHECKED (no access to
   sonarcloud.io) is named in the PR description.
   Test docs under another name (e.g. `docs/TESTS.md`) are renamed to `docs/UNIT_TESTS.md` with `git mv`
   and every link updated; the profile's seed is only used when the target has no test document, and an
   existing one gets the *Code coverage* and checklist sections of the seed merged in.
6. **Fill `.squad/project.md`** from `ARCHITECTURE.md`, `SECURITY.md`, the README configuration table, the
   decision records and old review skills or agents: concrete security areas, guarantees with their
   decision records, the integration surface (what must change together), and the test doubles — as pointers, the
   way its introduction says: values, limits and sequences stay in the document they came from (an area document,
   `ARCHITECTURE.md`, `README.md`), which the entry links. On a
   first adoption, also read `git diff HEAD` of the **managed** files the apply step overwrote — a
   repository that already had a squad keeps its project knowledge there (e.g. the integration-surface
   sweep in an old `squad-reviewer.md`, project names in old charters or the PR template) — and carry that
   knowledge into `project.md` or `stack.md` before it is lost.
7. **Old skills and agents** (the "not part of the template" list): fold their project-specific content
   into `project.md`, `stack.md` or `docs/`, then delete the ones the template replaces — `fix-issue` →
   `squad-issue`, `publish-pr`/`create-pr` → `create-pr`, `rereview-pr`/`review-pr` → `review-pr`, a
   repository-specific reviewer agent → `squad-reviewer`. A genuinely project-specific skill stays under
   `.claude/skills/`; a copy of it under `.agents/skills/` or `.github/skills/` is deleted. Copilot custom agents
   (`.github/agents/`) and path instructions (`.github/instructions/`) stay; align their rules with `stack.md`
   where they contradict it.
8. **Decision records, settings, CI.**
   - The squad's process decisions are the managed `docs/decisions/process.md`, which the apply step writes and
     every refresh overwrites: no number, no index row, and no record in the target for a change to them. The
     records that carried them before are retired once, here: the ones the apply step lists under *Process
     records* (numbered from `decision-seeds/` by older template versions, and the records that supersede or
     amend one, all still in force) and, on a first adoption, a record of the target's own that only states what
     `process.md` now decides (what a product PR may touch, where squad lessons go, how pull requests merge). A
     listed record marked "supersedes or amends" that states a rule of the project's own stays, and so does every
     record its *Supersedes* names. Of the others, an unreleased one (no release tag contains it) is deleted with
     its index row, together with every unreleased record it supersedes (a chain from before the first release),
     and every link to them points at `process.md`. When a released one is among them, or a released
     record's `Superseded by` names a deleted one, one record from `decision-seeds/process-decisions-moved.md`
     (next free number, date today) lists all those under *Supersedes*, and each of them gets the status
     `Superseded by NNNN`; a released record superseded by another released one stays as it is. Run
     `decision-check.py`; afterwards the apply step lists only the records kept as the project's own.
   - `.claude/settings.json`: make sure the SessionStart hook entry for `.claude/hooks/session-start.sh`, the
     PreToolUse `Bash` hook running `.claude/hooks/git-guard.py` and the PreToolUse
     `Write|Edit|MultiEdit|NotebookEdit` hook running `.claude/hooks/file-guard.py` exist, as in the template's
     `seed/.claude/settings.json` (the apply step adds a missing PreToolUse hook; a `conflict` for
     `.claude/settings.json` means adding them by hand); keep every other hook. `config-check.py` fails while one
     is missing.
   - The file guard lets the Tester write only the test paths (`COVERAGE_TEST_PATHSPECS` in `squad_settings.py`, by
     default its `COVERAGE_EXCLUDES`) and `docs/UNIT_TESTS.md`: when the target keeps test files elsewhere (fixtures,
     test data, a test project file), set `COVERAGE_TEST_PATHSPECS` to every test location, the default's patterns
     included, and name the guard and that setting in the PR description.
   - CI: an existing workflow is kept. Add only what the template's decisions need — e.g. excluding
     `.squad/**` and `.claude/**` from the coverage measure of the code analysis.
   - `.github/workflows/fork-scope.yml` (seeded when missing, also on a refresh): name it in the PR description
     and ask the user to make *Scope of a fork pull request* a required check of `main` and to require approval
     for workflow runs of outside contributors (repository settings, *Actions*); neither can be set from a PR.
   - `.squad/decisions.md`, `.squad/agents/*/history.md` and `.squad/agents/*/charter.md` from older template
     versions are removed by the apply step (the charters now live in `.claude/agents/`; nothing read or wrote
     the other two, process decisions are in `docs/decisions/process.md`). An entry in `decisions.md` that is
     still worth keeping becomes a decision record.
9. **Verify** in the target, once the apply step lists no reference to a removed file (step 3):
   `python3 .squad/tools/config-check.py` passes (no placeholder left, `AGENTS.md` and
   `.github/copilot-instructions.md` identical from the first `##` heading on, `CLAUDE.md` importing `AGENTS.md`), then
   *Restore*, *Format check*, *Build*, *Analyzer gate*, *Test with coverage* and *Coverage gate* from the
   new `stack.md`. A gate that fails on code this PR did not change is reported in the PR description and to
   the user. One exception: when overall coverage is below the threshold before this PR, set
   `COVERAGE_OVERALL_THRESHOLD` in `squad_settings.py` to the current overall value (rounded down) so the
   *Coverage gate* holds the line from here on, and say so in the PR; it is raised towards 80 as coverage
   improves and never lowered again. Then run the
   target's `squad-reviewer` agent (round 1, full) on the diff and fix its blocking findings; later rounds
   review only the delta.
10. **Pull request** in the target, opened as a draft (`draft: true`), from its
    `.github/pull_request_template.md`: title `[Docs] Adopt the Squad-Spec-Repository-Template squad and agent rules` (refresh:
    `[Docs] Update the squad from Squad-Spec-Repository-Template`), a description naming the release (its
    `CHANGELOG.md` section) and what was added, replaced,
    moved and deleted, the profile, new dev dependencies, and any gate that fails for reasons outside this PR.
    Subscribe to the PR's activity and stay with it until it merges cleanly, CI is green and the code
    analysis lists no new issue, then mark it ready for review (the target's `.squad/orchestration.md`, *Draft
    until green*). Read its mergeability on every look at the PR: a conflict with the target's base branch
    keeps CI from starting and is merged and resolved first (*Merge conflicts* there).
11. **Report** to the user: target, profile, PR URL, deleted and kept skills/agents, open issues (e.g.
    coverage below the threshold), and any template change you had to make here first.

## Updating the template itself

A lesson about a template-managed file arrives as a `squad-upstream` issue in a target (squad runs file their
lessons in their own repository) and is moved here as a `squad` issue: `python3 tools/squad-report.py --upstream`
lists the open ones of every active consumer in `consumers.json` (or of the `--repo` given), `--move` moves them in one batch (a new issue here with the title, the
body and a link back; the original gets a comment linking it and is closed). Without `gh` write access, move each the
same way with the GitHub tools. A lesson is fixed here: change `core/` or the profile, run
`python3 tools/template-check.py`, open a PR here with its `CHANGELOG.md` line, and once a release contains it refresh
every active target of `consumers.json` with this skill (README, *Rolling out a change*).
