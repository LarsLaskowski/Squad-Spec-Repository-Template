#!/usr/bin/env python3
"""Quality report of the squad runs in the repositories that use this template: what happened to each pull
request after it was opened, read from GitHub and SonarQube Cloud instead of from the runs' own logs.

For every pull request merged in the window it reports:

- **kind** — `squad` (its issue or the PR carries a "Squad working record" comment), `refresh` (a template
  refresh: "Update the squad from …"), `dependabot`, or `manual`;
- **tier**, **launches** and **tokens** of a squad run, read from its working record and "Squad run metrics";
- **fix pushes** — commits pushed after the PR was opened, merges of the base branch counted apart;
- **CI failures** — failed or timed-out check runs on those commits;
- **Sonar** — the SonarQube Cloud issues ever raised on the pull request (fixed ones included), when the
  repository's project key is given;
- **bot** and **human** review comments, and the hours from opening to merge.

The totals per repository and week show what the squad's rules changed: the share of squad pull requests that
needed no fix push, that SonarQube found nothing on, the CI failures per pull request, and the median tokens per
tier. Follow-up defects (a later fix of code a run wrote) are not detectable this way and stay a reading task.

Usage (needs `gh` with read access to the repositories):
    python3 tools/squad-report.py --repo LarsLaskowski/Vandox=networlddev_vandox --repo LarsLaskowski/Seluna \\
        --since 2026-10-11 [--until 2026-10-18] [--out report.md]

`owner/name=sonar-key` adds the SonarQube Cloud project key of that repository. Exit code 0, or 1 when GitHub
cannot be read.
"""
import argparse
import datetime
import json
import re
import statistics
import subprocess
import sys
import urllib.parse
import urllib.request

SONAR = "https://sonarcloud.io/api"
TIER = re.compile(r"\btier\b[:*\s`]*(patch/security|docs|patch|trivial|standard|security)\b", re.I)
TOTAL = re.compile(r"^\|\s*\*\*Total\*\*\s*\|[^|]*\|\s*(\d+)[^|]*\|\s*([\d,]+)\s*\|", re.M)
CLOSES = re.compile(r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.I)
FAILED = {"failure", "timed_out"}


PER_PAGE = 100


def gh(path):
    """GET a GitHub API path through `gh api`."""
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(result.stdout or "null")


def gh_list(path, stop=None):
    """Every item of a list endpoint, page by page (`gh api --paginate` follows links by repository id, which some
    proxies refuse); `stop(item)` ends the walk early, for a list sorted newest first."""
    items, page = [], 1
    separator = "&" if "?" in path else "?"
    while True:
        batch = gh(f"{path}{separator}per_page={PER_PAGE}&page={page}") or []
        for item in batch:
            if stop and stop(item):
                return items
            items.append(item)
        if len(batch) < PER_PAGE:
            return items
        page += 1


def sonar_issues(key, number):
    """How many issues SonarQube Cloud raised on the pull request, fixed ones included; None when unreadable."""
    query = urllib.parse.urlencode({"componentKeys": key, "pullRequest": number, "ps": 1})
    try:
        with urllib.request.urlopen(f"{SONAR}/issues/search?{query}", timeout=30) as response:  # noqa: S310  # nosec B310
            return json.load(response).get("total", 0)
    except (OSError, ValueError):
        return None


def parse_record(comments):
    """(tier, launches, tokens) from the "Squad working record" and "Squad run metrics" comments."""
    text = "\n".join(c.get("body") or "" for c in comments)
    if "Squad working record" not in text:
        return None
    tier = TIER.search(text)
    total = TOTAL.search(text)
    return (tier.group(1).lower() if tier else None,
            int(total.group(1)) if total else None,
            int(total.group(2).replace(",", "")) if total else None)


def classify(pr, record):
    title = pr.get("title", "")
    if record is not None:
        return "squad"
    if "Update the squad from" in title:
        return "refresh"
    if (pr.get("user") or {}).get("login", "").startswith("dependabot"):
        return "dependabot"
    return "manual"


def pushes_after_open(commits, opened):
    """(fix pushes, merges of the base) among the commits dated after the pull request was opened."""
    later = [c for c in commits if c["commit"]["committer"]["date"] > opened]
    merges = [c for c in later if len(c.get("parents", [])) > 1]
    return len(later) - len(merges), len(merges), later


def hours(start, end):
    parse = lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))  # noqa: E731
    return round((parse(end) - parse(start)).total_seconds() / 3600, 1)


