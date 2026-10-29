# Unit Tests

This document describes how unit tests are written in this repository. It is binding for human
contributors and AI agents alike: **unit tests are mandatory for newly written code**, new tests follow the
conventions below, and existing tests are the reference implementation — when in doubt, look at a
neighboring test file before inventing a new pattern.

## Test stack

<!-- project:begin stack -->
- Test runner: `{{TODO: Node's built-in test runner via tsx | Vitest | Jest}}`; assertions: `{{TODO: node:assert/strict | expect}}`.
- No mocking library beyond what the runner ships with — prefer real objects and the hand-written fakes
  listed in `.squad/project.md` (*Test doubles*).
<!-- project:end stack -->

## Where tests live

<!-- project:begin layout -->
- One test file per module under test, `<module>.test.ts`, next to the module (or under `test/`, mirroring
  `src/`).
<!-- project:end layout -->

## Naming

- `describe` (or the file) names the module; each test name states the scenario and the expected result,
  e.g. `"parseLine returns null for an empty line"`.

## Structure

- Arrange / Act / Assert, separated by blank lines; **one act per test**.
- No logic in tests (no `if`, loops or `switch`); use a table of cases with one test per case for several
  inputs.
- Every assertion carries a message where the assertion API accepts one (`assert.equal(actual, expected,
  "message")`).
- No real network, no real clock (inject a clock or use the runner's mock timers), temporary directories
  for file-system tests, cleaned up afterwards.
- Every promise is awaited; a test never relies on timing.
- **Time bounds as a ratio.** A time bound that cannot be tested as a count (allocations, iterations) — a
  quadratic check that must stay linear, say — is the one exception to the real clock: measure two durations
  in the same test (the base input and a multiple of it) and assert their **ratio**, never an absolute
  duration; set the limit to at least three times the highest ratio measured, with the coverage
  instrumentation of *Test with coverage* included.

## Tests that read repository documents

`.gitattributes` may check files out with CRLF (`*.md text eol=crlf`), so on a CI runner a document carries
`\r\n` where the repository blob has `\n`. A test or script that reads a repository document (`*.md`, and the
other files `.gitattributes` checks out with CRLF) normalizes `\r\n` to `\n` before it compares lines or feeds
them to a shell. The first such test also tests the normalizer with CRLF input.

## Code coverage

**Threshold: at least 80 % line coverage on new or changed production code, and at least 80 % overall** —
the same measure as SonarQube's "coverage on new code". Both values are set in `.squad/tools/squad_settings.py`
(`COVERAGE_THRESHOLD`, `COVERAGE_OVERALL_THRESHOLD`); the overall one may start lower in a repository adopted
with a coverage debt and is only ever raised. Check it locally before a push with *Test with coverage* and the
*Coverage gate* from [`.squad/stack.md`](../.squad/stack.md). Lines that genuinely
cannot be covered by a unit test (for example process startup glue) need an explicit, recorded decision.

## Checklist for new tests

- [ ] New production code has accompanying unit tests — mandatory, not optional.
- [ ] The *Analyzer gate* reports nothing in a changed test file.
- [ ] At least 80 % line coverage on new/changed production code and overall (*Coverage gate*).
- [ ] File and test names as above; Arrange / Act / Assert; one act; assertion messages.
- [ ] No real network or clock (a time bound only as a ratio of two durations).
- [ ] *Format* from `.squad/stack.md` run before committing.
