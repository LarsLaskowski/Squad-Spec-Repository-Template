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
- **seed** files (`seed/` and `profiles/<profile>/seed/`) are written only when the target does not have
  them yet;
- **retired** files (`RETIRED` below) that an older template version wrote are removed from the target;
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
removed) and the files in template-owned folders of the target that the template does not know (old skills or
agents to review).
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
MARKED = [
    "CLAUDE.md",
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
OWNED_DIRS = [".claude/agents", ".claude/skills", ".agents/skills", ".github/skills", ".squad/agents", ".squad/tools"]
# Written by older template versions and removed on a refresh: the Codex and Copilot mirrors of the instruction file
# and of the template's skills (the squad runs on Claude Code subagents only), the squad's decisions.md and
# history.md files, which nothing read or wrote (process decisions are the records in docs/decisions/), and the
# charters, which now live in the subagent files under .claude/agents/.
RETIRED = ["AGENTS.md", ".github/copilot-instructions.md", ".squad/decisions.md"] + [
    f"{mirror}/{skill}/SKILL.md" for mirror in (".agents/skills", ".github/skills")
    for skill in ("create-pr", "review-pr", "squad-issue", "squad-spec", "decision-consolidate")] + [
    f".squad/agents/{role}/{name}"
    for role in ("code-officer", "dev", "devils-advocate", "lead", "reviewer", "security", "tester")
    for name in ("history.md", "charter.md")]
# Stored under another name here, because a .gitattributes inside this repository would apply to it.
RENAMES = {"gitattributes": ".gitattributes"}
BLOCK = re.compile(r"<!-- (project|stack):begin ([\w-]+) -->\n(.*?)<!-- \1:end \2 -->", re.S)


def recorded_profiles(target):
    """The profiles `.squad/template.json` of the target names: `profiles`, else `profile` plus the older
    `additionalProfiles`; empty when the file is missing or unreadable."""
    path = os.path.join(target, ".squad", "template.json")
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


def merge_stack_md(parts):
    intro = ("# Stack: " + " + ".join(name for name, _ in parts) + "\n\n"
             "This repository combines the stack profiles " + ", ".join(f"`{name}`" for name, _ in parts) + ". "
             "Every command name below (*Format*, *Build*, *Test*, *Analyzer gate*, …) exists once per profile, in the "
             "section of that profile; a gate is passed only when it passes for **every** profile. "
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


def merge_settings(profile_dirs):
    """squad_settings.py of a repository with several profiles: the union of the paths and one coverage report
    per profile; the primary profile's other settings (e.g. SOLUTION) come first."""
    modules = [load_settings(os.path.join(p, "seed", ".squad", "tools", "squad_settings.py")) for p in profile_dirs]
    names = [os.path.basename(p) for p in profile_dirs]

    def union(attr, default=()):
        result = []
        for module in modules:
            for value in getattr(module, attr, default):
                if value not in result:
                    result.append(value)
        return result

    lines = ['"""Per-repository settings for the squad tools (profiles: ' + ", ".join(names) + '). Seeded once by',
             'adopt-template and kept on later refreshes; the scripts that import it are template-managed."""', "",
             "# Base branch the gates diff against (merge base with HEAD); fetch it before running the gates.",
             f"BASE_REF = {getattr(modules[0], 'BASE_REF', 'origin/main')!r}", ""]
    for name, module in zip(names, modules, strict=True):
        if hasattr(module, "SOLUTION"):
            lines += [f"# Solution or project file the {name} analyzer gate builds.", f"SOLUTION = {module.SOLUTION!r}", ""]
    reports = [(m.COVERAGE_FORMAT, m.COVERAGE_REPORT_GLOB) for m in modules]
    tests = []
    for module in modules:
        for value in getattr(module, "COVERAGE_TEST_PATHSPECS", module.COVERAGE_EXCLUDES):
            if value not in tests:
                tests.append(value)
    lines += ["# Coverage gate (.squad/tools/coverage-check.py): one (format, glob) report per profile, merged.",
              "# COVERAGE_OVERALL_THRESHOLD may start below COVERAGE_THRESHOLD in a repository adopted with a coverage debt;",
              "# it is never lowered and is raised towards COVERAGE_THRESHOLD as coverage improves.",
              f"COVERAGE_THRESHOLD = {getattr(modules[0], 'COVERAGE_THRESHOLD', 80)!r}",
              f"COVERAGE_OVERALL_THRESHOLD = {getattr(modules[0], 'COVERAGE_OVERALL_THRESHOLD', 80)!r}",
              "COVERAGE_REPORTS = ["]
    lines += [f"    ({fmt!r}, {pattern!r})," for fmt, pattern in reports]
    lines += ["]",
              f"COVERAGE_PATHSPECS = {union('COVERAGE_PATHSPECS')!r}",
              f"COVERAGE_EXCLUDES = {union('COVERAGE_EXCLUDES')!r}",
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
    seen = {re.match(r"  - package-ecosystem: *(\S+)", c).group(1).strip('"') for c in chunks}
    for text in texts[1:]:
        for chunk in split_chunks(text, r"^  - package-ecosystem:")[1]:
            ecosystem = re.match(r"  - package-ecosystem: *(\S+)", chunk).group(1).strip('"')
            if ecosystem not in seen:
                seen.add(ecosystem)
                chunks[-1] = chunks[-1].rstrip("\n") + "\n\n"
                chunks.append(chunk)
    return head + "".join(chunks)


def merge_codeql(texts):
    """Matrix entries and the set-up steps before `Initialize CodeQL` of every profile, side by side."""
    initialize = re.compile(r"^      - name: Initialize CodeQL", re.M)

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
    taken = set(re.findall(r"^  ([\w-]+):", jobs, re.M))
    permissions = set(re.findall(r"^  ([\w-]+: \w+)$", head.split("permissions:", 1)[1].split("\n\n")[0], re.M))
    out = jobs.rstrip("\n") + "\n"
    for name, text in zip(names[1:], texts[1:], strict=True):
        other_head, other = text.split("\njobs:\n", 1)
        permissions |= set(re.findall(r"^  ([\w-]+: \w+)$", other_head.split("permissions:", 1)[1].split("\n\n")[0], re.M))
        for job in re.findall(r"^  ([\w-]+):", other, re.M):
            if job in taken:
                other = re.sub(rf"^  {re.escape(job)}:", f"  {name}-{job}:", other, flags=re.M)
                job = f"{name}-{job}"
            taken.add(job)
        out += "\n" + other.rstrip("\n") + "\n"
    block = "permissions:\n" + "".join(f"  {p}\n" for p in sorted(permissions))
    head = re.sub(r"permissions:\n(?:  .*\n)+", lambda _: block, head + "\n", count=1).rstrip("\n")
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
    path = os.path.join(target, ".gitattributes")
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
    dest = os.path.join(target, rel)
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
        path = os.path.join(target, rel)
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


def backup(target, rel, dry_run, report):
    dest = os.path.join(target, ".git", "adopt-template", "backup", rel)
    report.append(("backed-up", rel + " -> .git/adopt-template/backup/" + rel))
    if not dry_run:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(target, rel), dest)


def seed_files(profile_dirs, names, report):
    """The seed files of all profiles: {rel: text-or-path}. Paths that exist in several profiles are merged
    (MERGERS, stack.md, UNIT_TESTS.md, squad_settings.py); anything else keeps the primary profile's file."""
    sources = {}
    for profile in profile_dirs:
        for rel, src in files_under(os.path.join(profile, "seed")).items():
            sources.setdefault(rel, []).append((os.path.basename(profile), src))
    result = dict(files_under(os.path.join(ROOT, "seed")))
    for rel, found in sources.items():
        if len(found) == 1:
            result[rel] = found[0][1]
            continue
        texts = [read(src) for _, src in found]
        owners = [name for name, _ in found]
        if rel == ".squad/stack.md":
            result[rel] = merge_stack_md(list(zip(owners, texts, strict=True)))
        elif rel == "docs/UNIT_TESTS.md":
            result[rel] = merge_unit_tests(list(zip(owners, texts, strict=True)))
        elif rel == ".squad/tools/squad_settings.py":
            result[rel] = merge_settings([os.path.join(ROOT, "profiles", name) for name in names])
        elif rel in MERGERS:
            result[rel] = MERGERS[rel](texts, owners)
        else:
            result[rel] = found[0][1]
            report.append(("conflict", f"{rel} (in {', '.join(owners)}; kept the {owners[0]} version, merge by hand)"))
    return result


def managed_files(profile_dirs, names):
    """core/ (minus the marked files) plus every profile's managed files. With several profiles the files of
    the same name are written per profile (`analyzer-check-go.py`) next to the dispatcher from multi/."""
    core = files_under(os.path.join(ROOT, "core"))
    managed = {rel: src for rel, src in core.items() if rel not in MARKED}
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

    target = os.path.abspath(args.target)
    if not os.path.isdir(os.path.join(target, ".git")):
        sys.exit(f"{target} is not the root of a git repository")
    recorded = recorded_profiles(target)
    names = list(dict.fromkeys(args.profile or recorded))
    if not names:
        sys.exit("No profile: pass --profile (repeat it for several), the target has no .squad/template.json")
    unknown_profiles = [name for name in names if name not in PROFILES]
    if unknown_profiles:
        sys.exit(f".squad/template.json names profiles this template does not have: {', '.join(unknown_profiles)}")
    if args.profile and recorded and set(names) != set(recorded) and not args.reset_profiles:
        sys.exit(f"The target records the profiles {', '.join(recorded)}, but --profile names {', '.join(names)}: "
                 "refresh without --profile to keep the recorded ones, or add --reset-profiles to change them")
    profile_dirs = [os.path.join(ROOT, "profiles", name) for name in names]
    stack = combine_stack_blocks([(name, blocks(read(os.path.join(directory, "instructions.md")), "stack"))
                                  for name, directory in zip(names, profile_dirs, strict=True)])
    crlf = uses_crlf(target, profile_dirs)
    report = []

    core, managed = managed_files(profile_dirs, names)
    eols = eol_attributes(target, [*managed, *MARKED, ".squad/template.json"])
    for rel, src in sorted(managed.items()):
        write(target, rel, read(src), crlf_for(rel, eols, crlf), args.dry_run, report)

    for rel in MARKED:
        template = read(core[rel])
        dest = os.path.join(target, rel)
        current = read(dest) if os.path.isfile(dest) else ""
        project = blocks(current, "project")
        if current and not project:
            backup(target, rel, args.dry_run, report)
        write(target, rel, fill(template, project, stack), crlf_for(rel, eols, crlf), args.dry_run, report)

    seeds = seed_files(profile_dirs, names, report)
    eols.update(eol_attributes(target, seeds))
    existing = is_existing_repository(target)
    for rel, src in sorted(seeds.items()):
        if os.path.exists(os.path.join(target, rel)):
            report.append(("kept", rel))
        elif SEEDS_REFUSED_WITH.get(rel) in names:
            report.append(("skipped", f"{rel} (the profile {SEEDS_REFUSED_WITH[rel]} cannot use it: its Sonar scanner "
                                      "refuses a repository that has one and takes the settings as arguments)"))
        elif rel == ".gitattributes" and existing:
            # A new .gitattributes renormalizes line endings across the whole repository; that is a decision of
            # its own, not a side effect of adopting the squad.
            report.append(("skipped", rel + " (existing repository without one; add it in a change of its own)"))
        else:
            text = read(src) if os.path.isfile(src) else src
            if rel == ".editorconfig":
                text = re.sub(r"^(end_of_line\s*=\s*)(crlf|lf)[ \t]*$", r"\g<1>" + ("crlf" if crlf else "lf"), text,
                              flags=re.M)
            write(target, rel, text, crlf_for(rel, eols, crlf), args.dry_run, report)

    retire(target, args.dry_run, report)

    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=False).stdout.strip()
    record = json.dumps({"repository": TEMPLATE_REPOSITORY, "commit": commit, "profile": names[0],
                         "profiles": names}, indent=2) + "\n"
    write(target, ".squad/template.json", record, crlf_for(".squad/template.json", eols, crlf), args.dry_run, report)

    known = set(managed) | set(seeds) | {".squad/template.json"}
    unknown = sorted(f"{d}/{rel}" for d in OWNED_DIRS for rel in files_under(os.path.join(target, d))
                     if f"{d}/{rel}" not in known)

    for status, rel in report:
        if status != "unchanged":
            print(f"{status:10} {rel}")
    print(f"\n{sum(1 for s, _ in report if s == 'unchanged')} files unchanged.")
    if unknown:
        print("\nNot part of the template (review: migrate, keep as project-specific, or delete):")
        for rel in unknown:
            print(f"  {rel}")
    if args.dry_run:
        print("\nDry run: nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
