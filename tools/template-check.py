#!/usr/bin/env python3
"""Self-check for Squad-Spec-Repository-Template, run before every PR in this repository.

Checks, without arguments:

- every agent and skill, both in `core/` and at the repository root, has valid front matter;
- `core/AGENTS.md` and `core/CLAUDE.md` use only repository-rooted links, `core/CLAUDE.md` only imports
  `AGENTS.md` (no section, no marker of its own), and every `<!-- …:begin X -->` marker in a core file has
  its matching end marker;
- no Markdown file under `core/`, `profiles/`, `seed/`, `multi/` or `decision-seeds/` contains a character
  `scope-check.py` rejects (a zero width joiner in an emoji, for example);
- every profile has the same required files, its `instructions.md` provides every stack block the core
  instruction files use, its `stack.md` defines every command name the core refers to (and `gate-stamp.py` reads a
  command for every gate it runs from it, also from the merged `stack.md` of several profiles), and its
  `squad_settings.py` defines the coverage settings, the size limits of `config-check.py` and `decision-check.py`
  and the settings of `figure-check.py`;
- a smoke test: each profile is applied to an empty git repository with `tools/apply-template.py`, and the
  target's `config-check.py` then reports nothing but unfilled placeholders; after every placeholder is
  filled and the template is applied a second time (a refresh), `config-check.py` passes completely, the
  files the template no longer manages (`RETIRED` in `apply-template.py`) are gone and a line that still refers
  to one is reported, `docs/decisions/process.md` is written and a numbered process record of an older template
  version is listed for retiring; a `.claude/settings.json` that declares only the Git guard (the template before the file guard)
  gets the file guard added; a `CLAUDE.md` that still holds the rules (the layout before `AGENTS.md` held them) has its
  project blocks carried into `AGENTS.md` and is replaced by the core one; `.github/copilot-instructions.md`
  carries the body of `AGENTS.md`, and `config-check.py` fails once the two differ or `CLAUDE.md` stops importing
  `AGENTS.md`;
- the same smoke test for all profiles together (a repository with several languages): the merged CI,
  CodeQL and Dependabot files are valid YAML with every profile's jobs, languages and ecosystems, a refresh
  without `--profile` keeps the recorded profiles, naming another set is refused, and `config-check.py`
  fails when a profile's analyzer script is missing;
- the `sonar-project.properties` seed is skipped in a repository with the `dotnet` profile (its scanner refuses
  the file) and still written for go+node;
- `decision-check.py` on a temporary repository: consistent records pass, a duplicate number and a link to a
  renamed record fail, an unreleased record may be edited in place, and around a release tag a rewritten,
  deleted or wrongly superseded record fails; once areas are defined, a record without a listed `Area:` and an
  area without its document fail, and a released record without `Area:` passes only with one listed area from an
  `## Area assignment` table in a later record;
- every Python tool a target receives (`core/`, `profiles/`, `multi/`, `seed/`) and the template's own (`tools/`)
  stays at or below SonarQube Cloud's cognitive-complexity limit of 15 (`python:S3776`), measured with complexipy
  where it is installed (CI installs it), and trips none of the other SonarQube Cloud rules that have flagged one
  (`SONAR_RULES`: duplicated string literals, nested conditional expressions, anchored regex alternatives without a
  group, several spaces in a regex, a function that always returns the same value, a mock lambda that ignores its
  arguments instead of `return_value`, a unittest assertion a more specific one replaces, a reluctant quantifier
  followed only by zero-width assertions, a comma in the explanation of a `noqa` comment, an unanchored regex that
  starts with an unbounded repetition and goes on with something that can fail, two adjacent unbounded repetitions
  that can match the same character, a character class that names a character twice, a regex more complex than 20, a
  non-capturing group without alternation or quantifier, a `not` of a single comparison, an attribute of a module the
  test file loads, assigned by hand in a test);
  `sonar-project.properties`
  lists the directory of each of these files as a source, since the scanner skips the hidden `.squad/` and
  `.claude/` below a source directory and CI's SonarQube Cloud analysis would miss them;
- every squad rule file in `RULE_FILES` (the squad's rules, skills and agents, the template parts of
  `AGENTS.md` and `docs/ARCHITECTURE.md` with their empty blocks, the work-folder templates) exists. Against the
  merge base with `origin/main` it reports, as information, how many words (counted like `wc -w` in a UTF-8
  locale) each changed rule file gained or lost and the total against `RULE_WORDS_BASELINE`, the size after the
  last consolidation; a total more than `CONSOLIDATION_GROWTH` above it is a warning to plan a consolidation PR.
  Every sentence that left the rule files (found in none of them any more) is a warning the pull request answers:
  where it moved or why it goes. A run of 20 words that two rule files share is a warning (a rule in two places).
  Members read the rule files they are pointed to on every launch, so size is watched, but a rule is never cut to make room; the
  evidence behind a rule goes into `docs/squad-rationale.md`, which no target receives;
- as information, the words each role reads on every launch: its charter and the files of its *Read first* list
  (only the sections it names, where it names some), split into the template's text and the seeded files a target
  starts with (its own text replaces those), and the orchestrator's skills with the rule files they link — where a
  split of a rule file would pay shows here;
- `consumers.json` lists every repository that uses the template, each with its profiles, its SonarQube Cloud project
  key (or null) and a status `active` or `legacy`;
- `CHANGELOG.md` has the format `tools/release.py` expects, and a branch that changes what the targets receive
  (`CHANGELOG_PATHS`) adds a line under its `## Unreleased` against the merge base with `origin/main`
  (`AGENTS.md`, *Releases*);
- `core/.squad/tools/lesson-label.py` names every file `apply-template.py` manages as managed, the marked and
  generated files as marked and no seed as managed, so a lesson's label follows what a refresh overwrites.

Exit code 0 when everything passes, 1 otherwise. Requires PyYAML.
"""
import ast
import difflib
import fnmatch
import glob
import importlib.util
import io
import itertools
import json
import os
import re
import re._constants as sre_constants
import re._parser as sre_parser
import shutil
import subprocess
import sys
import tempfile
import tokenize
import types

sys.dont_write_bytecode = True  # importing the profiles' squad_settings.py must not leave __pycache__ behind

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
SQUAD_DIR = ".squad"
CLAUDE_DIR = ".claude"
GITHUB_DIR = ".github"
README_MD = "README.md"
SKILL_MD = "SKILL.md"
INSTRUCTIONS_MD = "instructions.md"
CONFIG_CHECK = "config-check.py"
DECISION_CHECK = "decision-check.py"
DEPENDABOT_YML = "dependabot.yml"
CODEQL_YML = "codeql.yml"
YML_FILES = "*.yml"
# Values the decision-check tests repeat.
STORAGE_MD = "storage.md"
STORAGE_AREA = "[Storage](storage.md)"
SUPERSEDED = "Superseded by 0003"
UNRELEASED_EDIT = "Changed before any release."
SKILLS = os.path.join(CLAUDE_DIR, "skills")
RULES = "AGENTS.md"
ORIGIN_MAIN = "origin/main"
CLAUDE = "CLAUDE.md"
INSTRUCTIONS = [RULES, CLAUDE, os.path.join(GITHUB_DIR, "copilot-instructions.md")]
COPILOT = os.path.join(GITHUB_DIR, "copilot-instructions.md")
PROFILE_FILES = [
    INSTRUCTIONS_MD,
    "managed/.claude/hooks/session-start.sh",
    "managed/.squad/tools/analyzer-check.py",
    "seed/.squad/stack.md",
    "seed/.squad/tools/squad_settings.py",
    "seed/docs/UNIT_TESTS.md",
    "seed/.github/workflows/ci.yml",
    "seed/.github/workflows/codeql.yml",
    "seed/.github/dependabot.yml",
]
COMMANDS = ["*Restore*", "*Format*", "*Format check*", "*Build*", "*Test*", "*Single test*", "*Test (project)*",
            "*Test with coverage*", "*Coverage gate*", "*Analyzer gate*", "*Sonar gate*", "*Image build check*"]
STACK_SECTIONS = ["## Toolchain", "## Layout", "## Commands", "## Analyzer gate", "## Image build check",
                  "## Coverage exclusions", "## Writing code", "## Writing tests", "## Skeleton", "## Dependencies",
                  "## Concurrency", "## Known pitfalls"]
# The commands core/.squad/tools/gate-stamp.py runs by their name in stack.md.
GATE_COMMANDS = ["Format check", "Analyzer gate", "Test", "Test (project)", "Test with coverage", "Coverage gate"]
MULTI_FILES = [".squad/tools/analyzer-check.py", ".claude/hooks/session-start.sh"]
SETTINGS = ["COVERAGE_FORMAT", "COVERAGE_REPORT_GLOB", "COVERAGE_PATHSPECS", "COVERAGE_EXCLUDES",
            "PROJECT_MAX_WORDS", "AREA_MAX_WORDS", "RECORD_MAX_WORDS", "RECORD_MAX_OPTIONS", "FIGURE_TRIVIAL",
            "FIGURE_EXCLUDES"]
DISTRIBUTED_DIRS = ["core", "profiles", "multi", "seed"]
COGNITIVE_LIMIT = 15
# SonarQube Cloud rules a refresh has tripped, checked on every distributed Python file and on `tools/` (see
# check_sonar_rules); python:S3776 is checked with complexipy (check_complexity).
SONAR_RULES = ["python:S1192", "python:S1481", "python:S1940", "python:S3358", "python:S3516", "python:S5843",
               "python:S5850", "python:S5906", "python:S5869", "python:S6019", "python:S6326", "python:S6395", "python:S7632",
               "python:S8786", "python:S8997", "python:S9081"]
# python:S5906: assertTrue/assertFalse of a comparison or isinstance(), and an equality or identity assertion against
# None, True, False or round(), have a more specific unittest assertion.
# python:S1481: a parameter a function only ever augments (`errors += found`) and never reads: Sonar takes the
# rebinding for an unused local variable; `errors.extend(found)` says what happens.
# python:S1940: `not` of a single comparison, which the opposite operator states directly (for sets, where `not a <= b`
# is no `a > b`, a difference or another form).
INVERTED_COMPARISONS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn)
TRUTH_ASSERTS = {"assertTrue": (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn),
                 "assertFalse": (ast.Eq, ast.NotEq, ast.Is, ast.IsNot, ast.In, ast.NotIn)}
VALUE_ASSERTS = ("assertEqual", "assertNotEqual", "assertIs", "assertIsNot", "assertAlmostEqual", "assertNotAlmostEqual")
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
LITERAL_EXCLUSIONS = [re.compile(p) for p in (r"[_\-a-zA-Z0-9]+", r"[0-9{} .\-_%:dfrsymhYMHS<>]+", r"#[0-9a-fA-F]{6}")]
REGEX_FUNCTIONS = {"compile", "search", "match", "fullmatch", "split", "findall", "finditer", "sub", "subn"}
FLAG_SETTER = re.compile(r"\(\?[aiLmsux-]+\)")
# The opening of a group with its prefix (`(?:`, `(?=`, `(?<!`, `(?P<name>`, `(?i:`), which matches nothing itself.
GROUP_OPENER = re.compile(r"\((?:\?(?:[:=!>]|<[=!]|P?<\w+>|[aiLmsux-]+:))?")
# python:S6019: a reluctant quantifier, and what may follow one without matching a character (lookarounds, anchors,
# the end of groups), outside character classes.
# python:S6395: the opening of a non-capturing group, a flag group (`(?i:`) included.
NON_CAPTURING = re.compile(r"\(\?[aiLmsux-]*:")
LAZY_QUANTIFIER = re.compile(r"(?<!\\)(?:[*+?]|\{\d*+(?:,\d*+)?+\})\?")
ZERO_WIDTH_PREFIX = re.compile(r"(?:[$)]|\\[AZzbB])*+")
LOOKAROUNDS = ("(?=", "(?!", "(?<=", "(?<!")
# python:S7632: a `noqa` comment whose explanation holds a comma, which Sonar reads as the separator of another rule key.
NOQA = re.compile(r"#\s*noqa:\s*[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*(?P<rest>[^#]*)")
MULTIPLE_SPACES = re.compile(r" {2,}")
# python:S8786: how a regex is used. A compiled one counts once the module calls a method on it, as a partial match
# (search, findall, match, …) unless it is only fullmatched; a fullmatch next to a partial use anchors its end too.
SUPER_LINEAR = "python:S8786"
PARTIAL_FUNCTIONS = {"search", "findall", "finditer", "sub", "subn", "split"}
REPEATS = {sre_constants.MAX_REPEAT, sre_constants.MIN_REPEAT, getattr(sre_constants, "POSSESSIVE_REPEAT", None)}
LOOKAROUND_OPS = {sre_constants.ASSERT, sre_constants.ASSERT_NOT}
# python:S5843: Sonar's regex complexity and its limit. A quantifier, a lookaround and the first `|` of a disjunction
# add their nesting depth (1 at the top level, one more inside each of them), every further `|`, a character class and
# a backreference add 1. Sonar has reported it on a pattern written as one string literal only, never on one spread
# over adjacent literals (two such regexes on main, at 30 and 44 by this count, carry no issue).
REGEX_COMPLEXITY_LIMIT = 20
QUANTIFIER = re.compile(r"(?:[*+?]|\{\d+(?:,\d*)?\}|\{,\d+\})[?+]?")
BACKREFERENCE = re.compile(r"\\[1-9]")
END_ANCHORS = {sre_constants.AT_END, sre_constants.AT_END_STRING}
CHAR_CLASS = re.compile(r"\[\^?\]?(?:\\.|[^\]\\])*\]?", re.S)
# python:S5869 and the second form of python:S8786 ask whether two parts of a regex can match the same character; it is
# tried on the characters the tools' regexes name (Latin-1, Latin Extended and a few other spaces and digits).
SAMPLE = tuple(chr(code) for code in range(0x250)) + ("\u2028", "\u3000", "\uff10")
CATEGORIES = {getattr(sre_constants, f"CATEGORY_{name}"): re.compile(escape) for name, escape in
              (("DIGIT", r"\d"), ("NOT_DIGIT", r"\D"), ("SPACE", r"\s"), ("NOT_SPACE", r"\S"), ("WORD", r"\w"),
               ("NOT_WORD", r"\W"))}
