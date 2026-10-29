# Unit Tests

This document describes how unit tests are written in this repository. It is binding for human
contributors and AI agents alike: **unit tests are mandatory for newly written code**, new tests follow the
conventions below, and existing tests are the reference implementation — when in doubt, look at a
neighboring test file before inventing a new pattern.

## Test stack

- **MSTest** (`[TestClass]`, `[TestMethod]`, `[DataRow]`). No other test framework.
- **No assertion library** (no FluentAssertions) and **no mocking library** — use real objects or the
  hand-written fakes and stubs listed in `.squad/project.md` (*Test doubles*).
- Coverage is collected with `coverlet.collector`.

## Where tests live

<!-- project:begin layout -->
- Test project: `tests/{{TODO: Project}}.Tests/`, test classes placed flat in it (no subfolders).
- One test class per type under test, in `{TypeUnderTest}Tests.cs`.
<!-- project:end layout -->

## Naming

- Class: `{TypeUnderTest}Tests`.
- Method: `{TypeUnderTest}{Scenario}{ExpectedResult}` in PascalCase **without underscores**, e.g.
  `ParserEmptyInputReturnsNull`.

## Structure

- Arrange / Act / Assert, separated by blank lines; **one act per test**.
- No logic in tests (no `if`, loops or `switch`); use `[DataRow]` for several inputs.
- Shared setup goes into a private/static helper method, not the constructor.
- **Every `Assert.*` call has an explanatory message.**
- Use the specific `Assert` member (`Assert.AreEqual`, `Assert.Contains`, `Assert.HasCount`,
  `Assert.AreSame`, `Assert.ThrowsExactly`, …) instead of `Assert.IsTrue(...)` around a boolean or
  `StringAssert` (MSTEST0037 / MSTEST0046).
- Pass `TestContext.CancellationToken` (constructor-injected `TestContext`) to every call that accepts a
  token — `Task.Run`, `Task.Delay`, `*Async` APIs (MSTEST0049).
- Drive timing through an injected `TimeProvider` (`FakeTimeProvider`), never `Thread.Sleep` or the real
  clock; use a temporary directory for file-system tests and delete it afterwards.
- **Time bounds as a ratio.** A time bound that cannot be tested as a count (allocations, iterations) — a
  quadratic check that must stay linear, say — is the one exception to the real clock: measure two durations
  in the same test (the base input and a multiple of it) and assert their **ratio**, never an absolute
  duration; set the limit to at least three times the highest ratio measured, with the coverage
  instrumentation of *Test with coverage* included.
- `#region` blocks and XML documentation as in production code.

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
*Coverage gate* from [`.squad/stack.md`](../.squad/stack.md). The gate lists every
changed production file with its covered/coverable changed lines and the uncovered line numbers. Lines
that genuinely cannot be covered by a unit test (for example host startup glue) need an explicit,
recorded decision — they are not silently accepted.

## Checklist for new tests

- [ ] New production code has accompanying unit tests — mandatory, not optional.
- [ ] The *Analyzer gate* reports no diagnostic in a changed test file (MSTest analyzer rules are
      info-level and only visible there or in SonarQube Cloud).
- [ ] At least 80 % line coverage on new/changed production code and overall (*Coverage gate*).
- [ ] File, class and method named as above.
- [ ] Arrange / Act / Assert, one act, an explanatory message on every assertion, the specific `Assert`
      member, `TestContext.CancellationToken` passed on.
- [ ] No mocking library — real objects or a hand-written fake/stub.
- [ ] *Format* from `.squad/stack.md` run before committing.
