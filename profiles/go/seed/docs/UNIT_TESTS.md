# Unit Tests

This document describes how unit tests are written in this repository. It is binding for human
contributors and AI agents alike: **unit tests are mandatory for newly written code**, new tests follow the
conventions below, and existing tests are the reference implementation — when in doubt, look at a
neighboring test file before inventing a new pattern.

## Test stack

- The standard `testing` package (plus `net/http/httptest` for handlers). No assertion or mocking
  library — hand-written fakes behind small interfaces, listed in `.squad/project.md` (*Test doubles*).

## Where tests live

- Colocated `_test.go` files, one per source file under test (`foo.go` → `foo_test.go`), in the same
  package (white-box) unless the test exercises only the exported API (`package foo_test`).

## Naming

- `TestFunction_Scenario` or `TestType_Method` with `t.Run` subtests named after the scenario, e.g.
  `t.Run("empty input returns error", …)`.

## Structure

- Table-driven tests for several inputs: a slice of cases, one `t.Run` per case.
- Arrange / Act / Assert inside each case; one act per case.
- Failure messages state what was called, what came back and what was expected:
  `t.Errorf("Parse(%q) = %v, want %v", in, got, want)`.
- Leak tests (a secret must not appear in an error or log): keep the sentinel out of subtest names —
  `t.TempDir()` embeds the sanitized subtest name in the path, and an error that legitimately shows the
  path then contains the sentinel. Strip the file path from the error text before the leak check.
- Where the plan fixes an error format, assert the exact text instead of forbidding substrings; a
  forbidden substring must not overlap text the format requires.
- `t.Helper()` in helpers; `t.TempDir()` for files; no real network, no real clock (inject a clock or a
  fixture path); tests pass under `-race`.
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
cannot be covered by a unit test (for example `main` wiring) need an explicit, recorded decision.

## Checklist for new tests

- [ ] New production code has accompanying unit tests — mandatory, not optional.
- [ ] The *Analyzer gate* passes.
- [ ] At least 80 % line coverage on new/changed production code and overall (*Coverage gate*).
- [ ] Table-driven where there is more than one input; failure messages with got and want.
- [ ] Passes with `-race`; no real network or clock (a time bound only as a ratio of two durations).
- [ ] *Format* from `.squad/stack.md` run before committing.
