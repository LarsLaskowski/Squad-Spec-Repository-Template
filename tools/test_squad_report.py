"""Unit tests for tools/squad-report.py: run `python3 -m unittest discover tools`."""
import importlib.util
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "squad-report.py")
spec = importlib.util.spec_from_file_location("squad_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

RECORD = {"body": "<details>\n<summary>Squad working record</summary>\n\n**Tier:** security. The plan …\n</details>"}
METRICS = {"body": "### Squad run metrics\n\n| Member | Model/effort | Launches | Tokens | Tool uses | Seconds |\n"
                   "| ------ | --- | --- | --- | --- | --- |\n"
                   "| squad-dev | sonnet/medium | 4 (2 continued) | 308,449 | 52 | 737 |\n"
                   "| **Total** | | 16 (6 continued) | 1,382,358 | 333 | 4160 |\n"}


def commit(sha, date, parents=1):
    return {"sha": sha, "commit": {"committer": {"date": date}}, "parents": [{}] * parents}


class TestSquadReport(unittest.TestCase):
    def test_record_gives_tier_launches_and_tokens(self):
        self.assertEqual(report.parse_record([RECORD, METRICS]), ("security", 16, 1382358))
        self.assertIsNone(report.parse_record([{"body": "looks good"}]))

    def test_kinds(self):
        self.assertEqual(report.classify({"title": "[Agent] x"}, ("security", 1, 1)), "squad")
        self.assertEqual(report.classify({"title": "[Docs] Update the squad from Squad-Spec-Repository-Template"},
                                         None), "refresh")
        self.assertEqual(report.classify({"title": "Bump x", "user": {"login": "dependabot[bot]"}}, None),
                         "dependabot")
        self.assertEqual(report.classify({"title": "[Web] Fix login"}, None), "manual")

    def test_pushes_after_open_count_merges_apart(self):
        commits = [commit("a", "2026-10-17T10:00:00Z"), commit("b", "2026-10-17T12:00:00Z"),
                   commit("c", "2026-10-17T13:00:00Z", parents=2)]
        fixes, merges, later = report.pushes_after_open(commits, "2026-10-17T11:00:00Z")
        self.assertEqual((fixes, merges, [c["sha"] for c in later]), (1, 1, ["a", "b", "c"]),
                         "the head at opening carries the PR's first CI run")

    def test_record_reads_only_squad_comments_and_the_last_match(self):
        prose = {"body": "The tier `standard` review looked fine."}
        raised = {"body": "### Squad run metrics\n\nTier raised: tier **security**\n"
                          "| **Total** | | 9 | 600,000 | 1 | 2 |\n"}
        record = report.parse_record([prose, {"body": "Squad working record\n\nTier: **standard**"}, raised])
        self.assertEqual(record, ("security", 9, 600000))

    def test_linked_issues_ignore_html_comments(self):
        body = "<!--- For example: Closes #123 -->\nFixes #7, closed #8 and resolves: #9"
        self.assertEqual(report.linked_issues(body), [7, 8, 9])

    def test_check_runs_are_paged_and_include_reruns(self):
        pages = {1: {"total_count": 3, "check_runs": [{"conclusion": "failure"}, {"conclusion": "success"}]},
                 2: {"total_count": 3, "check_runs": [{"conclusion": "timed_out"}]}}
        calls = []

        def fake(path):
            calls.append(path)
            return pages[int(path.rsplit("page=", 1)[1])]
        with mock.patch.object(report, "gh", fake), mock.patch.object(report, "PER_PAGE", 2):
            self.assertEqual(report.failed_checks("o/r", "abc"), 2)
        self.assertIn("filter=all", calls[0])

    def test_review_comments_leave_out_replies_and_the_author(self):
        comments = [{"user": {"login": "bot", "type": "Bot"}}, {"user": {"login": "me"}},
                    {"user": {"login": "rev"}, "in_reply_to_id": 1}, {"user": {"login": "rev"}}]
        reviews = [{"user": {"login": "copilot", "type": "Bot"}, "body": "Summary"},
                   {"user": {"login": "rev"}, "body": ""}]
        answers = {"comments": comments, "reviews": reviews}
        with mock.patch.object(report, "gh_list", lambda path: answers[path.rsplit("/", 1)[1]]):
            self.assertEqual(report.review_comments("o/r", 5, "me"), (2, 1))

    def test_row_counts_the_ci_run_of_the_head_at_opening(self):
        pr = {"number": 5, "title": "[Web] x", "body": "Closes #4", "user": {"login": "me"},
              "created_at": "2026-10-17T11:00:00Z", "merged_at": "2026-10-17T13:00:00Z"}
        lists = {"repos/o/r/issues/4/comments": [{"body": "Squad working record\n\nTier: **standard**"}],
                 "repos/o/r/issues/5/comments": [],
                 "repos/o/r/pulls/5/commits": [commit("a", "2026-10-17T10:00:00Z"), commit("b", "2026-10-17T12:00:00Z")],
                 "repos/o/r/pulls/5/comments": [], "repos/o/r/pulls/5/reviews": []}
        failed = {"a": 1, "b": 0}
        with mock.patch.object(report, "gh_list", lambda path, stop=None: lists[path]), \
                mock.patch.object(report, "failed_checks", lambda repo, sha: failed[sha]):
            row = report.pull_request_row("o/r", pr, None)
        self.assertEqual((row["kind"], row["tier"], row["fix_pushes"], row["ci_failures"]), ("squad", "standard", 1, 1))

    def test_dates_are_validated(self):
        self.assertEqual(report.day("2026-10-01"), "2026-10-01")
        with self.assertRaises(ValueError):
            report.day("2026-10-1x")

    def test_list_walks_pages_and_stops_early(self):
        pages = {1: [{"n": i, "updated_at": "2026-10-18"} for i in range(100)],
                 2: [{"n": 100, "updated_at": "2026-10-18"}, {"n": 101, "updated_at": "2026-10-01"}]}
        with mock.patch.object(report, "gh", lambda path: pages[int(path.rsplit("page=", 1)[1])]):
            items = report.gh_list("repos/o/r/pulls?state=closed", stop=lambda p: p["updated_at"] < "2026-10-11")
        self.assertEqual(len(items), 101)

    def test_totals_per_repository_and_week(self):
        rows = [{"repo": "Vandox", "pr": 1, "kind": "squad", "merged_at": "2026-10-17T10:00:00Z", "tier": "security",
                 "launches": 9, "tokens": 1_000_000, "fix_pushes": 0, "sonar": 0, "ci_failures": 0},
                {"repo": "Vandox", "pr": 2, "kind": "squad", "merged_at": "2026-10-18T10:00:00Z", "tier": "security",
                 "launches": 12, "tokens": 2_000_000, "fix_pushes": 2, "sonar": 3, "ci_failures": 1},
                {"repo": "Vandox", "pr": 3, "kind": "squad", "merged_at": "2026-10-18T11:00:00Z", "tier": "trivial",
                 "launches": None, "tokens": None, "fix_pushes": 0, "sonar": 0, "ci_failures": 0},
                {"repo": "Vandox", "pr": 4, "kind": "manual", "merged_at": "2026-10-18T10:00:00Z", "tier": None,
                 "launches": None, "tokens": None, "fix_pushes": 5, "sonar": None, "ci_failures": 4}]
        line = report.totals(rows)[2]
        self.assertIn("| Vandox | 2026-W42 | 3 | 2/3 | 2/3 | 0.33 | 1 | security 1.50 M |", line)
        self.assertIn("Vandox#3", report.without_metrics(rows)[-1], "a squad PR without run metrics is named")
        self.assertNotIn("Vandox#4", report.without_metrics(rows)[-1], "a manual PR never has run metrics")
        self.assertEqual(report.without_metrics(rows[:2]), [])


class TestMainOutput(unittest.TestCase):
    ARGS = ["--repo", "o/r", "--since", "2026-10-01", "--until", "2026-10-02"]

    def run_main(self, *extra):
        stderr = io.StringIO()
        with mock.patch.object(report, "merged_in_window", return_value=[]), contextlib.redirect_stderr(stderr), \
                contextlib.redirect_stdout(io.StringIO()):
            return report.main([*self.ARGS, *extra]), stderr.getvalue()

    def test_out_writes_a_file_in_the_working_directory(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder):
            code, _ = self.run_main("--out", "report.md")
            with open(os.path.join(folder, "report.md"), encoding="utf-8") as handle:
                self.assertIn("# Squad report 2026-10-01 to 2026-10-02", handle.read())
        self.assertEqual(code, 0)

    def test_out_with_a_directory_is_refused(self):
        for out in (os.path.join("..", "report.md"), os.path.join("sub", "report.md"), "sub" + os.sep):
            with self.subTest(out=out), tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder):
                code, message = self.run_main("--out", out)
                self.assertEqual(code, 1)
                self.assertIn("--out must name a file in the current directory", message)


if __name__ == "__main__":
    unittest.main()
