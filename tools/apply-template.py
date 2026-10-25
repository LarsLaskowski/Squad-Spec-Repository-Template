#!/usr/bin/env python3
"""Apply Squad-Spec-Repository-Template to a target repository.

This is the mechanical half of the `adopt-template` skill.

What it does, for the chosen stack profile (`profiles/<profile>`) — or several profiles for a repository
with more than one language, see "Several profiles" below:

- **managed** files (`core/`, except the marked files below, plus `profiles/<profile>/managed/`) are
  written to the target, overwriting what is there — they are owned by the template;
- **marked** files (`MARKED` below) are rebuilt from the template: every
  `<!-- project:begin NAME -->…<!-- project:end NAME -->` block keeps the target's current content, every
  `<!-- stack:begin NAME -->…<!-- stack:end NAME -->` block is filled from
  `profiles/<profile>/instructions.md`, everything else comes from the template. A target file that has no
  project markers yet (first adoption) is backed up to `.git/adopt-template/backup/` and replaced by the
  template version, so the skill can move its content into the project blocks;
- the rules live in the marked `AGENTS.md` (`RULES` below), which Codex, Kimi Code and GitHub Copilot's coding
  agent read directly; the managed `CLAUDE.md` only imports it (`@AGENTS.md`). A target whose `CLAUDE.md` still
  holds the rules (it has project blocks: written by a template version before the rules moved) has those project
  blocks carried into `AGENTS.md`; a hand-written `CLAUDE.md` (no project blocks) is backed up before it is
  replaced, like a marked file;
- the **generated** `.github/copilot-instructions.md` (`GENERATED` below) is the title and introduction of
  `core/.github/copilot-instructions.md` followed by the rebuilt `AGENTS.md` from its first `## ` heading on,
  without Claude Code's `@path` import lines (the file GitHub Copilot's code review and chat read). A target file
  without project markers (written by hand) is backed up first, like a marked file;
- **seed** files (`seed/` and `profiles/<profile>/seed/`) are written only when the target does not have
  them yet; an existing `.claude/settings.json` only gets the squad's git-guard hook (`GIT_GUARD_HOOK`) added
  when it lacks it, everything else in it stays;
- **retired** files (`RETIRED` below) that an older template version wrote are removed from the target, and
  every line of the target that still refers to one is listed for fixing by hand;
- `.squad/template.json` records the template repository, its commit and the profile(s).

Several profiles (`--profile go --profile dotnet`, the first one is the primary): the stack blocks of the
instruction files get one labelled part per profile, `.squad/stack.md` one section per profile,
`squad_settings.py` the union of the profiles' paths and one coverage report per profile
(`COVERAGE_REPORTS`), and the CI jobs, CodeQL languages and Dependabot ecosystems are merged side by side.
The profiles' analyzer gates and SessionStart hooks are written as `analyzer-check-<profile>.py` and
`session-start-<profile>.sh`, run by the dispatchers in `multi/`. A seed file the merge does not know how
to combine keeps the primary profile's version and is reported as `conflict`. A seed that another profile's
tooling refuses (`sonar-project.properties` with `dotnet`, see `SEEDS_REFUSED_WITH`) is skipped. A refresh without
`--profile` keeps the profiles recorded in `.squad/template.json`; naming a different set needs
`--reset-profiles`.

Line endings follow the target, file by file: a file is written with the line ending Git checks it out
with, read from the target's `.gitattributes` with `git check-attr eol` (so `*.md text eol=crlf` under
`* text=auto eol=lf` is honored). A file without an `eol` attribute gets the repository-wide default: CRLF
when the global rule is `* text=auto eol=crlf`; an existing repository without a `.gitattributes` keeps the
majority line ending of its index and gets no seeded `.gitattributes` (that would renormalize the whole
repository — a decision of its own); only an empty repository follows the profile's seeds. A seeded
`.editorconfig` gets an `end_of_line` that matches that default. Shell scripts always keep LF and the
executable bit. A file whose content is unchanged but whose line endings in the working copy differ from
what Git would check out is rewritten and reported as `renormalized`.

Usage, from the template repository's root:
    python3 tools/apply-template.py --target ../OtherRepo --profile dotnet [--dry-run]
    python3 tools/apply-template.py --target ../OtherRepo      # refresh with the recorded profile(s)

Prints one line per file (created / updated / renormalized / unchanged / kept / skipped / backed-up / conflict /
removed), the files in template-owned folders of the target that the template does not know (old skills or
agents to review) and the lines that still refer to a retired file.
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

# Where squad lessons about template-managed files are filed; recorded in every target's .squad/template.json.
TEMPLATE_REPOSITORY = "LarsLaskowski/Squad-Spec-Repository-Template"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "profiles", "*")) if os.path.isdir(p))
# The instruction file every agent reads (marked) and the one Claude Code reads, which only imports it (managed).
RULES = "AGENTS.md"
CLAUDE = "CLAUDE.md"
MARKED = [
    RULES,
    "docs/CONTRIBUTING.md",
    "docs/ARCHITECTURE.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    "docs/decisions/README.md",
    "docs/areas/README.md",
    ".github/pull_request_template.md",
]
# A seed the tooling of a profile in the repository refuses: the SonarScanner for .NET stops when the repository holds
# a sonar-project.properties, so its settings are passed as scanner arguments (the dotnet profile's ci.yml does).
SEEDS_REFUSED_WITH = {"sonar-project.properties": "dotnet"}
# Generated from AGENTS.md: {target path: core file holding its title and introduction}.
GENERATED = {".github/copilot-instructions.md": ".github/copilot-instructions.md"}
# A Claude Code memory import on a line of its own (`@.github/instructions/csharp.instructions.md`); GitHub Copilot
# reads `.github/instructions/*.instructions.md` through their `applyTo` front matter, so the mirror leaves it out.
IMPORT_LINE = re.compile(r"^@[^\s@]\S*[ \t]*\n", re.M)
OWNED_DIRS = [".claude/agents", ".claude/skills", ".agents/skills", ".github/skills", ".squad/agents", ".squad/tools"]
# Written by older template versions and removed on a refresh: the Codex and Copilot mirrors of the template's skills
# (the squad runs on Claude Code subagents only), the squad's decisions.md and history.md files, which nothing read or
# wrote (process decisions are the records in docs/decisions/), and the charters, which now live in the subagent
# files under .claude/agents/.
RETIRED = [".squad/decisions.md"] + [
    f"{mirror}/{skill}/SKILL.md" for mirror in (".agents/skills", ".github/skills")
    for skill in ("create-pr", "review-pr", "squad-issue", "squad-spec", "decision-consolidate")] + [
    f".squad/agents/{role}/{name}"
    for role in ("code-officer", "dev", "devils-advocate", "lead", "reviewer", "security", "tester")
    for name in ("history.md", "charter.md")]
# What a reference to a retired file looks like: the file's path, a retired skill mirror's folder, or the charter and
# history folder .squad/agents/ (written with a wildcard as often as with a role).
# Decision records state history and a released one is append-only, so a retired file named there stays.
DECISION_RECORD = re.compile(r"^docs/decisions/\d{4}-[^/]*\.md$")
RETIRED_REFERENCES = sorted(set(RETIRED) | {os.path.dirname(rel) for rel in RETIRED if rel.endswith("/SKILL.md")}
                            | {".squad/agents/"})
# Stored under another name here, because a .gitattributes inside this repository would apply to it.
GITATTRIBUTES = ".gitattributes"
TEMPLATE_JSON = ".squad/template.json"
RENAMES = {"gitattributes": GITATTRIBUTES}
# The members' Git guard runs from the project settings, the only hooks Claude Code runs for project agents in a folder
# without workspace trust (a cloud or `-p` session); a refresh adds it to a settings file the target already has.
CLAUDE_SETTINGS = ".claude/settings.json"
GIT_GUARD_HOOK = {"matcher": "Bash", "hooks": [{"type": "command",
                                                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/git-guard.py"'}]}
BLOCK = re.compile(r"<!-- (project|stack):begin ([\w-]+) -->\n(.*?)<!-- \1:end \2 -->", re.S)


def recorded_profiles(target):
    """The profiles `.squad/template.json` of the target names: `profiles`, else `profile` plus the older
    `additionalProfiles`; empty when the file is missing or unreadable."""
    path = os.path.join(target, TEMPLATE_JSON)
    try:
        record = json.loads(read(path))
    except (OSError, ValueError):
        return []
    if not isinstance(record, dict):
        return []
    names = record.get("profiles")
    if not isinstance(names, list):
        names = [record.get("profile"), *(record.get("additionalProfiles") or [])]
    result = []
    for name in names:
        if isinstance(name, str) and name and name not in result:
            result.append(name)
    return result


def label(name, text):
    """One profile's part of a stack block in a repository with several profiles."""
    return f"**Profile `{name}`**\n\n{text.rstrip(chr(10))}\n"