# The squad's rule files under core/ (paths relative to core/): watched for growth and for removed sentences.
RULE_FILES = [
    ".squad/routing.md",
    ".squad/orchestration.md",
    ".squad/team.md",
    ".claude/skills/squad-issue/SKILL.md",
    ".claude/skills/squad-spec/SKILL.md",
    ".claude/skills/create-pr/SKILL.md",
    ".claude/skills/review-pr/SKILL.md",
    ".claude/agents/squad-code-officer.md",
    ".claude/agents/squad-dev.md",
    ".claude/agents/squad-devils-advocate.md",
    ".claude/agents/squad-lead.md",
    ".claude/agents/squad-reviewer.md",
    ".claude/agents/squad-security.md",
    ".claude/agents/squad-tester.md",
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "specs/_template/log.md",
    "specs/_template/plan.md",
    "specs/_template/spec.md",
    "specs/_template/tasks.md",
]
# The words of all rule files after the last consolidation; set anew by each consolidation PR (AGENTS.md, Writing rules).
RULE_WORDS_BASELINE = 28656
CONSOLIDATION_GROWTH = 0.15
SENTENCE_MIN_WORDS = 6
NEAR_MATCH = 0.8
MARKER = re.compile(r"<!-- (project|stack):(begin|end) ([\w-]+) -->")

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def check_front_matter(path, expected, errors):
    text = read(path)
    end = text.find("\n---", 4)
    try:
        data = yaml.safe_load(text[4:end]) if text.startswith("---\n") and end > 0 else None
    except yaml.YAMLError as error:
        errors.append(f"{path}: {str(error).splitlines()[0]}")
        return
    if not isinstance(data, dict) or not data.get("name") or not data.get("description"):
        errors.append(f"{path}: front matter needs name and description")
    elif data["name"] != expected:
        errors.append(f"{path}: name '{data['name']}' does not match '{expected}'")


def check_agents_and_skills(base, errors):
    for path in glob.glob(os.path.join(base, SKILLS, "*", SKILL_MD)):
        check_front_matter(path, os.path.basename(os.path.dirname(path)), errors)
    for path in glob.glob(os.path.join(base, CLAUDE_DIR, "agents", "*.md")):
        check_front_matter(path, os.path.splitext(os.path.basename(path))[0], errors)


CORE_HOOKS = [os.path.join(CLAUDE_DIR, "hooks", name) for name in ("git-guard.py", "file-guard.py", "install-linters.sh")]


def check_relative_links(errors):
    relative = re.compile(r"\]\((?!https?:|#|/|mailto:)[^)\s]+\)")
    for rel in INSTRUCTIONS:
        for match in relative.finditer(read(os.path.join(CORE, rel))):
            errors.append(f"core/{rel}: relative link {match.group(0)} - use a repository-rooted link (/path)")


def check_core(errors):
    if "\n## " in read(os.path.join(CORE, COPILOT)):
        errors.append(f"core/{COPILOT}: holds only the title and introduction, the body is generated from {RULES}")
    claude = read(os.path.join(CORE, CLAUDE))
    if not re.search(r"^@AGENTS\.md$", claude, re.M) or "\n## " in claude or MARKER.search(claude):
        errors.append(f"core/{CLAUDE}: only imports {RULES} ('@{RULES}' on a line of its own, no section or marker)")
    for rel in CORE_HOOKS:
        if not os.path.isfile(os.path.join(CORE, rel)):
            errors.append(f"core/{rel} is missing")
    check_relative_links(errors)
    for path in glob.glob(os.path.join(CORE, "**", "*.md"), recursive=True) + \
            glob.glob(os.path.join(CORE, ".*", "**", "*.md"), recursive=True):
        check_markers(path, errors)


def check_markers(path, errors):
    """Every `<!-- …:begin X -->` marker of a core file has its matching end marker."""
    open_blocks = []
    for kind, edge, name in MARKER.findall(read(path)):
        if edge == "begin":
            open_blocks.append((kind, name))
        elif not open_blocks or open_blocks.pop() != (kind, name):
            errors.append(f"{os.path.relpath(path, ROOT)}: unbalanced marker {kind}:{edge} {name}")
    if open_blocks:
        errors.append(f"{os.path.relpath(path, ROOT)}: unclosed markers {open_blocks}")


def load_scope_check():
    """core/.squad/tools/scope-check.py as a module; it imports the target's squad_settings, which is stubbed here."""
    tools = os.path.join(CORE, SQUAD_DIR, "tools")
    sys.modules.setdefault("squad_settings", types.SimpleNamespace(BASE_REF=ORIGIN_MAIN))
    if tools not in sys.path:
        sys.path.insert(0, tools)
    spec = importlib.util.spec_from_file_location("scope_check", os.path.join(tools, "scope-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_control_characters(errors):
    """A Markdown file the template writes must pass scope-check.py's control-character check: it checks the whole
    file, so a joiner in template text would fail every product change that edits the file's project blocks."""
    scope_check = load_scope_check()
    paths = []
    for base in ("core", "profiles", "seed", "multi", "decision-seeds"):
        paths += glob.glob(os.path.join(ROOT, base, "**", "*.md"), recursive=True)
        paths += glob.glob(os.path.join(ROOT, base, "**", ".*", "**", "*.md"), recursive=True)
    for path in sorted(set(paths)):
        found = scope_check.control_characters(scope_check.read_text(path))
        if found:
            errors.append(f"{os.path.relpath(path, ROOT)}: control characters {', '.join(found)} that scope-check.py "
                          "rejects (use an emoji of a single code point, or a text escape)")


PLACEHOLDER = re.compile(r"\{\{TODO:[^{}]*\}\}")
BLOCK = re.compile(r"<!-- project:begin ([\w-]+) -->\n.*?<!-- project:end \1 -->", re.S)
MARKED = [RULES, os.path.join("docs", "CONTRIBUTING.md"), os.path.join("docs", "ARCHITECTURE.md"),
          os.path.join(GITHUB_DIR, "ISSUE_TEMPLATE", "bug_report.md"), os.path.join("docs", "decisions", README_MD),
          os.path.join("docs", "areas", README_MD),
          os.path.join(GITHUB_DIR, "pull_request_template.md")]


def check_placeholders(errors):
    """A placeholder outside a project block would be reset by every refresh and could never be filled."""
    paths = [p for p in glob.glob(os.path.join(CORE, "**", "*"), recursive=True) +
             glob.glob(os.path.join(CORE, ".*", "**", "*"), recursive=True) +
             glob.glob(os.path.join(ROOT, "profiles", "*", "managed", "**", "*"), recursive=True) +
             glob.glob(os.path.join(ROOT, "profiles", "*", "managed", ".*", "**", "*"), recursive=True) +
             glob.glob(os.path.join(ROOT, "profiles", "*", INSTRUCTIONS_MD))
             if os.path.isfile(p) and "_template" not in p and "__pycache__" not in p and not p.endswith(".py")]
    for path in sorted(set(paths)):
        text = read(path)
        if os.path.relpath(path, CORE) in MARKED:
            text = BLOCK.sub("", text)
        for match in PLACEHOLDER.finditer(text):
            errors.append(f"{os.path.relpath(path, ROOT)}: placeholder {match.group(0)!r} outside a project block")


def check_profiles(errors):
    stack_blocks = set(re.findall(r"<!-- stack:begin ([\w-]+) -->", read(os.path.join(CORE, RULES))))
    profiles = sorted(p for p in glob.glob(os.path.join(ROOT, "profiles", "*")) if os.path.isdir(p))
    for profile in profiles:
        name = os.path.basename(profile)
        for rel in PROFILE_FILES:
            if not os.path.isfile(os.path.join(profile, rel)):
                errors.append(f"profile {name}: missing {rel}")
        check_profile_instructions(profile, name, stack_blocks, errors)
        check_profile_scripts(profile, name, errors)
        check_profile_stack(profile, name, errors)
        check_profile_settings(profile, name, errors)
    return [os.path.basename(p) for p in profiles]


def check_profile_instructions(profile, name, stack_blocks, errors):
    instructions = os.path.join(profile, INSTRUCTIONS_MD)
    if os.path.isfile(instructions):
        provided = set(re.findall(r"<!-- stack:begin ([\w-]+) -->", read(instructions)))
        for block in sorted(stack_blocks - provided):
            errors.append(f"profile {name}: instructions.md lacks stack block '{block}'")


def check_profile_scripts(profile, name, errors):
    hook = os.path.join(profile, "managed", CLAUDE_DIR, "hooks", "session-start.sh")
    if os.path.isfile(hook) and "install-linters.sh" not in read(hook):
        errors.append(f"profile {name}: session-start.sh does not run .claude/hooks/install-linters.sh")
    gate = os.path.join(profile, "managed", SQUAD_DIR, "tools", "analyzer-check.py")
    if os.path.isfile(gate) and "lint_check" not in read(gate):
        errors.append(f"profile {name}: analyzer-check.py does not call lint_check() from analyzer_common.py")
    if os.path.isfile(gate) and "lint_only_requested()" not in read(gate):
        errors.append(f"profile {name}: analyzer-check.py does not offer --lint-only (lint_only_requested())")


def check_profile_stack(profile, name, errors):
    stack = os.path.join(profile, "seed", SQUAD_DIR, "stack.md")
    if os.path.isfile(stack):
        text = read(stack)
        for needle in COMMANDS + STACK_SECTIONS:
            if needle not in text:
                errors.append(f"profile {name}: stack.md lacks '{needle}'")
        check_gate_commands(name, text, errors)


_GATE_STAMP = []


def gate_stamp():
    """core/.squad/tools/gate-stamp.py as a module (loaded once)."""
    if not _GATE_STAMP:
        spec = importlib.util.spec_from_file_location("gate_stamp", os.path.join(CORE, SQUAD_DIR, "tools",
                                                                                 "gate-stamp.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _GATE_STAMP.append(module)
    return _GATE_STAMP[0]


def check_gate_commands(label, text, errors):
    """gate-stamp.py finds a command for every gate it runs in the stack.md text."""
    commands = gate_stamp().stack_commands(text)
    for name in GATE_COMMANDS:
        if not commands.get(name):
            errors.append(f"profile {label}: gate-stamp.py finds no command for *{name}* in stack.md (the first code "
                          "span of its row in a Commands table)")


def check_profile_settings(profile, name, errors):
    settings = os.path.join(profile, "seed", SQUAD_DIR, "tools", "squad_settings.py")
    if os.path.isfile(settings):
        spec = importlib.util.spec_from_file_location(f"settings_{name}", settings)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for key in SETTINGS:
            if not hasattr(module, key):
                errors.append(f"profile {name}: squad_settings.py lacks {key}")


def apply(target, *options):
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "apply-template.py"), "--target", target,
                           *options], capture_output=True, text=True)


def profile_options(names):
    return [option for name in names for option in ("--profile", name)]


def run_config_check(target):
    return subprocess.run([sys.executable, os.path.join(target, SQUAD_DIR, "tools", CONFIG_CHECK)],
                          capture_output=True, text=True)


def smoke_test(profiles, errors):
    groups = [[name] for name in profiles]
    if len(profiles) > 1:
        groups.append(profiles)
    for names in groups:
        smoke_profiles(names, errors)


def smoke_profiles(names, errors):
    """Apply the profiles to an empty repository, fill the placeholders, refresh, and check what config-check reports."""
    label = "+".join(names)
    with tempfile.TemporaryDirectory() as target:
        subprocess.run(["git", "init", "-q", target], check=True)
        applied = apply(target, *profile_options(names))
        if applied.returncode != 0:
            errors.append(f"profile {label}: apply-template failed: {applied.stderr.strip()[-500:]}")
            return
        checked = run_config_check(target)
        lines = [line for line in checked.stdout.splitlines()
                 if line and not line.startswith("Checked") and "placeholder" not in line]
        for line in lines:
            errors.append(f"profile {label}: config-check after apply: {line}")
        fill_placeholders(target)
        plant_retired(target)
        plant_process_record(target)
        plant_legacy_rules(target)
        plant_git_guard_only(target)
        # a refresh names no profile: the recorded ones are kept
        refresh = apply(target)
        if refresh.returncode != 0:
            errors.append(f"profile {label}: refresh failed: {refresh.stderr.strip()[-500:]}")
            return
        check_refresh(label, target, refresh, errors)
        check_legacy_rules(label, target, errors)
        check_copilot_mirror(label, target, errors)
        if len(names) > 1:
            check_multi(names, target, errors)


CLAUDE_SETTINGS = os.path.join(CLAUDE_DIR, "settings.json")
FILE_GUARD = "file-guard.py"


def plant_git_guard_only(target):
    """Turn the target's settings into those of the template before the file guard: the Git guard's hook only."""
    path = os.path.join(target, CLAUDE_SETTINGS)
    with open(path, encoding="utf-8") as handle:
        settings = json.load(handle)
    settings["hooks"]["PreToolUse"] = [group for group in settings["hooks"]["PreToolUse"]
                                       if FILE_GUARD not in json.dumps(group)]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)


