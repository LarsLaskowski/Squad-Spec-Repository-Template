#!/usr/bin/env python3
"""Releases of Squad-Spec-Repository-Template: a tag and a `CHANGELOG.md` section each (`AGENTS.md`, *Releases*).

`CHANGELOG.md` starts with an `## Unreleased` section: one line per pull request that changes what a target receives
(`core/`, `profiles/`, `multi/`, `seed/`, `decision-seeds/`, `tools/apply-template.py`). Below it one section per
release, newest first, headed `## vYYYY.MM.N — YYYY-MM-DD` (N counts the releases of that month).

    python3 tools/release.py check               # the format of CHANGELOG.md
    python3 tools/release.py prepare [--date D]  # on a release branch: Unreleased becomes the next version
    python3 tools/release.py tag [--create]      # on main, after the release PR's merge: the tag of its section

`prepare` rewrites `CHANGELOG.md` only and prints the version; the release pull request carries the change. `tag`
checks that the checkout is `origin/main` and that the newest version section has no tag yet, locally or on
`origin`, and prints the commands that set the annotated tag on that commit and push it; with `--create` it creates
the tag locally and prints the push command. A tag is created only with the owner's explicit approval (`AGENTS.md`,
*Golden rules*), so nothing here pushes.

Exit code 0, 1 on a finding or a refused step.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = "CHANGELOG.md"
UNRELEASED = "## Unreleased"
VERSION = re.compile(r"v(\d{4})\.(\d{2})\.(\d+)")
HEADING = re.compile(r"^## (?:(Unreleased)|(v\d{4}\.\d{2}\.\d+) — (\d{4}-\d{2}-\d{2}))[ \t]*$")
ENTRY = re.compile(r"^- \S")
REMOTE_TIMEOUT = 20


def sections(text):
    """[(heading line, body lines)] of every `## ` section, in order."""
    found = []
    for line in text.splitlines():
        if line.startswith("## "):
            found.append((line, []))
        elif found:
            found[-1][1].append(line)
    return found


def version_key(version):
    match = VERSION.fullmatch(version)
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def check_release(heading, match, body, previous):
    """Findings of one release section; `previous` is the version and date above it, or None."""
    version, date = match.group(2), match.group(3)
    errors = []
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError:
        return [f"{CHANGELOG}: '{heading}' has no valid date"]
    if version_key(version)[:2] != (day.year, day.month):
        errors.append(f"{CHANGELOG}: '{heading}' names another month than its date")
    if not any(ENTRY.match(line) for line in body):
        errors.append(f"{CHANGELOG}: '{heading}' lists no change")
    if previous and (version_key(version) >= version_key(previous[0]) or date > previous[1]):
        errors.append(f"{CHANGELOG}: '{heading}' is not older than the release above it (newest first)")
    return errors


def check(text):
    """The findings of the changelog's format: `## Unreleased` first, then release sections newest first, each with a
    valid heading, a date in its version's month and at least one change."""
    found = sections(text)
    if not found or found[0][0].strip() != UNRELEASED:
        return [f"{CHANGELOG}: the first section must be '{UNRELEASED}'"]
    errors, previous, seen = [], None, set()
    for heading, body in found[1:]:
        match = HEADING.match(heading)
        if not match or match.group(1):
            errors.append(f"{CHANGELOG}: '{heading}' is no release heading ('## vYYYY.MM.N — YYYY-MM-DD')")
            continue
        if match.group(2) in seen:
            errors.append(f"{CHANGELOG}: {match.group(2)} appears twice")
        seen.add(match.group(2))
        errors += check_release(heading, match, body, previous)
        previous = (match.group(2), match.group(3))
    return errors


def unreleased_entries(text):
    """The change lines of the `## Unreleased` section."""
    found = sections(text)
    if not found or found[0][0].strip() != UNRELEASED:
        return []
    return [line for line in found[0][1] if ENTRY.match(line)]


def releases(text):
    """[(version, date, body text)] of the release sections, newest first."""
    result = []
    for heading, body in sections(text):
        match = HEADING.match(heading)
        if match and match.group(2):
            result.append((match.group(2), match.group(3), "\n".join(body).strip()))
    return result


