#!/usr/bin/env python3
"""Quality report of the squad runs in the repositories that use this template: what happened to each pull
request after it was opened, read from GitHub and SonarQube Cloud instead of from the runs' own logs.

For every pull request merged in the window it reports:

- **kind** — `squad` (its issue or the PR carries a "Squad working record" comment), `refresh` (a template
  refresh: "Update the squad from …"), `dependabot`, or `manual`;
- **tier**, **launches** and **tokens** of a squad run, read from its working record and the total row of its "Squad
  run metrics" (`squad-log.py --summary`: `| **Total** | | <launches> | <tokens> | …`) above a "Session usage" heading,
  and the run's **weighted** figure (every token at its list price, the orchestrator's share included) from the total
  row of the table of tokens per kind below it (`| **Total** | | … | <weighted> | 100% |`), for runs whose launches
  were logged from their transcripts (`squad-log.py --agent-id`);
- the **session tokens** per kind (input, output, cache read, cache write), read from the per-model total row under
  that heading (`session-usage.py`), in columns of their own: they count the whole session, the orchestrator and the
  cache reads included, and are never taken for the run metrics;
- **fix commits** — commits dated after the PR was opened, merges of the base branch counted apart (a force-push
  re-dates the commits it rewrites, which then all count);
- **CI failures** — failed or timed-out check runs, re-runs included, on the head at opening and those commits;
- **Sonar** — the SonarQube Cloud issues ever raised on the pull request (fixed ones included), when the
  repository's project key is given;
- **bot** and **human** review comments and review bodies (the author's own replies left out), and the hours
  from opening to merge.

The totals per repository and week show what the squad's rules changed: the share of squad pull requests that
needed no fix commit, that SonarQube found nothing on, the CI failures per pull request, and the median tokens and
weighted figure per tier. Follow-up defects (a later fix of code a run wrote) are not detectable this way and stay a
reading task.

With `--upstream` it instead lists the open issues labelled `squad-upstream` of the repositories: the squad lessons
a run filed in its own repository because they concern a template-managed file (`core/.squad/orchestration.md`, *Squad
lessons*). `--move` moves them here in one batch: each becomes an issue labelled `squad` in the template repository
with its title, its body and a link back, and the original gets a comment linking the new issue and is closed.

Usage (needs `gh` with read access to the repositories; `--move` also needs write access to their issues):
    python3 tools/squad-report.py --repo LarsLaskowski/Vandox=networlddev_vandox --repo LarsLaskowski/Seluna \\
        --since 2026-10-11 [--until 2026-10-18] [--out report.md]
    python3 tools/squad-report.py --upstream --repo LarsLaskowski/Vandox --repo LarsLaskowski/Seluna [--move]

`owner/name=sonar-key` adds the SonarQube Cloud project key of that repository. Exit code 0, or 1 when GitHub
cannot be read or written.
"""
import argparse
import datetime
import json
import os
import re
import statistics
import subprocess
import sys
import urllib.parse
import urllib.request

SONAR = "https://sonarcloud.io/api"
TEMPLATE_REPOSITORY = "LarsLaskowski/Squad-Spec-Repository-Template"
UPSTREAM = "squad-upstream"
TIER = re.compile(r"\btier\b[:*\s`]*(patch/security|docs|patch|trivial|standard|security)\b", re.I)
# The total row of `squad-log.py --summary`: an empty Model/effort cell, then launches and tokens. The session's own
# total rows (`session-usage.py`) carry a number in that cell, so they never match; the total row of the table of
# tokens per kind ends in a share of 100 % and is left out.
RUN_TOTAL = re.compile(r"^(?![^\n]*%)\|[ \t]*+\*\*Total\*\*[ \t]*+\|[ \t]*+\|[ \t]*+(\d++)[^|\n]*+\|[ \t]*+([\d,]++)[ \t]*+\|",
                       re.M)