def check_refresh(label, target, refresh, errors):
    """The refresh removed the retired files, reported the reference to one of them, added the file guard to the
    settings, and config-check passes."""
    for rel in RETIRED_SAMPLE:
        if os.path.exists(os.path.join(target, rel)):
            errors.append(f"profile {label}: refresh kept the retired file {rel}")
    if FILE_GUARD not in read(os.path.join(target, CLAUDE_SETTINGS)):
        errors.append(f"profile {label}: refresh did not add the {FILE_GUARD} hook to an existing {CLAUDE_SETTINGS}")
    if f"{STALE_REFERENCE}:1: " not in refresh.stdout or "References to removed files" not in refresh.stdout:
        errors.append(f"profile {label}: refresh does not report the reference to a retired file in "
                      f"{STALE_REFERENCE}")
    if HISTORICAL_REFERENCE in refresh.stdout:
        errors.append(f"profile {label}: refresh lists the decision record {HISTORICAL_REFERENCE}")
    os.remove(os.path.join(target, HISTORICAL_REFERENCE))
    if not os.path.isfile(os.path.join(target, PROCESS_FILE)):
        errors.append(f"profile {label}: refresh did not write {PROCESS_FILE}")
    if f"  {PROCESS_RECORD} (Accepted)" not in refresh.stdout:
        errors.append(f"profile {label}: refresh does not list the process record {PROCESS_RECORD} to retire")
    os.remove(os.path.join(target, PROCESS_RECORD))
    refreshed = run_config_check(target)
    if refreshed.returncode != 0:
        for line in refreshed.stdout.splitlines()[:10]:
            errors.append(f"profile {label}: config-check after filling and refreshing: {line}")


# A project block's content in the rules of the layout before AGENTS.md held them; the refresh carries it over.
LEGACY_BLOCK = "Legacy overview kept in CLAUDE.md."


def plant_legacy_rules(target):
    """Turn the target into the old layout: the rules, with a filled project block, in CLAUDE.md and no AGENTS.md."""
    rules = os.path.join(target, RULES)
    text = re.sub(r"(<!-- project:begin overview -->\n).*?(<!-- project:end overview -->)",
                  lambda m: m.group(1) + LEGACY_BLOCK + "\n" + m.group(2), read(rules), count=1, flags=re.S)
    with open(os.path.join(target, CLAUDE), "w", encoding="utf-8") as handle:
        handle.write(text.replace(f"# {RULES}", f"# {CLAUDE}", 1))
    os.remove(rules)


def check_legacy_rules(label, target, errors):
    """The refresh of the old layout moved CLAUDE.md's project blocks into AGENTS.md and wrote the core CLAUDE.md."""
    rules = os.path.join(target, RULES)
    if not os.path.isfile(rules) or LEGACY_BLOCK not in read(rules):
        errors.append(f"profile {label}: refresh did not carry the project blocks of the old {CLAUDE} into {RULES}")
    if read(os.path.join(target, CLAUDE)) != read(os.path.join(CORE, CLAUDE)):
        errors.append(f"profile {label}: refresh did not replace the old {CLAUDE} with core/{CLAUDE}")


def check_copilot_mirror(label, target, errors):
    """The refresh wrote the Copilot mirror with AGENTS.md's body, and config-check.py fails once the two drift or
    CLAUDE.md stops importing AGENTS.md."""
    mirror = os.path.join(target, COPILOT)
    if not os.path.isfile(mirror):
        errors.append(f"profile {label}: refresh did not write {COPILOT}")
        return
    rules = read(os.path.join(target, RULES))
    if read(mirror).split("\n## ", 1)[-1] != rules.split("\n## ", 1)[-1]:
        errors.append(f"profile {label}: {COPILOT} differs from {RULES} after the first '## ' heading")
    original = read(mirror)
    with open(mirror, "a", encoding="utf-8") as handle:
        handle.write("\nA rule only Copilot knows.\n")
    drifted = run_config_check(target)
    if drifted.returncode == 0 or "copilot-instructions.md differs" not in drifted.stdout:
        errors.append(f"profile {label}: config-check passes although {COPILOT} drifted from {RULES}")
    with open(mirror, "w", encoding="utf-8", newline="") as handle:
        handle.write(original)
    claude = os.path.join(target, CLAUDE)
    original = read(claude)
    with open(claude, "w", encoding="utf-8") as handle:
        handle.write(original.replace(f"@{RULES}", f"See {RULES}."))
    unlinked = run_config_check(target)
    if unlinked.returncode == 0 or f"does not import {RULES}" not in unlinked.stdout:
        errors.append(f"profile {label}: config-check passes although {CLAUDE} no longer imports {RULES}")
    with open(claude, "w", encoding="utf-8", newline="") as handle:
        handle.write(original)


def check_multi(names, target, errors):
    label = "+".join(names)
    with open(os.path.join(target, SQUAD_DIR, "template.json"), encoding="utf-8") as handle:
        record = json.load(handle)
    if record.get("profiles") != names or record.get("profile") != names[0]:
        errors.append(f"profile {label}: template.json after a refresh records {record.get('profile')} / "
                      f"{record.get('profiles')}")
    if apply(target, "--profile", names[0]).returncode == 0:
        errors.append(f"profile {label}: apply-template accepted a different profile set without --reset-profiles")
    for rel in MULTI_FILES:
        if not os.path.isfile(os.path.join(target, rel)):
            errors.append(f"profile {label}: {rel} (dispatcher) missing")
    check_gate_commands(label, read(os.path.join(target, SQUAD_DIR, "stack.md")), errors)
    for path in glob.glob(os.path.join(target, GITHUB_DIR, "**", YML_FILES), recursive=True):
        check_merged_yaml(label, names, target, path, errors)
    os.remove(os.path.join(target, SQUAD_DIR, "tools", f"analyzer-check-{names[-1]}.py"))
    if run_config_check(target).returncode == 0:
        errors.append(f"profile {label}: config-check passes although analyzer-check-{names[-1]}.py is missing")


def check_merged_yaml(label, names, target, path, errors):
    """A merged workflow or Dependabot file of a repository with several profiles is valid YAML with every profile's part."""
    try:
        with open(path, encoding="utf-8") as handle:
            parsed = yaml.safe_load(handle)
    except yaml.YAMLError as error:
        errors.append(f"profile {label}: {os.path.relpath(path, target)} is not valid YAML: "
                      f"{str(error).splitlines()[0]}")
        return
    checks = {CODEQL_YML: check_merged_codeql, DEPENDABOT_YML: check_merged_dependabot, "ci.yml": check_merged_ci}
    check = checks.get(os.path.basename(path))
    if check:
        check(label, names, parsed, errors)
    if os.path.basename(os.path.dirname(path)) == "workflows":
        errors += [f"profile {label}: merged {problem}" for problem in
                   workflow_hardening(os.path.relpath(path, target).replace(os.sep, "/"), parsed)]