def next_version(text, tags, date):
    """The version of a release on `date`: `vYYYY.MM.N`, N one more than the highest of that month among the
    changelog's releases and the existing tags."""
    month = (date.year, date.month)
    known = [version for version, _, _ in releases(text)] + list(tags)
    counts = [version_key(version)[2] for version in known if version_key(version)[:2] == month]
    return f"v{date.year}.{date.month:02d}.{max(counts, default=0) + 1}"


def prepare(text, version, date):
    """The changelog with the `## Unreleased` entries moved into a new section of `version`; an empty
    `## Unreleased` stays on top."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == UNRELEASED)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = "\n".join(lines[start + 1:end]).strip("\n")
    head = "\n".join(lines[:start]).rstrip("\n")
    rest = "\n".join(lines[end:]).strip("\n")
    parts = [head, UNRELEASED, f"## {version} — {date.isoformat()}\n\n{body}"] + ([rest] if rest else [])
    return "\n\n".join(parts) + "\n"


def git(*args, root=ROOT):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=False)


def local_tags(root=ROOT):
    return git("tag", "--list", "v*", root=root).stdout.split()


def remote_has_tag(tag, root=ROOT):
    """True when `origin` has the tag, None when it cannot be asked (offline, no access), False otherwise."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(["git", "-C", root, "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
                                capture_output=True, text=True, env=env, timeout=REMOTE_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def read_changelog(root=ROOT):
    with open(os.path.join(root, CHANGELOG), encoding="utf-8") as handle:
        return handle.read()


def check_command(root=ROOT):
    errors = check(read_changelog(root))
    for error in errors:
        print(error)
    return 1 if errors else 0


def prepare_command(date, root=ROOT):
    text = read_changelog(root)
    errors = check(text)
    if errors or not unreleased_entries(text):
        for error in errors or [f"{CHANGELOG}: '{UNRELEASED}' lists no change; there is nothing to release"]:
            print(error)
        return 1
    version = next_version(text, local_tags(root), date)
    with open(os.path.join(root, CHANGELOG), "w", encoding="utf-8") as handle:
        handle.write(prepare(text, version, date))
    print(f"{CHANGELOG}: '{UNRELEASED}' became {version} — {date.isoformat()}. Open the release pull request "
          f"('[Docs] Release {version}'); after its merge, run 'python3 tools/release.py tag' on main.")
    return 0


def tag_refusal(root, version):
    """Why the newest release cannot be tagged on this checkout, or None."""
    head = git("rev-parse", "HEAD", root=root).stdout.strip()
    main = git("rev-parse", "origin/main", root=root).stdout.strip()
    if not head or head != main:
        return "the checkout is not origin/main: 'git fetch origin main' and check out the release PR's merge commit"
    if version in local_tags(root):
        return f"{version} exists already"
    remote = remote_has_tag(version, root)
    if remote is None:
        return "origin could not be asked for its tags"
    return f"origin has {version} already" if remote else None


def tag_command(create, root=ROOT):
    found = releases(read_changelog(root))
    if not found:
        print(f"{CHANGELOG}: no release section yet; run 'python3 tools/release.py prepare' in a release pull request")
        return 1
    version, date, body = found[0]
    refusal = tag_refusal(root, version)
    if refusal:
        print(f"Not tagged: {refusal}.")
        return 1
    message = f"Squad-Spec-Repository-Template {version} ({date})\n\n{body}\n"
    if create:
        created = git("tag", "-a", version, "-m", message, "HEAD", root=root)
        if created.returncode != 0:
            print(f"Not tagged: {created.stderr.strip()}")
            return 1
        print(f"Created the annotated tag {version} on HEAD. Push it with: git push origin {version}")
        return 0
    print(f"The release {version} ({date}) is not tagged yet. With the owner's approval:\n"
          f"    python3 tools/release.py tag --create\n    git push origin {version}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the changelog, prepare a release, or tag it.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check the format of CHANGELOG.md")
    prepared = commands.add_parser("prepare", help="turn the Unreleased section into the next version")
    prepared.add_argument("--date", type=datetime.date.fromisoformat, help="release date (default: today, UTC)")
    tagged = commands.add_parser("tag", help="the tag of the newest release section, on origin/main")
    tagged.add_argument("--create", action="store_true", help="create the annotated tag locally (never pushed)")
    args = parser.parse_args(argv)
    if args.command == "check":
        return check_command()
    if args.command == "prepare":
        return prepare_command(args.date or datetime.datetime.now(datetime.UTC).date())
    return tag_command(args.create)


if __name__ == "__main__":
    sys.exit(main())
