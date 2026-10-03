#!/usr/bin/env python3
"""Apply Squad-Spec-Repository-Template to a target repository: the mechanical half of the `adopt-template` skill.

What it does, for the chosen stack profile (`profiles/<profile>`):

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
- `.squad/template.json` records the template repository, its commit and the profile.

Line endings follow the target: CRLF when its `.gitattributes` sets `* text=auto eol=crlf` (a target without
one uses the `.gitattributes` the profile seeds), LF otherwise;
shell scripts always keep LF and the executable bit.

Usage, from the template repository's root:
    python3 tools/apply-template.py --target ../OtherRepo --profile dotnet [--dry-run]

Prints one line per file (created / updated / unchanged / kept / merged / backed-up) and the files in
template-owned folders of the target that the template does not know (old skills or agents to review).
"""
import argparse
import glob
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
    "AGENTS.md",
    ".github/copilot-instructions.md",
    "docs/CONTRIBUTING.md",
    "docs/ARCHITECTURE.md",
    "SECURITY.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    "docs/decisions/README.md",
]
OWNED_DIRS = [".claude/agents", ".claude/skills", ".agents/skills", ".github/skills", ".squad/agents", ".squad/tools"]
# Stored under another name here, because a .gitattributes inside this repository would apply to it.
RENAMES = {"gitattributes": ".gitattributes"}
BLOCK = re.compile(r"<!-- (project|stack):begin ([\w-]+) -->\n(.*?)<!-- \1:end \2 -->", re.S)


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


def uses_crlf(target, profile):
    """The target's own .gitattributes decides; without one, the profile's seeded one does."""
    path = os.path.join(target, ".gitattributes")
    if not os.path.isfile(path):
        path = os.path.join(profile, "seed", "gitattributes")
    return os.path.isfile(path) and re.search(r"^\*\s+text=auto\s+eol=crlf", read(path), re.M) is not None


def write(target, rel, text, crlf, dry_run, report, status_if_new="created"):
    dest = os.path.join(target, rel)
    if rel.endswith(".sh"):
        crlf = False
    data = (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")
    old = None
    if os.path.isfile(dest):
        with open(dest, "rb") as existing:
            old = existing.read()
    status = status_if_new if old is None else ("unchanged" if old == data else "updated")
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


def backup(target, rel, dry_run, report):
    dest = os.path.join(target, ".git", "adopt-template", "backup", rel)
    report.append(("backed-up", rel + " -> .git/adopt-template/backup/" + rel))
    if not dry_run:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(target, rel), dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", required=True)
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.isdir(os.path.join(target, ".git")):
        sys.exit(f"{target} is not the root of a git repository")
    profile = os.path.join(ROOT, "profiles", args.profile)
    stack = blocks(read(os.path.join(profile, "instructions.md")), "stack")
    crlf = uses_crlf(target, profile)
    report = []

    core = files_under(os.path.join(ROOT, "core"))
    managed = {rel: src for rel, src in core.items() if rel not in MARKED}
    managed.update(files_under(os.path.join(profile, "managed")))
    for rel, src in sorted(managed.items()):
        write(target, rel, read(src), crlf, args.dry_run, report)

    for rel in MARKED:
        template = read(core[rel])
        dest = os.path.join(target, rel)
        current = read(dest) if os.path.isfile(dest) else ""
        project = blocks(current, "project")
        if current and not project:
            backup(target, rel, args.dry_run, report)
        write(target, rel, fill(template, project, stack), crlf, args.dry_run, report)

    seeds = files_under(os.path.join(ROOT, "seed"))
    seeds.update(files_under(os.path.join(profile, "seed")))
    for rel, src in sorted(seeds.items()):
        if os.path.exists(os.path.join(target, rel)):
            report.append(("kept", rel))
        else:
            write(target, rel, read(src), crlf, args.dry_run, report)

    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=False).stdout.strip()
    record = json.dumps({"repository": TEMPLATE_REPOSITORY, "commit": commit, "profile": args.profile}, indent=2) + "\n"
    write(target, ".squad/template.json", record, crlf, args.dry_run, report)

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
