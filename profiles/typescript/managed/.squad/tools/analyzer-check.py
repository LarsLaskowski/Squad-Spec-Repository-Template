#!/usr/bin/env python3
"""Analyzer gate (TypeScript profile): the type check (`tsc --noEmit`) must pass for the whole repository, and
ESLint — configured with typescript-eslint's type-aware rules and eslint-plugin-sonarjs, so the SonarQube rules
run locally — must report nothing, at any severity, in a file changed since the merge base with origin/main
(working tree and untracked files included). A changed file the TypeScript project does not include is a
parse finding of its own (typescript-eslint's `projectService` cannot type it), so it fails the gate too.

The base (origin/main), the npm scripts and the linted extensions are fixed here and in
`.squad/tools/squad_settings.py`: the script accepts one flag, `--lint-only` (the lint pass over changed shell
scripts, workflows and Dockerfiles without the type check and ESLint, for a `patch` that touches no
TypeScript — `.squad/routing.md`, *Gates of a patch*), and no value, so nothing user-supplied reaches the
shell, git or the filesystem.

Usage, from the repository root (after `npm ci`):
    python3 .squad/tools/analyzer-check.py [--lint-only]

Exit code 0 when the type check passes and no changed file has a finding, 1 otherwise.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squad_settings as settings  # noqa: E402  (per-repository settings next to this script)
from analyzer_common import git, merge_base, lint_check, lint_only_requested, lint_only_main  # noqa: E402  (shared helpers next to this script)



def changed_files():
    base = merge_base()
    names = git("diff", "--name-only", "--diff-filter=d", base).splitlines()
    names += git("ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({n.strip() for n in names
                   if n.strip().endswith(tuple(settings.LINT_EXTENSIONS)) and os.path.isfile(n.strip())})


def run_check_scripts():
    """Run every npm script of CHECK_SCRIPTS; return True when all of them pass."""
    passed = True
    for script in settings.CHECK_SCRIPTS:
        result = subprocess.run(["npm", "run", "--silent", script], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print((result.stdout + result.stderr)[-4000:])
            print(f"npm run {script}: FAIL")
            passed = False
        else:
            print(f"npm run {script}: PASS")
    return passed


def eslint_findings(files):
    """ESLint's messages for the changed files, one line each; None when ESLint produced no JSON report."""
    if not files:
        return []
    lint = subprocess.run(["npx", "--no-install", "eslint", "--format", "json", "--no-warn-ignored", "--", *files],
                          capture_output=True, text=True, check=False)
    try:
        report = json.loads(lint.stdout or "[]")
    except json.JSONDecodeError:
        print(lint.stdout[-4000:] + lint.stderr[-4000:])
        return None
    findings = []
    for entry in report:
        path = os.path.relpath(entry["filePath"]).replace(os.sep, "/")
        for message in entry.get("messages", []):
            level = "error" if message.get("severity") == 2 else "warning"
            findings.append(f"{path}({message.get('line', 0)}): {level} {message.get('ruleId') or 'parse'}: "
                            f"{message.get('message', '')}")
    return findings


def main():
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    if lint_only_requested():
        return lint_only_main()
    scripts_passed = run_check_scripts()
    files = changed_files()
    findings = eslint_findings(files)
    if findings is None:
        print("ESLint did not produce a JSON report - is it installed and configured?")
        return 1
    for finding in findings:
        print(finding)
    print(f"\nChanged files linted: {len(files)}")
    print(f"Findings in changed files: {len(findings)}")
    ok = lint_check() and scripts_passed and not findings
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
