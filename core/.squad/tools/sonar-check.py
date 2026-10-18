#!/usr/bin/env python3
"""Sonar gate: the CI code analysis (SonarQube Cloud) read as a check, so its findings are a gate result
instead of a surprise after the pull request, and a rule the local analyzers do not know is no squad lesson.

Two modes:

- `branch -- <scan command>` (step 7, before the pull request): needs `SONAR_TOKEN` in the environment.
  Runs the scan command (*Sonar scan* in `.squad/stack.md`: the stack's scanner, analysing the work branch as
  a branch of the project), waits for SonarQube to process the report, and lists every open issue and
  security hotspot on a line this branch added or changed since the merge base with BASE_REF. Without a token,
  or when the scan fails (a network policy that blocks the scanner's download hosts, for example), the result
  is NOT CHECKED: the pull request mode below then runs on the draft pull request instead.
- `pr <number>` (step 11, on the draft pull request): no token needed for a public project. Reads the
  analysis of that pull request and checks that it belongs to the current head (`HEAD`, or `--head <sha>`); an
  analysis of an earlier head is PENDING, never a pass. Then lists the quality gate status, the open issues and
  the security hotspots to review.

The project comes from `SONAR_PROJECT_KEY` in `.squad/tools/squad_settings.py`, else `sonar.projectKey` in
`sonar-project.properties`, else the `/k:"…"` argument of the scanner in a workflow under `.github/workflows/`;
the server from `SONAR_HOST` (default https://sonarcloud.io).

Every finding is printed as `rule path:line message` and fixed like an analyzer diagnostic. A rule that no local
analyzer reports is noted in the *Analyzer gate* section of `.squad/stack.md` (project knowledge, in the same
change), not filed as a squad lesson: with this gate it no longer reaches the pull request unseen.

Usage, from the repository root:
    python3 .squad/tools/sonar-check.py branch -- <scan command and arguments>
    python3 .squad/tools/sonar-check.py pr <number> [--head <sha>]

Exit code 0 clean, 1 findings or a failed quality gate, 2 NOT CHECKED (no token, no project key, scan failed),
3 PENDING (the analysis of this head is not there yet: wait and run again).
"""
import argparse
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyzer_common import git, merge_base, settings  # noqa: E402  (shared helpers next to this script)

CLEAN, FINDINGS, NOT_CHECKED, PENDING = 0, 1, 2, 3
HOST = getattr(settings, "SONAR_HOST", "https://sonarcloud.io").rstrip("/")
REPORT_TASKS = [".scannerwork/report-task.txt", ".sonarqube/out/.sonar/report-task.txt"]
SCAN_DIRS = [".scannerwork", ".sonarqube"]
WAIT_SECONDS = 600
PAGE_SIZE = 500
KEY_ARGUMENT = re.compile(r'/k:"?([\w.:-]+)"?')


def project_key():
    """The SonarQube project key, or None when no source names one."""
    key = getattr(settings, "SONAR_PROJECT_KEY", "")
    if key:
        return key
    if os.path.isfile("sonar-project.properties"):
        with open("sonar-project.properties", encoding="utf-8") as handle:
            for line in handle:
                name, _, value = line.partition("=")
                if name.strip() == "sonar.projectKey" and value.strip() and "{{" not in value:
                    return value.strip()
    for workflow in sorted(glob.glob(".github/workflows/*.y*ml")):
        with open(workflow, encoding="utf-8") as handle:
            match = KEY_ARGUMENT.search(handle.read())
        if match and "{{" not in match.group(1):
            return match.group(1)
    return None


def api(path, params, token=None):
    """GET a SonarQube Web API endpoint and return the decoded JSON."""
    url = f"{HOST}/api/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)  # noqa: S310  (fixed https host from the settings)
    if token:
        request.add_header("Authorization", "Basic " + base64.b64encode(f"{token}:".encode()).decode())
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return json.load(response)


def paged(path, params, field, token=None):
    """Every item of a paged list endpoint."""
    items, page = [], 1
    while True:
        data = api(path, {**params, "p": page, "ps": PAGE_SIZE}, token)
        items += data.get(field, [])
        total = data.get("paging", {}).get("total", data.get("total", 0))
        if page * PAGE_SIZE >= total:
            return items
        page += 1


def file_of(component, key):
    return component[len(key) + 1:] if component.startswith(key + ":") else component


def finding_line(item, key, kind):
    """`rule path:line message` for an issue or a hotspot."""
    path = file_of(item.get("component", ""), key)
    line = item.get("line") or item.get("textRange", {}).get("startLine") or "-"
    rule = item.get("rule") or item.get("ruleKey") or kind
    return f"{rule} {path}:{line} {item.get('message', '')}".rstrip()


def changed_lines():
    """{path: set(line numbers)} added or changed since the merge base, working tree included."""
    diff = git("diff", "-U0", merge_base())
    result, current = {}, None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            current = path[2:] if path.startswith("b/") else None
            if current:
                result.setdefault(current, set())
        elif line.startswith("@@") and current:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, count = int(match.group(1)), int(match.group(2) or "1")
            result[current].update(range(start, start + count))
    return result


def on_changed_line(item, key, lines):
    """True when the finding sits on a changed line, or is a file-level finding of a changed file."""
    path = file_of(item.get("component", ""), key)
    if path not in lines:
        return False
    line = item.get("line") or item.get("textRange", {}).get("startLine")
    return line is None or line in lines[path]


