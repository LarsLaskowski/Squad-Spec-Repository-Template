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
# The wrap-up appends the output of session-usage.py below the run metrics (LarsLaskowski/Seluna#140).
SESSION = ("### Session usage\n\nTokens per model (the session and all its subagents; …):\n\n"
           "| Model | Input | Output | Cache read | Cache write |\n| --- | ---: | ---: | ---: | ---: |\n"
           "| claude-opus-5-5 | 316 | 169,340 | 11,439,361 | 653,244 |\n"
           "| **Total** | 750 | 256,585 | 36,619,921 | 1,165,127 |\n\nSubagents:\n\n"
           "| Subagent | Launches | Models | Input | Output | Cache read | Cache write |\n"
           "| --- | ---: | --- | ---: | ---: | ---: | ---: |\n"
           "| squad-dev | 2 | claude-sonnet-5-5 | 92 | 17,956 | 2,978,915 | 250,828 |\n"
           "| **Total** | 12 | | 426 | 199,347 | 15,120,034 | 963,420 |\n")


def commit(sha, date, parents=1):
    return {"sha": sha, "commit": {"committer": {"date": date}}, "parents": [{}] * parents}


class TestSquadReport(unittest.TestCase):
    def test_record_gives_tier_launches_and_tokens(self):
        self.assertEqual(report.parse_record([RECORD, METRICS]), ("security", 16, 1382358, None))
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
        self.assertEqual(record, ("security", 9, 600000, None))

    def test_session_usage_below_the_run_metrics_is_not_the_runs_total(self):
        both = {"body": f"{RECORD['body']}\n\n{METRICS['body']}\n{SESSION}"}
        self.assertEqual(report.parse_record([both]), ("security", 16, 1382358, None))
        self.assertEqual(report.parse_session([both]), (750, 256585, 36619921, 1165127))
        crlf = {"body": both["body"].replace("\n", "\r\n")}
        self.assertEqual((report.parse_record([crlf])[1:], report.parse_session([crlf])),
                         ((16, 1382358, None), (750, 256585, 36619921, 1165127)))

    def test_the_session_tables_never_count_as_run_metrics(self):
        no_heading = {"body": f"{RECORD['body']}\n\n{SESSION.replace('### Session usage', 'Usage of the session:')}"}
        self.assertEqual(report.parse_record([no_heading]), ("security", None, None, None),
                         "a session total row has no empty Model/effort cell")
        self.assertIsNone(report.parse_session([no_heading]), "session figures are read under their heading only")
        apart = {"body": SESSION.replace("### Session usage", "**Session usage:**")}
        self.assertEqual(report.parse_session([RECORD, METRICS, apart]), (750, 256585, 36619921, 1165127),
                         "the session usage may be posted in a comment of its own")
        self.assertIsNone(report.parse_session([apart]), "without a working record nothing is read")
        absent = {"body": "### Session usage\n\nnot provided (no Claude Code session transcript found)\n"}
        self.assertIsNone(report.parse_session([RECORD, METRICS, absent]))

    def test_weighted_total_comes_from_the_table_of_tokens_per_kind(self):
        kinds = ("\n| Member | Model/effort | Input | Output | Cache read | Cache write | Weighted | Share |\n"
                 "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                 "| Lead | opus/medium | 31 | 9,870 | 612,400 | 48,210 | 280,527 | 41% |\n"
                 "| Orchestrator | opus/xhigh | 6 | 2,053 | 1,016,629 | 3,620 | 401,000 | 59% |\n"
                 "| **Total** | | 37 | 11,923 | 1,629,029 | 51,830 | 681,527 | 100% |\n")
        session = SESSION.replace("| Cache write |\n| --- | ---: | ---: | ---: | ---: |", "| Cache write | Weighted |\n"
                                  "| --- | ---: | ---: | ---: | ---: | ---: |").replace(
            "| **Total** | 750 | 256,585 | 36,619,921 | 1,165,127 |", "| **Total** | 750 | 256,585 | 36,619,921 | 1,165,127 | "
            "9,000,000 |")
        both = {"body": f"{RECORD['body']}\n\n{METRICS['body']}{kinds}\n{session}"}
        self.assertEqual(report.parse_record([both]), ("security", 16, 1382358, 681527),
                         "the per-kind total is no launch total, and the session's figures stay apart")
        self.assertEqual(report.parse_session([both]), (750, 256585, 36619921, 1165127))

    def test_the_table_shows_the_session_tokens_in_columns_of_their_own(self):
        row = {"repo": "o/r", "pr": 5, "kind": "squad", "tier": "security", "launches": 16, "tokens": 1382358,
               "session": (750, 256585, 36619921, 1165127), "fix_pushes": 0, "base_merges": 0, "ci_failures": 0,
               "sonar": None, "bot_comments": 0, "human_comments": 0, "hours_to_merge": 1.5}
        lines = report.table([row, {**row, "pr": 6, "session": None, "weighted": 9876543}])
        self.assertIn("| Tokens | Weighted | Session input | Session output | Session cache read | Session cache write |",
                      lines[0])
        self.assertIn("| 16 | 1,382,358 | - | 750 | 256,585 | 36,619,921 | 1,165,127 | 0 |", lines[2])
        self.assertIn("| 16 | 1,382,358 | 9,876,543 | - | - | - | - | 0 |", lines[3])
        self.assertTrue(all(line.count("|") == lines[0].count("|") for line in lines))

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

    def test_issue_record_of_an_earlier_run_is_not_counted(self):
        record = {"body": "Squad working record\n\nTier: **security**", "created_at": "2026-10-26T19:43:05Z"}
        release = {"number": 118, "title": "[Release] Prepare version 0.7.0", "body": "Closes #69",
                   "user": {"login": "me"}, "created_at": "2026-10-27T17:57:18Z", "merged_at": "2026-10-27T18:02:57Z"}
        lists = {"repos/o/r/issues/69/comments": [record], "repos/o/r/issues/118/comments": [],
                 "repos/o/r/pulls/118/commits": [commit("c", "2026-10-27T17:50:00Z")],
                 "repos/o/r/pulls/118/comments": [], "repos/o/r/pulls/118/reviews": []}
        with mock.patch.object(report, "gh_list", lambda path, stop=None: lists[path]), \
                mock.patch.object(report, "failed_checks", return_value=0):
            self.assertEqual(report.pull_request_row("o/r", release, None)["kind"], "manual")
        early = {"body": "Squad working record", "created_at": "2026-10-27T18:00:00Z"}
        self.assertEqual(len(report.own_issue_comments([record, early], [commit("c", "2026-10-27T17:50:00Z")],
                                                       "2026-10-27T18:02:57Z")), 1,
                         "a record posted after an early draft PR opened still counts")

    def test_merge_before_creation_shows_no_hours(self):
        self.assertIsNone(report.hours("2026-11-01T09:52:13Z", "2026-11-01T09:31:03Z"))
        self.assertEqual(report.hours("2026-11-01T09:00:00Z", "2026-11-01T10:30:00Z"), 1.5)

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
        self.assertIn("| Vandox | 2026-W42 | 3 | 2/3 | 2/3 | 0.33 | 1 | security 1.50 M | - |", line)
        self.assertIn("Vandox#3", report.without_metrics(rows)[-1], "a squad PR without run metrics is named")
        self.assertNotIn("Vandox#4", report.without_metrics(rows)[-1], "a manual PR never has run metrics")
        self.assertEqual(report.without_metrics(rows[:2]), [])


