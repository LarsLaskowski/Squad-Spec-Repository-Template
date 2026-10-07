#!/usr/bin/env python3
"""Self-check for Squad-Spec-Repository-Template, run before every PR in this repository.

Checks, without arguments:

- the skill mirrors (`.claude/skills`, `.agents/skills`, `.github/skills`) are identical, both in `core/`
  and at the repository root, and every agent and skill has valid front matter;
- `core/CLAUDE.md`, `core/AGENTS.md` and `core/.github/copilot-instructions.md` are identical from their
  first `## ` heading on, and every `<!-- …:begin X -->` marker in a core file has its matching end marker;
- every profile has the same required files, its `instructions.md` provides every stack block the core
  instruction files use, its `stack.md` defines every command name the core refers to, and its
  `squad_settings.py` defines the coverage settings;
- a smoke test: each profile is applied to an empty git repository with `tools/apply-template.py`, and the
  target's `config-check.py` then reports nothing but unfilled placeholders; after every placeholder is
  filled and the template is applied a second time (a refresh), `config-check.py` passes completely;
- the same smoke test for all profiles together (a repository with several languages): the merged CI,
  CodeQL and Dependabot files are valid YAML with every profile's jobs, languages and ecosystems, a refresh
  without `--profile` keeps the recorded profiles, naming another set is refused, and `config-check.py`
  fails when a profile's analyzer script is missing;
- `decision-check.py` on a temporary repository: consistent records pass, an unreleased record may be edited
  in place, and around a release tag a rewritten, deleted or wrongly superseded record fails.

Exit code 0 when everything passes, 1 otherwise. Requires PyYAML.
"""
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # importing the profiles' squad_settings.py must not leave __pycache__ behind

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
MIRRORS = [os.path.join(".claude", "skills"), os.path.join(".agents", "skills"), os.path.join(".github", "skills")]
INSTRUCTIONS = ["CLAUDE.md", "AGENTS.md", os.path.join(".github", "copilot-instructions.md")]
PROFILE_FILES = [
    "instructions.md",
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
            "*Test with coverage*", "*Coverage gate*", "*Analyzer gate*"]
STACK_SECTIONS = ["## Toolchain", "## Layout", "## Commands", "## Analyzer gate", "## Writing code",
                  "## Writing tests", "## Skeleton", "## Dependencies", "## Concurrency", "## Known pitfalls"]
MULTI_FILES = [".squad/tools/analyzer-check.py", ".claude/hooks/session-start.sh"]
SETTINGS = ["COVERAGE_FORMAT", "COVERAGE_REPORT_GLOB", "COVERAGE_PATHSPECS", "COVERAGE_EXCLUDES"]
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


def check_mirrors(base, errors):
    found = []
    for mirror in MIRRORS:
        skills = {}
        for path in glob.glob(os.path.join(base, mirror, "*", "SKILL.md")):
            name = os.path.basename(os.path.dirname(path))
            check_front_matter(path, name, errors)
            skills[name] = read(path)
        found.append((mirror, skills))
    reference_name, reference = found[0]
    for mirror, skills in found[1:]:
        if skills != reference:
            errors.append(f"{os.path.relpath(base, ROOT) or '.'}: {mirror} differs from {reference_name}")
    for path in glob.glob(os.path.join(base, ".claude", "agents", "*.md")):
        check_front_matter(path, os.path.splitext(os.path.basename(path))[0], errors)