def combine_stack_blocks(parts):
    """parts: [(profile, {block: content})] -> {block: content}; a single profile is taken as is."""
    if len(parts) == 1:
        return parts[0][1]
    names = []
    for _, found in parts:
        names += [name for name in found if name not in names]
    return {name: "\n".join(label(profile, found[name]) for profile, found in parts if name in found)
            for name in names}


def demote(text):
    """Turn every Markdown heading outside code fences one level deeper."""
    out, fenced = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        out.append("#" + line if not fenced and re.match(r"#{1,5} ", line) else line)
    return "\n".join(out)


SONAR_GATE_ROW = re.compile(r"^\| \*Sonar gate\* \|.*\n?", re.M)


def sonar_profile(names):
    """The profile whose scanner analyses a repository with several profiles: the .NET scanner when `dotnet` is one
    of them (it refuses a sonar-project.properties, so CI runs it for the whole repository), else the primary."""
    return "dotnet" if "dotnet" in names else names[0]


def merge_stack_md(parts):
    scanner = sonar_profile([name for name, _ in parts])
    parts = [(name, text if name == scanner else SONAR_GATE_ROW.sub("", text)) for name, text in parts]
    intro = ("# Stack: " + " + ".join(name for name, _ in parts) + "\n\n"
             "This repository combines the stack profiles " + ", ".join(f"`{name}`" for name, _ in parts) + ". "
             "Every command name below (*Format*, *Build*, *Test*, *Analyzer gate*, …) exists once per profile, in the "
             "section of that profile; a gate is passed only when it passes for **every** profile. The one exception is "
             f"*Sonar gate*: one SonarQube Cloud project analyses the whole repository, so it is defined once, in the "
             f"`{scanner}` section. "
             "`python3 .squad/tools/analyzer-check.py` and `python3 .squad/tools/coverage-check.py` cover all of "
             "them in one call. Paths and globs of the tools are in `.squad/tools/squad_settings.py`.\n")
    return intro + "".join("\n" + demote(text).rstrip("\n") + "\n" for _, text in parts)