def workflow_hardening(rel, parsed):
    """The token settings a seeded workflow lacks: every `actions/checkout` step keeps no credentials in `.git/config`
    (`persist-credentials: false`), and a CodeQL workflow grants nothing at the workflow level (`permissions: {}`), so a
    job added later does not inherit the repository's default token (#360, #372)."""
    problems = []
    if os.path.basename(rel) == CODEQL_YML and parsed.get("permissions") != {}:
        problems.append(f"{rel}: no workflow-level `permissions: {{}}`")
    for job_id, job in (parsed.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            if str(step.get("uses", "")).startswith("actions/checkout@") and \
                    (step.get("with") or {}).get("persist-credentials") is not False:
                problems.append(f"{rel}: the checkout of job {job_id} lacks `persist-credentials: false`")
    return problems


def check_seed_workflows(errors):
    """Every seeded workflow of the core and the profiles carries the token settings of workflow_hardening(); a
    `{{TODO: …}}` placeholder, which a target fills in, is read as a plain word."""
    for path in sorted(glob.glob(os.path.join(ROOT, "seed", GITHUB_DIR, "workflows", YML_FILES)) +
                       glob.glob(os.path.join(ROOT, "profiles", "*", "seed", GITHUB_DIR, "workflows", YML_FILES))):
        text = PLACEHOLDER.sub("placeholder", read(path))
        errors.extend(workflow_hardening(os.path.relpath(path, ROOT).replace(os.sep, "/"), yaml.safe_load(text)))


def check_merged_codeql(label, names, parsed, errors):
    languages = [entry["language"] for entry in parsed["jobs"]["analyze"]["strategy"]["matrix"]["include"]]
    expected = list(dict.fromkeys(language for n in names
                                  for language in re.findall(r"- language: (\S+)", profile_file(n, CODEQL_YML))))
    if languages != expected:
        errors.append(f"profile {label}: codeql.yml languages {languages}, expected {expected}")


def check_merged_dependabot(label, names, parsed, errors):
    ecosystems = [u["package-ecosystem"] for u in parsed["updates"]]
    if len(set(ecosystems)) != len(ecosystems):
        errors.append(f"profile {label}: dependabot.yml repeats an ecosystem: {ecosystems}")
    for n in names:
        for ecosystem in re.findall(r"package-ecosystem: *\"?([\w-]+)", profile_file(n, DEPENDABOT_YML)):
            if ecosystem not in ecosystems:
                errors.append(f"profile {label}: dependabot.yml lacks the {n} ecosystem {ecosystem}")


def check_merged_ci(label, names, parsed, errors):
    jobs = set(parsed["jobs"])
    for n in names:
        own = set(re.findall(r"^ {2}([\w-]+):", profile_file(n, "ci.yml").split("\njobs:\n", 1)[1], re.M))
        if len(jobs) < len(own):
            errors.append(f"profile {label}: ci.yml lost jobs of {n}")


def profile_file(name, rel):
    return read(os.path.join(ROOT, "profiles", name, "seed", GITHUB_DIR, rel if rel == DEPENDABOT_YML
                             else os.path.join("workflows", rel)))


# Files an older template version wrote into every target; a refresh must remove them (RETIRED in apply-template.py).
RETIRED_SAMPLE = [os.path.join(SQUAD_DIR, "decisions.md"), os.path.join(SQUAD_DIR, "agents", "lead", "history.md"),
                  os.path.join(SQUAD_DIR, "agents", "dev", "charter.md"),
                  os.path.join(".agents", "skills", "create-pr", SKILL_MD),
                  os.path.join(GITHUB_DIR, "skills", "squad-issue", SKILL_MD)]


# A project file that still links a retired file after the refresh removed it; the refresh must list the line.
STALE_REFERENCE = "docs/build-notes.md"
# A decision record naming a retired file; records state history, so the refresh must not list it.
HISTORICAL_REFERENCE = "docs/decisions/0099-old-instructions.md"


# The squad's process decisions (managed), and a record an older template version numbered in for one of them.
PROCESS_FILE = "docs/decisions/process.md"
PROCESS_RECORD = "docs/decisions/0098-squash-merge-pull-requests.md"


def plant_process_record(target):
    os.makedirs(os.path.dirname(os.path.join(target, PROCESS_RECORD)), exist_ok=True)
    with open(os.path.join(target, PROCESS_RECORD), "w", encoding="utf-8") as handle:
        handle.write("# 0098: Squash-merge pull requests\n\n- **Status:** Accepted\n"
                     "- **Source:** Squad adopted from Squad-Spec-Repository-Template\n")


def plant_retired(target):
    for rel in RETIRED_SAMPLE:
        path = os.path.join(target, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("old mirror\n")
    with open(os.path.join(target, STALE_REFERENCE), "w", encoding="utf-8") as handle:
        handle.write("Process decisions: [`decisions.md`](/.squad/decisions.md).\n"
                     "Not a reference: my.squad/decisions.md.\n")
    os.makedirs(os.path.dirname(os.path.join(target, HISTORICAL_REFERENCE)), exist_ok=True)
    with open(os.path.join(target, HISTORICAL_REFERENCE), "w", encoding="utf-8") as handle:
        handle.write("Process decisions then lived in `.squad/decisions.md`.\n")


def fill_placeholders(target):
    for directory, dirs, names in os.walk(target):
        dirs[:] = [d for d in dirs if d != ".git"]
        for file_name in names:
            path = os.path.join(directory, file_name)
            with open(path, encoding="utf-8", newline="") as handle:
                text = handle.read()
            filled = PLACEHOLDER.sub("filled", text)
            if filled != text:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(filled)


RECORD = """# {n}: {title}

- **Status:** {status}
- **Date:** 2026-01-01
- **Source:** Issue #1
- **Supersedes:** {supersedes}

## Decision

{body}
"""


def write_record(repo, number, status="Accepted", supersedes="—", body="Do it.", area=None):
    path = os.path.join(repo, "docs", "decisions", f"{number}-topic.md")
    text = RECORD.format(n=number, title="Topic", status=status, supersedes=supersedes, body=body)
    if area:
        text = text.replace("- **Source:**", f"- **Area:** {area}\n- **Source:**")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_areas(repo, rows, documents):
    """`docs/areas/README.md` with an index row per (name, link target) and the documents that exist."""
    os.makedirs(os.path.join(repo, "docs", "areas"), exist_ok=True)
    lines = ["# Areas", "", "<!-- project:begin area-index -->", "| Area | Scope | Not here |",
             "| ---- | ----- | -------- |"]
    lines += [f"| {name} | Scope. | Elsewhere. |" for name in rows]
    lines.append("<!-- project:end area-index -->")
    with open(os.path.join(repo, "docs", "areas", README_MD), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    for document in documents:
        with open(os.path.join(repo, "docs", "areas", document), "w", encoding="utf-8") as handle:
            handle.write("# Area\n")


def linked(text):
    """Every record number in text as a link, the way some repositories write their index."""
    return re.sub(r"\b(\d{4})\b", r"[\1](\1-topic.md)", text)


def write_index(repo, rows, link=False):
    lines = ["# Decision records", "", "<!-- project:begin index -->", "| # | Title | Status | Date |",
             "| - | ----- | ------ | ---- |"]
    lines += [f"| {linked(number) if link else number} | Topic | {linked(status) if link else status} | 2026-01-01 |"
              for number, status in rows]
    lines.append("<!-- project:end index -->")
    with open(os.path.join(repo, "docs", "decisions", README_MD), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def check_decision_tool(errors):
    """decision-check.py: consistency without tags, then the freeze rules around a release tag."""
    tool = os.path.join(CORE, SQUAD_DIR, "tools", DECISION_CHECK)
    with tempfile.TemporaryDirectory() as repo:
        def git_in(*args):
            subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                           check=True, capture_output=True)

        def passes():
            return subprocess.run([sys.executable, tool], cwd=repo, capture_output=True, text=True).returncode == 0

        def expect(label, wanted):
            if passes() != wanted:
                errors.append(f"decision-check: {label}: expected {'PASS' if wanted else 'FAIL'}")

        git_in("init", "-q")
        os.makedirs(os.path.join(repo, "docs", "decisions"))
        write_record(repo, "0001")
        write_record(repo, "0002", body="Second.")
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted")])
        git_in("add", "-A")
        git_in("commit", "-qm", "records")
        expect("consistent records without tags", True)
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted")], link=True)
        expect("index rows that link the record", True)
        write_record(repo, "0002", body="Second, extends [0001](0001-topic.md#decision) and "
                                        "[0001](../decisions/0001-topic.md).")
        expect("links to existing records", True)
        write_record(repo, "0002", body="Second, extends [0001](0001-renamed.md).")
        expect("link to a renamed record", False)
        write_record(repo, "0002", body="Second.")
        write_index(repo, [("[0001](0001-old.md)", "Accepted"), ("0002", "Accepted")])
        expect("index row linking a renamed record", False)
        with open(os.path.join(repo, "docs", "decisions", "0002-other.md"), "w", encoding="utf-8") as handle:
            handle.write(RECORD.format(n="0002", title="Other", status="Accepted", supersedes="—", body="Other."))
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted")])
        expect("two records with one number", False)
        os.remove(os.path.join(repo, "docs", "decisions", "0002-other.md"))
        write_index(repo, [("0001", "Accepted")])
        expect("record missing in the index", False)
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted")])
        write_record(repo, "0002", status=SUPERSEDED)
        write_index(repo, [("0001", "Accepted"), ("0002", SUPERSEDED)])
        expect("Superseded by a record that does not exist", False)
        git_in("checkout", "-q", "--", ".")
        write_record(repo, "0001", body=UNRELEASED_EDIT)
        expect("unreleased record edited in place", True)
        git_in("commit", "-qam", "edit")
        git_in("tag", "v0.1.0")
        write_record(repo, "0001", body="Changed after the release.")
        expect("released record rewritten", False)
        git_in("checkout", "-q", "--", ".")
        write_record(repo, "0003", supersedes="0001", body="Replaces 0001.")
        write_record(repo, "0001", status=SUPERSEDED, body=UNRELEASED_EDIT)
        write_index(repo, [("0001", SUPERSEDED), ("0002", "Accepted"), ("0003", "Accepted")])
        expect("released record superseded by a new record", True)
        write_record(repo, "0001", status="Superseded by [0003](0003-topic.md)", body=UNRELEASED_EDIT)
        write_index(repo, [("0001", SUPERSEDED), ("0002", "Accepted"), ("0003", "Accepted")], link=True)
        expect("linked Superseded by status in the record and the index", True)
        write_record(repo, "0001", status=SUPERSEDED, body=UNRELEASED_EDIT)
        write_index(repo, [("0001", SUPERSEDED), ("0002", "Accepted"), ("0003", "Accepted")])
        git_in("add", "-A")
        git_in("commit", "-qm", "supersede")
        write_record(repo, "0003", status="Superseded by 0004", supersedes="0001", body="Replaces 0001.")
        write_record(repo, "0004", supersedes="0003")
        write_index(repo, [("0001", SUPERSEDED), ("0002", "Accepted"), ("0003", "Superseded by 0004"),
                           ("0004", "Accepted")])
        expect("unreleased record superseded", False)
        git_in("checkout", "-q", "--", ".")
        os.remove(os.path.join(repo, "docs", "decisions", "0002-topic.md"))
        write_index(repo, [("0001", SUPERSEDED), ("0003", "Accepted")])
        expect("released record deleted", False)


def check_sonar_seed(profiles, errors):
    """`sonar-project.properties` is seeded by go and node, but not into a repository with dotnet: its scanner refuses it."""
    for names, wanted in ((["go", "dotnet"], False), (["dotnet", "go"], False), (["go", "node"], True)):
        if all(name in profiles for name in names):
            check_sonar_seed_of(names, wanted, errors)


def check_sonar_seed_of(names, wanted, errors):
    label = "+".join(names)
    with tempfile.TemporaryDirectory() as target:
        subprocess.run(["git", "init", "-q", target], check=True)
        for step in ("apply", "refresh"):
            options = profile_options(names) if step == "apply" else []
            applied = apply(target, *options)
            if applied.returncode != 0:
                errors.append(f"sonar seed {label}: {step} failed: {applied.stderr.strip()[-300:]}")
                break
            check_sonar_seed_step(label, step, target, applied, wanted, errors)


def check_sonar_seed_step(label, step, target, applied, wanted, errors):
    exists = os.path.isfile(os.path.join(target, "sonar-project.properties"))
    if exists != wanted:
        state = "exists" if exists else "is missing"
        errors.append(f"sonar seed {label}: sonar-project.properties {state} after {step}")
    skipped = "skipped    sonar-project.properties" in applied.stdout
    if step == "apply" and skipped == wanted:
        state = "skipped" if skipped else "not skipped"
        errors.append(f"sonar seed {label}: apply reports the file as {state}")


def check_area_checks(errors):
    """decision-check.py with areas: records need a listed `Area:`, every area links an existing document."""
    tool = os.path.join(CORE, SQUAD_DIR, "tools", DECISION_CHECK)
    with tempfile.TemporaryDirectory() as repo:
        def expect(label, wanted):
            passed = subprocess.run([sys.executable, tool], cwd=repo, capture_output=True,
                                    text=True).returncode == 0
            if passed != wanted:
                errors.append(f"decision-check areas: {label}: expected {'PASS' if wanted else 'FAIL'}")

        subprocess.run(["git", "init", "-q", repo], check=True)
        os.makedirs(os.path.join(repo, "docs", "decisions"))
        write_record(repo, "0001")
        write_index(repo, [("0001", "Accepted")])
        write_areas(repo, [], [])
        expect("no areas defined, record without Area", True)
        write_areas(repo, [STORAGE_AREA], [STORAGE_MD])
        expect("areas defined, record without Area", False)
        write_record(repo, "0001", area="Network")
        expect("record names an unlisted area", False)
        write_record(repo, "0001", area="Storage")
        expect("record names a listed area", True)
        write_record(repo, "0001", area="\u2014")
        expect("record about no area", True)
        write_areas(repo, [STORAGE_AREA], [])
        os.remove(os.path.join(repo, "docs", "areas", STORAGE_MD))
        expect("area links a document that does not exist", False)
        write_areas(repo, ["Storage"], [STORAGE_MD])
        expect("area without a link", False)


def write_assignment(repo, number, rows):
    """Record `number` with an `## Area assignment` table of (record, area) rows."""
    table = "\n".join(["## Area assignment", "", "| Record | Area |", "| ------ | ---- |"]
                      + [f"| {record} | {area} |" for record, area in rows])
    write_record(repo, number, area="\u2014", body="Assigns areas.\n\n" + table)


def check_area_assignments(errors):
    """decision-check.py: a released record without `Area:` takes its area from a later record's table."""
    tool = os.path.join(CORE, SQUAD_DIR, "tools", DECISION_CHECK)
    with tempfile.TemporaryDirectory() as repo:
        def git_in(*args):
            subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                           check=True, capture_output=True)

        def expect(label, wanted):
            passed = subprocess.run([sys.executable, tool], cwd=repo, capture_output=True,
                                    text=True).returncode == 0
            if passed != wanted:
                errors.append(f"decision-check area assignment: {label}: expected {'PASS' if wanted else 'FAIL'}")

        git_in("init", "-q")
        os.makedirs(os.path.join(repo, "docs", "decisions"))
        write_record(repo, "0001")
        write_record(repo, "0002")
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted")])
        git_in("add", "-A")
        git_in("commit", "-qm", "records")
        git_in("tag", "v1.0.0")
        write_record(repo, "0004")
        write_areas(repo, [STORAGE_AREA], [STORAGE_MD])
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted"), ("0003", "Accepted"), ("0004", "Accepted")])
        write_assignment(repo, "0003", [("0001", "Storage"), ("[0002](0002-topic.md)", "\u2014"),
                                        ("0004", "Storage")])
        expect("unreleased record without Area, named in a table", False)
        write_record(repo, "0004", area="Storage")
        expect("table names a record with its own Area", False)
        write_assignment(repo, "0003", [("0001", "Storage"), ("[0002](0002-topic.md)", "\u2014")])
        expect("released records assigned by a later record", True)
        write_assignment(repo, "0003", [("0001", "Storage")])
        expect("released record named by no table", False)
        write_assignment(repo, "0003", [("0001", "Network"), ("0002", "\u2014")])
        expect("assigned area not listed", False)
        write_assignment(repo, "0003", [("0001", "Storage"), ("0002", "\u2014"), ("0009", "Storage")])
        expect("table names a record that does not exist", False)
        write_assignment(repo, "0003", [("0001", "Storage"), ("0002", "\u2014")])
        write_assignment(repo, "0005", [("0001", "\u2014")])
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted"), ("0003", "Accepted"), ("0004", "Accepted"),
                           ("0005", "Accepted")])
        expect("two tables disagree", False)


