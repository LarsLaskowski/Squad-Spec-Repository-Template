<!-- stack:begin golden-rules -->
- Every tool runs through a `package.json` script (`format`, `format:check`, `lint`, `typecheck`, `test`,
  `coverage:lcov`); **typescript-eslint with type information** (`strictTypeChecked`) and
  **eslint-plugin-sonarjs** run locally, so type-aware and SonarQube issues surface before the CI analysis.
- The compiler is the first reviewer: `tsc --noEmit` passes for the whole repository, and a type error is
  never silenced with `any`, a cast or `@ts-ignore`.
- Add dependencies with npm and commit `package-lock.json` with them.
<!-- stack:end golden-rules -->
<!-- stack:begin commands -->
```bash
npm ci --ignore-scripts
npm run format                                              # prettier --write
npm run typecheck                                           # tsc --noEmit
npm run build
npm test
npm run coverage:lcov                                       # coverage/lcov.info
python3 .squad/tools/analyzer-check.py                      # analyzer gate
python3 .squad/tools/coverage-check.py                      # coverage gate
```
<!-- stack:end commands -->
<!-- stack:begin configuration -->
- **TypeScript** with `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride` and `verbatimModuleSyntax`
  in `tsconfig.json`; **Node.js** version from `engines` in `package.json`; **npm** with a committed
  `package-lock.json`.
- **ESLint** (flat config) with **typescript-eslint** `strictTypeChecked` (type-aware, `projectService`) and
  **eslint-plugin-sonarjs**; **Prettier**; **Vitest** with `@vitest/coverage-v8`.
<!-- stack:end configuration -->
<!-- stack:begin code-style -->
ES modules with `import type` for type-only imports; no `any` — `unknown` narrowed by a type guard at the
boundary; no `as` cast and no non-null assertion to silence the compiler (a cast only after a runtime check,
with a comment); `@ts-expect-error` with a reason instead of `@ts-ignore`; exhaustive `switch` over a union
with a `never` check; `readonly` where nothing mutates; `const` by default; `===` only; async/await; every
promise awaited or explicitly handled; formatting is Prettier's, never hand-tuned.
<!-- stack:end code-style -->
<!-- stack:begin testing -->
**Unit tests are mandatory for newly written code.** One test file per module under test
(`<module>.test.ts`), test names describing scenario and expected result, an assertion message where the
assertion API accepts one, no real network or clock (the one exception, a time bound tested as a ratio of
two durations, is in `docs/UNIT_TESTS.md`). Test code is type-checked and linted like production code.
<!-- stack:end testing -->
