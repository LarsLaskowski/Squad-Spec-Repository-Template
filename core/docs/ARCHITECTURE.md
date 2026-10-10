# Architecture

<!-- project:begin architecture -->
{{TODO: What the system does, in two or three sentences.}}

## Components

{{TODO: The projects/packages/modules and what each owns. A diagram (Mermaid) of the main data flow.}}

## {{TODO: Main flow, e.g. request pipeline / sync pipeline}}

{{TODO: How data moves through the system, and the deliberate guarantees along the way — each guarantee also
listed in `.squad/project.md` (*Guarantees*) and linked to its decision record.}}

## Configuration

{{TODO: Where configuration comes from, required settings, defaults, validation at startup. The rules per area
are in [`areas/`](areas/README.md); this overview links them instead of repeating them.}}

## Security model

{{TODO: Authentication, secrets, trust boundaries. Kept in sync with `SECURITY.md` and the *Security areas* in
`.squad/project.md`.}}

## Deployment

{{TODO: How the software is built, packaged and released.}}
<!-- project:end architecture -->

## Development process

This repository is developed with Claude Code: `CLAUDE.md` holds the rules, the skills live under
`.claude/skills/` and the squad roles under `.claude/agents/`. Every pull request is reviewed before it is opened by the read-only reviewer in `.claude/agents/squad-reviewer.md`
— round 1 is a full review, every later round looks only at the delta, and only blocking findings earn
another round, because a fresh full re-review of unchanged code always finds something new.

The squad skills (`squad-issue`, `squad-spec`) wrap that review in a larger, bounded pipeline described in
[`.squad/routing.md`](../.squad/routing.md): an Opus Lead plans, classifies the change into a tier (`docs`,
`trivial`, `standard`, `security`) that decides how much of the pipeline runs, and owns every decision;
for `standard` and `security` a Devil's Advocate challenges the plan once (no veto); on the `security` tier
a Security member reviews the plan and the diff, below it the Reviewer carries the security checklist; tests are
written first and new/changed code is covered until the *Coverage gate* passes; a Code Officer clears formatting
and analyzer diagnostics *before* the review so the reviewed code is the merged code; and the review loop
is one full pass plus at most two delta rounds; the pull request is approved by a checklist the orchestrating
session runs, and the Lead is asked only for what is open. Every limit ends in a Lead decision, and only a
decision the Lead cannot make reaches the human. The stack-specific commands live in
[`.squad/stack.md`](../.squad/stack.md), the project's guarantees and attack surface in
[`.squad/project.md`](../.squad/project.md).

The reasoning behind individual choices is kept out of this document and recorded instead as decision
records in [`docs/decisions/`](decisions/README.md); this document describes how the system works and
links a record where a guarantee or flow is the result of one.