def merge_unit_tests(parts):
    out = []
    for name, text in parts:
        out.append(re.sub(r"^# .*$", f"# Unit Tests ({name})", text.rstrip("\n"), count=1, flags=re.M))
    return "\n\n---\n\n".join(out) + "\n"


def load_settings(path):
    spec = importlib.util.spec_from_file_location("profile_settings", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def union_values(lists):
    """The values of all lists, each once, in order of appearance."""
    return list(dict.fromkeys(value for values in lists for value in values))


def merge_settings(profile_dirs):
    """squad_settings.py of a repository with several profiles: the union of the paths and one coverage report
    per profile; the primary profile's other settings (e.g. SOLUTION) come first."""
    modules = [load_settings(os.path.join(p, "seed", ".squad", "tools", "squad_settings.py")) for p in profile_dirs]
    names = [os.path.basename(p) for p in profile_dirs]

    lines = ['"""Per-repository settings for the squad tools (profiles: ' + ", ".join(names) + '). Seeded once by',
             'adopt-template and kept on later refreshes; the scripts that import it are template-managed."""', "",
             "# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.",
             f"BASE_REF = {getattr(modules[0], 'BASE_REF', 'origin/main')!r}", "",
             "# Tier `patch` (.squad/routing.md, *Tiers*; scope-check.py --tier patch): changed lines outside specs/ at most.",
             f"PATCH_MAX_LINES = {getattr(modules[0], 'PATCH_MAX_LINES', 30)!r}", ""]
    scanner = modules[names.index(sonar_profile(names))]
    if hasattr(scanner, "SONAR_REPORT_TASK"):
        lines += ["# Sonar gate (.squad/tools/sonar-check.py): the report file the repository's scanner writes.",
                  f"SONAR_REPORT_TASK = {scanner.SONAR_REPORT_TASK!r}", ""]
    for name, module in zip(names, modules, strict=True):
        if hasattr(module, "SOLUTION"):
            lines += [f"# Solution or project file the {name} analyzer gate builds.", f"SOLUTION = {module.SOLUTION!r}", ""]
    reports = [(m.COVERAGE_FORMAT, m.COVERAGE_REPORT_GLOB) for m in modules]
    tests = union_values([getattr(m, "COVERAGE_TEST_PATHSPECS", m.COVERAGE_EXCLUDES) for m in modules])
    lines += ["# Coverage gate (.squad/tools/coverage-check.py): one (format, glob) report per profile, merged.",
              "# COVERAGE_OVERALL_THRESHOLD may start below COVERAGE_THRESHOLD in a repository adopted with a coverage debt;",
              "# it is never lowered and is raised towards COVERAGE_THRESHOLD as coverage improves.",
              f"COVERAGE_THRESHOLD = {getattr(modules[0], 'COVERAGE_THRESHOLD', 80)!r}",
              f"COVERAGE_OVERALL_THRESHOLD = {getattr(modules[0], 'COVERAGE_OVERALL_THRESHOLD', 80)!r}",
              "COVERAGE_REPORTS = ["]
    lines += [f"    ({fmt!r}, {pattern!r})," for fmt, pattern in reports]
    lines += ["]",
              f"COVERAGE_PATHSPECS = {union_values([getattr(m, 'COVERAGE_PATHSPECS', ()) for m in modules])!r}",
              f"COVERAGE_EXCLUDES = {union_values([getattr(m, 'COVERAGE_EXCLUDES', ()) for m in modules])!r}",
              f"COVERAGE_TEST_PATHSPECS = {tests!r}  # a diff touching these is gated on overall coverage too", ""]
    return "\n".join(lines)


def split_chunks(text, pattern):
    """Split text at every line matching pattern: (head before the first match, [chunk, ...])."""
    starts = [m.start() for m in re.finditer(pattern, text, re.M)]
    if not starts:
        return text, []
    return text[:starts[0]], [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)], strict=True)]


