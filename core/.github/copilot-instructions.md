# Copilot instructions

Project guidance for GitHub Copilot when working in this repository. These rules mirror
[`AGENTS.md`](/AGENTS.md): everything from the first `##` heading on is generated from it by the template's
`adopt-template` skill (Claude Code's `@` import lines aside — Copilot reads
`.github/instructions/*.instructions.md` through their `applyTo` front matter), and
`.squad/tools/config-check.py` fails when the two differ. Change both files together. This file is a
summary; the binding, detailed references are [`ARCHITECTURE.md`](/docs/ARCHITECTURE.md) (how the system is
put together and why), [`CONTRIBUTING.md`](/docs/CONTRIBUTING.md) (workflow, PR conventions, versioning),
[`UNIT_TESTS.md`](/docs/UNIT_TESTS.md) (test conventions — **unit tests are mandatory for new code**) and
[`.squad/stack.md`](/.squad/stack.md) (toolchain and commands). Read them before making a non-trivial
change; when this file and one of them appear to disagree, treat that as a sync bug to fix, not as
license to pick either one.