def word_count(path):
    """Words as `wc -w` counts them in a UTF-8 locale: runs of non-whitespace characters."""
    return len(read(path).split())


def check_rule_files(errors, base=CORE, files=None):
    """Every listed rule file exists."""
    for rel in RULE_FILES if files is None else files:
        if not os.path.isfile(os.path.join(base, rel)):
            errors.append(f"core/{rel}: listed in RULE_FILES but missing")


def rule_paths(listed):
    """The listed rule files plus every squad agent and skill, so a renamed or retired one is compared too."""
    names = set(listed)
    for pattern in (".claude/agents/squad-*.md", ".claude/skills/*/SKILL.md"):
        names |= {os.path.relpath(path, CORE) for path in glob.glob(os.path.join(CORE, pattern))}
    return sorted(names)


def base_rule_texts(files=None, root=ROOT):
    """{rel: text or None} of the rule files at the merge base with origin/main (the listed ones, the squad agents and
    skills of either side), or None without a merge base (a shallow checkout) or without git."""
    def git(*args):
        return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=False)

    try:
        base = git("merge-base", ORIGIN_MAIN, "HEAD")
        if base.returncode != 0:
            return None
        sha = base.stdout.strip()
        listed = git("ls-tree", "-r", "--name-only", sha, "core/.claude/").stdout.split()
        at_base = [path.removeprefix("core/") for path in listed
                   if fnmatch.fnmatch(path, "core/.claude/agents/squad-*.md")
                   or fnmatch.fnmatch(path, "core/.claude/skills/*/SKILL.md")]
        texts = {}
        for rel in sorted(set(rule_paths(RULE_FILES if files is None else files)) | set(at_base)):
            shown = git("show", f"{sha}:core/{rel}")
            texts[rel] = shown.stdout if shown.returncode == 0 else None
        return texts
    except OSError:
        return None


def current_rule_texts(base=CORE, files=None):
    return {rel: read(os.path.join(base, rel)) for rel in rule_paths(RULE_FILES if files is None else files)
            if os.path.isfile(os.path.join(base, rel))}


def rule_growth(old, new, baseline=None):
    """(information lines, warnings): the words each changed rule file gained or lost, and the total against the
    size after the last consolidation."""
    baseline = RULE_WORDS_BASELINE if baseline is None else baseline
    info = []
    for rel in sorted(set(old) | set(new)):
        before = len((old.get(rel) or "").split())
        after = len((new.get(rel) or "").split())
        if before != after:
            info.append(f"INFO core/{rel}: {before} -> {after} words ({after - before:+d})")
    total = sum(len(text.split()) for text in new.values())
    growth = total / baseline - 1 if baseline else 0.0
    info.append(f"INFO rule files: {total} words, {growth:+.1%} against {baseline} after the last consolidation"
                if baseline else f"INFO rule files: {total} words; no RULE_WORDS_BASELINE set")
    warnings = []
    if baseline and growth > CONSOLIDATION_GROWTH:
        warnings.append(f"WARNING rule files: {total} words, more than {CONSOLIDATION_GROWTH:.0%} over the last "
                        f"consolidation ({baseline}) — plan a consolidation pull request of its own; never cut a "
                        "rule in another pull request to make room (AGENTS.md, Writing rules)")
    return info, warnings


BLOCK_START = re.compile(r"(?:#|[-*] |\d+[.)] |\|)")


def blocks(text):
    """The paragraphs, list items, headings and table rows of a rule text, each joined into one line."""
    found, current = [], []
    for line in re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S).splitlines():
        stripped = line.strip()
        if not stripped or BLOCK_START.match(stripped):
            found.append(" ".join(current))
            current = []
        if stripped.startswith(("#", "|")):
            found.append(stripped)  # a heading or a table row stands alone
        elif stripped:
            current.append(stripped)
    return [block for block in found + [" ".join(current)] if block]


def sentences(text):
    """The sentences of a rule text of at least SENTENCE_MIN_WORDS words, YAML front matter left out."""
    return [s.strip() for block in blocks(text) for s in re.split(r"(?<=[.!?])\s+", block)
            if len(re.findall(r"\w+", s)) >= SENTENCE_MIN_WORDS]


def normalized(text):
    return " ".join(re.findall(r"\w+", text.lower()))


def removed_sentences(old, new):
    """(file, sentence, closest new sentence or None) for every sentence of the old rule files that none of the new
    ones contains any more (moved text is found in its new place and does not count); the closest new sentence is
    given when it shares at least NEAR_MATCH of the words, a rewording rather than a removal."""
    everything = " " + normalized(" ".join(new.values())) + " "
    candidates = [(normalized(s), s) for text in new.values() for s in sentences(text)]
    found = []
    for rel, text in sorted(old.items()):
        for sentence in sentences(text or ""):
            words = normalized(sentence)
            if f" {words} " not in everything:
                found.append((rel, sentence, closest(words, candidates)))
    return found


def closest(words, candidates):
    """The candidate sentence most like `words` when it reaches NEAR_MATCH, else None."""
    best, best_ratio = None, NEAR_MATCH
    for other_words, other in candidates:
        matcher = difflib.SequenceMatcher(None, words.split(), other_words.split())
        if matcher.real_quick_ratio() >= best_ratio and matcher.quick_ratio() >= best_ratio:
            ratio = matcher.ratio()
            if ratio >= best_ratio:
                best, best_ratio = other, ratio
    return best


def dropped_words(sentence, rewording):
    """The words of `sentence` that its rewording no longer has, in order."""
    old, new = normalized(sentence).split(), normalized(rewording).split()
    matcher = difflib.SequenceMatcher(None, old, new)
    return [w for tag, i1, i2, _, _ in matcher.get_opcodes() if tag in ("replace", "delete") for w in old[i1:i2]]


def check_rule_changes(warnings, info, old=None, new=None):
    """Growth and removed sentences of the rule files against origin/main (AGENTS.md, Writing rules)."""
    old = base_rule_texts() if old is None else old
    if old is None:
        info.append("INFO rule files: no merge base with origin/main here, so growth and removed sentences are "
                    "not compared")
        return
    new = current_rule_texts() if new is None else new
    lines, growth_warnings = rule_growth(old, new)
    info += lines
    warnings += growth_warnings
    for rel, sentence, rewording in removed_sentences(old, new):
        if rewording is None:
            warnings.append(f"WARNING core/{rel}: sentence removed — say in the pull request where it moved or why it "
                            f"goes: \"{sentence}\"")
        else:
            dropped = " ".join(dropped_words(sentence, rewording)) or "none (words added)"
            info.append(f"INFO core/{rel}: sentence reworded, words no longer in it: {dropped} — \"{sentence}\"")


REPEAT_MIN_WORDS = 20


def rule_words(base, files):
    """The words of every existing rule file, YAML front matter left out."""
    texts = {}
    for rel in RULE_FILES if files is None else files:
        path = os.path.join(base, rel)
        if os.path.isfile(path):
            body = re.sub(r"\A---\n.*?\n---\n", "", read(path), flags=re.S)
            texts[rel] = re.findall(r"[\w`./<>*-]+", body.lower())
    return texts


def shared_starts(texts, minimum):
    """{(file, other file): {(i, j)}} for every position pair where the two files share `minimum` words."""
    index = {}
    for rel, words in texts.items():
        for i in range(len(words) - minimum + 1):
            index.setdefault(tuple(words[i:i + minimum]), []).append((rel, i))
    found = {}
    for places in index.values():
        for (rel, i), (other, j) in itertools.combinations(places, 2):
            if rel != other:
                found.setdefault((rel, other), set()).add((i, j))
    return found


def run_lengths(starts, minimum):
    """[(i, length)] of the maximal runs the start pairs (i, j) of two files form."""
    runs = []
    for i, j in sorted(starts):
        if (i - 1, j - 1) not in starts:
            length = minimum
            while (i + length - minimum + 1, j + length - minimum + 1) in starts:
                length += 1
            runs.append((i, length))
    return runs


def repeated_runs(base=CORE, files=None, minimum=REPEAT_MIN_WORDS):
    """(file, other file, words, snippet) for every run of at least `minimum` consecutive words that two squad
    rule files share word for word (case and punctuation aside): a rule stated in two places."""
    texts = rule_words(base, files)
    return [(rel, other, length, " ".join(texts[rel][i:i + 8]))
            for (rel, other), starts in sorted(shared_starts(texts, minimum).items())
            for i, length in run_lengths(starts, minimum)]


def check_repeated_rules(warnings, base=CORE, files=None, minimum=REPEAT_MIN_WORDS):
    """A rule lives in exactly one place (AGENTS.md): two squad rule files sharing a long run of words is a
    warning to replace one copy by a pointer, or to say in the pull request why both stay."""
    for rel, other, length, start in repeated_runs(base, files, minimum):
        warnings.append(f"WARNING core/{rel} and core/{other} share {length} words in a row (\"{start} …\") — "
                        "state the rule in one place and point to it from the other")


# The words each role reads on every launch (#249): its charter and the files of its *Read first* list.
PARAGRAPH_BREAK = re.compile(r"\n[ \t]*+\n")
READ_FIRST = "Read first:"
READ_ITEM = re.compile(r"(?:the\s+((?:\*[^*]+\*[\s,]*(?:and\s+|or\s+)?)+)sections?\s+of\s+)?`([^`\s]+\.md)`"
                       r"(?:\s*\(([^()]*)\))?")
ITALIC = re.compile(r"\*([^*]+)\*")
HEADING_LINE = re.compile(r"^(#+) (.+)$")
SKILL_LINK = re.compile(r"\]\((?:\.\./)+(\.squad/[\w./-]+\.md)\)")
# The orchestrator of each squad skill reads that skill, the skills it follows and the rule files they link.
ORCHESTRATOR_SKILLS = {"squad-issue": [], "squad-spec": ["squad-issue"]}