# The total row of the table of tokens per kind: input, output, cache read, cache write, weighted, a share of 100 %.
WEIGHTED_TOTAL = re.compile(r"^\|[ \t]*+\*\*Total\*\*[ \t]*+\|[ \t]*+\|(?:[ \t]*+[\d,]++[ \t]*+\|){4}[ \t]*+([\d,]++)[ \t]*+\|"
                            r"[ \t]*+100[ \t]*+%[ \t]*+\|[ \t]*+$", re.M)
# The per-model total row of `session-usage.py`: input, output, cache-read and cache-write tokens, and the weighted
# figure since the template added it.
SESSION_TOTAL = re.compile(r"^\|[ \t]*+\*\*Total\*\*[ \t]*+((?:\|[ \t]*+[\d,]++[ \t]*+){4,5})\|[ \t]*+$", re.M)
SESSION_HEADING = re.compile(r"^[#*_ \t]*+Session usage[*_: \t]*+$", re.M | re.I)
CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)(?:\s*+:)?+\s++#(\d+)", re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)
MARKERS = ("Squad working record", "Squad run metrics")
FAILED = {"failure", "timed_out"}


PER_PAGE = 100


def gh(path):
    """GET a GitHub API path through `gh api`."""
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(result.stdout or "null") or None


def gh_write(method, path, fields):
    """Send `fields` as JSON to a GitHub API path through `gh api` (POST, PATCH); the answer as JSON."""
    result = subprocess.run(["gh", "api", "-X", method, path, "--input", "-"], input=json.dumps(fields),
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout or "null") or {}


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


def record_bodies(comments):
    """(run part, session part) of every "Squad working record", "Squad run metrics" or "Session usage" comment: the
    text above its "Session usage" heading and the text below it; None when no working record is among them."""
    parts = []
    for comment in comments:
        body = (comment.get("body") or "").replace("\r\n", "\n")
        heading = SESSION_HEADING.search(body)
        if heading:
            parts.append((body[:heading.start()], body[heading.end():]))
        elif any(marker in body for marker in MARKERS):
            parts.append((body, ""))
    return parts if any(MARKERS[0] in run for run, _ in parts) else None


def parse_record(comments):
    """(tier, launches, tokens, weighted) from the "Squad working record" and "Squad run metrics" comments only, the
    last match winning (a later record of the same issue, a raised tier); None when there is no working record.
    Launches and tokens come from the run metrics' total row only, never from the "Session usage" tables below them;
    the weighted figure from the total row of the table of tokens per kind (None for a run without one)."""
    parts = record_bodies(comments)
    if parts is None:
        return None
    runs = "\n".join(run for run, _ in parts)
    tiers, totals_found, weights = TIER.findall(runs), RUN_TOTAL.findall(runs), WEIGHTED_TOTAL.findall(runs)
    return (tiers[-1].lower() if tiers else None,
            int(totals_found[-1][0]) if totals_found else None,
            int(totals_found[-1][1].replace(",", "")) if totals_found else None,
            int(weights[-1].replace(",", "")) if weights else None)


def parse_session(comments):
    """(input, output, cache read, cache write) tokens of the last per-model total row under a "Session usage"
    heading of the record's comments; None without a working record or without such a row (a session that printed
    "not provided")."""
    parts = record_bodies(comments)
    found = SESSION_TOTAL.findall("\n".join(session for _, session in parts)) if parts else []
    if not found:
        return None
    return tuple(int(cell.strip().replace(",", "")) for cell in found[-1].split("|")[1:5])


def linked_issues(body):
    """The issue numbers a pull request body closes, outside HTML comments (a kept template example is no link)."""
    return sorted({int(n) for n in CLOSES.findall(COMMENT.sub("", body or ""))})


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
    """(fix commits, merges of the base, the commits CI ran on from the opening on): the commits dated after the
    pull request was opened, and the head at opening, whose CI run is the PR's first. A force-push re-dates the
    commits it rewrites, which then all count as fixes."""
    later = [c for c in commits if c["commit"]["committer"]["date"] > opened]
    earlier = [c for c in commits if c["commit"]["committer"]["date"] <= opened]
    merges = [c for c in later if len(c.get("parents", [])) > 1]
    return len(later) - len(merges), len(merges), earlier[-1:] + later