def check_core(errors):
    bodies = []
    for rel in INSTRUCTIONS:
        text = read(os.path.join(CORE, rel))
        bodies.append(text[text.find("\n## "):])
    if len(set(bodies)) != 1:
        errors.append("core instruction files differ after the first '## ' heading")
    relative = re.compile(r"\]\((?!https?:|#|/|mailto:)[^)\s]+\)")
    for rel in INSTRUCTIONS:
        for match in relative.finditer(read(os.path.join(CORE, rel))):
            errors.append(f"core/{rel}: relative link {match.group(0)} - use a repository-rooted link (/path)")
    for path in glob.glob(os.path.join(CORE, "**", "*.md"), recursive=True) + \
            glob.glob(os.path.join(CORE, ".*", "**", "*.md"), recursive=True):
        open_blocks = []
        for kind, edge, name in MARKER.findall(read(path)):
            if edge == "begin":
                open_blocks.append((kind, name))
            elif not open_blocks or open_blocks.pop() != (kind, name):
                errors.append(f"{os.path.relpath(path, ROOT)}: unbalanced marker {kind}:{edge} {name}")
        if open_blocks:
            errors.append(f"{os.path.relpath(path, ROOT)}: unclosed markers {open_blocks}")


PLACEHOLDER = re.compile(r"\{\{TODO:[^{}]*\}\}")
BLOCK = re.compile(r"<!-- project:begin ([\w-]+) -->\n.*?<!-- project:end \1 -->", re.S)
MARKED = ["CLAUDE.md", "AGENTS.md", os.path.join(".github", "copilot-instructions.md"),
          os.path.join("docs", "CONTRIBUTING.md"), os.path.join("docs", "ARCHITECTURE.md"),
          os.path.join(".github", "ISSUE_TEMPLATE", "bug_report.md"), os.path.join("docs", "decisions", "README.md"),
          os.path.join(".github", "pull_request_template.md")]


def check_placeholders(errors):
    """A placeholder outside a project block would be reset by every refresh and could never be filled."""
    paths = [p for p in glob.glob(os.path.join(CORE, "**", "*"), recursive=True) +
             glob.glob(os.path.join(CORE, ".*", "**", "*"), recursive=True) +
             glob.glob(os.path.join(ROOT, "profiles", "*", "managed", "**", "*"), recursive=True) +
             glob.glob(os.path.join(ROOT, "profiles", "*", "managed", ".*", "**", "*"), recursive=True) +
             glob.glob(os.path.join(ROOT, "profiles", "*", "instructions.md"))
             if os.path.isfile(p) and "_template" not in p and not p.endswith(".py")]
    for path in sorted(set(paths)):
        text = read(path)
        if os.path.relpath(path, CORE) in MARKED:
            text = BLOCK.sub("", text)
        for match in PLACEHOLDER.finditer(text):
            errors.append(f"{os.path.relpath(path, ROOT)}: placeholder {match.group(0)!r} outside a project block")


def check_profiles(errors):
    stack_blocks = set(re.findall(r"<!-- stack:begin ([\w-]+) -->", read(os.path.join(CORE, "CLAUDE.md"))))
    profiles = sorted(p for p in glob.glob(os.path.join(ROOT, "profiles", "*")) if os.path.isdir(p))
    for profile in profiles:
        name = os.path.basename(profile)
        for rel in PROFILE_FILES:
            if not os.path.isfile(os.path.join(profile, rel)):
                errors.append(f"profile {name}: missing {rel}")
        instructions = os.path.join(profile, "instructions.md")
        if os.path.isfile(instructions):
            provided = set(re.findall(r"<!-- stack:begin ([\w-]+) -->", read(instructions)))
            for block in sorted(stack_blocks - provided):
                errors.append(f"profile {name}: instructions.md lacks stack block '{block}'")
        stack = os.path.join(profile, "seed", ".squad", "stack.md")
        if os.path.isfile(stack):
            text = read(stack)
            for needle in COMMANDS + STACK_SECTIONS:
                if needle not in text:
                    errors.append(f"profile {name}: stack.md lacks '{needle}'")
        settings = os.path.join(profile, "seed", ".squad", "tools", "squad_settings.py")
        if os.path.isfile(settings):
            spec = importlib.util.spec_from_file_location(f"settings_{name}", settings)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for key in SETTINGS:
                if not hasattr(module, key):
                    errors.append(f"profile {name}: squad_settings.py lacks {key}")
    return [os.path.basename(p) for p in profiles]


def apply(target, *options):
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "apply-template.py"), "--target", target,
                           *options], capture_output=True, text=True)