def section_text(text, name):
    """The section whose heading starts with `name`, to the next heading of the same or a higher level; None when
    there is none."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HEADING_LINE.match(line)
        if not match or not match.group(2).startswith(name):
            continue
        level = len(match.group(1))
        end = next((later for later in range(index + 1, len(lines))
                    if (found := HEADING_LINE.match(lines[later])) and len(found.group(1)) <= level), len(lines))
        return "\n".join(lines[index:end])
    return None


def read_words(text, names):
    """Words of the named sections of `text` (all of it without names, or when none of them is found)."""
    parts = [part for part in (section_text(text, name) for name in names) if part is not None]
    return len(("\n".join(parts) if parts else text).split())


def read_first_sources(rel):
    """(template text or None, [seed texts]) of a file a charter names: the core file, or the seeds a target starts
    with (one per profile for a profile's seed)."""
    if os.path.isfile(os.path.join(CORE, rel)):
        return read(os.path.join(CORE, rel)), []
    seeds = [os.path.join(ROOT, "seed", rel)] + sorted(glob.glob(os.path.join(ROOT, "profiles", "*", "seed", rel)))
    return None, [read(path) for path in seeds if os.path.isfile(path)]


def read_first(charter_text):
    """[(file, section names)] of a charter's *Read first* paragraph."""
    found = [part for part in PARAGRAPH_BREAK.split(charter_text) if part.lstrip().startswith(READ_FIRST)]
    if not found:
        return []
    items = []
    for before, rel, after in READ_ITEM.findall(found[0].lstrip()[len(READ_FIRST):]):
        names = ITALIC.findall(before or "") + ITALIC.findall(after or "")
        items.append((rel, [" ".join(name.split()) for name in names]))
    return items


def launch_words(name, text, items):
    """(template words, seeded minimum, seeded maximum, parts) a launch reads: `text` (the charter or skill) and the
    listed files."""
    template, low, high, parts = len(text.split()), 0, 0, [f"{name} {len(text.split()):,}"]
    for rel, names in items:
        core_text, seeds = read_first_sources(rel)
        label = rel + (f" ({', '.join(names)})" if names else "")
        if core_text is not None:
            words = read_words(core_text, names)
            template += words
            parts.append(f"{label} {words:,}")
        elif seeds:
            counts = [read_words(seed, names) for seed in seeds]
            low, high = low + min(counts), high + max(counts)
            parts.append(f"{label} {min(counts):,}" + (f"–{max(counts):,}" if max(counts) != min(counts) else ""))
    return template, low, high, parts


def words_per_launch():
    """INFO lines with the words each role reads on every launch, and the orchestrator per squad skill."""
    lines = ["INFO words read per launch (the charter and its Read first files; template text, then the seeded "
             "files a target starts with, which its own text replaces):"]
    entries = []
    for path in sorted(glob.glob(os.path.join(CORE, CLAUDE_DIR, "agents", "squad-*.md"))):
        text = read(path)
        entries.append((os.path.basename(path)[:-3], launch_words(os.path.basename(path), text, read_first(text))))
    for skill, followed in ORCHESTRATOR_SKILLS.items():
        paths = [os.path.join(SKILLS, name, SKILL_MD) for name in followed]
        if not os.path.isfile(os.path.join(CORE, SKILLS, skill, SKILL_MD)):
            continue
        text = read(os.path.join(CORE, SKILLS, skill, SKILL_MD))
        links = SKILL_LINK.findall(text + "".join(read(os.path.join(CORE, rel)) for rel in paths))
        items = [(rel, []) for rel in dict.fromkeys(paths + links)]
        entries.append((f"orchestrator ({skill})", launch_words(f"{skill}/{SKILL_MD}", text, items)))
    for name, (template, low, high, parts) in entries:
        seeded = ""
        if high:
            seeded = f" + {low:,}" + (f"–{high:,}" if high != low else "") + " seeded"
        lines.append(f"INFO   {name}: {template:,} template{seeded} — {'; '.join(parts)}")
    return lines


CONSUMER_REPOSITORY = re.compile(r"[\w.-]+/[\w.-]+")
CONSUMER_STATUS = ("active", "legacy")


def check_consumer(entry, profiles, seen, errors):
    """Findings of one entry of consumers.json."""
    if not isinstance(entry, dict) or not CONSUMER_REPOSITORY.fullmatch(str(entry.get("repository", ""))):
        errors.append(f"consumers.json: an entry without a valid 'repository' (owner/name): {entry!r}")
        return
    name = entry["repository"]
    if name in seen:
        errors.append(f"consumers.json: {name} is listed twice")
    seen.add(name)
    listed = entry.get("profiles")
    if not isinstance(listed, list) or not listed or set(listed) - set(profiles):
        errors.append(f"consumers.json: {name} needs 'profiles', a list of {', '.join(profiles)}")
    if entry.get("sonar") is not None and not re.fullmatch(r"[\w.:-]+", str(entry.get("sonar"))):
        errors.append(f"consumers.json: {name} has an invalid 'sonar' project key")
    if entry.get("status") not in CONSUMER_STATUS:
        errors.append(f"consumers.json: {name} needs 'status' {' or '.join(CONSUMER_STATUS)}")


def check_consumers(errors, profiles, path=None):
    """consumers.json lists the repositories that use the template: repository, profiles, Sonar key and status."""
    path = path or os.path.join(ROOT, "consumers.json")
    try:
        data = json.loads(read(path))
    except (OSError, ValueError) as error:
        errors.append(f"consumers.json: {error}")
        return
    entries = data.get("consumers") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        errors.append("consumers.json: no 'consumers' list")
        return
    seen = set()
    for entry in entries:
        check_consumer(entry, profiles, seen, errors)


# A change under these paths reaches the targets and needs a line in CHANGELOG.md (AGENTS.md, Releases).
CHANGELOG_PATHS = ("core/", "profiles/", "multi/", "seed/", "decision-seeds/", "tools/apply-template.py")


def load_tool(path, name):
    """A Python file of the repository as a module."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_lesson_labels(errors):
    """`lesson-label.py` names every file `apply-template.py` manages (one profile and all together) as managed, the
    marked and generated files as marked, no seed as managed, no tool the template does not ship, and the template's
    skills as they are in core/."""
    labels = load_tool(os.path.join("core", SQUAD_DIR, "tools", "lesson-label.py"), "lesson_label")
    applier = load_tool(os.path.join("tools", "apply-template.py"), "apply_template")
    profile_dirs = [os.path.join(ROOT, "profiles", name) for name in applier.PROFILES]
    sets = [[path] for path in profile_dirs] + [profile_dirs]
    managed, seeds = set(), set()
    for dirs in sets:
        names = [os.path.basename(path) for path in dirs]
        managed |= set(applier.managed_files(dirs, names)[1])
        seeds |= {applier.RENAMES.get(rel, rel) for rel in applier.seed_files(dirs, names, [])}
    wrong = sorted(rel for rel in managed if labels.kind(rel) != "managed")
    wrong += sorted(rel for rel in [*applier.MARKED, *applier.GENERATED] if labels.kind(rel) != "marked")
    wrong += sorted(rel for rel in seeds if labels.kind(rel) == "managed")
    shipped = {rel.rsplit("/", 1)[1] for rel in managed if rel.startswith(".squad/tools/")}
    wrong += sorted(f".squad/tools/{tool}" for tool in labels.TOOLS if "*" not in tool and tool not in shipped)
    if wrong:
        errors.append("lesson-label.py (MANAGED, MARKED, TOOLS) disagrees with apply-template.py on: " + ", ".join(wrong))
    skills = sorted(os.listdir(os.path.join(CORE, CLAUDE_DIR, "skills")))
    if sorted(labels.SKILLS) != skills:
        errors.append(f"lesson-label.py SKILLS {sorted(labels.SKILLS)} is not the template's skills {skills}")


def load_release():
    """tools/release.py as a module."""
    spec = importlib.util.spec_from_file_location("release", os.path.join(ROOT, "tools", "release.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def changed_since_base(root):
    """(merge base with origin/main, the paths changed since it, untracked files included), or (None, []) without
    one."""
    def git(*args):
        return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=False)
    base = git("merge-base", ORIGIN_MAIN, "HEAD")
    if base.returncode != 0:
        return None, []
    sha = base.stdout.strip()
    paths = git("diff", "--name-only", sha).stdout.split() + git("ls-files", "--others", "--exclude-standard").stdout.split()
    return sha, paths


def check_changelog(errors, info, root=ROOT):
    """CHANGELOG.md has the format tools/release.py expects, and a branch that changes what the targets receive adds
    a line under its `## Unreleased`."""
    release = load_release()
    path = os.path.join(root, release.CHANGELOG)
    if not os.path.isfile(path):
        errors.append(f"{release.CHANGELOG} is missing (AGENTS.md, Releases)")
        return
    text = read(path)
    errors += release.check(text)
    base, paths = changed_since_base(root)
    if base is None:
        info.append(f"INFO {release.CHANGELOG}: no merge base with origin/main here, so the entry of this change is not "
                    "checked")
        return
    reaching = sorted(name for name in paths if name.startswith(CHANGELOG_PATHS))
    shown = subprocess.run(["git", "-C", root, "show", f"{base}:{release.CHANGELOG}"], capture_output=True, text=True,
                           check=False)
    before = set(release.unreleased_entries(shown.stdout if shown.returncode == 0 else ""))
    if reaching and not set(release.unreleased_entries(text)) - before:
        errors.append(f"{release.CHANGELOG}: this branch changes what the targets receive ({', '.join(reaching[:3])}"
                      f"{', …' if len(reaching) > 3 else ''}) but adds no line under '{release.UNRELEASED}' (AGENTS.md, "
                      "Releases)")


def distributed_python_files():
    """Every Python file a target receives, by name (a directory walk of complexipy would skip `.squad/`)."""
    return sorted(os.path.join(top, name) for d in DISTRIBUTED_DIRS for top, _, names in os.walk(os.path.join(ROOT, d))
                  for name in names if name.endswith(".py"))


def checked_python_files():
    """The files the SonarQube Cloud rules and the cognitive complexity are checked on: the tools a target receives and
    the template's own tools in `tools/`, which CI's SonarQube job analyses as well."""
    return distributed_python_files() + sorted(glob.glob(os.path.join(ROOT, "tools", "*.py")))


def nested_conditionals(tree):
    """python:S3358: a conditional expression inside another one, unless both sit in a comprehension."""
    found = []

    def visit(node, in_conditional, in_comprehension):
        if isinstance(node, ast.IfExp):
            if in_conditional and not in_comprehension:
                found.append((node.lineno, "python:S3358", "nested conditional expression; extract it into a statement"))
            in_conditional = True
        in_comprehension = in_comprehension or isinstance(node, COMPREHENSIONS)
        for child in ast.iter_child_nodes(node):
            visit(child, in_conditional, in_comprehension)

    visit(tree, False, False)
    return found


def own_returns(function):
    """The return statements of a function, those of nested functions and classes left out."""
    found, pending = [], list(function.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Return):
            found.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            pending.extend(ast.iter_child_nodes(node))
    return found


def invariant_returns(tree):
    """python:S3516: a function with several returns that all return the same literal value."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        values = [ret.value for ret in own_returns(node)]
        if len(values) < 2 or not all(isinstance(value, ast.Constant) for value in values):
            continue
        literals = {repr(value.value) for value in values}
        if len(literals) == 1 and values[0].value is not None:
            found.append((node.lineno, "python:S3516", "the function always returns the same value"))
    return found


def mock_lambdas(tree):
    """python:S9081: a lambda that ignores its arguments, given as the replacement of `patch` or `patch.object`."""
    found = []
    for node in ast.walk(tree):
        name = node.func.attr if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) else None
        position = {"object": 2, "patch": 1}.get(name)
        if position is None or len(node.args) <= position or not isinstance(node.args[position], ast.Lambda):
            continue
        replacement = node.args[position]
        parameters = {arg.arg for arg in ast.walk(replacement.args) if isinstance(arg, ast.arg)}
        used = {child.id for child in ast.walk(replacement.body) if isinstance(child, ast.Name)}
        if not parameters & used:
            found.append((replacement.lineno, "python:S9081", "a lambda that ignores its arguments; use return_value"))
    return found


def is_string(node):
    return isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)))


def counted_children(node):
    """The children of an AST node whose literals Sonar counts: no decorator, annotation or return annotation."""
    for field, value in ast.iter_fields(node):
        if field not in ("decorator_list", "annotation", "returns"):
            yield from value if isinstance(value, list) else [value]


def string_literals(node):
    """The string literals Sonar counts for python:S1192: no docstring (any string statement), decorator or annotation."""
    for child in counted_children(node):
        if not isinstance(child, ast.AST) or (isinstance(child, ast.Expr) and is_string(child.value)):
            continue
        if is_string(child):
            yield child
        else:
            yield from string_literals(child)


def literal_value(node):
    """The value of a literal, or None for an f-string with an interpolation (Sonar leaves those out)."""
    if isinstance(node, ast.Constant):
        return node.value.decode("latin-1") if isinstance(node.value, bytes) else node.value
    if any(not isinstance(part, ast.Constant) for part in node.values):
        return None
    return "".join(part.value for part in node.values)


def literal_tokens(source, node):
    """The literal as Sonar keys it: its tokens with quotes and prefixes, without the whitespace between them."""
    segment = ast.get_source_segment(source, node)
    try:
        return "".join(token.string for token in tokenize.generate_tokens(io.StringIO(segment).readline)
                       if token.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.COMMENT))
    except (tokenize.TokenError, SyntaxError):
        return segment


def duplicated_literals(source, tree):
    """python:S1192: the same string literal (5 characters or more, not a plain word or format) three times or more."""
    occurrences = {}
    for node in string_literals(tree):
        value = literal_value(node)
        if value is None or len(value) < 5 or any(p.fullmatch(value) for p in LITERAL_EXCLUSIONS):
            continue
        occurrences.setdefault(literal_tokens(source, node), []).append(node.lineno)
    return [(lines[0], "python:S1192", f"literal {key} appears {len(lines)} times; define a constant")
            for key, lines in occurrences.items() if len(lines) >= 3]


def escaped_item(pattern, i):
    """The item of the escape at pattern[i]: `\\A` anchors the start like `^`, `\\Z` and `\\z` the end like `$`."""
    escaped = pattern[i + 1:i + 2]
    if escaped == "A":
        return "^"
    return "$" if escaped in "Zz" else "x"


def regex_items(pattern):
    """The disjunctions of a regex, top level and in every group: each a list of alternatives, each alternative its
    items (`^`, `$`, `flags` for a group that only sets flags, `x` for anything else)."""
    disjunctions, stack, i = [], [[[]]], 0
    while i < len(pattern):
        char, item = pattern[i], "x"
        flag_setter = FLAG_SETTER.match(pattern, i)
        if flag_setter:
            item, i = "flags", flag_setter.end() - 1
        elif char == "\\":
            item, i = escaped_item(pattern, i), i + 1
        elif char == "[":
            i = CHAR_CLASS.match(pattern, i).end() - 1
        elif char in "^$":
            item = char
        elif char == "(":
            stack.append([[]])
            i = GROUP_OPENER.match(pattern, i).end()
            continue
        elif char == "|":
            stack[-1].append([])
            i += 1
            continue
        elif char == ")" and len(stack) > 1:
            disjunctions.append(stack.pop())
        stack[-1][-1].append(item)
        i += 1
    return disjunctions + stack