def pull_request_row(repo, pr, sonar_key):
    number = pr["number"]
    comments = gh_list(f"repos/{repo}/issues/{number}/comments")
    linked = CLOSES.search(pr.get("body") or "")
    if linked:
        comments += gh_list(f"repos/{repo}/issues/{linked.group(1)}/comments")
    record = parse_record(comments)
    commits = gh_list(f"repos/{repo}/pulls/{number}/commits")
    fixes, merges, later = pushes_after_open(commits, pr["created_at"])
    failures = 0
    for commit in later:
        runs = gh(f"repos/{repo}/commits/{commit['sha']}/check-runs").get("check_runs", [])
        failures += sum(1 for run in runs if run.get("conclusion") in FAILED)
    review = gh_list(f"repos/{repo}/pulls/{number}/comments")
    return {
        "repo": repo.split("/")[-1], "pr": number, "title": pr["title"], "kind": classify(pr, record),
        "tier": record[0] if record else None, "launches": record[1] if record else None,
        "tokens": record[2] if record else None, "fix_pushes": fixes, "base_merges": merges,
        "ci_failures": failures, "sonar": sonar_issues(sonar_key, number) if sonar_key else None,
        "bot_comments": sum(1 for c in review if (c.get("user") or {}).get("type") == "Bot"),
        "human_comments": sum(1 for c in review if (c.get("user") or {}).get("type") != "Bot"),
        "hours_to_merge": hours(pr["created_at"], pr["merged_at"]), "merged_at": pr["merged_at"],
    }


def week(stamp):
    year, number, _ = datetime.date.fromisoformat(stamp[:10]).isocalendar()
    return f"{year}-W{number:02d}"


def share(rows, test):
    return f"{sum(1 for r in rows if test(r))}/{len(rows)}" if rows else "-"


def totals(rows):
    """Markdown lines with the totals of the squad pull requests per repository and week."""
    lines = ["| Repository | Week | Squad PRs | No fix push | No Sonar issue | CI failures per PR | Median tokens by tier |",
             "| ---------- | ---- | --------- | ----------- | -------------- | ------------------ | --------------------- |"]
    groups = {}
    for row in rows:
        if row["kind"] == "squad":
            groups.setdefault((row["repo"], week(row["merged_at"])), []).append(row)
    for (repo, when), group in sorted(groups.items()):
        tiers = {}
        for row in group:
            if row["tokens"]:
                tiers.setdefault(row["tier"] or "?", []).append(row["tokens"])
        median = ", ".join(f"{t} {statistics.median(v) / 1e6:.2f} M" for t, v in sorted(tiers.items())) or "-"
        known = [r for r in group if r["sonar"] is not None]
        failures = sum(r["ci_failures"] for r in group) / len(group)
        lines.append(f"| {repo} | {when} | {len(group)} | {share(group, lambda r: r['fix_pushes'] == 0)} | "
                     f"{share(known, lambda r: r['sonar'] == 0)} | {failures:.2f} | {median} |")
    return lines


def table(rows):
    lines = ["| Repo | PR | Kind | Tier | Launches | Tokens | Fix pushes | Base merges | CI failures | Sonar | "
             "Bot / human comments | Hours to merge |",
             "| ---- | -- | ---- | ---- | -------- | ------ | ---------- | ----------- | ----------- | ----- | "
             "-------------------- | -------------- |"]
    show = lambda value: "-" if value is None else (f"{value:,}" if isinstance(value, int) else str(value))  # noqa: E731
    for r in rows:
        lines.append(f"| {r['repo']} | #{r['pr']} | {r['kind']} | {show(r['tier'])} | {show(r['launches'])} | "
                     f"{show(r['tokens'])} | {r['fix_pushes']} | {r['base_merges']} | {r['ci_failures']} | "
                     f"{show(r['sonar'])} | {r['bot_comments']} / {r['human_comments']} | {r['hours_to_merge']} |")
    return lines


def merged_in_window(repo, since, until):
    pulls = gh_list(f"repos/{repo}/pulls?state=closed&sort=updated&direction=desc",
                    stop=lambda p: p["updated_at"][:10] < since)
    return [p for p in pulls if p.get("merged_at") and since <= p["merged_at"][:10] <= until]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Quality report of squad pull requests.")
    parser.add_argument("--repo", action="append", required=True, help="owner/name, or owner/name=sonar-project-key")
    parser.add_argument("--since", required=True, help="first merge date, YYYY-MM-DD")
    parser.add_argument("--until", default=datetime.date.today().isoformat(), help="last merge date, YYYY-MM-DD")
    parser.add_argument("--out", help="write the report to this file instead of printing it")
    args = parser.parse_args(argv)
    rows = []
    try:
        for entry in args.repo:
            repo, _, key = entry.partition("=")
            for pr in sorted(merged_in_window(repo, args.since, args.until), key=lambda p: p["merged_at"]):
                rows.append(pull_request_row(repo, pr, key or None))
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as error:
        print(f"GitHub could not be read: {error}", file=sys.stderr)
        return 1
    report = "\n".join([f"# Squad report {args.since} to {args.until}", "", "## Totals of squad pull requests", "",
                        *totals(rows), "", "## Pull requests", "", *table(rows), ""])
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
