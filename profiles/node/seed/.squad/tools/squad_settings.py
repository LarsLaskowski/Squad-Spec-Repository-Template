"""Per-repository settings for the squad tools (Node/TypeScript profile). Seeded once by adopt-template
and kept on later refreshes; the scripts that import it are template-managed."""

# Analyzer gate (.squad/tools/analyzer-check.py): npm scripts that must pass for the whole repository,
# and the extensions ESLint checks in changed files.
CHECK_SCRIPTS = ["typecheck"]
LINT_EXTENSIONS = [".ts", ".tsx", ".js", ".mjs", ".cjs"]

# Coverage gate (.squad/tools/coverage-check.py)
COVERAGE_FORMAT = "lcov"
COVERAGE_REPORT_GLOB = "coverage/lcov.info"
COVERAGE_PATHSPECS = ["src/*.ts", "src/*.tsx", "src/*.js", "src/*.mjs"]
COVERAGE_EXCLUDES = ["*.test.ts", "*.spec.ts", "*.test.js", "*.spec.js"]
