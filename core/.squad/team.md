# Team

Squad for this repository, used for both GitHub issues (`squad-issue` skill) and new features
(`squad-spec` skill). The idea follows [bradygaster/squad](https://github.com/bradygaster/squad): this
file names the members, `routing.md` holds the pipeline and its limits, and each role's charter is the
Claude Code subagent file under `.claude/agents/` (all changed only in squad-maintenance PRs). The roles run
as subagents, driven by the invoking session (the orchestrator).

The squad files are stack-neutral and come from the Squad-Spec-Repository-Template repository. Everything
specific to this repository lives in two files the members read first:

- [`stack.md`](stack.md) — toolchain, layout and the exact commands: format, build, test, coverage, the
  analyzer gate, how to write code and tests that pass it, and how to build a compile-only skeleton.
- [`project.md`](project.md) — what this project guarantees: the security areas that decide the
  `security` tier, deliberate guarantees, the integration surface the Reviewer sweeps, and the test doubles.

## Members

| Role             | Subagent (charter)                                                    | Model  | Writes                                                           |
| ---------------- | --------------------------------------------------------------------- | ------ | ---------------------------------------------------------------- |
| Lead             | [`squad-lead`](../.claude/agents/squad-lead.md)                       | Opus   | plans, decisions, area documents                                 |
| Devil's Advocate | [`squad-devils-advocate`](../.claude/agents/squad-devils-advocate.md) | Opus   | nothing (read-only)                                              |
| Security         | [`squad-security`](../.claude/agents/squad-security.md)               | Opus   | nothing (read-only)                                              |
| Tester           | [`squad-tester`](../.claude/agents/squad-tester.md)                   | Sonnet | test code                                                        |
| Dev              | [`squad-dev`](../.claude/agents/squad-dev.md)                         | Sonnet | production code                                                  |
| Code Officer     | [`squad-code-officer`](../.claude/agents/squad-code-officer.md)       | Sonnet | production and test code (format, analyzer and style fixes only) |
| Reviewer         | [`squad-reviewer`](../.claude/agents/squad-reviewer.md)               | Opus   | nothing (read-only)                                              |
| Product Manager  | —                                                                     | —      | answers escalations (the human user)                             |

Where production and test code live is defined in `stack.md` (*Layout*).

The **Lead** decides everything inside the squad, including approving plans and approving the pull
request. The **Product Manager** is only involved when the Lead escalates: an unclear requirement, a
product decision that cannot be derived from the issue or the existing documentation, or a deadlock the
Lead cannot resolve.

## Shared rules (apply to every member)

`CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, `docs/UNIT_TESTS.md`, `.squad/stack.md` and
`.squad/project.md` are binding: unit tests for all new code until the *Coverage gate* passes, the code
conventions from `stack.md` while writing, English for everything
that ends up in the repository or on GitHub. Inside the squad, only the Code Officer runs the formatter
(*Format* in `stack.md`) and owns a clean analyzer gate. Subagents never run Git write operations, except
creating and removing a scratch `git worktree` for experiments (`.squad/routing.md`, *Concurrency*); the
orchestrator commits and pushes to the work branch at any time (see `CLAUDE.md`, golden rules) and opens
the pull request only after the Lead's approval.
