# AGENTS.md — Squad-Spec-Repository-Template

Guidance for AI coding agents working in this repository: Codex, Kimi Code and GitHub Copilot's coding agent
read this file directly, Claude Code through the `@AGENTS.md` import in [`CLAUDE.md`](CLAUDE.md).

## What this repository is

Squad-Spec-Repository-Template: the shared squad, AI-agent rules and scaffolding that `adopt-template` applies
to the other repositories. It contains no product code. See [`README.md`](README.md) for the layout (`core/`,
`profiles/`, `multi/`, `seed/`, `decision-seeds/`, `tools/`).

## Golden rules

- **Never commit or push to `main`** — every change goes through a separate branch and a pull request.
  Commits and pushes to a feature branch are always allowed; force-pushing, deleting branches and creating
  tags need explicit user approval.
- **Pull requests are opened only when the user asks** (running `adopt-template` counts as asking for the
  PR in the target repository).
- **`core/` stays stack- and project-neutral.** Commands are referred to by their name in
  `.squad/stack.md` (*Format*, *Build*, *Analyzer gate*, …), project knowledge by `.squad/project.md` or a
  `<!-- project:… -->` block. Stack details belong in `profiles/<stack>/`.
- Run `python3 tools/template-check.py` before every pull request, with `complexipy` installed (`pip install
  complexipy`) so it also checks the cognitive complexity of the tools a target receives; it must pass. It also
  checks those tools for the SonarQube Cloud rules a refresh has tripped before (`SONAR_RULES`); when a refresh
  brings a new Sonar finding in a template-managed file, fix it here and add its rule to that check.
  CI also runs SonarQube Cloud's own analysis of these tools (`sonarqube` job, `sonar-project.properties`); fix a
  finding there before merging and add its rule to `SONAR_RULES` where `template-check.py` can detect it.
- A lesson from a squad run in another repository that concerns a template-managed file is fixed here and
  rolled out with `adopt-template`, never patched in the target only.
- **Every squad rule lives in exactly one place** (mostly `core/.squad/routing.md`, `core/.squad/orchestration.md`
  for what only the orchestrator does, and `core/.squad/team.md`); other files point to it. The evidence behind a
  rule (incidents, measured numbers) goes into `docs/squad-rationale.md`, which no target receives. How the rule
  files are kept from growing without losing a rule: *Writing rules*.

## Writing rules

Every member reads the rule files it is pointed to on every launch, so a rule text says what to do or not do, and when,
and nothing else. A reason in a half sentence stays when it keeps the rule from being misread or worked
around; so does an example of the case the rule exists for. Leave out: a rule repeated from another file (point
to it), the history of how it came about, incident reports and measured numbers (they go to
`docs/squad-rationale.md`), and sentences that change nothing a member does. What only the orchestrator does goes
into `core/.squad/orchestration.md`, which the members need not read.

There is no word budget: a rule is never cut to make room for another. `template-check.py` reports instead:

- how many words each changed rule file gained or lost against its merge base with `origin/main`, and the total against
  `RULE_WORDS_BASELINE`, the size after the last consolidation — information for the PR description;
- every sentence that left the rule files (found in none of them any more) — the PR description says for each
  where it moved or why it goes;
- a run of 20 words two rule files share — the copy becomes a pointer, or the PR says why both stay.

Rule text is shortened only in a consolidation PR of its own, which `template-check.py` asks for once the total is
more than 15 % over the baseline: a reviewer checks every removed sentence for a rule or a reason that would be
lost, and the PR sets `RULE_WORDS_BASELINE` to the new total.

## Commit messages and pull requests

- Subject line: one summary of **no more than 80 characters**, no trailing period, not in the first
  person; a body only where the subject does not explain the change.
- PR title `[area] Description` (areas: `Core`, `Profile`, `Tools`, `Skill`, `Docs`), description of 3–5
  sentences, both in **English**. Pull requests are merged with *Squash and merge*, so the PR title and
  description are what reaches `main`.

## Skills

- `adopt-template` — apply or refresh the template in a target repository and open a PR there.
