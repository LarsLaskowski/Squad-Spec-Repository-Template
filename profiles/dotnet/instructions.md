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
```bash
dotnet restore <Solution>.slnx
reihitsu-format ./                                          # dotnet tool install -g Reihitsu.Cli
dotnet build <Solution>.slnx -c Release --no-restore
dotnet test <Solution>.slnx -c Release --no-build
python3 .squad/tools/analyzer-check.py                      # analyzer gate
python3 .squad/tools/coverage-check.py                      # coverage gate, after a coverage run
```
<!-- stack:end commands -->
<!-- stack:begin configuration -->
- **Target framework** `<net10.0>`; **nullable reference types**, **implicit usings**, and
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
**Unit tests are mandatory for newly written code.** MSTest only (no FluentAssertions, no mocking
library — use real objects or the hand-written fakes/stubs). Classes `{TypeUnderTest}Tests`, methods
`{Class}{Scenario}{ExpectedResult}` in PascalCase **without underscores**; always pass an assert message.
<!-- stack:end testing -->