def merge_dependabot(texts):
    head, chunks = split_chunks(texts[0], r"^  - package-ecosystem:")
    seen = {re.match(r" {2}- package-ecosystem: *(\S+)", c).group(1).strip('"') for c in chunks}
    for text in texts[1:]:
        for chunk in split_chunks(text, r"^  - package-ecosystem:")[1]:
            ecosystem = re.match(r" {2}- package-ecosystem: *(\S+)", chunk).group(1).strip('"')
            if ecosystem not in seen:
                seen.add(ecosystem)
                chunks[-1] = chunks[-1].rstrip("\n") + "\n\n"
                chunks.append(chunk)
    return head + "".join(chunks)


def merge_codeql(texts):
    """Matrix entries and the set-up steps before `Initialize CodeQL` of every profile, side by side."""
    initialize = re.compile(r"^ {6}- name: Initialize CodeQL", re.M)

    def parts(text):
        before, after = text.split("    steps:\n", 1)
        cut = initialize.search(after).start()
        return before, after[:cut], after[cut:]

    before, pre, tail = parts(texts[0])
    head, entries = split_chunks(before, r"^          - language:")
    steps = split_chunks(pre, r"^      - ")[1]
    for text in texts[1:]:
        other_before, other_pre, _ = parts(text)
        entries += [c for c in split_chunks(other_before, r"^          - language:")[1] if c not in entries]
        steps += [c for c in split_chunks(other_pre, r"^      - ")[1]
                  if c.strip() not in [known.strip() for known in steps]]
    return head + "".join(entries) + "    steps:\n" + "".join(c.rstrip("\n") + "\n\n" for c in steps) + tail


def merge_ci(texts, names):
    """Jobs of every profile under one `jobs:`; a job id that already exists gets the profile as prefix."""
    head, jobs = texts[0].split("\njobs:\n", 1)
    taken = set(re.findall(r"^ {2}([\w-]+):", jobs, re.M))
    permissions = set(re.findall(r"^ {2}([\w-]+: \w+)$", head.split("permissions:", 1)[1].split("\n\n")[0], re.M))
    out = jobs.rstrip("\n") + "\n"
    for name, text in zip(names[1:], texts[1:], strict=True):
        other_head, other = text.split("\njobs:\n", 1)
        permissions |= set(re.findall(r"^ {2}([\w-]+: \w+)$", other_head.split("permissions:", 1)[1].split("\n\n")[0], re.M))
        for job in re.findall(r"^ {2}([\w-]+):", other, re.M):
            if job in taken:
                other = re.sub(rf"^  {re.escape(job)}:", f"  {name}-{job}:", other, flags=re.M)
                job = f"{name}-{job}"
            taken.add(job)
        out += "\n" + other.rstrip("\n") + "\n"
    block = "permissions:\n" + "".join(f"  {p}\n" for p in sorted(permissions))
    head = re.sub(r"permissions:\n(?: {2}.*\n)+", lambda _: block, head + "\n", count=1).rstrip("\n")
    return head + "\n\njobs:\n" + out