def profile_options(names):
    return [option for name in names for option in ("--profile", name)]


def smoke_test(profiles, errors):
    for names in [[name] for name in profiles] + ([profiles] if len(profiles) > 1 else []):
        label = "+".join(names)
        with tempfile.TemporaryDirectory() as target:
            subprocess.run(["git", "init", "-q", target], check=True)
            applied = apply(target, *profile_options(names))
            if applied.returncode != 0:
                errors.append(f"profile {label}: apply-template failed: {applied.stderr.strip()[-500:]}")
                continue
            checked = subprocess.run([sys.executable, os.path.join(target, ".squad", "tools", "config-check.py")],
                                     capture_output=True, text=True)
            lines = [line for line in checked.stdout.splitlines()
                     if line and not line.startswith("Checked") and "placeholder" not in line]
            for line in lines:
                errors.append(f"profile {label}: config-check after apply: {line}")
            fill_placeholders(target)
            # a refresh names no profile: the recorded ones are kept
            refresh = apply(target)
            if refresh.returncode != 0:
                errors.append(f"profile {label}: refresh failed: {refresh.stderr.strip()[-500:]}")
                continue
            refreshed = subprocess.run([sys.executable, os.path.join(target, ".squad", "tools", "config-check.py")],
                                       capture_output=True, text=True)
            if refreshed.returncode != 0:
                for line in refreshed.stdout.splitlines()[:10]:
                    errors.append(f"profile {label}: config-check after filling and refreshing: {line}")
            if len(names) > 1:
                check_multi(names, target, errors)


def check_multi(names, target, errors):
    label = "+".join(names)
    with open(os.path.join(target, ".squad", "template.json"), encoding="utf-8") as handle:
        record = json.load(handle)
    if record.get("profiles") != names or record.get("profile") != names[0]:
        errors.append(f"profile {label}: template.json after a refresh records {record.get('profile')} / "
                      f"{record.get('profiles')}")
    if apply(target, "--profile", names[0]).returncode == 0:
        errors.append(f"profile {label}: apply-template accepted a different profile set without --reset-profiles")
    for rel in MULTI_FILES:
        if not os.path.isfile(os.path.join(target, rel)):
            errors.append(f"profile {label}: {rel} (dispatcher) missing")
    for path in glob.glob(os.path.join(target, ".github", "**", "*.yml"), recursive=True):
        try:
            with open(path, encoding="utf-8") as handle:
                parsed = yaml.safe_load(handle)
        except yaml.YAMLError as error:
            errors.append(f"profile {label}: {os.path.relpath(path, target)} is not valid YAML: "
                          f"{str(error).splitlines()[0]}")
            continue
        name = os.path.basename(path)
        if name == "codeql.yml":
            languages = [entry["language"] for entry in parsed["jobs"]["analyze"]["strategy"]["matrix"]["include"]]
            expected = [single_value(n, "codeql.yml", r"- language: (\S+)") for n in names]
            if languages != expected:
                errors.append(f"profile {label}: codeql.yml languages {languages}, expected {expected}")
        elif name == "dependabot.yml":
            ecosystems = [u["package-ecosystem"] for u in parsed["updates"]]
            if len(set(ecosystems)) != len(ecosystems):
                errors.append(f"profile {label}: dependabot.yml repeats an ecosystem: {ecosystems}")
            for n in names:
                for ecosystem in re.findall(r"package-ecosystem: *\"?([\w-]+)", profile_file(n, "dependabot.yml")):
                    if ecosystem not in ecosystems:
                        errors.append(f"profile {label}: dependabot.yml lacks the {n} ecosystem {ecosystem}")
        elif name == "ci.yml":
            jobs = set(parsed["jobs"])
            for n in names:
                own = set(re.findall(r"^  ([\w-]+):", profile_file(n, "ci.yml").split("\njobs:\n", 1)[1], re.M))
                if len(jobs) < len(own):
                    errors.append(f"profile {label}: ci.yml lost jobs of {n}")
    os.remove(os.path.join(target, ".squad", "tools", f"analyzer-check-{names[-1]}.py"))
    broken = subprocess.run([sys.executable, os.path.join(target, ".squad", "tools", "config-check.py")],
                            capture_output=True, text=True)
    if broken.returncode == 0:
        errors.append(f"profile {label}: config-check passes although analyzer-check-{names[-1]}.py is missing")


