"""Per-repository settings for the squad tools (Go profile). Seeded once by adopt-template and kept on
later refreshes; the scripts that import it are template-managed."""

# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.
BASE_REF = "origin/main"

# Coverage gate (.squad/tools/coverage-check.py): line coverage on new/changed production lines, and overall.
# COVERAGE_OVERALL_THRESHOLD may start below COVERAGE_THRESHOLD in a repository adopted with a coverage debt;
# it is never lowered and is raised towards COVERAGE_THRESHOLD as coverage improves.
COVERAGE_THRESHOLD = 80
COVERAGE_OVERALL_THRESHOLD = 80
COVERAGE_FORMAT = "go"
COVERAGE_REPORT_GLOB = "coverage.out"
COVERAGE_PATHSPECS = ["*.go"]
COVERAGE_EXCLUDES = ["*_test.go"]
