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

## Code coverage

**Threshold: at least 80 % line coverage on new or changed production code, and at least 80 % overall** —
the same measure as SonarQube's "coverage on new code". Check it locally before a push with *Test with
coverage* and the *Coverage gate* from [`.squad/stack.md`](../.squad/stack.md). Lines that genuinely
cannot be covered by a unit test (for example process startup glue) need an explicit, recorded decision.

## Checklist for new tests

- [ ] New production code has accompanying unit tests — mandatory, not optional.
- [ ] The *Analyzer gate* reports nothing in a changed test file.
- [ ] At least 80 % line coverage on new/changed production code and overall (*Coverage gate*).
- [ ] File and test names as above; Arrange / Act / Assert; one act; assertion messages.
- [ ] No real network or clock.
- [ ] *Format* from `.squad/stack.md` run before committing.