class TestUpstream(unittest.TestCase):
    ISSUE = {"number": 7, "title": "[Squad] Tester model (from o/r#3)", "body": "Proposal.", "user": {"login": "me"},
             "html_url": "https://github.com/o/r/issues/7", "created_at": "2026-11-05T10:00:00Z"}

    def test_upstream_lists_the_open_issues_without_pull_requests(self):
        lists = {"repos/o/r/issues?state=open&labels=squad-upstream": [self.ISSUE, {"number": 8, "pull_request": {}}],
                 "repos/o/s/issues?state=open&labels=squad-upstream": []}
        out = io.StringIO()
        with mock.patch.object(report, "gh_list", lambda path, stop=None: lists[path]), contextlib.redirect_stdout(out):
            code = report.main(["--upstream", "--repo", "o/r=key", "--repo", "o/s"])
        self.assertEqual(code, 0)
        self.assertIn("| o/r | #7 | 2026-11-05 | [Squad] Tester model (from o/r#3) |", out.getvalue())
        self.assertNotIn("#8", out.getvalue(), "a pull request is no lesson")

    def test_move_files_the_issue_here_and_closes_the_original(self):
        writes = []

        def fake_write(method, path, fields):
            writes.append((method, path, fields))
            return {"number": 300, "html_url": "https://github.com/t/t/issues/300"} if path == "repos/t/t/issues" else {}
        with mock.patch.object(report, "gh_list", lambda path, stop=None: [self.ISSUE]), \
                mock.patch.object(report, "gh_write", fake_write), contextlib.redirect_stdout(io.StringIO()) as out:
            code = report.main(["--upstream", "--move", "--template", "t/t", "--repo", "o/r"])
        self.assertEqual(code, 0)
        (create_method, create_path, created), (_, comment_path, comment), (close_method, close_path, closed) = writes
        self.assertEqual((create_method, create_path, created["labels"]), ("POST", "repos/t/t/issues", ["squad"]))
        self.assertIn("Moved from o/r#7 (https://github.com/o/r/issues/7)", created["body"])
        self.assertTrue(created["body"].endswith("Proposal."))
        self.assertEqual(comment_path, "repos/o/r/issues/7/comments")
        self.assertIn("https://github.com/t/t/issues/300", comment["body"])
        self.assertEqual((close_method, close_path, closed["state"]), ("PATCH", "repos/o/r/issues/7", "closed"))
        self.assertIn("o/r#7 -> https://github.com/t/t/issues/300", out.getvalue())

    def test_move_needs_upstream_and_the_report_needs_since(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for args in (["--move", "--repo", "o/r", "--since", "2026-10-01"], ["--repo", "o/r"]):
                with self.assertRaises(SystemExit):
                    report.main(args)


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