def anchored(alternative, anchor):
    """Whether a sequence of two items or more starts (`^`) or ends (`$`) with the anchor, flag setters left out."""
    items = [item for item in alternative if item != "flags"]
    return len(alternative) > 1 and bool(items) and items[0 if anchor == "^" else -1] == anchor


def regex_item(pattern, i):
    """(kind, its alternatives or None, the index after it) of the regex item at pattern[i]: `class`, `backreference`,
    `lookaround`, `group` or `atom` (a flag setter included)."""
    char = pattern[i]
    flag_setter = FLAG_SETTER.match(pattern, i)
    if flag_setter:
        return "atom", None, flag_setter.end()
    if char == "\\":
        return ("backreference" if BACKREFERENCE.match(pattern, i) else "atom"), None, i + 2
    if char == "[":
        return "class", None, CHAR_CLASS.match(pattern, i).end()
    if char == "(":
        alternatives, end = regex_tree(pattern, GROUP_OPENER.match(pattern, i).end())
        return ("lookaround" if pattern.startswith(LOOKAROUNDS, i) else "group"), alternatives, end + 1
    return "atom", None, i + 1


def regex_tree(pattern, i=0):
    """(alternatives, the index of the closing parenthesis or the end) of the sequence from pattern[i]: each
    alternative a list of (kind, alternatives or None, quantified) items."""
    alternatives = [[]]
    while i < len(pattern) and pattern[i] != ")":
        if pattern[i] == "|":
            alternatives.append([])
            i += 1
            continue
        kind, children, i = regex_item(pattern, i)
        quantifier = QUANTIFIER.match(pattern, i)
        i = quantifier.end() if quantifier else i
        alternatives[-1].append((kind, children, bool(quantifier)))
    return alternatives, i


def regex_complexity(alternatives, nesting=1):
    """python:S5843: the complexity of a parsed regex at the nesting depth (REGEX_COMPLEXITY_LIMIT)."""
    total = 0
    if len(alternatives) > 1:
        total, nesting = nesting + len(alternatives) - 2, nesting + 1
    for kind, children, quantified in itertools.chain.from_iterable(alternatives):
        depth = nesting + quantified
        total += (nesting if quantified else 0) + {"class": 1, "backreference": 1, "lookaround": depth}.get(kind, 0)
        if children is not None:
            total += regex_complexity(children, depth + (kind == "lookaround"))
    return total


def one_literal(source, node):
    """Whether the string constant is written as one literal, not as adjacent literals Python joins."""
    try:
        tokens = tokenize.generate_tokens(io.StringIO(ast.get_source_segment(source, node)).readline)
        return sum(token.type == tokenize.STRING for token in tokens) == 1
    except (tokenize.TokenError, SyntaxError):
        return False


def complex_regexes(source, tree):
    """python:S5843: a regex more complex than REGEX_COMPLEXITY_LIMIT; split it, or leave the rarer forms to code."""
    findings = []
    for node in regex_call_nodes(tree):
        value = node.args[0].value
        complexity = regex_complexity(regex_tree(value.decode("latin-1") if isinstance(value, bytes) else value)[0])
        if complexity > REGEX_COMPLEXITY_LIMIT and one_literal(source, node.args[0]):
            findings.append((node.lineno, "python:S5843", f"regex complexity {complexity}, over {REGEX_COMPLEXITY_LIMIT}"))
    return findings


def regex_call_nodes(tree, functions=REGEX_FUNCTIONS):
    """The `re.<function>(<string or bytes literal>, …)` calls of a module."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "re"
                and node.func.attr in functions and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, (str, bytes))):
            yield node


def regex_calls(tree, functions=REGEX_FUNCTIONS):
    """The `re.<function>(<string or bytes literal>, …)` calls of a module, as (line, pattern); a bytes pattern as
    the text it spells (Sonar checks both)."""
    for node in regex_call_nodes(tree, functions):
        value = node.args[0].value
        yield node.lineno, value.decode("latin-1") if isinstance(value, bytes) else value


def ungrouped_anchors(alternatives):
    """Whether a disjunction anchors only its first (`^`) or last (`$`) alternative."""
    first, last, middle = alternatives[0], alternatives[-1], alternatives[1:-1]
    return len(alternatives) > 1 and (anchored(first, "^") or anchored(last, "$")) \
        and not (anchored(first, "$") or anchored(last, "^")
                 or any(anchored(a, "^") or anchored(a, "$") for a in middle))


def anchor_precedence(tree):
    """python:S5850: `^a|b$` anchors only the first and the last alternative; group them to make that explicit."""
    return [(line, "python:S5850", "anchored alternatives without a group")
            for line, pattern in regex_calls(tree) for alternatives in regex_items(pattern)
            if ungrouped_anchors(alternatives)]


def zero_width(rest):
    """Whether the rest of a regex matches no character: nothing but group ends and anchors, then at most a lookaround
    that runs to the end."""
    rest = rest[ZERO_WIDTH_PREFIX.match(rest).end():]
    return not rest or (rest.startswith(LOOKAROUNDS) and rest.endswith(")"))


def lazy_quantifiers(tree):
    """python:S6019: a reluctant quantifier followed by nothing that has to match a character (`.*?(?=^## |\\Z)`)
    only ever matches its minimum; write the end it should stop at as a character it consumes, or split the text."""
    return [(line, "python:S6019", "reluctant quantifier followed only by zero-width assertions")
            for line, pattern in regex_calls(tree)
            for found in LAZY_QUANTIFIER.finditer(CHAR_CLASS.sub("x", pattern))
            if zero_width(CHAR_CLASS.sub("x", pattern)[found.end():])]


def suppression_comments(source):
    """python:S7632: `# noqa: BLE001  (missing, or broken)`: Sonar reads a comma after the rule keys as the start of
    another key, so the explanation goes on a comment line of its own."""
    comments = (token for token in tokenize.generate_tokens(io.StringIO(source).readline)
                if token.type == tokenize.COMMENT)
    return [(token.start[0], "python:S7632", "comma in the explanation of a noqa comment")
            for token in comments for found in [NOQA.search(token.string)] if found and "," in found.group("rest")]


def compiled_patterns(tree):
    """The `NAME = re.compile(<string literal>, …)` assignments of a module, as {name: (line, pattern)}."""
    return {node.targets[0].id: (node.lineno, node.value.args[0].value) for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == "re"
            and node.value.func.attr == "compile" and node.value.args and isinstance(node.value.args[0], ast.Constant)
            and isinstance(node.value.args[0].value, str)}


def regex_uses(tree):
    """The regexes of a module that are matched partially, as (line, pattern, whether a fullmatch anchors the end)."""
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            methods.setdefault(node.value.id, set()).add(node.attr)
    uses = [(line, pattern, False) for line, pattern in regex_calls(tree, PARTIAL_FUNCTIONS)]
    for name, (line, pattern) in compiled_patterns(tree).items():
        used = methods.get(name, set())
        if used - {"fullmatch"}:
            uses.append((line, pattern, "fullmatch" in used))
    return uses


def after_leading_repetition(items):
    """The items after the unbounded repetition a regex starts with (lookarounds before it skipped, a group around it
    opened), or None when it starts with anything else, an anchor included."""
    items = list(items)
    while items and items[0][0] in LOOKAROUND_OPS:
        items.pop(0)
    if not items:
        return None
    op, value = items[0]
    if op is sre_constants.SUBPATTERN:
        inner = after_leading_repetition(value[-1].data)
        return None if inner is None else inner + items[1:]
    return items[1:] if op in REPEATS and value[1] == sre_constants.MAXREPEAT else None


def super_linear(pattern, end_anchored):
    """Whether an unanchored regex starts with an unbounded repetition and goes on with something that can fail (a
    character, an end anchor): every start position retries the repetition (`\\d+x`, `[^,]+,`, `\\s+$`)."""
    try:
        parsed = sre_parser.parse(pattern)
    except re.error:
        return False
    rest = after_leading_repetition(parsed.data)
    if rest is None:
        return False
    return end_anchored or any(op is sre_constants.AT and value in END_ANCHORS for op, value in rest) \
        or sre_parser.SubPattern(parsed.state, rest).getwidth()[0] > 0


def super_linear_regexes(tree):
    """python:S8786: a regex that backtracks super-linearly. Sonar reports it with possessive quantifiers and atomic
    groups too: start with a single character (`\\d[\\d_.]*`), anchor it, or check the match in code."""
    return [(line, SUPER_LINEAR, "unanchored regex that starts with an unbounded repetition followed by more")
            for line, pattern, end_anchored in regex_uses(tree) if super_linear(pattern, end_anchored)]


def member_test(op, value):
    """Whether a character is one a single-character regex item matches (a literal, a range, `\\d`, `.`), or None."""
    tests = {sre_constants.LITERAL: lambda char: ord(char) == value,
             sre_constants.NOT_LITERAL: lambda char: ord(char) != value,
             sre_constants.RANGE: lambda char: value[0] <= ord(char) <= value[1],
             sre_constants.ANY: lambda char: char != "\n"}
    if op is sre_constants.CATEGORY:
        return CATEGORIES[value].fullmatch if value in CATEGORIES else None
    return tests.get(op)


def matched_chars(test, ignore_case):
    """The characters of SAMPLE a test accepts, with their other case under IGNORECASE."""
    def accepts(char):
        variants = (char, char.lower(), char.upper()) if ignore_case else (char,)
        return any(len(variant) == 1 and test(variant) for variant in variants)
    return frozenset(char for char in SAMPLE if accepts(char))


def item_chars(op, value, ignore_case):
    """The characters a single-character item matches (a class negated included), or None for any other item."""
    if op is not sre_constants.IN:
        test = member_test(op, value)
        return None if test is None else matched_chars(test, ignore_case)
    tests = [member_test(member, item) for member, item in value if member is not sre_constants.NEGATE]
    if None in tests:
        return None
    inside = matched_chars(lambda char: any(test(char) for test in tests), ignore_case)
    negated = any(member is sre_constants.NEGATE for member, _ in value)
    return frozenset(SAMPLE) - inside if negated else inside


def duplicated_member(members, ignore_case):
    """python:S5869: whether two members of a character class match a common character (`[\\w_]`, `[a-zA-Z]` under
    IGNORECASE); a literal named twice (`[aab]`) is folded by Python's parser before this sees it."""
    seen = frozenset()
    for op, value in members:
        test = member_test(op, value) if op is not sre_constants.NEGATE else None
        found = matched_chars(test, ignore_case) if test else frozenset()
        if seen & found:
            return True
        seen |= found
    return False


def nested_bodies(value):
    """The item lists an item's value holds: a group's or a repetition's body, the alternatives of a branch."""
    for part in value if isinstance(value, (list, tuple)) else (value,):
        for sub in part if isinstance(part, list) else [part]:
            if isinstance(sub, sre_parser.SubPattern):
                yield sub.data


def sub_patterns(items):
    """Every nested item list of a parsed regex: the bodies of groups, repetitions, lookarounds and alternatives."""
    for _, value in items:
        for body in nested_bodies(value):
            yield body
            yield from sub_patterns(body)


def flattened(items):
    """The items of a sequence with the groups that take no quantifier opened, atomic ones too, as Sonar reads them."""
    for op, value in items:
        if op is sre_constants.SUBPATTERN:
            yield from flattened(value[-1].data)
        elif op is getattr(sre_constants, "ATOMIC_GROUP", None):
            yield from flattened(value.data)
        else:
            yield op, value


def repeated_chars(item, ignore_case, possessive=True):
    """The characters an unbounded repetition of a single-character item matches, or None (also for a possessive one
    unless `possessive`)."""
    op, value = item
    allowed = REPEATS if possessive else {sre_constants.MAX_REPEAT, sre_constants.MIN_REPEAT}
    if op not in allowed or value[1] != sre_constants.MAXREPEAT or len(value[2].data) != 1:
        return None
    return item_chars(*value[2].data[0], ignore_case)


def can_fail(state, rest):
    """Whether what follows can fail: something of a width above zero, or an end anchor."""
    return any(op is sre_constants.AT and value in END_ANCHORS for op, value in rest) \
        or sre_parser.SubPattern(state, list(rest)).getwidth()[0] > 0


