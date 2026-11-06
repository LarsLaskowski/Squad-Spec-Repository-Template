"""Per-repository settings for the squad tools (TypeScript profile). Seeded once by adopt-template
and kept on later refreshes; the scripts that import it are template-managed."""

# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.
BASE_REF = "origin/main"

# Tier `patch` (.squad/routing.md, *Tiers*; scope-check.py --tier patch): changed lines outside specs/ at most.
PATCH_MAX_LINES = 30

# Analyzer gate (.squad/tools/analyzer-check.py): npm scripts that must pass for the whole repository,
# and the extensions ESLint checks in changed files.
CHECK_SCRIPTS = ["typecheck"]
LINT_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts"]

# Coverage gate (.squad/tools/coverage-check.py): line coverage on new/changed production lines, and overall.
# COVERAGE_OVERALL_THRESHOLD may start below COVERAGE_THRESHOLD in a repository adopted with a coverage debt;
# it is never lowered and is raised towards COVERAGE_THRESHOLD as coverage improves.
COVERAGE_THRESHOLD = 80
COVERAGE_OVERALL_THRESHOLD = 80
COVERAGE_FORMAT = "lcov"
COVERAGE_REPORT_GLOB = "coverage/lcov.info"
COVERAGE_PATHSPECS = ["src/*.ts", "src/*.tsx", "src/*.mts", "src/*.cts"]
COVERAGE_EXCLUDES = ["*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx", "*.d.ts"]

# Size warnings (config-check.py, decision-check.py): a file past its limit is reported with the split it needs.
PROJECT_MAX_WORDS = 1500  # .squad/project.md, read by five members on every launch
AREA_MAX_WORDS = 5000  # each area document in docs/areas/
RECORD_MAX_WORDS = 1500  # each unreleased decision record
RECORD_MAX_OPTIONS = 8  # the options under *Options considered* of an unreleased decision record

# Stale-figure check (.squad/tools/figure-check.py): values it does not search in the documentation (prose uses them
# for list items, steps and counts), and source files whose values it does not read (lock files, generated files).
FIGURE_TRIVIAL = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "100"]
FIGURE_EXCLUDES = ["package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "*.lock", "*.svg"]
