"""Per-repository settings for the squad tools (Node/TypeScript profile). Seeded once by adopt-template
and kept on later refreshes; the scripts that import it are template-managed."""

# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.
BASE_REF = "origin/main"

# Analyzer gate (.squad/tools/analyzer-check.py): npm scripts that must pass for the whole repository,
# and the extensions ESLint checks in changed files.
CHECK_SCRIPTS = ["typecheck"]
LINT_EXTENSIONS = [".ts", ".tsx", ".js", ".mjs", ".cjs"]

# Coverage gate (.squad/tools/coverage-check.py): line coverage on new/changed production lines, and overall.
# COVERAGE_OVERALL_THRESHOLD may start below COVERAGE_THRESHOLD in a repository adopted with a coverage debt;
# it is never lowered and is raised towards COVERAGE_THRESHOLD as coverage improves.
COVERAGE_THRESHOLD = 80
COVERAGE_OVERALL_THRESHOLD = 80
COVERAGE_FORMAT = "lcov"
COVERAGE_REPORT_GLOB = "coverage/lcov.info"
COVERAGE_PATHSPECS = ["src/*.ts", "src/*.tsx", "src/*.js", "src/*.mjs"]
COVERAGE_EXCLUDES = ["*.test.ts", "*.spec.ts", "*.test.js", "*.spec.js"]
