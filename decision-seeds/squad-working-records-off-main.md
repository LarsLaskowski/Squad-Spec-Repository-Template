# NNNN: Squad working records stay off main, and product PRs never change the squad

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Source:** Squad adopted from ProjectTemplate
- **Supersedes:** —

## Context

The squad writes a plan and a log per issue or feature under `specs/`. Kept on `main`, these records
accumulate without being read again, while the lasting reasoning already lives in decision records. Squad
lessons fixed inside a product PR mix two unrelated changes and are easy to lose in a later template
refresh.

## Options considered

1. **Keep `specs/` on `main`** — full history in the repository; grows with every change and duplicates
   the decision records.
2. **Working records only on the work branch** — posted as a "Squad working record" comment on the issue
   (or the PR) before the PR opens, then removed; `main` keeps only `specs/README.md` and the templates.

## Decision

Option 2. In addition, an issue or feature PR never changes the squad or the agent instructions
(`.squad/` except `stack.md` and `project.md`, `.claude/`, `.github/skills/`, `.agents/skills/`,
`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`). Lessons about the squad become a GitHub issue
labelled `squad` and are worked in a separate squad-maintenance PR; lessons about template-managed files
are fixed in ProjectTemplate and rolled out with `adopt-template`.

## Consequences

- `main` stays free of per-change working records; the issue comment keeps them findable.
- A crashed session can still resume, because the work folder is committed on the work branch.
- Squad fixes need their own PR, even when they are small.
