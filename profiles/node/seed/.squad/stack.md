# Stack: Node.js / TypeScript

The toolchain and the exact commands of this repository. Every squad member, skill and instruction file
refers to the entries below by their *italic name*. Seeded from the Squad-Spec-Repository-Template `node`
profile and owned by this repository: keep it true when the build changes.

## Toolchain

- Node.js `{{TODO: version, e.g. 22}}` (`engines` in `package.json`), npm with a committed `package-lock.json`.
- TypeScript (`tsc`), **ESLint** with **eslint-plugin-sonarjs** (the SonarQube JS/TS rules locally, so
  SonarQube issues surface before the push) and **Prettier** as the formatter.
- The SessionStart hook `.claude/hooks/session-start.sh` runs `npm ci` in remote sessions.

## Layout

- Production code: `{{TODO: src/ …}}`.
- Tests: `{{TODO: colocated `*.test.ts` next to the code | `test/`}}`, one test file per module under test, named
  `<module>.test.ts`.

## Commands

All commands go through `package.json` scripts; a missing script is added, not worked around.

| Name | Command |
| ---- | ------- |
| *Restore* | `npm ci` |
| *Format* (in the squad: by the member that changed the files, `.squad/team.md`) | `npm run format` (`prettier --write .`) |
| *Format check* | `npm run format:check` (`prettier --check .`) |
| *Build* | `npm run build` |
| *Test* | `npm test` |
| *Single test* | `{{TODO: e.g. node --import tsx --test --test-name-pattern "<name>" src/x.test.ts}}` |
| *Test (project)* | `{{TODO: e.g. node --import tsx --test src/<dir>/*.test.ts}}` (the tests of the changed code; a `patch` that changes only test code, `.squad/routing.md` *Gates of a patch* — it writes no coverage report, so a `patch` that changes production code runs *Test with coverage* instead) |
| *Test with coverage* | `npm run coverage:lcov` (overwrites `coverage/lcov.info`) |
| *Coverage gate* | `python3 .squad/tools/coverage-check.py` |
| *Analyzer gate* | `python3 .squad/tools/analyzer-check.py` |
| *Sonar gate* | `python3 .squad/tools/sonar-check.py branch -- npx --yes @sonar/scan@5.0.1 -Dsonar.branch.name="$(git branch --show-current)"` (after *Test with coverage*, so the analysis carries coverage; needs `SONAR_TOKEN`, see *Sonar gate* below) |
| *Image build check* | `docker build -f {{TODO: Dockerfile, or "none" when the repository builds no image}} .` where Docker runs; otherwise the reproduction under *Image build check* below (`.squad/routing.md`, *Criteria verified only in CI*) |

## Analyzer gate

`analyzer-check.py` runs the npm scripts in `CHECK_SCRIPTS` of `.squad/tools/squad_settings.py` (at least
`typecheck`, which must pass for the whole repository) and ESLint on every file changed since the merge
base with `origin/main`; any ESLint message — error or warning — in a changed file fails the gate.
Fixable style findings are the Code Officer's (`eslint --fix` on the changed files, then *Format*); rule
findings that need a code change go to the Dev or Tester.

SonarQube Cloud can still report rules the local plugin version does not have, and its non-lint checks
(hotspots, taint analysis, duplication) have no local equivalent: the *Sonar gate* below is the first to
report their issues and hotspots, and squad step 11 reads the quality gate, duplication included.

Changed shell scripts (`*.sh`), GitHub workflows (`.github/workflows/*.yml`) and Dockerfiles are checked with
`shellcheck`, `actionlint` and `hadolint`; the SessionStart hook installs the three as pinned, checksum-verified
binaries (`.claude/hooks/install-linters.sh`), and the gate reports NOT RUN for one that is missing (a refused
download, for example). The gate itself checks two SonarQube Cloud shell rules shellcheck does not report:
`shelldre:S7679` (a positional parameter `$1`…`$9` used as a word of its own inside a function — assign it to a
local variable first) and `shelldre:S7688` (`[ … ]` instead of `[[ … ]]`). Other `shelldre:*` findings are first
reported by the *Sonar gate* below.