def failed_checks(repo, sha):
    """Failed or timed-out check runs of a commit, re-run attempts included."""
    runs, page = [], 1
    while True:
        data = gh(f"repos/{repo}/commits/{sha}/check-runs?filter=all&per_page={PER_PAGE}&page={page}") or {}
        runs += data.get("check_runs", [])
        if len(runs) >= data.get("total_count", 0) or not data.get("check_runs"):
            return sum(1 for run in runs if run.get("conclusion") in FAILED)
        page += 1


def review_comments(repo, number, author):
    """(bot, human) top-level review comments and review bodies; replies and the author's own are left out."""
    comments = [c for c in gh_list(f"repos/{repo}/pulls/{number}/comments") if not c.get("in_reply_to_id")]
    comments += [r for r in gh_list(f"repos/{repo}/pulls/{number}/reviews") if (r.get("body") or "").strip()]
    comments = [c for c in comments if (c.get("user") or {}).get("login") != author]
    bots = sum(1 for c in comments if (c.get("user") or {}).get("type") == "Bot")
    return bots, len(comments) - bots


def hours(start, end):
    """Hours from `start` to `end`; None when GitHub reports the end before the start (a pull request whose
    creation time is later than its merge)."""
    parse = lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))  # noqa: E731
    value = round((parse(end) - parse(start)).total_seconds() / 3600, 1)
    return value if value >= 0 else None


def own_issue_comments(comments, commits, merged_at):
    """The comments of a linked issue that belong to this pull request's run: posted from the branch's first
    commit to the merge. An issue that two pull requests close (a feature, then its release) carries the working
    record of the earlier run only, which was posted before the later branch started."""
    dates = [c["commit"]["committer"]["date"] for c in commits]
    first = min(dates) if dates else None
    return [c for c in comments
            if not c.get("created_at") or ((first is None or c["created_at"] >= first) and c["created_at"] <= merged_at)]


def pull_request_row(repo, pr, sonar_key):
    number = pr["number"]
    commits = gh_list(f"repos/{repo}/pulls/{number}/commits")
    comments = []
    for issue in (i for i in linked_issues(pr.get("body")) if i != number):
        comments += own_issue_comments(gh_list(f"repos/{repo}/issues/{issue}/comments"), commits, pr["merged_at"])
    comments += gh_list(f"repos/{repo}/issues/{number}/comments")
    record = parse_record(comments)
    session = parse_session(comments)
    fixes, merges, checked = pushes_after_open(commits, pr["created_at"])
    failures = sum(failed_checks(repo, commit["sha"]) for commit in checked)
    bots, humans = review_comments(repo, number, (pr.get("user") or {}).get("login"))
    return {
        "repo": repo, "pr": number, "title": pr["title"], "kind": classify(pr, record),
        "tier": record[0] if record else None, "launches": record[1] if record else None,
        "tokens": record[2] if record else None, "weighted": record[3] if record else None, "session": session,
        "fix_pushes": fixes, "base_merges": merges,
        "ci_failures": failures, "sonar": sonar_issues(sonar_key, number) if sonar_key else None,
        "bot_comments": bots, "human_comments": humans,
        "hours_to_merge": hours(pr["created_at"], pr["merged_at"]), "merged_at": pr["merged_at"],
    }


def week(stamp):
    year, number, _ = datetime.date.fromisoformat(stamp[:10]).isocalendar()
    return f"{year}-W{number:02d}"


def share(rows, test):
    return f"{sum(1 for r in rows if test(r))}/{len(rows)}" if rows else "-"


def medians(group, field):
    """The median of `field` per tier of the rows that have it, in millions, e.g. "security 1.77 M, patch 0.21 M"."""
    tiers = {}
    for row in group:
        if row.get(field):
            tiers.setdefault(row["tier"] or "?", []).append(row[field])
    return ", ".join(f"{t} {statistics.median(v) / 1e6:.2f} M" for t, v in sorted(tiers.items())) or "-"


def by_repository_and_week(row):
    return row["repo"], week(row["merged_at"])


