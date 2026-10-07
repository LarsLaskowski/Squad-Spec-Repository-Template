# AGENTS.md — Squad-Spec-Repository-Template

Guidance for Codex/GPT and other agents that read AGENTS.md when working in this repository. `CLAUDE.md`, `AGENTS.md` and
`.github/copilot-instructions.md` are identical from the first `##` heading on; keep them in sync.

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
- **Mirrors stay identical:** `.claude/skills/`, `.agents/skills/` and `.github/skills/` (here and in
  `core/`), and `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` from the first `##` heading on.
- Run `python3 tools/template-check.py` before every pull request; it must pass.
- A lesson from a squad run in another repository that concerns a template-managed file is fixed here and
  rolled out with `adopt-template`, never patched in the target only.

## Commit messages and pull requests

- Subject line: one summary of **no more than 80 characters**, no trailing period, not in the first
  person; body of **3–5 sentences**.
- PR title `[area] Description` (areas: `Core`, `Profile`, `Tools`, `Skill`, `Docs`), title and description
  in **English**. Pull requests are merged with *Squash and merge*.

## Skills

- `adopt-template` (mirrored under `.claude/skills/`, `.agents/skills/` and `.github/skills/`) — apply or
  refresh the template in a target repository and open a PR there.