def overlapping_repetitions(state, items, ignore_case):
    """Whether two unbounded repetitions follow each other, can match a common character and are followed by something
    that can fail: python:S8786 reports `\\d+\\S* x`, `[a-z]+\\w*y`, `\\d*?\\d+y` and `(?>\\d+)\\S*y`, not `[a-z]+\\d+y`,
    `\\w+ \\w+y` or a possessive first repetition (`\\d++\\S*y`)."""
    sequence = list(flattened(items))
    for i in range(len(sequence) - 1):
        first = repeated_chars(sequence[i], ignore_case, possessive=False)
        second = repeated_chars(sequence[i + 1], ignore_case)
        if first and second and first & second and can_fail(state, sequence[i + 2:]):
            return True
    return False


def ignores_case(node):
    """Whether a regex call passes re.I or re.IGNORECASE among its flags."""
    return any(isinstance(part, ast.Attribute) and part.attr in ("I", "IGNORECASE")
               for argument in node.args[1:] + [keyword.value for keyword in node.keywords]
               for part in ast.walk(argument))


def parsed_regexes(tree):
    """(line, parsed regex, whether it ignores case) of every `re.<function>(<literal>, …)` call of a module."""
    for node in regex_call_nodes(tree):
        value = node.args[0].value
        try:
            parsed = sre_parser.parse(value.decode("latin-1") if isinstance(value, bytes) else value,
                                      re.IGNORECASE if ignores_case(node) else 0)
        except re.error:
            continue
        yield node.lineno, parsed, bool(parsed.state.flags & re.IGNORECASE)


def overlap_findings(tree, test_file=False):
    """python:S5869 (a character class that names a character twice) and python:S8786 (two adjacent unbounded
    repetitions that share a character and something after them that can fail: `\\d+\\S* x`), which Sonar does not
    report in a test file."""
    findings = []
    for line, parsed, ignore_case in parsed_regexes(tree):
        bodies = [parsed.data, *sub_patterns(parsed.data)]
        classes = [value for body in bodies for op, value in body if op is sre_constants.IN]
        if any(duplicated_member(members, ignore_case) for members in classes):
            findings.append((line, "python:S5869", "a character class that names a character twice"))
        if not test_file and any(overlapping_repetitions(parsed.state, body, ignore_case) for body in bodies):
            findings.append((line, SUPER_LINEAR, "two adjacent unbounded repetitions that can match the same character"))
    return findings


def needless_groups(pattern):
    """The non-capturing groups of a regex (flag groups too) that hold no alternation and take no quantifier, outside
    character classes: python:S6395 asks to unwrap them."""
    found, i = [], 0
    while i < len(pattern):
        opener = NON_CAPTURING.match(pattern, i)
        if pattern[i] == "\\":
            i += 2
            continue
        if pattern[i] == "[":
            i = CHAR_CLASS.match(pattern, i).end()
            continue
        if opener:
            alternatives, end = regex_tree(pattern, opener.end())
            if len(alternatives) == 1 and not QUANTIFIER.match(pattern, end + 1):
                found.append(pattern[i:end + 1])
        i += 1
    return found


def unwrapped_groups(tree):
    """python:S6395: a non-capturing group without alternation or quantifier; a flag group of one alternative is
    flagged too, so its flag goes to the whole regex or a regex of its own."""
    return [(line, "python:S6395", f"unnecessary non-capturing group {group}")
            for line, pattern in regex_calls(tree) for group in needless_groups(pattern)]


def multiple_spaces(tree):
    """python:S6326: two spaces or more in a regex outside a character class; a quantifier (`{2}`) says how many."""
    return [(line, "python:S6326", "several spaces in a regex; use a quantifier")
            for line, pattern in regex_calls(tree) if MULTIPLE_SPACES.search(CHAR_CLASS.sub("", pattern))]


def is_call_of(node, name):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name


def needs_specific_assertion(name, args):
    """Whether a unittest assertion with these arguments has a more specific one (python:S5906)."""
    first = args[0]
    if name in TRUTH_ASSERTS:
        compared = isinstance(first, ast.Compare) and len(first.ops) == 1 and isinstance(first.ops[0], TRUTH_ASSERTS[name])
        return compared or is_call_of(first, "isinstance")
    constant = any(isinstance(arg, ast.Constant) and (arg.value is None or isinstance(arg.value, bool))
                   for arg in args[:2])
    return name in VALUE_ASSERTS and (constant or (len(args) > 1 and is_call_of(args[1], "round")))


def specific_assertions(tree):
    """python:S5906: `assertTrue(x == y)`, `assertEqual(x, None)`, `assertEqual(x, False)` and the like; the dedicated
    assertion says more."""
    return [(node.lineno, "python:S5906", f"{node.func.attr} here has a more specific unittest assertion")
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args
            and needs_specific_assertion(node.func.attr, node.args)]


def inverted_comparisons(tree):
    """python:S1940: `not a <= b` and the like: the opposite operator says it without the inversion."""
    return [(node.lineno, "python:S1940", "a `not` of a comparison: use the opposite operator (or, for sets, another form)")
            for node in ast.walk(tree)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Compare)
            and len(node.operand.ops) == 1 and isinstance(node.operand.ops[0], INVERTED_COMPARISONS)]


def assigned_globals(tree):
    """The names a module binds by an assignment at its top level: a module it loads (`tool = …`), a constant."""
    return {target.id for node in tree.body if isinstance(node, ast.Assign) for target in node.targets
            if isinstance(target, ast.Name)}


def local_names(function):
    """The parameters of a function and the names it assigns."""
    assigned = {target.id for node in ast.walk(function) if isinstance(node, ast.Assign) for target in node.targets
                if isinstance(target, ast.Name)}
    return assigned | {arg.arg for arg in function.args.args}


def assigned_attributes(function):
    """(line, target) of every assignment in a function whose target is an attribute of a name (`tool.run = …`)."""
    for node in ast.walk(function):
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AugAssign):
            targets = [node.target]
        unpacked = [element for target in targets for element in (target.elts if isinstance(target, ast.Tuple) else [target])]
        yield from ((node.lineno, target) for target in unpacked
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name))


def patched_globals(tree):
    """python:S8997: a test that assigns an attribute of a module the test file loads at its top level
    (`tool.run = fake`) changes global state and must restore it by hand; `mock.patch.object` does both. Sonar leaves
    an imported module (`sys.stdin = …`), a module loaded inside the test, `self` and a helper that is no test
    (`test_…`) alone, and so does this check."""
    names = assigned_globals(tree)
    found = []
    for function in (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.name.startswith("test")):
        shared = names - local_names(function)
        found += [(line, "python:S8997", f"{target.value.id}.{target.attr} assigned in a test: use mock.patch.object")
                  for line, target in assigned_attributes(function) if target.value.id in shared]
    return found


def augmented_parameters(tree):
    """python:S1481: a parameter whose only use in its function is the target of an augmented assignment (`errors +=
    found`, never `errors.append` or another read): Sonar reports it as an unused local variable."""
    found = []
    for function in (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))):
        parameters = {arg.arg for arg in function.args.args + function.args.posonlyargs + function.args.kwonlyargs}
        read = {node.id for node in ast.walk(function) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
        found += [(node.lineno, "python:S1481", f"parameter `{node.target.id}` is only augmented, never read: use "
                   "extend() or another call on it") for node in ast.walk(function)
                  if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                  and node.target.id in parameters - read]
    return found


def sonar_findings(path, source):
    """The findings of the SonarQube Cloud rules a refresh has tripped before, as (line, rule, message)."""
    tree = ast.parse(source, path)
    findings = nested_conditionals(tree) + anchor_precedence(tree) + multiple_spaces(tree) + invariant_returns(tree) \
        + mock_lambdas(tree) + specific_assertions(tree) + lazy_quantifiers(tree) + suppression_comments(source) \
        + super_linear_regexes(tree) + complex_regexes(source, tree) + unwrapped_groups(tree) \
        + inverted_comparisons(tree) + augmented_parameters(tree) \
        + overlap_findings(tree, os.path.basename(path).startswith("test"))
    if not os.path.basename(path).startswith("test"):  # Sonar skips S1192 in test files
        findings += duplicated_literals(source, tree)
    else:
        findings += patched_globals(tree)
    return sorted(findings)


def check_sonar_rules(errors, paths=None):
    """The Python tools (a target's and the template's own) trip none of the SonarQube Cloud rules that have flagged them
    (`SONAR_RULES`): every finding there keeps the refresh PR in draft and costs a template PR and another refresh."""
    for path in checked_python_files() if paths is None else paths:
        for line, rule, message in sonar_findings(path, read(path)):
            errors.append(f"{os.path.relpath(path, ROOT)}:{line}: {rule} {message}")


def sonar_sources(path):
    """The source directories `sonar.sources` lists in a properties file (continuation lines joined)."""
    text = re.sub(r"\\\n\s*", "", read(path)) if os.path.isfile(path) else ""
    found = re.search(r"^sonar\.sources=(.*)$", text, re.M)
    return [entry.strip().rstrip("/") for entry in found.group(1).split(",") if entry.strip()] if found else []


def sonar_analyses(relpath, sources):
    """Whether SonarQube Cloud analyses the file: it lies below a source directory with no hidden directory in
    between, which the scanner would skip."""
    return any(relpath.startswith(source + "/")
               and not any(part.startswith(".") for part in relpath[len(source) + 1:].split("/")[:-1])
               for source in sources)


def check_sonar_sources(errors):
    """CI's SonarQube Cloud analysis (`sonar-project.properties`) covers every Python file a target receives and the
    template's own tools, so a finding shows here before a refresh brings it into a target's analysis."""
    sources = sonar_sources(os.path.join(ROOT, "sonar-project.properties"))
    for path in checked_python_files():
        relpath = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if not os.path.basename(path).startswith("test_") and not sonar_analyses(relpath, sources):
            errors.append(f"{relpath}: not analysed by SonarQube Cloud; add its directory to sonar.sources in "
                          "sonar-project.properties (the scanner skips hidden directories below a source directory)")


CI_WORKFLOW = os.path.join(ROOT, ".github", "workflows", "python-ci.yml")
COMPLEXIPY_PIN = re.compile(r"\bcomplexipy==([\w.]+)")


def version_note(warnings):
    """A warning when the installed complexipy is not the version CI pins: versions count differently (8.0.1 counted
    a comprehension's `if` and a conditional expression with nesting, 9.0.0 counts as SonarQube does)."""
    with open(CI_WORKFLOW, encoding="utf-8") as handle:
        pinned = COMPLEXIPY_PIN.search(handle.read())
    done = subprocess.run(["complexipy", "--version"], capture_output=True, text=True, check=False)
    installed = done.stdout.split()[-1] if done.stdout.split() else "unknown"
    if pinned and installed != pinned.group(1):
        warnings.append(f"WARNING complexipy {installed} is installed, CI pins {pinned.group(1)} "
                        f"(pip install complexipy=={pinned.group(1)}): the cognitive-complexity counts can differ")


def check_complexity(errors, warnings):
    """The Python tools (a target's and the template's own) stay below SonarQube Cloud's cognitive-complexity limit
    (python:S3776, 15): every refresh puts them under the target's code analysis, so a finding there would cost a template PR
    and a refresh of every target. complexipy measures the same cognitive complexity; CI installs it."""
    if not shutil.which("complexipy"):
        print("NOTE: complexipy is not installed (pip install complexipy); cognitive complexity not checked here, "
              "CI checks it")
        return
    version_note(warnings)
    paths = checked_python_files()
    with tempfile.TemporaryDirectory() as cache:
        result = subprocess.run(["complexipy", *paths, "--max-complexity-allowed", str(COGNITIVE_LIMIT), "--failed",
                                 "--plain", "--cache-dir", cache], capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        if line.strip():
            errors.append(f"cognitive complexity above {COGNITIVE_LIMIT} (python:S3776): {line.strip()}")
    if result.returncode != 0 and not result.stdout.strip():
        errors.append(f"complexipy failed: {result.stderr.strip()}")


def main():
    errors = []
    warnings = []
    check_agents_and_skills(ROOT, errors)
    check_agents_and_skills(CORE, errors)
    check_core(errors)
    check_control_characters(errors)
    check_placeholders(errors)
    info = []
    check_rule_files(errors)
    check_rule_changes(warnings, info)
    check_repeated_rules(warnings)
    info += words_per_launch()
    profiles = check_profiles(errors)
    check_seed_workflows(errors)
    check_consumers(errors, profiles)
    check_changelog(errors, info)
    check_lesson_labels(errors)
    smoke_test(profiles, errors)
    check_decision_tool(errors)
    check_area_checks(errors)
    check_area_assignments(errors)
    check_sonar_seed(profiles, errors)
    check_sonar_rules(errors)
    check_sonar_sources(errors)
    check_complexity(errors, warnings)
    for line in info + warnings + errors:
        print(line)
    print(f"\nChecked core and {len(profiles)} profiles ({', '.join(profiles)}): {'PASS' if not errors else 'FAIL'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
