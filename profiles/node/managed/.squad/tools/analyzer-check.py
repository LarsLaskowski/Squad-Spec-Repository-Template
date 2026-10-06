#!/usr/bin/env python3
"""Analyzer gate (Node/TypeScript profile): the type check must pass, and ESLint — configured with
eslint-plugin-sonarjs so the SonarQube rules run locally — must report nothing, at any severity, in a file
changed since the merge base with origin/main (working tree and untracked files included).

The base (origin/main), the npm scripts and the linted extensions are fixed here and in
`.squad/tools/squad_settings.py`: the script takes no arguments, so nothing user-supplied reaches the
shell, git or the filesystem.

Usage, from the repository root (after `npm ci`):
    python3 .squad/tools/analyzer-check.py

Exit code 0 when the type check passes and no changed file has a finding, 1 otherwise.
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squad_settings as settings  # noqa: E402  (per-repository settings next to this script)

BASE_REF = "origin/main"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def shell_check():
    """shellcheck on changed shell scripts when it is installed; says so when files are skipped (the gate
    does not analyse shell otherwise). Returns True when nothing failed."""
    merge_base = git("merge-base", BASE_REF, "HEAD").strip()
    names = git("diff", "--name-only", "--diff-filter=d", merge_base).splitlines()
    names += git("ls-files", "--others", "--exclude-standard").splitlines()
    files = sorted({n.strip() for n in names if n.strip().endswith(".sh") and os.path.isfile(n.strip())})
    if not files:
        return True
    if shutil.which("shellcheck") is None:
        print(f"shellcheck: NOT RUN (not installed) - {len(files)} changed shell script(s) are not analysed locally\n")
        return True
    result = subprocess.run(["shellcheck", "--", *files], capture_output=True, text=True, check=False)
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output[-6000:])
    print(f"shellcheck (changed shell scripts): {'PASS' if result.returncode == 0 else 'FAIL'}\n")
    return result.returncode == 0


def changed_files():
    merge_base = git("merge-base", BASE_REF, "HEAD").strip()
    names = git("diff", "--name-only", "--diff-filter=d", merge_base).splitlines()
    names += git("ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({n.strip() for n in names
                   if n.strip().endswith(tuple(settings.LINT_EXTENSIONS)) and os.path.isfile(n.strip())})


def main():
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    failed = False

    for script in settings.CHECK_SCRIPTS:
        result = subprocess.run(["npm", "run", "--silent", script], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print((result.stdout + result.stderr)[-4000:])
            print(f"npm run {script}: FAIL")
            failed = True
        else:
            print(f"npm run {script}: PASS")

    files = changed_files()
    findings = []
    if files:
        lint = subprocess.run(["npx", "--no-install", "eslint", "--format", "json", "--no-warn-ignored", "--", *files],
                              capture_output=True, text=True, check=False)
        try:
            report = json.loads(lint.stdout or "[]")
        except json.JSONDecodeError:
            print(lint.stdout[-4000:] + lint.stderr[-4000:])
            print("ESLint did not produce a JSON report - is it installed and configured?")
            return 1
        for entry in report:
            path = os.path.relpath(entry["filePath"]).replace(os.sep, "/")
            for message in entry.get("messages", []):
                level = "error" if message.get("severity") == 2 else "warning"
                findings.append(f"{path}({message.get('line', 0)}): {level} {message.get('ruleId') or 'parse'}: "
                                f"{message.get('message', '')}")
    for finding in findings:
        print(finding)
    print(f"\nChanged files linted: {len(files)}")
    print(f"Findings in changed files: {len(findings)}")
    ok = shell_check() and not failed and not findings
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