def report(findings, gate=None):
    """Print the result and return the exit code."""
    for finding in findings:
        print(finding)
    if gate and gate != "OK":
        print(f"Quality gate: {gate}")
    if findings or (gate and gate != "OK"):
        print(f"FAIL: {len(findings)} finding(s). Fix them like analyzer diagnostics; a rule no local analyzer "
              "reports is noted in the *Analyzer gate* section of .squad/stack.md.")
        return FINDINGS
    print("PASS: no new SonarQube issue or hotspot" + (" and the quality gate passed" if gate else ""))
    return CLEAN


def check_pr(key, number, head):
    """The analysis of the pull request, matched to the head."""
    analyses = api("project_pull_requests/list", {"project": key}).get("pullRequests", [])
    analysis = next((a for a in analyses if a.get("key") == str(number)), None)
    analysed = (analysis or {}).get("commit", {}).get("sha", "")
    if not analysis or analysed != head:
        print(f"PENDING: SonarQube has no analysis of pull request {number} at {head[:12]} yet"
              + (f" (latest: {analysed[:12]})" if analysed else "") + "; wait and run again.")
        return PENDING
    gate = api("qualitygates/project_status", {"projectKey": key, "pullRequest": number})["projectStatus"]["status"]
    issues = paged("issues/search", {"componentKeys": key, "pullRequest": number, "resolved": "false"}, "issues")
    hotspots = paged("hotspots/search", {"projectKey": key, "pullRequest": number, "status": "TO_REVIEW"},
                     "hotspots")
    return report([finding_line(i, key, "issue") for i in issues]
                  + [finding_line(h, key, "hotspot") for h in hotspots], gate)


def ce_task_id():
    for path in REPORT_TASKS:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    name, _, value = line.strip().partition("=")
                    if name == "ceTaskId":
                        return value
    return None


def wait_for_task(task, token):
    """Wait until SonarQube has processed the uploaded report; return its final status."""
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        status = api("ce/task", {"id": task}, token)["task"]["status"]
        if status not in ("PENDING", "IN_PROGRESS"):
            return status
        time.sleep(5)
    return "TIMEOUT"


def scan(command):
    """Run the scan command; return the CE task id, or None when the scan failed."""
    left_behind = [d for d in SCAN_DIRS if not os.path.exists(d)]
    try:
        result = subprocess.run(command, check=False)  # the command line of *Sonar scan* in .squad/stack.md
        return ce_task_id() if result.returncode == 0 else None
    finally:
        for directory in left_behind:  # leave no untracked scanner output behind
            shutil.rmtree(directory, ignore_errors=True)


def check_branch(key, command, token):
    if not command:
        sys.exit("branch mode needs the scan command after `--` (*Sonar scan* in .squad/stack.md)")
    task = scan(command)
    if not task:
        print("NOT CHECKED: the scan failed or wrote no report (output above); check the draft pull request "
              "with `sonar-check.py pr <number>` in step 11 instead.")
        return NOT_CHECKED
    status = wait_for_task(task, token)
    if status != "SUCCESS":
        print(f"NOT CHECKED: SonarQube processed the report with status {status}.")
        return NOT_CHECKED
    branch = git("branch", "--show-current").strip()
    lines = changed_lines()
    issues = paged("issues/search", {"componentKeys": key, "branch": branch, "resolved": "false"}, "issues", token)
    hotspots = paged("hotspots/search", {"projectKey": key, "branch": branch, "status": "TO_REVIEW"},
                     "hotspots", token)
    return report([finding_line(i, key, "issue") for i in issues if on_changed_line(i, key, lines)]
                  + [finding_line(h, key, "hotspot") for h in hotspots if on_changed_line(h, key, lines)])


def parse(argv):
    parser = argparse.ArgumentParser(description="SonarQube Cloud findings as a gate result.")
    modes = parser.add_subparsers(dest="mode", required=True)
    branch = modes.add_parser("branch", help="scan the work branch (needs SONAR_TOKEN)")
    branch.add_argument("command", nargs=argparse.REMAINDER, help="-- followed by the *Sonar scan* command")
    pr = modes.add_parser("pr", help="check the analysis of a pull request")
    pr.add_argument("number", type=int)
    pr.add_argument("--head", help="commit SHA the analysis must belong to (default: HEAD)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse(argv)
    key = project_key()
    if not key:
        print("NOT CHECKED: no SonarQube project key (SONAR_PROJECT_KEY in .squad/tools/squad_settings.py, "
              "sonar.projectKey in sonar-project.properties or /k: in a workflow).")
        return NOT_CHECKED
    try:
        if args.mode == "pr":
            head = args.head or git("rev-parse", "HEAD").strip()
            return check_pr(key, args.number, head)
        token = os.environ.get("SONAR_TOKEN", "")
        if not token:
            print("NOT CHECKED: SONAR_TOKEN is not set in this environment; check the draft pull request with "
                  "`sonar-check.py pr <number>` in step 11 instead.")
            return NOT_CHECKED
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        return check_branch(key, command, token)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as error:
        print(f"NOT CHECKED: SonarQube could not be read ({error}).")
        return NOT_CHECKED


if __name__ == "__main__":
    sys.exit(main())
