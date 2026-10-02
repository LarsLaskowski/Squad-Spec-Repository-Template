<!-- stack:begin golden-rules -->
- Every tool runs through a `package.json` script (`format`, `format:check`, `lint`, `typecheck`, `test`,
  `coverage:lcov`); **ESLint with eslint-plugin-sonarjs** runs the SonarQube rules locally, so SonarQube
  issues surface before the CI analysis.
- Add dependencies with npm and commit `package-lock.json` with them.
<!-- stack:end golden-rules -->
<!-- stack:begin commands -->
```bash
npm ci
npm run format                                              # prettier --write
npm run typecheck
npm run build
npm test
npm run coverage:lcov                                       # coverage/lcov.info
python3 .squad/tools/analyzer-check.py                      # analyzer gate
python3 .squad/tools/coverage-check.py                      # coverage gate
```
<!-- stack:end commands -->
<!-- stack:begin configuration -->
- **Node.js** version from `engines` in `package.json`; **npm** with a committed `package-lock.json`.
- **TypeScript** in `strict` mode; **ESLint** (flat config) with **eslint-plugin-sonarjs**; **Prettier**.
<!-- stack:end configuration -->
<!-- stack:begin code-style -->
ES modules; `strict` TypeScript; no `any` without a justifying comment; no non-null assertions to silence
the compiler; `const` by default; `===` only; async/await; every promise awaited or explicitly handled;
formatting is Prettier's, never hand-tuned.
<!-- stack:end code-style -->
<!-- stack:begin testing -->
**Unit tests are mandatory for newly written code.** One test file per module under test
(`<module>.test.ts`), test names describing scenario and expected result, an assertion message where the
assertion API accepts one, no real network or clock.
<!-- stack:end testing -->
