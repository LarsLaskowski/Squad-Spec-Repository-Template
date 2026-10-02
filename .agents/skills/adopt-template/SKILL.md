---
name: adopt-template
description: Use when the user wants to bring the ProjectTemplate squad and AI rules (Claude, Codex/GPT, Copilot) into another repository, or to refresh a repository that already uses them. Detects the stack profile, applies the template with tools/apply-template.py, moves the repository's own knowledge into the project sections, .squad/stack.md and .squad/project.md, replaces old skills, verifies everything and opens a pull request in the target repository.
---

# Adopt Template

Bring ProjectTemplate into a **target repository**, or refresh it there. You run in a session that has both
this repository and the target cloned. Invoking this skill is the user's approval for opening the pull
request in the target repository at the end (step 10) — nothing else.

Rules that hold throughout:

- **Never commit to `main`** of the target. Work on a new branch off its latest `main`
  (`adopt-project-template`, or `update-project-template` for a refresh — or the branch the session
  prescribes). Commit and push to that branch after every completed step.
- **Never lose the target's knowledge.** Everything project-specific in the files the template replaces —
  overview, architecture, commands, conventions, guarantees, security notes, review checklists in old
  skills or agents — ends up in a project block, `.squad/stack.md`, `.squad/project.md`, `docs/` or a kept
  file. Deleting is only allowed for content the template now covers word for word in meaning.
- **Template-managed files are not edited in the target** (`.squad/routing.md`, *Template-managed files*).
  If one does not fit the target, stop and fix it here in ProjectTemplate first, then re-apply.
- Everything written into the target is in **English**.

## Steps

1. **Target and branch.** Clone the target if needed, `git fetch origin main`, and create the work branch
   off `origin/main`. Read its `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `README.md`,
   `docs/`, `SECURITY.md`, `.claude/`, `.agents/`, `.github/` and its build files before changing anything.
   If `.squad/template.json` exists, this is a **refresh**: note its `commit` and `profile` and continue
   with step 3.
2. **Profile.** Detect the stack: `*.slnx`/`*.sln`/`*.csproj` → `dotnet`, `go.mod` → `go`,
   `package.json` → `node`. If several match, the profile of the main product code wins (e.g. a .NET
   solution with an Angular client is `dotnet`); say which you chose and why. If none matches, stop: a new
   profile has to be added to ProjectTemplate first (see `README.md`, *Adding a stack*).
3. **Apply.** From the ProjectTemplate root run
   `python3 tools/apply-template.py --target <path> --profile <profile> --dry-run`, read the list, then run
   it without `--dry-run`. Keep the output: it names the backed-up files and the files in template-owned
   folders the template does not know.
4. **Move the knowledge into the project blocks** (first adoption; on a refresh only check that nothing
   new needs a block). For every file backed up under `.git/adopt-template/backup/` in the target, move its
   project-specific content into the matching `<!-- project:begin … -->` block of the new file:
   - instruction files: *overview*, *architecture*, *configuration*, *code-style* (only what goes beyond
     the stack block);
   - `docs/CONTRIBUTING.md`: *getting-started*, *areas* (the PR title areas), *releases*, *stability*;
   - `docs/ARCHITECTURE.md`: *architecture* (normally the whole former document, minus a former
     "development process" section the template now provides);
   - `SECURITY.md`: *contact* (the real reporting address), *deployment*, *scope*;
   - `.github/ISSUE_TEMPLATE/bug_report.md`: *environment*;
   - `docs/decisions/README.md`: *index* (the existing table rows).
   Replace every `{{TODO: …}}` placeholder — they only occur inside project blocks and seeded files, so a
   refresh never brings them back. Rules that the stack or core sections already state are dropped from
   the project blocks rather than kept twice. Copy `CLAUDE.md`'s body to `AGENTS.md` and
   `.github/copilot-instructions.md` unchanged from the first `##` heading on.