MERGERS = {
    ".github/dependabot.yml": lambda texts, names: merge_dependabot(texts),
    ".github/workflows/codeql.yml": lambda texts, names: merge_codeql(texts),
    ".github/workflows/ci.yml": merge_ci,
}


def files_under(base):
    result = {}
    for directory, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for name in names:
            path = os.path.join(directory, name)
            rel = os.path.relpath(path, base).replace(os.sep, "/")
            head, _, tail = rel.rpartition("/")
            tail = RENAMES.get(tail, tail)
            result[f"{head}/{tail}" if head else tail] = path
    return result


def read(path):
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read().replace("\r\n", "\n")


def blocks(text, kind):
    return {name: content for k, name, content in BLOCK.findall(text) if k == kind}


def fill(template, project, stack):
    def replace(match):
        kind, name, content = match.group(1), match.group(2), match.group(3)
        source = project if kind == "project" else stack
        new = source.get(name, content)
        if new and not new.endswith("\n"):
            new += "\n"
        return f"<!-- {kind}:begin {name} -->\n{new}<!-- {kind}:end {name} -->"
    return BLOCK.sub(replace, template)


def tracked_eol(target):
    """Count text files stored with CRLF and with LF in the target's index."""
    listing = subprocess.run(["git", "-C", target, "ls-files", "--eol"], capture_output=True, text=True,
                             check=False).stdout.split()
    return listing.count("i/crlf"), listing.count("i/lf")


def is_existing_repository(target):
    crlf, lf = tracked_eol(target)
    return crlf + lf > 0


def uses_crlf(target, profile_dirs):
    """The target's own .gitattributes decides; an existing repository without one keeps the line endings
    of its index; only an empty repository follows the profiles' seeded .gitattributes (CRLF if any has it, as
    that file is seeded then)."""
    path = os.path.join(target, GITATTRIBUTES)
    if os.path.isfile(path):
        return re.search(r"^\*\s+text=auto\s+eol=crlf", read(path), re.M) is not None
    if is_existing_repository(target):
        crlf, lf = tracked_eol(target)
        return crlf > lf
    paths = [os.path.join(profile, "seed", "gitattributes") for profile in profile_dirs]
    return any(os.path.isfile(path) and re.search(r"^\*\s+text=auto\s+eol=crlf", read(path), re.M) is not None
               for path in paths)


def eol_attributes(target, rels):
    """The `eol` attribute Git resolves for each path from the target's `.gitattributes`: {rel: "crlf" | "lf"};
    a path without one (unspecified, or a pattern that sets neither) is left out."""
    rels = [rel for rel in rels if rel]
    if not rels:
        return {}
    listing = subprocess.run(["git", "-C", target, "check-attr", "--stdin", "-z", "eol"], input="\0".join(rels) + "\0",
                             capture_output=True, text=True, check=False).stdout.split("\0")
    # -z output: path, attribute, value, repeated; the trailing empty field after the last value is dropped.
    triples = zip(listing[0::3], listing[1::3], listing[2::3], strict=False)
    return {path: value for path, attribute, value in triples if attribute == "eol" and value in ("crlf", "lf")}


def crlf_for(rel, eols, default):
    """CRLF for one file: its `eol` attribute decides, a file without one takes the repository-wide default;
    shell scripts always stay LF (bash fails on carriage returns)."""
    if rel.endswith(".sh"):
        return False
    eol = eols.get(rel)
    return default if eol is None else eol == "crlf"


def status_of(old, data):
    """unchanged when the file already has these bytes, renormalized when only the line endings differ."""
    if old == data:
        return "unchanged"
    if old.replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n"):
        return "renormalized"
    return "updated"


