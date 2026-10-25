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
  instruction files use, its `stack.md` defines every command name the core refers to, and its
  `squad_settings.py` defines the coverage settings;
- a smoke test: each profile is applied to an empty git repository with `tools/apply-template.py`, and the
  target's `config-check.py` then reports nothing but unfilled placeholders; after every placeholder is
  filled and the template is applied a second time (a refresh), `config-check.py` passes completely, the
  files the template no longer manages (`RETIRED` in `apply-template.py`) are gone and a line that still refers
  to one is reported; a `CLAUDE.md` that still holds the rules (the layout before `AGENTS.md` held them) has its
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
  group, several spaces in a regex);
- every squad rule file in `WORD_BUDGETS` (the squad's rules, skills and agents, the template parts of
  `AGENTS.md` and `docs/ARCHITECTURE.md` with their empty blocks, the work-folder templates) stays within its word
  budget, counted like `wc -w` in a UTF-8 locale (whitespace-separated words); a file over it is a warning, as is a run of
  20 words that two of them share (a rule in two places). Every
  member reads these files on every launch, so size is watched, but a rule is not cut to fit; the
  evidence behind a rule goes into `docs/squad-rationale.md`, which no target receives.

Exit code 0 when everything passes, 1 otherwise. Requires PyYAML.
"""
import ast
import glob
import importlib.util
import io
import itertools
import json
import os
import re
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
# Values the decision-check tests repeat.
STORAGE_MD = "storage.md"
STORAGE_AREA = "[Storage](storage.md)"
SUPERSEDED = "Superseded by 0003"
UNRELEASED_EDIT = "Changed before any release."
SKILLS = os.path.join(CLAUDE_DIR, "skills")
RULES = "AGENTS.md"
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
COMMANDS = ["*Restore*", "*Format*", "*Format check*", "*Build*", "*Test*", "*Single test*",
            "*Test with coverage*", "*Coverage gate*", "*Analyzer gate*", "*Sonar gate*", "*Image build check*"]
STACK_SECTIONS = ["## Toolchain", "## Layout", "## Commands", "## Analyzer gate", "## Image build check",
                  "## Coverage exclusions", "## Writing code", "## Writing tests", "## Skeleton", "## Dependencies",
                  "## Concurrency", "## Known pitfalls"]
MULTI_FILES = [".squad/tools/analyzer-check.py", ".claude/hooks/session-start.sh"]
SETTINGS = ["COVERAGE_FORMAT", "COVERAGE_REPORT_GLOB", "COVERAGE_PATHSPECS", "COVERAGE_EXCLUDES"]
DISTRIBUTED_DIRS = ["core", "profiles", "multi", "seed"]
COGNITIVE_LIMIT = 15
# SonarQube Cloud rules a refresh has tripped, checked on every distributed Python file and on `tools/` (see
# check_sonar_rules); python:S3776 is checked with complexipy (check_complexity).
SONAR_RULES = ["python:S1192", "python:S3358", "python:S5850", "python:S6326"]
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
LITERAL_EXCLUSIONS = [re.compile(p) for p in (r"[_\-a-zA-Z0-9]+", r"[0-9{} .\-_%:dfrsymhYMHS<>]+", r"#[0-9a-fA-F]{6}")]
REGEX_FUNCTIONS = {"compile", "search", "match", "fullmatch", "split", "findall", "finditer", "sub", "subn"}
FLAG_SETTER = re.compile(r"\(\?[aiLmsux-]+\)")
MULTIPLE_SPACES = re.compile(r" {2,}")
CHAR_CLASS = re.compile(r"\[\^?\]?(?:\\.|[^\]\\])*\]?", re.S)
# Word ceilings of the squad's rule files under core/ (paths relative to core/).
WORD_BUDGETS = {
    ".squad/routing.md": 6500,
    ".squad/team.md": 1230,
    ".claude/skills/squad-issue/SKILL.md": 2690,
    ".claude/skills/squad-spec/SKILL.md": 970,
    ".claude/skills/create-pr/SKILL.md": 1390,
    ".claude/skills/review-pr/SKILL.md": 840,
    ".claude/agents/squad-code-officer.md": 600,
    ".claude/agents/squad-dev.md": 870,
    ".claude/agents/squad-devils-advocate.md": 820,
    ".claude/agents/squad-lead.md": 2360,
    ".claude/agents/squad-reviewer.md": 2140,
    ".claude/agents/squad-security.md": 700,
    ".claude/agents/squad-tester.md": 1170,
    "AGENTS.md": 1550,
    "docs/ARCHITECTURE.md": 350,
    "specs/_template/log.md": 60,
    "specs/_template/plan.md": 960,
    "specs/_template/spec.md": 480,
    "specs/_template/tasks.md": 110,
}
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


CORE_HOOKS = [os.path.join(CLAUDE_DIR, "hooks", "git-guard.py"), os.path.join(CLAUDE_DIR, "hooks", "install-linters.sh")]


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
    sys.modules.setdefault("squad_settings", types.SimpleNamespace(BASE_REF="origin/main"))
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
        plant_legacy_rules(target)
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


def check_refresh(label, target, refresh, errors):
    """The refresh removed the retired files, reported the reference to one of them, and config-check passes."""
    for rel in RETIRED_SAMPLE:
        if os.path.exists(os.path.join(target, rel)):
            errors.append(f"profile {label}: refresh kept the retired file {rel}")
    if f"{STALE_REFERENCE}:1: " not in refresh.stdout or "References to removed files" not in refresh.stdout:
        errors.append(f"profile {label}: refresh does not report the reference to a retired file in "
                      f"{STALE_REFERENCE}")
    if HISTORICAL_REFERENCE in refresh.stdout:
        errors.append(f"profile {label}: refresh lists the decision record {HISTORICAL_REFERENCE}")
    os.remove(os.path.join(target, HISTORICAL_REFERENCE))
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
    for path in glob.glob(os.path.join(target, GITHUB_DIR, "**", "*.yml"), recursive=True):
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
    checks = {"codeql.yml": check_merged_codeql, DEPENDABOT_YML: check_merged_dependabot, "ci.yml": check_merged_ci}
    check = checks.get(os.path.basename(path))
    if check:
        check(label, names, parsed, errors)


def check_merged_codeql(label, names, parsed, errors):
    languages = [entry["language"] for entry in parsed["jobs"]["analyze"]["strategy"]["matrix"]["include"]]
    expected = list(dict.fromkeys(language for n in names
                                  for language in re.findall(r"- language: (\S+)", profile_file(n, "codeql.yml"))))
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


def check_word_budgets(errors, base=CORE, budgets=None, warnings=None):
    """A squad rule file past its budget is a warning, not an error: a rule is never cut to fit, but the PR says
    why the file cannot be shorter (AGENTS.md, *Writing rules*). A budgeted file that is missing is an error."""
    for rel, budget in (WORD_BUDGETS if budgets is None else budgets).items():
        path = os.path.join(base, rel)
        if not os.path.isfile(path):
            errors.append(f"core/{rel}: listed in WORD_BUDGETS but missing")
            continue
        words = word_count(path)
        if words > budget and warnings is not None:
            warnings.append(f"WARNING core/{rel}: {words} words, over its budget of {budget} (WORD_BUDGETS in "
                            "tools/template-check.py) — cut repetition and evidence, keep reasons and examples "
                            "that change how a rule is read; justify the size in the pull request")


REPEAT_MIN_WORDS = 20


def repeated_runs(base=CORE, budgets=None, minimum=REPEAT_MIN_WORDS):
    """(file, other file, words, snippet) for every run of at least `minimum` consecutive words that two squad
    rule files share word for word (case and punctuation aside): a rule stated in two places."""
    texts = {rel: re.findall(r"[\w`./<>*-]+", re.sub(r"\A---\n.*?\n---\n", "", read(os.path.join(base, rel)), flags=re.S).lower())
             for rel in (WORD_BUDGETS if budgets is None else budgets) if os.path.isfile(os.path.join(base, rel))}
    index = {}
    for rel, words in texts.items():
        for i in range(len(words) - minimum + 1):
            index.setdefault(tuple(words[i:i + minimum]), []).append((rel, i))
    found = {}
    for places in index.values():
        for (rel, i), (other, j) in itertools.combinations(places, 2):
            if rel != other:
                found.setdefault((rel, other), set()).add((i, j))
    runs = []
    for (rel, other), starts in sorted(found.items()):
        covered = set()
        for i, j in sorted(starts):
            if (i, j) in covered:
                continue
            length = minimum
            while (i + length - minimum + 1, j + length - minimum + 1) in starts:
                covered.add((i + length - minimum + 1, j + length - minimum + 1))
                length += 1
            runs.append((rel, other, length, " ".join(texts[rel][i:i + 8])))
    return runs


def check_repeated_rules(warnings, base=CORE, budgets=None, minimum=REPEAT_MIN_WORDS):
    """A rule lives in exactly one place (AGENTS.md): two squad rule files sharing a long run of words is a
    warning to replace one copy by a pointer, or to say in the pull request why both stay."""
    for rel, other, length, start in repeated_runs(base, budgets, minimum):
        warnings.append(f"WARNING core/{rel} and core/{other} share {length} words in a row (\"{start} …\") — "
                        "state the rule in one place and point to it from the other")


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
            i += 1
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


def regex_calls(tree):
    """The `re.<function>(<string literal>, …)` calls of a module, as (line, pattern)."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "re"
                and node.func.attr in REGEX_FUNCTIONS and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            yield node.lineno, node.args[0].value


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