5. **Fill `.squad/stack.md` and `.squad/tools/squad_settings.py`** from the target's real build: versions,
   solution or module name, layout, every command, coverage paths. Run each command once to prove it
   works. Where the profile expects a tool the target does not have yet (e.g. ESLint with
   eslint-plugin-sonarjs, Prettier and the npm scripts `format`, `format:check`, `lint`, `typecheck`,
   `coverage:lcov` for `node`; Reihitsu or SonarAnalyzer.CSharp for `dotnet`), add it — a new dev
   dependency is part of this PR and is named in its description. If adding it would change a lot of
   unrelated code (a formatter's first run), keep the gate limited to changed files and say so in the PR.
   Test docs under another name (e.g. `docs/TESTS.md`) are renamed to `docs/UNIT_TESTS.md` with `git mv`
   and every link updated; the profile's seed is only used when the target has no test document, and an
   existing one gets the *Code coverage* and checklist sections of the seed merged in.
6. **Fill `.squad/project.md`** from `ARCHITECTURE.md`, `SECURITY.md`, the README configuration table, the
   decision records and old review skills or agents: concrete security areas, guarantees with their
   decision records, the integration surface (what must change together), and the test doubles. On a
   first adoption, also read `git diff HEAD` of the **managed** files the apply step overwrote — a
   repository that already had a squad keeps its project knowledge there (e.g. the integration-surface
   sweep in an old `squad-reviewer.md`, project names in charters or the PR template) — and carry that
   knowledge into `project.md` or `stack.md` before it is lost.
7. **Old skills and agents** (the "not part of the template" list): fold their project-specific content
   into `project.md`, `stack.md` or `docs/`, then delete the ones the template replaces — `fix-issue` →
   `squad-issue`, `publish-pr`/`create-pr` → `create-pr`, `rereview-pr`/`review-pr` → `review-pr`, a
   repository-specific reviewer agent → `squad-reviewer`. A genuinely project-specific skill stays and is
   mirrored identically into `.claude/skills/`, `.agents/skills/` and `.github/skills/`. Copilot custom
   agents (`.github/agents/`) and path instructions (`.github/instructions/`) stay; align their rules with
   `stack.md` where they contradict it.
8. **Decision records, settings, CI.**
   - Add the records from ProjectTemplate's `decision-seeds/` with the next free numbers (date today,
     *Source* "Squad adopted from ProjectTemplate"), unless the target already has an equivalent record;
     add them to the index.
   - `.claude/settings.json`: make sure the SessionStart hook entry for `.claude/hooks/session-start.sh`
     exists; keep every other hook.
   - CI: an existing workflow is kept. Add only what the template's decisions need — e.g. excluding
     `.squad/**` and `.claude/**` from the coverage measure of the code analysis.
   - `.squad/decisions.md`: replace `<date>` and `<profile>` in the seeded entry.
9. **Verify** in the target: `python3 .squad/tools/config-check.py` passes (no placeholder left), then
   *Restore*, *Format check*, *Build*, *Analyzer gate*, *Test with coverage* and *Coverage gate* from the
   new `stack.md`. A gate that fails on code this PR did not change (e.g. overall coverage below 80 %) is
   not fixed by lowering a threshold: report it in the PR description and to the user. Then run the
   target's `squad-reviewer` agent (round 1, full) on the diff and fix its blocking findings; later rounds
   review only the delta.
10. **Pull request** in the target, from its `.github/pull_request_template.md`: title
    `[Docs] Adopt the ProjectTemplate squad and agent rules` (refresh:
    `[Docs] Update the squad from ProjectTemplate`), a description of what was added, replaced, moved and
    deleted, the profile, new dev dependencies, and any gate that fails for reasons outside this PR.
    Subscribe to the PR's activity and stay with it until CI is green.
11. **Report** to the user: target, profile, PR URL, deleted and kept skills/agents, open issues (e.g.
    coverage below 80 %), and any template change you had to make here first.

## Updating the template itself

A lesson from a target (a `squad` issue there that concerns a template-managed file) is fixed in this
repository: change `core/` or the profile, run `python3 tools/template-check.py`, open a PR here, and after
its merge refresh the targets with this skill.