def write(target, rel, text, crlf, dry_run, report, status_if_new="created"):
    dest = target_path(target, rel)
    data = (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")
    old = None
    if os.path.isfile(dest):
        with open(dest, "rb") as existing:
            old = existing.read()
    status = status_if_new if old is None else status_of(old, data)
    report.append((status, rel))
    if dry_run or status == "unchanged":
        return
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(data)
    if rel.endswith(".sh"):
        # Add the execute bit only where read is already granted, so the umask is respected.
        mode = os.stat(dest).st_mode & 0o777
        os.chmod(dest, mode | ((mode & 0o444) >> 2))


def retire(target, dry_run, report):
    """Remove the files an older template version wrote (RETIRED) and the folders that become empty."""
    for rel in RETIRED:
        path = target_path(target, rel)
        if not os.path.isfile(path):
            continue
        report.append(("removed", rel))
        if dry_run:
            continue
        os.remove(path)
        folder = os.path.dirname(path)
        while folder != target and not os.listdir(folder):
            os.rmdir(folder)
            folder = os.path.dirname(folder)


def retired_references(target):
    """Lines of the target's files (tracked or untracked, not ignored) that name a retired file: [(path, line, text)].
    Project blocks and build files are never rewritten by the apply step, so a reference there outlives the file.
    Decision records (DECISION_RECORD) are left out: they describe what was true when they were written."""
    terms = [arg for term in RETIRED_REFERENCES for arg in ("-e", term)]
    listing = subprocess.run(["git", "-C", target, "grep", "-n", "-I", "-F", "--untracked", "--no-color", *terms],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout
    # A term inside a longer name (MY_AGENTS.md, docs.agents/skills) is not a reference.
    boundary = re.compile(r"(?<![\w.-])(?:" + "|".join(re.escape(term) for term in RETIRED_REFERENCES) + ")")
    hits = []
    for line in listing.splitlines():
        path, number, text = (line.split(":", 2) + ["", ""])[:3]
        if path not in RETIRED and DECISION_RECORD.match(path) is None and number.isdigit() and boundary.search(text):
            hits.append((path, int(number), text.strip()))
    return hits


def instruction_body(text):
    """The part of an instruction file both AGENTS.md and its Copilot mirror share: from the first `## ` heading on,
    without Claude Code import lines."""
    start = text.find("\n## ")
    return IMPORT_LINE.sub("", text[start:]) if start >= 0 else ""


def generated_files(core, rules):
    """{rel: text} of the files generated from the rebuilt AGENTS.md: the core file's title and introduction, then the
    body."""
    return {rel: read(core[source]).rstrip("\n") + "\n" + instruction_body(rules) for rel, source in GENERATED.items()}


def legacy_rules(target, template, dry_run, report):
    """The project blocks of a target CLAUDE.md that still holds the rules (template versions before AGENTS.md held
    them), to carry into AGENTS.md; a hand-written CLAUDE.md (no project blocks, not the template's) is backed up
    before the managed one replaces it."""
    if not os.path.isfile(os.path.join(target, CLAUDE)):
        return {}
    current = read(os.path.join(target, CLAUDE))
    project = blocks(current, "project")
    if not project and current != template:
        backup(target, CLAUDE, dry_run, report)
    return project


def backup(target, rel, dry_run, report):
    dest = target_path(target, os.path.join(".git", "adopt-template", "backup", rel))
    report.append(("backed-up", rel + " -> .git/adopt-template/backup/" + rel))
    if not dry_run:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(target_path(target, rel), dest)


def merge_seed(rel, found, names, report):
    """One seed file that several profiles have: the merged text, or the primary profile's file (reported as a conflict)."""
    texts = [read(src) for _, src in found]
    owners = [name for name, _ in found]
    if rel == ".squad/stack.md":
        return merge_stack_md(list(zip(owners, texts, strict=True)))
    if rel == "docs/UNIT_TESTS.md":
        return merge_unit_tests(list(zip(owners, texts, strict=True)))
    if rel == ".squad/tools/squad_settings.py":
        return merge_settings([os.path.join(ROOT, "profiles", name) for name in names])
    if rel in MERGERS:
        return MERGERS[rel](texts, owners)
    report.append(("conflict", f"{rel} (in {', '.join(owners)}; kept the {owners[0]} version, merge by hand)"))
    return found[0][1]


def seed_files(profile_dirs, names, report):
    """The seed files of all profiles: {rel: text-or-path}. Paths that exist in several profiles are merged
    (MERGERS, stack.md, UNIT_TESTS.md, squad_settings.py); anything else keeps the primary profile's file."""
    sources = {}
    for profile in profile_dirs:
        for rel, src in files_under(os.path.join(profile, "seed")).items():
            sources.setdefault(rel, []).append((os.path.basename(profile), src))
    result = dict(files_under(os.path.join(ROOT, "seed")))
    for rel, found in sources.items():
        result[rel] = found[0][1] if len(found) == 1 else merge_seed(rel, found, names, report)
    return result


def managed_files(profile_dirs, names):
    """core/ (minus the marked files) plus every profile's managed files. With several profiles the files of
    the same name are written per profile (`analyzer-check-go.py`) next to the dispatcher from multi/."""
    core = files_under(os.path.join(ROOT, "core"))
    managed = {rel: src for rel, src in core.items() if rel not in MARKED and rel not in GENERATED.values()}
    if len(profile_dirs) == 1:
        managed.update(files_under(os.path.join(profile_dirs[0], "managed")))
        return core, managed
    dispatchers = files_under(os.path.join(ROOT, "multi"))
    for name, profile in zip(names, profile_dirs, strict=True):
        for rel, src in files_under(os.path.join(profile, "managed")).items():
            if rel not in dispatchers:
                managed[rel] = src
                continue
            stem, ext = os.path.splitext(rel)
            managed[f"{stem}-{name}{ext}"] = src
    managed.update(dispatchers)
    return core, managed


def target_root(path):
    """The target's real path, which must be the root of a git repository; every path the tool touches stays below it."""
    root = os.path.realpath(path)
    if not os.path.isdir(os.path.join(root, ".git")):
        sys.exit(f"{root} is not the root of a git repository")
    return root


def target_path(target, rel):
    """The path of a template-relative file inside the target; a path that would leave it is refused."""
    dest = os.path.normpath(os.path.join(target, rel))
    if os.path.commonpath([target, dest]) != target:
        sys.exit(f"{rel} would leave the target repository")
    return dest


def profile_names(args, recorded):
    """The profiles to apply: the ones named, else the ones the target records; refuses a changed set without
    --reset-profiles."""
    names = list(dict.fromkeys(args.profile or recorded))
    if not names:
        sys.exit("No profile: pass --profile (repeat it for several), the target has no .squad/template.json")
    unknown_profiles = [name for name in names if name not in PROFILES]
    if unknown_profiles:
        sys.exit(f".squad/template.json names profiles this template does not have: {', '.join(unknown_profiles)}")
    if args.profile and recorded and set(names) != set(recorded) and not args.reset_profiles:
        sys.exit(f"The target records the profiles {', '.join(recorded)}, but --profile names {', '.join(names)}: "
                 "refresh without --profile to keep the recorded ones, or add --reset-profiles to change them")
    return names


def write_marked(target, core, legacy, stack, emit, dry_run, report):
    """Rebuild the marked files from the template; returns {rel: text}."""
    rebuilt = {}
    for rel in MARKED:
        template = read(core[rel])
        dest = os.path.join(target, rel)
        current = read(dest) if os.path.isfile(dest) else ""
        project = blocks(current, "project")
        if current and not project:
            backup(target, rel, dry_run, report)
        if rel == RULES and legacy:
            project = legacy
        rebuilt[rel] = fill(template, project, stack)
        emit(rel, rebuilt[rel])
    return rebuilt


def write_generated(target, core, rules, emit, dry_run, report):
    for rel, text in generated_files(core, rules).items():
        dest = os.path.join(target, rel)
        if os.path.isfile(dest) and not blocks(read(dest), "project"):
            backup(target, rel, dry_run, report)
        emit(rel, text)


def seed_text(rel, src, crlf):
    """The text of a seed file; a seeded .editorconfig gets the end_of_line of the repository default."""
    text = read(src) if os.path.isfile(src) else src
    if rel == ".editorconfig":
        text = re.sub(r"^(end_of_line\s*=\s*)(crlf|lf)[ \t]*$", r"\g<1>" + ("crlf" if crlf else "lf"), text, flags=re.M)
    return text


def seed_skip_reason(target, rel, names, existing):
    """Why a seed file is left alone: (status, note), or None when it is to be written."""
    if os.path.exists(os.path.join(target, rel)):
        return "kept", rel
    if SEEDS_REFUSED_WITH.get(rel) in names:
        return "skipped", (f"{rel} (the profile {SEEDS_REFUSED_WITH[rel]} cannot use it: its Sonar scanner "
                           "refuses a repository that has one and takes the settings as arguments)")
    if rel == GITATTRIBUTES and existing:
        # A new .gitattributes renormalizes line endings across the whole repository; that is a decision of
        # its own, not a side effect of adopting the squad.
        return "skipped", rel + " (existing repository without one; add it in a change of its own)"
    return None


def with_git_guard(text):
    """The settings text with GIT_GUARD_HOOK among its PreToolUse hooks; None when it has it already.
    ValueError when the text is no JSON object (the hook is then added by hand)."""
    data = json.loads(text)
    hooks = data.setdefault("hooks", {}) if isinstance(data, dict) else None
    pre_tool_use = hooks.setdefault("PreToolUse", []) if isinstance(hooks, dict) else None
    if not isinstance(pre_tool_use, list):
        raise ValueError("no JSON object with a hooks.PreToolUse list")
    if any("git-guard.py" in str(hook.get("command", "")) for group in pre_tool_use if isinstance(group, dict)
           for hook in (group.get("hooks") if isinstance(group.get("hooks"), list) else [])
           if isinstance(hook, dict)):
        return None
    pre_tool_use.append(GIT_GUARD_HOOK)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def merge_git_guard(target, emit, report):
    """Add the git-guard hook to the target's existing .claude/settings.json."""
    path = target_path(target, CLAUDE_SETTINGS)
    try:
        text = with_git_guard(read(path))
    except ValueError as error:
        report.append(("conflict", f"{CLAUDE_SETTINGS} ({error}: add the PreToolUse hook for Bash running "
                                   ".claude/hooks/git-guard.py by hand)"))
        return
    if text is None:
        report.append(("kept", CLAUDE_SETTINGS))
    else:
        emit(CLAUDE_SETTINGS, text)


def write_seeds(target, seeds, names, crlf, emit, report):
    existing = is_existing_repository(target)
    for rel, src in sorted(seeds.items()):
        skipped = seed_skip_reason(target, rel, names, existing)
        if rel == CLAUDE_SETTINGS and skipped and skipped[0] == "kept":
            merge_git_guard(target, emit, report)
        elif skipped:
            report.append(skipped)
        else:
            emit(rel, seed_text(rel, src, crlf))


def print_report(report, unknown, references, dry_run):
    for status, rel in report:
        if status != "unchanged":
            print(f"{status:10} {rel}")
    print(f"\n{sum(1 for s, _ in report if s == 'unchanged')} files unchanged.")
    if unknown:
        print("\nNot part of the template (review: migrate, keep as project-specific, or delete):")
        for rel in unknown:
            print(f"  {rel}")
    if references:
        print("\nReferences to removed files - fix by hand (link the replacement or drop the line):")
        for path, number, text in references:
            print(f"  {path}:{number}: {text[:120]}")
    if dry_run:
        print("\nDry run: nothing was written.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", required=True)
    parser.add_argument("--profile", action="append", choices=PROFILES,
                        help="stack profile; repeat for a repository with several (the first is the primary). "
                             "Default: the profile(s) recorded in .squad/template.json")
    parser.add_argument("--reset-profiles", action="store_true",
                        help="accept a --profile set that differs from the one recorded in .squad/template.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = target_root(args.target)
    names = profile_names(args, recorded_profiles(target))
    profile_dirs = [os.path.join(ROOT, "profiles", name) for name in names]
    stack = combine_stack_blocks([(name, blocks(read(os.path.join(directory, "instructions.md")), "stack"))
                                  for name, directory in zip(names, profile_dirs, strict=True)])
    crlf = uses_crlf(target, profile_dirs)
    report = []

    core, managed = managed_files(profile_dirs, names)
    legacy = legacy_rules(target, read(core[CLAUDE]), args.dry_run, report)
    eols = eol_attributes(target, [*managed, *MARKED, *GENERATED, TEMPLATE_JSON])

    def emit(rel, text):
        write(target, rel, text, crlf_for(rel, eols, crlf), args.dry_run, report)

    for rel, src in sorted(managed.items()):
        emit(rel, read(src))
    rebuilt = write_marked(target, core, legacy, stack, emit, args.dry_run, report)
    write_generated(target, core, rebuilt[RULES], emit, args.dry_run, report)

    seeds = seed_files(profile_dirs, names, report)
    eols.update(eol_attributes(target, seeds))
    write_seeds(target, seeds, names, crlf, emit, report)

    retire(target, args.dry_run, report)
    references = retired_references(target)

    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=False).stdout.strip()
    record = json.dumps({"repository": TEMPLATE_REPOSITORY, "commit": commit, "profile": names[0],
                         "profiles": names}, indent=2) + "\n"
    emit(TEMPLATE_JSON, record)

    known = set(managed) | set(seeds) | {TEMPLATE_JSON}
    unknown = sorted(f"{d}/{rel}" for d in OWNED_DIRS for rel in files_under(os.path.join(target, d))
                     if f"{d}/{rel}" not in known)
    print_report(report, unknown, references, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
