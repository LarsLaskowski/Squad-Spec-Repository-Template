"""Per-repository settings for the squad tools (TypeScript profile). Seeded once by adopt-template
and kept on later refreshes; the scripts that import it are template-managed."""

# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.
BASE_REF = "origin/main"

# Tier `patch` (.squad/routing.md, *Tiers*; scope-check.py --tier patch): changed lines outside specs/ at most.
PATCH_MAX_LINES = 30

# Who approves a feature's spec before it is planned (.squad/orchestration.md, *Spec approval*): "lead" or "pm".
SPEC_APPROVAL = "lead"

# Size of the squad's working records (.squad/tools/plan-check.py): words of plan.md per tier (a `Plan size:` line
# under its header allows up to twice as many), and of spec.md SPEC_BASE_WORDS plus SPEC_WORDS_PER_CRITERION per
# acceptance criterion, at most SPEC_MAX_WORDS. A feature of at most SMALL_FEATURE_CRITERIA criteria and no security
# area may let its criteria be its scenarios. Each is a ceiling for the largest change of its kind, not a target.
PLAN_MAX_WORDS = {"tests": 800, "trivial": 800, "standard": 2500, "security": 4000}
SPEC_BASE_WORDS = 300
SPEC_WORDS_PER_CRITERION = 200
SPEC_MAX_WORDS = 2500
SMALL_FEATURE_CRITERIA = 3

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