*Sonar gate* runs SonarQube Cloud's own analysis on the work branch before the pull request (squad step 7):
`sonar-check.py` runs the scanner with the branch name, waits for the analysis and fails on every open issue or
security hotspot on a line the branch changed, so the rules no local analyzer has stop surfacing only after the
pull request. It runs on the committed change (the scanner uploads the working tree, so it refuses uncommitted or
untracked files other than the coverage reports) and needs `SONAR_TOKEN` in the session's environment (an environment secret) and network access to the
scanner's download hosts (`api.sonarcloud.io`, `scanner.sonarcloud.io` and the package registry); without them it
reports NOT CHECKED, and step 11 reads the draft pull request with `python3 .squad/tools/sonar-check.py pr <number>`
instead. A finding of a rule no local analyzer reports is noted in this section, in the same change, instead of a
squad lesson.

## Image build check

The Dockerfile copies `package.json` and `package-lock.json` first, runs `npm ci`, then copies the sources and
runs *Build*. Where Docker runs, build the image. Where it does not (the sandbox), reproduce that order in a
scratch directory: copy the two manifests, `npm ci`, copy the tracked sources (`git ls-files`, so a file
`.dockerignore` or `.gitignore` leaves out is missing here too), then `npm run build` — a dependency the lock
file does not pin, or an asset the `COPY` lines leave out, fails here as it would in the image. Every change
to `package.json`, `package-lock.json`, a static asset or the Dockerfile runs it before the review; a build
from the full working tree does not replace it.

## Coverage exclusions

Two places compute coverage and must agree (`.squad/routing.md`, *Code a unit test cannot cover*): the
*Coverage gate* reads `COVERAGE_PATHSPECS` and `COVERAGE_EXCLUDES` in `.squad/tools/squad_settings.py`, and
SonarQube Cloud reads `sonar.coverage.exclusions` in `sonar-project.properties`. A file no unit test can cover
(a generated file, a browser-only script without a test runner) is added to both with a decision record —
never to `sonar.exclusions`, which would drop it from the analysis too.

## Writing code

- ES modules, `strict` TypeScript, no `any` without a comment explaining why, no non-null assertions to
  silence the compiler.
- `const` by default, `===` only, async/await over raw promise chains, every promise awaited or
  explicitly handled.
- {{TODO: project-specific conventions: naming, module layout, error handling}}

## Logger arguments

CodeQL's *Clear-text logging of sensitive information* (`js/clear-text-logging`) judges a value by its
**name**: a variable, property or call whose name contains `secret`, `trusted`, `confidential`,
`account`/`accnt`, `puid`, `uid`, `username`/`userid`, `sessionid`/`sessionkey`, `password`, `passwd`,
`passcode`, `passphrase`, `authkey`, `oauth`, `apikey`/`apitoken`, `mfa`, `cert`, or names private data
(`ssn`, `zipcode`, `phone`, `creditcard`, `iban`, `birthdate`, `gender`, `medical`, …) counts as sensitive,
unless it also contains `hash`, `md5`, `sha`, `random`, `crypt`, `encode`, `redact`, `censor`, `obfuscate`,
`file`, `path`, `url` (or `accounting`, `certain`, `concert`, `secretary`, `wildcard`, `coauthor`)
(`shared/concepts/codeql/concepts/internal/SensitiveDataHeuristics.qll` in `github/codeql`, `HeuristicNames`).
Such a name passed to a log call fails the PR in CI, also when it holds only a label, and no local gate
reports it. The remedy is a neutral name for the value whose text a test pins, never a suppression.

## Writing tests

See `docs/UNIT_TESTS.md`. Tests follow the same ESLint rules as production code; every assertion carries a
message where the assertion API accepts one.

## Skeleton

New exports with their full signature and JSDoc, bodies `throw new Error("Not implemented");`, so
`typecheck` passes and the tests load and fail.
Constructors store their arguments and never throw: a test harness builds these types, so only member bodies
fail.
The `Skeleton` body above is the default. A zero-value stub is allowed only where it would break a test that
exists and passes today: the new tests must still fail on the stub, and the Dev reports it as a deviation.

## Dependencies

Added with `npm install <pkg>` (or `--save-dev`), committed together with `package-lock.json`; exact or
caret versions as the repository already uses. A new runtime dependency is a `security`-tier change.

## Concurrency

Test runs and builds share `dist/`, `coverage/` and caches; run one at a time.

## Known pitfalls

- `npx --no-install eslint` fails when dependencies are not installed — run *Restore* first.
