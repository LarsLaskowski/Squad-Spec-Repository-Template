# ProjectTemplate

The shared squad, AI-agent rules and repository scaffolding for all repositories: one stack-neutral
**core** plus one **profile** per tech stack. It is not used through GitHub's "Use this template" button;
the `adopt-template` skill applies it to an existing (or new) repository and refreshes it there later.

## What a repository gets

- **The squad** (`.squad/`, `.claude/agents/squad-*.md`) — Lead, Devil's Advocate, Security, Tester,
  Dev, Code Officer and Reviewer, run by the `squad-issue` (bug fixes) and `squad-spec` (features)
  skills: plan → challenge → security review → tests first → implementation to ≥ 80 % coverage → format
  and analyzer gate → review loop → Lead approval → pull request. Details in
  [`core/.squad/routing.md`](core/.squad/routing.md).
- **One rule set for three agents** — `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex/GPT) and
  `.github/copilot-instructions.md` (GitHub Copilot) are identical from their first `##` heading on; the
  skills `create-pr`, `review-pr`, `squad-issue` and `squad-spec` exist identically under
  `.claude/skills/`, `.agents/skills/` and `.github/skills/`.
- **Quality gates before the PR** — *Format*, *Analyzer gate* (no diagnostic of any severity in a changed
  file) and *Coverage gate* (≥ 80 % on new/changed lines and overall; Cobertura, lcov or Go coverprofile),
  plus `config-check.py`, which keeps mirrors in sync and finds unfilled placeholders.
- **Documentation scaffolding** — `docs/CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `docs/UNIT_TESTS.md`,
  decision records (`docs/decisions/`, with three process records from `decision-seeds/`),
  `specs/_template/`, `SECURITY.md`.
- **GitHub scaffolding** — PR template, issue templates, CI workflow, CodeQL, Dependabot (per profile).

## Layout

```
core/             stack-neutral files; template-managed, except the "marked" files below
profiles/<stack>/
  instructions.md the stack blocks of CLAUDE.md / AGENTS.md / copilot-instructions.md
  managed/        stack tooling, overwritten on every refresh (analyzer gate, SessionStart hook)
  seed/           written once if missing: .squad/stack.md, squad_settings.py, UNIT_TESTS.md, CI, …
seed/             written once if missing: .squad/project.md, decisions.md, histories, .claude/settings.json
decision-seeds/   process decision records, numbered into docs/decisions/ on first adoption
tools/            apply-template.py (mechanical apply), template-check.py (self-check)
.claude/skills/adopt-template/   the skill (mirrored in .agents/skills/ and .github/skills/)
```

Three kinds of files in a target repository:

| Kind | Examples | On a refresh |
| ---- | -------- | ------------ |
| managed | `.squad/team.md`, `.squad/routing.md`, charters, `.claude/agents/squad-*.md`, the template's skills, `.squad/tools/*.py` (except `squad_settings.py`), SessionStart hook, PR template, feature-request template, `specs/` templates, `docs/decisions/_template.md` | overwritten |
| marked | `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `docs/CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `SECURITY.md`, bug report template, decision index | rebuilt; `<!-- project:… -->` blocks keep the repository's content, `<!-- stack:… -->` blocks come from the profile |
| seed | `.squad/stack.md`, `.squad/project.md`, `.squad/decisions.md`, histories, `squad_settings.py`, `.claude/settings.json`, `docs/UNIT_TESTS.md`, CI, CodeQL, Dependabot, tool configs | never touched again |

`.squad/stack.md` holds the stack's exact commands (*Format*, *Build*, *Test*, *Analyzer gate*, …) that
every agent and skill refers to by name; `.squad/project.md` holds the project's security areas,
guarantees, integration surface and test doubles. That is what keeps the core stack-neutral.

Placeholders are written `{{…}}` and only ever appear inside project blocks or seeded files, so a refresh
never resets filled-in text; `config-check.py` fails while any is left (GitHub Actions expressions
`${{ … }}` are not placeholders).

## Profiles

| Profile | Detected by | Formatter | Analyzer gate | Coverage | Repositories |
| ------- | ----------- | --------- | ------------- | -------- | ------------ |
| `dotnet` | `*.slnx`, `*.sln`, `*.csproj` | `reihitsu-format` | Roslyn SARIF of a full build: Reihitsu, SonarAnalyzer.CSharp, MSTest, CA | Cobertura (coverlet) | PlexToJellyfinSync, DockerUpdateGuard, F1-Telemetry |
| `node` | `package.json` | Prettier | `typecheck` + ESLint with eslint-plugin-sonarjs on changed files | lcov | OpenHabLogViewer, e-networld |
| `go` | `go.mod` | `gofmt` | `go vet` + `golangci-lint --new-from-merge-base --whole-files` | Go coverprofile | PiMonitor |

## Using it

In a Claude Code session with this repository and the target repository available, ask for it in plain
words ("bring ProjectTemplate into DockerUpdateGuard") or run `/adopt-template`. The skill detects the
profile, runs `tools/apply-template.py`, moves the target's own knowledge into the project blocks and
the two `.squad` files, replaces old skills (`fix-issue`, `publish-pr`, `rereview-pr`, repository-specific
reviewers), verifies every gate and opens a pull request in the target. A refresh works the same way and
keeps everything project-specific.

## Changing the template

- Lessons from a squad run that concern a template-managed file are fixed **here**, never in the target
  (the target's next refresh would overwrite the fix), and then rolled out with `adopt-template`.
- Keep `core/` free of anything stack- or project-specific; stack details go into a profile, project
  details into a project block or `.squad/project.md`.
- Run `python3 tools/template-check.py` before every pull request.

### Adding a stack

Create `profiles/<stack>/` with the files `tools/template-check.py` requires (`PROFILE_FILES`): the
stack blocks in `instructions.md`, an `analyzer-check.py` and a SessionStart hook under `managed/`, and
`stack.md` (every command name and section), `squad_settings.py`, `UNIT_TESTS.md`, CI, CodeQL and
Dependabot under `seed/`. Add a coverage loader to `core/.squad/tools/coverage-check.py` if the stack
writes a new report format, the detection rule to the `adopt-template` skill, and a row to the table above.