def profile_file(name, rel):
    return read(os.path.join(ROOT, "profiles", name, "seed", ".github", rel if rel == "dependabot.yml"
                             else os.path.join("workflows", rel)))


def single_value(name, rel, pattern):
    return re.search(pattern, profile_file(name, rel)).group(1)


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


def write_record(repo, number, status="Accepted", supersedes="—", body="Do it.", index=True):
    path = os.path.join(repo, "docs", "decisions", f"{number}-topic.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(RECORD.format(n=number, title="Topic", status=status, supersedes=supersedes, body=body))


def write_index(repo, rows):
    lines = ["# Decision records", "", "<!-- project:begin index -->", "| # | Title | Status | Date |",
             "| - | ----- | ------ | ---- |"]
    lines += [f"| {number} | Topic | {status} | 2026-01-01 |" for number, status in rows]
    lines.append("<!-- project:end index -->")
    with open(os.path.join(repo, "docs", "decisions", "README.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def check_decision_tool(errors):
    """decision-check.py: consistency without tags, then the freeze rules around a release tag."""
    tool = os.path.join(CORE, ".squad", "tools", "decision-check.py")
    with tempfile.TemporaryDirectory() as repo:
        def git_in(*args):
            subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                           check=True, capture_output=True)

        def passes():
            return subprocess.run([sys.executable, tool, repo], capture_output=True, text=True).returncode == 0

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
        write_index(repo, [("0001", "Accepted")])
        expect("record missing in the index", False)
        write_index(repo, [("0001", "Accepted"), ("0002", "Accepted")])
        write_record(repo, "0002", status="Superseded by 0003")
        write_index(repo, [("0001", "Accepted"), ("0002", "Superseded by 0003")])
        expect("Superseded by a record that does not exist", False)
        git_in("checkout", "-q", "--", ".")
        write_record(repo, "0001", body="Changed before any release.")
        expect("unreleased record edited in place", True)
        git_in("commit", "-qam", "edit")
        git_in("tag", "v0.1.0")
        write_record(repo, "0001", body="Changed after the release.")
        expect("released record rewritten", False)
        git_in("checkout", "-q", "--", ".")
        write_record(repo, "0003", supersedes="0001", body="Replaces 0001.")
        write_record(repo, "0001", status="Superseded by 0003", body="Changed before any release.")
        write_index(repo, [("0001", "Superseded by 0003"), ("0002", "Accepted"), ("0003", "Accepted")])
        expect("released record superseded by a new record", True)
        git_in("add", "-A")
        git_in("commit", "-qm", "supersede")
        write_record(repo, "0003", status="Superseded by 0004", supersedes="0001", body="Replaces 0001.")
        write_record(repo, "0004", supersedes="0003")
        write_index(repo, [("0001", "Superseded by 0003"), ("0002", "Accepted"), ("0003", "Superseded by 0004"),
                           ("0004", "Accepted")])
        expect("unreleased record superseded", False)
        git_in("checkout", "-q", "--", ".")
        os.remove(os.path.join(repo, "docs", "decisions", "0002-topic.md"))
        write_index(repo, [("0001", "Superseded by 0003"), ("0003", "Accepted")])
        expect("released record deleted", False)


def main():
    errors = []
    check_mirrors(ROOT, errors)
    check_mirrors(CORE, errors)
    check_core(errors)
    check_placeholders(errors)
    profiles = check_profiles(errors)
    smoke_test(profiles, errors)
    check_decision_tool(errors)
    for error in errors:
        print(error)
    print(f"\nChecked core and {len(profiles)} profiles ({', '.join(profiles)}): {'PASS' if not errors else 'FAIL'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
