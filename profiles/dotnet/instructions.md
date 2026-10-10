<!-- stack:begin golden-rules -->
- Add new packages via **Central Package Management** (`Directory.Packages.props`); do not put version
  numbers in individual `.csproj` files.
- Every C# project uses the **Reihitsu.Analyzer** and the **SonarAnalyzer.CSharp** rules, so SonarQube
  issues surface in the local build, not first in the CI analysis. A build must finish with **zero
  Reihitsu (`RH####`) warnings and errors**.
- Wrap every type's members in `#region` blocks **as you write the code** — never leave a type
  un-regioned and never add the regions only after an analyzer warning.
<!-- stack:end golden-rules -->
<!-- stack:begin commands -->
Run from the repository root, where the solution file lives, in this order: *Restore*, *Format*, *Build*,
*Test*, *Analyzer gate*, and after *Test with coverage* the *Coverage gate*. Use the commands of those names
in `.squad/stack.md` as they stand, never a copy from memory: they carry the solution name, the build
configuration the project tests in, and the formatter's `--force` (`reihitsu-format` asks for confirmation
for more than 25 files and, without a terminal, formats nothing). The formatter is installed with
`dotnet tool install -g Reihitsu.Cli`.
<!-- stack:end commands -->
<!-- stack:begin configuration -->
- **Target framework** as set in the project files (see `.squad/stack.md`); **nullable reference types**, **implicit usings**, and
  **documentation XML** generation are all enabled.
- **Central Package Management** via `Directory.Packages.props`; never put versions in individual
  `.csproj` files.
- **Reihitsu.Analyzer** and **SonarAnalyzer.CSharp** are dev dependencies in every project (via
  `Directory.Build.props`).
- **Solution format** is `.slnx` (XML-based) at the repository root.
<!-- stack:end configuration -->
<!-- stack:begin code-style -->
File-scoped namespaces; one top-level type per file; `using` outside namespace (System first); Allman
braces, always required; 4-space indent; `var` preferred; language keywords over BCL types; LINQ method
syntax only; `== false` instead of `!`; `is null` / `is not null`; no primary constructors; constructor
injection with `_camelCase` readonly fields; `#region` blocks grouped by member kind (an interface's
region named after the interface, its description not ending in "implementation"); XML docs on all
members (English, no `<remarks>`); `.ConfigureAwait(false)` in library/service code.
<!-- stack:end code-style -->
<!-- stack:begin testing -->
**Unit tests are mandatory for newly written code.** MSTest with its own `Assert` / `CollectionAssert` (no
FluentAssertions); test doubles as `.squad/project.md` (*Test doubles*) and `docs/UNIT_TESTS.md` prescribe —
real objects and hand-written fakes/stubs unless the project names a mocking library. Classes
`{TypeUnderTest}Tests`, methods `{Class}{Scenario}{ExpectedResult}` in PascalCase **without underscores**;
always pass an assert message.
<!-- stack:end testing -->
