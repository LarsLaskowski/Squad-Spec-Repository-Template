# Stack: .NET

The toolchain and the exact commands of this repository. Every squad member, skill and instruction file
refers to the entries below by their *italic name*. Seeded from the Squad-Spec-Repository-Template `dotnet`
profile and owned by this repository: keep it true when the build changes.

## Toolchain

- .NET SDK `{{TODO: version, e.g. 10.0.x}}` (target framework `{{TODO: net10.0}}`), solution `{{TODO: Solution}}.slnx`.
- Formatter: `reihitsu-format` (`dotnet tool install -g Reihitsu.Cli`), on the same release line as the
  **Reihitsu.Analyzer** version pinned in `Directory.Packages.props`; otherwise the formatter can revert
  code the analyzer considers correct.
- Analyzers in every project via `Directory.Build.props`: **Reihitsu.Analyzer**, **SonarAnalyzer.CSharp**
  (the Sonar C# rules locally, so SonarQube issues surface before the push) and the MSTest analyzers.
- The SessionStart hook `.claude/hooks/session-start.sh` installs the formatter, sets `DOTNET_ROOT` and
  restores the solution in remote sessions.

## Layout

- Production code: `src/` (`{{TODO: one line per project}}`).
- Tests: `tests/{{TODO: Project}}.Tests/`, one test class per type under test in `{TypeUnderTest}Tests.cs`,
  placed flat in the test project.

## Commands

| Name | Command |
| ---- | ------- |
| *Restore* | `dotnet restore {{TODO: Solution}}.slnx` |
| *Format* (Code Officer only in the squad) | `reihitsu-format --force ./` |
| *Format check* | `reihitsu-format --check ./` |
| *Build* | `dotnet build {{TODO: Solution}}.slnx -c Release --no-restore` |
| *Test* | `dotnet test {{TODO: Solution}}.slnx -c Release --no-build` |
| *Single test* | `dotnet test {{TODO: TestProject}}.csproj --filter "FullyQualifiedName~ClassName.MethodName"` |
| *Test with coverage* | `dotnet test {{TODO: Solution}}.slnx -c Release --no-build --collect:"XPlat Code Coverage" --results-directory ./TestResults` |
| *Coverage gate* | `python3 .squad/tools/coverage-check.py` |
| *Analyzer gate* | `python3 .squad/tools/analyzer-check.py` |

## Analyzer gate

`analyzer-check.py` runs a full, non-incremental Release build with a SARIF error log per project and
reports every non-suppressed Roslyn diagnostic — `RH####`, `S####`, `MSTEST####`, `CA####`, at **any
severity**, including info-level ones that never appear as build warnings but that SonarQube Cloud
imports — located in a file changed since the merge base with `origin/main`. Its solution comes from
`.squad/tools/squad_settings.py`. In addition the build must show **zero `RH####` warnings and errors**
anywhere. Do not grep console build output instead: an incremental build prints no warnings at all.

Easy to get wrong by hand: `#region` blocks on every type, XML documentation on every member, no
underscores in member names, a region for an interface implementation named after the interface.

SonarQube Cloud's own quality profile can still report `S####` rules the local default profile does not,
and its non-Roslyn checks (duplication, hotspots, taint analysis) only run in CI — such findings arrive in
squad step 11.

## Writing code

- File-scoped namespaces; one top-level type per file; `using` outside the namespace (System first).
- Wrap every type's members in `#region` blocks **as you write the code**, grouped by member kind
  (`Constants`, `Fields`, `Constructors`, `Properties`, `Events`, `Methods`, …); a region that groups an
  interface implementation is named after the interface (e.g. `#region IParser`) and its description
  does not end with the word "implementation".
- XML documentation on all members (English, no `<remarks>`).
- Nullable reference types, `var`, language keywords over BCL types, LINQ method syntax only,
  `== false` instead of `!`, `is null` / `is not null`, no primary constructors, constructor injection
  with `_camelCase` readonly fields, `.ConfigureAwait(false)` in library/service code.
- Guards an analyzer asks for (e.g. `if (_logger.IsEnabled(...))` for CA1873) are written by the Dev,
  not added later by the Code Officer.

## Writing tests

See `docs/UNIT_TESTS.md`. The rules the MSTest and Sonar analyzers enforce and the Code Officer cannot fix
without handing back: pass `TestContext.CancellationToken` to every call that accepts a token
(MSTEST0049 / S8949), and use the specific `Assert` member instead of `Assert.IsTrue(...)` or
`StringAssert` (MSTEST0037 / MSTEST0046).

## Skeleton

New members with their full signature, XML docs and `#region` blocks, bodies
`throw new NotImplementedException();`, so the solution builds and the tests compile and fail.

## Dependencies

NuGet packages through **Central Package Management**: the version goes into `Directory.Packages.props`,
never into a `.csproj`. Dev-only analyzers are referenced for every project in `Directory.Build.props`.

## Concurrency

Builds and test runs share `bin/` and `obj/`; two at once break each other. `analyzer-check.py` serializes
itself with a lock (`obj/analyzer-check.lock`), plain builds do not.

## Known pitfalls

- `reihitsu-format` fails with ".NET location: Not found" when `DOTNET_ROOT` is unset — the SessionStart
  hook sets it; otherwise prefix the command with
  `DOTNET_ROOT="$(dirname "$(readlink -f "$(command -v dotnet)")")"`.
- `reihitsu-format` asks for confirmation for more than 25 files; `--force` skips the prompt, which a
  non-interactive session cannot answer.