def totals(rows, key=by_repository_and_week, heads=("Repository", "Week")):
    """Markdown lines with the totals of the squad pull requests per group: per repository and week by default, or
    per the cells `key` returns for a row (`heads` names them)."""
    names = " | ".join(heads)
    rules = " | ".join("-" * len(head) for head in heads)
    lines = [f"| {names} | Squad PRs | No fix commit | No Sonar issue | CI failures per PR | Without run metrics | "
             "Median tokens by tier | Median weighted by tier |",
             f"| {rules} | --------- | ------------- | -------------- | ------------------ | ------------------- | "
             "--------------------- | ----------------------- |"]
    groups = {}
    for row in rows:
        if row["kind"] == "squad":
            groups.setdefault(key(row), []).append(row)
    for cells, group in sorted(groups.items()):
        known = [r for r in group if r["sonar"] is not None]
        failures = sum(r["ci_failures"] for r in group) / len(group)
        lines.append(f"| {' | '.join(cells)} | {len(group)} | {share(group, lambda r: r['fix_pushes'] == 0)} | "
                     f"{share(known, lambda r: r['sonar'] == 0)} | {failures:.2f} | "
                     f"{sum(1 for r in group if r['launches'] is None)} | {medians(group, 'tokens')} | "
                     f"{medians(group, 'weighted')} |")
    return lines


def without_metrics(rows):
    """Markdown lines naming the squad pull requests whose working record has no run metrics: the run's step 12
    (wrap-up) did not happen, so its lessons and costs are missing too."""
    missing = [f"{r['repo']}#{r['pr']}" for r in rows if r["kind"] == "squad" and r["launches"] is None]
    if not missing:
        return []
    return ["", f"**Squad pull requests without run metrics** (no step 12 wrap-up): {', '.join(missing)}"]


def table(rows):
    lines = ["| Repo | PR | Kind | Tier | Launches | Tokens | Weighted | Session input | Session output | Session cache read | "
             "Session cache write | Fix commits | Base merges | CI failures | Sonar | Bot / human comments | Hours to merge |",
             "| ---- | -- | ---- | ---- | -------- | ------ | -------- | ------------- | -------------- | ------------------ | "
             "------------------- | ----------- | ----------- | ----------- | ----- | -------------------- | -------------- |"]

    def show(value):
        if value is None:
            return "-"
        return f"{value:,}" if isinstance(value, int) else str(value)

    for r in rows:
        session = " | ".join(show(value) for value in r.get("session") or (None,) * 4)
        lines.append(f"| {r['repo']} | #{r['pr']} | {r['kind']} | {show(r['tier'])} | {show(r['launches'])} | "
                     f"{show(r['tokens'])} | {show(r.get('weighted'))} | {session} | {r['fix_pushes']} | "
                     f"{r['base_merges']} | {r['ci_failures']} | "
                     f"{show(r['sonar'])} | {r['bot_comments']} / {r['human_comments']} | {show(r['hours_to_merge'])} |")
    return lines


def merged_in_window(repo, since, until):
    pulls = gh_list(f"repos/{repo}/pulls?state=closed&sort=updated&direction=desc",
                    stop=lambda p: p["updated_at"][:10] < since)
    return [p for p in pulls if p.get("merged_at") and since <= p["merged_at"][:10] <= until]


def day(value):
    """A YYYY-MM-DD date, normalised, so the string comparison with GitHub's timestamps holds."""
    return datetime.date.fromisoformat(value).isoformat()


def upstream_issues(repo):
    """The open issues of a repository labelled squad-upstream, pull requests left out."""
    return [issue for issue in gh_list(f"repos/{repo}/issues?state=open&labels={UPSTREAM}") if "pull_request" not in issue]


def upstream_lines(found):
    """Markdown lines listing the (repository, issue) pairs."""
    lines = ["| Repository | Issue | Opened | Title |", "| ---------- | ----- | ------ | ----- |"]
    for repo, issue in found:
        title = (issue.get("title") or "").replace("|", "\\|")
        lines.append(f"| {repo} | #{issue['number']} | {(issue.get('created_at') or '')[:10]} | {title} |")
    return lines


