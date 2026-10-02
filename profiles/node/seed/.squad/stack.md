# Stack: Node.js / TypeScript

The toolchain and the exact commands of this repository. Every squad member, skill and instruction file
refers to the entries below by their *italic name*. Seeded from the ProjectTemplate `node` profile and
owned by this repository: keep it true when the build changes.

## Toolchain

- Node.js `<22+>` (`engines` in `package.json`), npm with a committed `package-lock.json`.
- TypeScript (`tsc`), **ESLint** with **eslint-plugin-sonarjs** (the SonarQube JS/TS rules locally, so
  SonarQube issues surface before the push) and **Prettier** as the formatter.
- The SessionStart hook `.claude/hooks/session-start.sh` runs `npm ci` in remote sessions.

## Layout

- Production code: `{{src/ …}}`.
- Tests: `{{colocated `*.test.ts` next to the code | `test/`}}`, one test file per module under test, named
  `<module>.test.ts`.

## Commands

All commands go through `package.json` scripts; a missing script is added, not worked around.

| Name | Command |
| ---- | ------- |
| *Restore* | `npm ci` |
| *Format* (Code Officer only in the squad) | `npm run format` (`prettier --write .`) |
| *Format check* | `npm run format:check` (`prettier --check .`) |
| *Build* | `npm run build` |
| *Test* | `npm test` |
| *Single test* | `<e.g. node --import tsx --test --test-name-pattern "<name>" src/x.test.ts>` |
| *Test with coverage* | `npm run coverage:lcov` (writes `coverage/lcov.info`) |
| *Coverage gate* | `python3 .squad/tools/coverage-check.py` |
| *Analyzer gate* | `python3 .squad/tools/analyzer-check.py` |

## Analyzer gate

`analyzer-check.py` runs the npm scripts in `CHECK_SCRIPTS` of `.squad/tools/squad_settings.py` (at least
`typecheck`, which must pass for the whole repository) and ESLint on every file changed since the merge
base with `origin/main`; any ESLint message — error or warning — in a changed file fails the gate.
Fixable style findings are the Code Officer's (`eslint --fix` on the changed files, then *Format*); rule
findings that need a code change go to the Dev or Tester.

SonarQube Cloud can still report rules the local plugin version does not have, and its non-lint checks
(duplication, hotspots, taint analysis) only run in CI — such findings arrive in squad step 11.

## Writing code

- ES modules, `strict` TypeScript, no `any` without a comment explaining why, no non-null assertions to
  silence the compiler.
- `const` by default, `===` only, async/await over raw promise chains, every promise awaited or
  explicitly handled.
- {{project-specific conventions: naming, module layout, error handling}}

## Writing tests

See `docs/UNIT_TESTS.md`. Tests follow the same ESLint rules as production code; every assertion carries a
message where the assertion API accepts one.

## Skeleton

New exports with their full signature and JSDoc, bodies `throw new Error("Not implemented");`, so
`typecheck` passes and the tests load and fail.

## Dependencies

Added with `npm install <pkg>` (or `--save-dev`), committed together with `package-lock.json`; exact or
caret versions as the repository already uses. A new runtime dependency is a `security`-tier change.

## Concurrency

Test runs and builds share `dist/`, `coverage/` and caches; run one at a time.

## Known pitfalls

- `npx --no-install eslint` fails when dependencies are not installed — run *Restore* first.
