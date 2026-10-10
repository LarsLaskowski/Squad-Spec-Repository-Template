"""Per-repository settings for the squad tools (.NET profile). Seeded once by adopt-template and kept on
later refreshes; the scripts that import it are template-managed."""

# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.
BASE_REF = "origin/main"

# Solution or project file the analyzer gate builds.
SOLUTION = "{{TODO: Solution}}.slnx"

# Coverage gate (.squad/tools/coverage-check.py): line coverage on new/changed production lines, and overall.
# COVERAGE_OVERALL_THRESHOLD may start below COVERAGE_THRESHOLD in a repository adopted with a coverage debt;
# it is never lowered and is raised towards COVERAGE_THRESHOLD as coverage improves.
COVERAGE_THRESHOLD = 80
COVERAGE_OVERALL_THRESHOLD = 80
COVERAGE_FORMAT = "cobertura"
COVERAGE_REPORT_GLOB = "TestResults/**/coverage.cobertura.xml"
COVERAGE_PATHSPECS = ["src/*.cs", "src/*.razor"]
COVERAGE_EXCLUDES = []
COVERAGE_TEST_PATHSPECS = ["tests/*.cs"]  # a diff touching these is gated on overall coverage too