def move_issue(repo, issue, template):
    """Move a squad-upstream issue to the template repository: a new issue labelled `squad` there with its title,
    its body and a link back, then a comment on the original linking the new issue, and the original closed. The
    new issue's URL."""
    number = issue["number"]
    author = (issue.get("user") or {}).get("login", "")
    body = (f"Moved from {repo}#{number} ({issue.get('html_url', '')}), opened on {(issue.get('created_at') or '')[:10]} "
            f"by `{author}` with the label `{UPSTREAM}`.\n\n{issue.get('body') or ''}")
    created = gh_write("POST", f"repos/{template}/issues",
                       {"title": issue.get("title") or f"{repo}#{number}", "body": body, "labels": ["squad"]})
    url = created.get("html_url") or f"{template}#{created.get('number')}"
    gh_write("POST", f"repos/{repo}/issues/{number}/comments",
             {"body": f"Moved to {url}: a `{UPSTREAM}` lesson is fixed in the template repository and arrives here "
                      "with the next refresh (`adopt-template`)."})
    gh_write("PATCH", f"repos/{repo}/issues/{number}", {"state": "closed", "state_reason": "not_planned"})
    return url


def upstream_command(repos, template, move):
    """List the open squad-upstream issues of the repositories; with `move`, move each to `template` as it goes."""
    found = [(repo, issue) for repo in repos for issue in upstream_issues(repo)]
    if not found:
        print(f"No open {UPSTREAM} issue in {', '.join(repos)}.")
        return 0
    print("\n".join([f"# Open {UPSTREAM} issues", "", *upstream_lines(found)]))
    if move:
        print("\nMoved:")
        for repo, issue in found:
            print(f"- {repo}#{issue['number']} -> {move_issue(repo, issue, template)}")
    return 0


def report_rows(args):
    """The rows of every pull request merged in the window, per repository."""
    rows = []
    for entry in args.repo:
        repo, _, key = entry.partition("=")
        for pr in sorted(merged_in_window(repo, args.since, args.until), key=lambda p: p["merged_at"]):
            rows.append(pull_request_row(repo, pr, key or None))
    return rows


def write_report(args, rows):
    """Print the report, or write it to `--out` (a file in the current directory); the exit code."""
    report = "\n".join([f"# Squad report {args.since} to {args.until}", "", "## Totals of squad pull requests", "",
                        *totals(rows), *without_metrics(rows), "", "## Pull requests", "", *table(rows), ""])
    if not args.out:
        print(report)
        return 0
    name = os.path.basename(args.out)
    if not name or name != args.out:
        print(f"--out must name a file in the current directory: {args.out}", file=sys.stderr)
        return 1
    with open(name, "w", encoding="utf-8") as handle:
        handle.write(report)
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Quality report of squad pull requests, or the open squad-upstream "
                                                 "issues of the repositories (--upstream).")
    parser.add_argument("--repo", action="append", required=True, help="owner/name, or owner/name=sonar-project-key")
    parser.add_argument("--since", type=day, help="first merge date, YYYY-MM-DD (required for the report)")
    parser.add_argument("--until", type=day, help="last merge date, YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--out", help="write the report to this file instead of printing it")
    parser.add_argument("--upstream", action="store_true", help=f"list the open {UPSTREAM} issues instead")
    parser.add_argument("--move", action="store_true", help="with --upstream: move them to --template")
    parser.add_argument("--template", default=TEMPLATE_REPOSITORY, help="the template repository (owner/name)")
    args = parser.parse_args(argv)
    if args.move and not args.upstream:
        parser.error("--move goes with --upstream")
    if not args.upstream and not args.since:
        parser.error("the report needs --since")
    args.until = args.until or datetime.datetime.now(datetime.UTC).date().isoformat()
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.upstream:
            return upstream_command([entry.partition("=")[0] for entry in args.repo], args.template, args.move)
        rows = report_rows(args)
    except subprocess.CalledProcessError as error:
        detail = str(error.stderr or "").strip() or str(error)
        print(f"GitHub could not be read or written: {detail}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"GitHub could not be read or written: {error}", file=sys.stderr)
        return 1
    return write_report(args, rows)


if __name__ == "__main__":
    sys.exit(main())
