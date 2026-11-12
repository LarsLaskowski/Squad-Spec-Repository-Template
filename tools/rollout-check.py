#!/usr/bin/env python3
"""Rehearse a rollout before the release: apply this checkout of the template to a scratch copy of every active
consumer's `main` and run there what a refresh runs (`AGENTS.md`, *Releases*; `README.md`, *Rolling out a change*).

A refresh that stops on something the release brought — a check that fails in the target, a reference to a file the
release removed, a seed the merge cannot combine, a seeded file whose change has to be carried over by hand — is found
here, before the tag, instead of in five refresh pull requests and a fix release after them. For each `active`
consumer of `consumers.json` it:

1. finds the consumer's clone (by default the folder of the repository's name next to this one; `--target
   OWNER/NAME=PATH` names another), fetches `main` and the tags, and unshallows a shallow clone, so the decision
   records' freeze check sees the release tags;
2. checks out `origin/main` in a scratch copy (a shared clone; the clone's own working tree is not touched) and reads the
   template commit and profiles its `.squad/template.json` records;
3. runs `tools/apply-template.py --target <copy>` from this checkout, then the target's
   `.squad/tools/config-check.py` (which runs `decision-check.py`) on the result;
4. reports as findings: a failing apply step or `config-check.py`, a `conflict` seed, a line that still refers to a
   removed file, a `.github/release.yml` that does not leave the label `ignore-for-release` (which the refresh's pull
   request carries) out of the release notes; and lists, without failing, the files in template-owned folders the
   template does not know and the seeded files this checkout changed since the recorded commit — the target keeps its
   own copy of those, so the refresh carries the change over by hand (`adopt-template` step 1);
5. for a consumer with the `dotnet` profile, runs what its first refresh to the shared rule baseline runs:
   `dotnet-rules.py` (a refusal is a finding), `sonar-rules.py` (no SonarQube Cloud access is a note) and
   `dotnet_config.py`, whose findings it lists as what the refresh fixes by hand; with `--build` it then restores and
   builds the solution (`SOLUTION` of its `squad_settings.py`) with every rule lowered to a warning, so the build
   gets through, and lists the diagnostics per rule: each rule the refresh does not fix gets an issue and a
   `DOTNET_RULES_PENDING` entry there. A build that fails anyway (a compiler error) is a finding.

The scratch copy is removed afterwards. Nothing is committed, pushed or posted.

Usage, from the template repository's root, on the commit to be released (before `release.py prepare`):
    python3 tools/rollout-check.py                         # every active consumer, clones next to this repository
    python3 tools/rollout-check.py --target LarsLaskowski/Vandox=../Vandox [--no-fetch] [--build]

Exit code 0 when no consumer has a finding, 1 otherwise (a consumer without a clone is a finding: the rehearsal covers
every active consumer, or names the one it skipped with `--skip OWNER/NAME`).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSUMERS = os.path.join(ROOT, "consumers.json")
APPLY = os.path.join(ROOT, "tools", "apply-template.py")
SQUAD_DIR = ".squad"
TEMPLATE_JSON = os.path.join(SQUAD_DIR, "template.json")
CONFIG_CHECK = os.path.join(SQUAD_DIR, "tools", "config-check.py")
SEED_ROOTS = ("seed", "decision-seeds")
REFERENCES = "References to removed files"
UNKNOWN = "Not part of the template"
SECTION_END = re.compile(r"^\S")
TAIL_LINES = 15
COMMAND_TIMEOUT = 600
BUILD_TIMEOUT = 3600
TOOLS_DIR = os.path.join(SQUAD_DIR, "tools")
DOTNET_RULES = os.path.join(TOOLS_DIR, "dotnet-rules.py")
SONAR_RULES = os.path.join(TOOLS_DIR, "sonar-rules.py")
DOTNET_CONFIG = os.path.join(TOOLS_DIR, "dotnet_config.py")
SETTINGS = os.path.join(TOOLS_DIR, "squad_settings.py")
SOLUTION = re.compile(r'^SOLUTION\s*=\s*"([^"]+)"', re.M)
SARIF_NAME = "rollout-check.sarif"
BUILD_PROPERTIES = ["-p:TreatWarningsAsErrors=false", "-p:EnforceCodeStyleInBuild=true",
                    "-p:AnalysisLevel=latest-recommended", f"-p:ErrorLog=obj/{SARIF_NAME}%2Cversion=2.1"]
ERROR_SEVERITY = re.compile(r"(?P<head>[=:] ?)error(?=[ \t]*\r?$)", re.M)
TOP_RULES = 30
RELEASE_YML = os.path.join(".github", "release.yml")
RELEASE_LABEL = "ignore-for-release"


def run(args, cwd=None, timeout=COMMAND_TIMEOUT):
    """(exit code, standard output and error) of a command; exit code 1 when it cannot be started or times out."""
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
                              env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return done.returncode, done.stdout + done.stderr


def git(repo, *args):
    return run(["git", "-C", repo, *args])


def active_consumers(path=CONSUMERS):
    """The repositories (`owner/name`) of the active consumers in `consumers.json`."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return [entry["repository"] for entry in data.get("consumers", []) if entry.get("status") == "active"]