def multiple_spaces(tree):
    """python:S6326: two spaces or more in a regex outside a character class; a quantifier (`{2}`) says how many."""
    return [(line, "python:S6326", "several spaces in a regex; use a quantifier")
            for line, pattern in regex_calls(tree) if MULTIPLE_SPACES.search(CHAR_CLASS.sub("", pattern))]


def sonar_findings(path, source):
    """The findings of the SonarQube Cloud rules a refresh has tripped before, as (line, rule, message)."""
    tree = ast.parse(source, path)
    findings = nested_conditionals(tree) + anchor_precedence(tree) + multiple_spaces(tree)
    if not os.path.basename(path).startswith("test"):  # Sonar skips S1192 in test files
        findings += duplicated_literals(source, tree)
    return sorted(findings)


def check_sonar_rules(errors, paths=None):
    """The Python tools (a target's and the template's own) trip none of the SonarQube Cloud rules that have flagged them
    (`SONAR_RULES`): every finding there keeps the refresh PR in draft and costs a template PR and another refresh."""
    for path in checked_python_files() if paths is None else paths:
        for line, rule, message in sonar_findings(path, read(path)):
            errors.append(f"{os.path.relpath(path, ROOT)}:{line}: {rule} {message}")


def check_complexity(errors):
    """The Python tools (a target's and the template's own) stay below SonarQube Cloud's cognitive-complexity limit
    (python:S3776, 15): every refresh puts them under the target's code analysis, so a finding there would cost a template PR
    and a refresh of every target. complexipy measures the same cognitive complexity; CI installs it."""
    if not shutil.which("complexipy"):
        print("NOTE: complexipy is not installed (pip install complexipy); cognitive complexity not checked here, "
              "CI checks it")
        return
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
    check_word_budgets(errors, warnings=warnings)
    check_repeated_rules(warnings)
    profiles = check_profiles(errors)
    smoke_test(profiles, errors)
    check_decision_tool(errors)
    check_area_checks(errors)
    check_area_assignments(errors)
    check_sonar_seed(profiles, errors)
    check_sonar_rules(errors)
    check_complexity(errors)
    for line in warnings + errors:
        print(line)
    print(f"\nChecked core and {len(profiles)} profiles ({', '.join(profiles)}): {'PASS' if not errors else 'FAIL'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
