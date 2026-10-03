# Decision records

Why the code is the way it is. Each file records one decision — its context, the options considered, what
was chosen and the consequences — so that months later the reasoning is still available without the
pull request, the issue thread or the session that produced it.

`docs/ARCHITECTURE.md` describes *how* the system works today; these records explain *why* individual
choices were made. When a decision changes the architecture, `ARCHITECTURE.md` is updated as well and
links the record.

## Rules

- One decision per file: `NNNN-short-title.md` (four digits, next free number), created from
  [`_template.md`](_template.md).
- Written by the squad Lead (see [`.squad/agents/lead/charter.md`](../../.squad/agents/lead/charter.md));
  anyone may add one for a change made outside the squad.
- Committed together with the change it explains.
- Records are **append-only**: an accepted record is never rewritten. A changed decision gets a new record
  that names the old one under *Supersedes*, and the old record's status becomes
  `Superseded by NNNN` (the only edit allowed).
- Not for routine changes: a record is needed when a choice between real alternatives was made, a
  trade-off or limitation was accepted, a review finding was deliberately not fixed, a documented
  guarantee was touched, a dependency was added or removed, or work was split into a follow-up issue.

## Index

<!-- project:begin index -->
| #    | Title | Status | Date |
| ---- | ----- | ------ | ---- |
<!-- project:end index -->