def clone_paths(consumers, targets):
    """{repository: clone path}: `--target` entries first, else the folder of the repository's name next to ROOT."""
    named = {}
    for entry in targets:
        repository, _, path = entry.partition("=")
        named[repository.lower()] = os.path.abspath(path)
    parent = os.path.dirname(ROOT)
    return {repo: named.get(repo.lower(), os.path.join(parent, repo.split("/")[-1])) for repo in consumers}


def fetch(clone):
    """Fetch `main` and the tags into the clone, unshallowing it; the problem, or None."""
    code, out = git(clone, "rev-parse", "--is-shallow-repository")
    options = ["--unshallow"] if code == 0 and out.strip() == "true" else []
    code, out = git(clone, "fetch", "--quiet", "--tags", *options, "origin", "main")
    return None if code == 0 else f"git fetch origin main failed: {tail(out)}"


def tail(text, lines=TAIL_LINES):
    kept = [line for line in text.strip().splitlines() if line.strip()]
    return "\n      ".join(kept[-lines:]) if kept else "(no output)"


def recorded(target):
    """(commit, profiles) from the target's `.squad/template.json`, or (None, []) without one."""
    try:
        with open(os.path.join(target, TEMPLATE_JSON), encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None, []
    return data.get("commit"), data.get("profiles") or [data.get("profile")]


def section(output, title):
    """The indented lines below a heading of the apply step's report that starts with `title`."""
    lines, inside = [], False
    for line in output.splitlines():
        if line.startswith(title):
            inside = True
        elif inside and (not line.strip() or SECTION_END.match(line)):
            inside = False
        elif inside:
            lines.append(line.strip())
    return lines


def conflicts(output):
    return [line.split(None, 1)[1] for line in output.splitlines() if line.startswith("conflict ")]


def changed_seeds(commit, profiles):
    """The seeded files this checkout changed since `commit` (working tree included); None when the commit is unknown
    here (fetch the template's history)."""
    if not commit or git(ROOT, "cat-file", "-e", f"{commit}^{{commit}}")[0] != 0:
        return None
    paths = [*SEED_ROOTS, *(os.path.join("profiles", name, "seed") for name in profiles if name)]
    code, out = git(ROOT, "-c", "core.quotePath=false", "diff", "--name-only", commit, "--", *paths)
    return sorted(line for line in out.splitlines() if line) if code == 0 else None


def excludes_release_label(text):
    """Whether a `release.yml` leaves pull requests labelled RELEASE_LABEL out of the generated release notes."""
    in_exclude = in_labels = False
    for line in text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped.startswith("exclude:"):
            in_exclude, in_labels = True, False
        elif in_exclude and stripped.startswith("labels:"):
            in_labels = True
            if RELEASE_LABEL in stripped:
                return True
        elif in_labels and stripped.startswith("- "):
            if stripped[2:].strip().strip("\"'") == RELEASE_LABEL:
                return True
        elif stripped:
            in_exclude = in_labels = False
    return False


def release_notes_findings(target):
    """The squad's own pull requests (labelled RELEASE_LABEL by adopt-template) stay out of the target's release notes."""
    path = os.path.join(target, RELEASE_YML)
    if not os.path.isfile(path):
        return [f"no {RELEASE_YML}: the seed was skipped, so the refresh's pull request would reach the release notes"]
    with open(path, encoding="utf-8-sig") as handle:
        excluded = excludes_release_label(handle.read())
    return [] if excluded else [f"{RELEASE_YML} does not exclude the label {RELEASE_LABEL} the refresh's pull request "
                                "carries: add it under changelog.exclude.labels"]


def solution_of(target):
    """The solution the target's gates build (`SOLUTION` of its `squad_settings.py`), or None."""
    try:
        with open(os.path.join(target, SETTINGS), encoding="utf-8") as handle:
            found = SOLUTION.search(handle.read())
    except OSError:
        return None
    return found.group(1) if found else None


def lower_errors(target):
    """The scratch copy's `.editorconfig` with every `error` severity a `warning`, so one rule does not stop the build
    of the projects after it and every rule is counted."""
    path = os.path.join(target, ".editorconfig")
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(ERROR_SEVERITY.sub(lambda found: found.group("head") + "warning", text))


def sarif_counts(target):
    """{rule id: diagnostics} of every SARIF log the build wrote, suppressed results left out."""
    counts = {}
    for folder, _, names in os.walk(target):
        if SARIF_NAME not in names:
            continue
        try:
            with open(os.path.join(folder, SARIF_NAME), encoding="utf-8-sig") as handle:
                runs = json.load(handle).get("runs", [])
        except (OSError, ValueError):
            continue
        for result in (result for run_ in runs for result in run_.get("results", []) if not result.get("suppressions")):
            counts[result.get("ruleId", "?")] = counts.get(result.get("ruleId", "?"), 0) + 1
    return counts


def build_rehearsal(target):
    """(findings, notes) of building the solution with the baseline: the diagnostics per rule."""
    solution = solution_of(target)
    if not solution or not os.path.isfile(os.path.join(target, solution)):
        return [f"no solution to build: SOLUTION in {SETTINGS} names {solution!r}"], []
    code, out = run(["dotnet", "restore", solution], cwd=target, timeout=BUILD_TIMEOUT)
    if code != 0:
        return [f"dotnet restore failed: {tail(out)}"], []
    lower_errors(target)
    code, out = run(["dotnet", "build", solution, "-c", "Release", "--no-restore", "--no-incremental", *BUILD_PROPERTIES],
                    cwd=target, timeout=BUILD_TIMEOUT)
    if code != 0:
        return [f"dotnet build failed with every rule a warning (a compiler error): {tail(out)}"], []
    counts = sorted(sarif_counts(target).items(), key=lambda item: (-item[1], item[0]))
    notes = [f"the build with the baseline reports {sum(n for _, n in counts)} diagnostic(s) of {len(counts)} rule(s); "
             "a rule the refresh does not fix gets an issue and a DOTNET_RULES_PENDING entry"]
    notes += [f"  {rule}: {number}" for rule, number in counts[:TOP_RULES]]
    if len(counts) > TOP_RULES:
        notes.append(f"  … and {len(counts) - TOP_RULES} more rule(s)")
    return [], notes


def config_drift(output):
    """The findings of `dotnet_config.py`, the settings outside the dotnet-rules block folded into one line."""
    found = [line.split(": ", 1)[1] for line in output.splitlines() if line.startswith(".NET config: ")]
    outside = [line.split(":", 2)[1] for line in found if "outside the dotnet-rules block" in line]
    kept = [line for line in found if "outside the dotnet-rules block" not in line]
    if outside:
        kept.append(f".editorconfig sets {len(outside)} rule(s) or code-style option(s) for every C# file outside the "
                    f"dotnet-rules block (lines {', '.join(outside[:12])}{', …' if len(outside) > 12 else ''}): they go")
    return kept


def dotnet_rehearsal(target, build):
    """(findings, notes) of the dotnet refresh's own steps on the scratch copy."""
    findings, notes = [], []
    code, out = run([sys.executable, DOTNET_RULES], cwd=target)
    if code != 0:
        findings.append(f"dotnet-rules.py refuses the target: {tail(out)}")
    code, out = run([sys.executable, SONAR_RULES], cwd=target)
    if code == 2:
        notes.append(f"sonar-rules.py NOT CHECKED, its block keeps the severities it has: {tail(out, 2)}")
    elif code != 0:
        findings.append(f"sonar-rules.py failed: {tail(out)}")
    code, out = run([sys.executable, DOTNET_CONFIG], cwd=target)
    if code != 0:
        notes += [f"the refresh fixes by hand: {line}" for line in config_drift(out)]
    if build and not findings:
        more, built = build_rehearsal(target)
        findings, notes = findings + more, notes + built
    return findings, notes


def rehearse(target, build=False):
    """(findings, notes) of applying this checkout to the scratch copy and checking the result."""
    findings, notes = [], []
    commit, profiles = recorded(target)
    if commit is None:
        findings.append(f"no {TEMPLATE_JSON} on main: a first adoption is no refresh, rehearse it with adopt-template")
        return findings, notes
    code, out = run([sys.executable, APPLY, "--target", target], cwd=ROOT)
    if code != 0:
        return [f"apply-template.py failed: {tail(out)}"], notes
    findings += [f"seed conflict (merge by hand): {rel}" for rel in conflicts(out)]
    findings += [f"reference to a removed file: {line}" for line in section(out, REFERENCES)]
    notes += [f"not part of the template: {line}" for line in section(out, UNKNOWN)]
    code, check = run([sys.executable, CONFIG_CHECK], cwd=target)
    if code != 0:
        findings.append(f"config-check.py fails after the apply step: {tail(check)}")
    findings += release_notes_findings(target)
    seeds = changed_seeds(commit, profiles)
    if seeds is None:
        findings.append(f"the recorded template commit {commit[:12]} is not in this checkout: git fetch origin "
                        "--tags and run again")
    else:
        notes += [f"seeded file changed since {commit[:12]}, carry it over by hand: {rel}" for rel in seeds]
    if "dotnet" in profiles:
        more, extra = dotnet_rehearsal(target, build)
        findings, notes = findings + more, notes + extra
    return findings, notes


def check_consumer(clone, do_fetch, build=False):
    """(findings, notes) of one consumer's clone."""
    if git(clone, "rev-parse", "--git-dir")[0] != 0:
        return [f"no clone at {clone}: clone it there or pass --target OWNER/NAME=PATH"], []
    problem = fetch(clone) if do_fetch else None
    if problem:
        return [problem], []
    with tempfile.TemporaryDirectory(prefix="rollout-check-") as scratch:
        copy = os.path.join(scratch, "main")
        problem = scratch_copy(clone, copy)
        return ([problem], []) if problem else rehearse(copy, build)


def scratch_copy(clone, copy):
    """A shared clone of the consumer's clone at its `origin/main`, with the tags and `origin/main` set (the apply
    step backs files up under `.git/`, so a worktree, whose `.git` is a file, does not do); the problem, or None."""
    code, sha = git(clone, "rev-parse", "--verify", "origin/main^{commit}")
    if code != 0:
        return f"the clone has no origin/main: {tail(sha)}"
    for args in (["clone", "--quiet", "--shared", "--no-checkout", clone, copy], ["-C", copy, "checkout", "--quiet",
                 "--detach", sha.strip()], ["-C", copy, "update-ref", "refs/remotes/origin/main", sha.strip()]):
        code, out = run(["git", *args])
        if code != 0:
            return f"cannot make a scratch copy of origin/main ({args[-2]}): {tail(out)}"
    return None


def report(repository, findings, notes):
    print(f"## {repository}: {'FAIL' if findings else 'pass'}")
    for line in findings:
        print(f"  FINDING {line}")
    for line in notes:
        print(f"  NOTE    {line}")
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", action="append", default=[], metavar="OWNER/NAME=PATH",
                        help="the clone of a consumer, when it is not the folder of its name next to this repository")
    parser.add_argument("--skip", action="append", default=[], metavar="OWNER/NAME",
                        help="leave an active consumer out (named in the output)")
    parser.add_argument("--no-fetch", action="store_true", help="use the clones' origin/main as they are")
    parser.add_argument("--build", action="store_true",
                        help="dotnet consumers: build with the rule baseline and list the diagnostics per rule")
    args = parser.parse_args(argv)
    skipped = {name.lower() for name in args.skip}
    consumers = [repo for repo in active_consumers() if repo.lower() not in skipped]
    failed = []
    for repository, clone in clone_paths(consumers, args.target).items():
        findings, notes = check_consumer(clone, not args.no_fetch, args.build)
        report(repository, findings, notes)
        if findings:
            failed.append(repository)
    for name in args.skip:
        print(f"Skipped: {name}")
    print(f"Rollout check: {'FAIL in ' + ', '.join(failed) if failed else 'pass'} "
          f"({len(consumers)} consumer(s) rehearsed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
