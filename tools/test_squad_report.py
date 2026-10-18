"""Unit tests for tools/squad-report.py: run `python3 -m unittest discover tools`."""
import importlib.util
import os
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
        self.assertEqual((fixes, merges, [c["sha"] for c in later]), (1, 1, ["b", "c"]))

    def test_list_walks_pages_and_stops_early(self):
        pages = {1: [{"n": i, "updated_at": "2026-10-18"} for i in range(100)],
                 2: [{"n": 100, "updated_at": "2026-10-18"}, {"n": 101, "updated_at": "2026-10-01"}]}
        with mock.patch.object(report, "gh", lambda path: pages[int(path.rsplit("page=", 1)[1])]):
            items = report.gh_list("repos/o/r/pulls?state=closed", stop=lambda p: p["updated_at"] < "2026-10-11")
        self.assertEqual(len(items), 101)

    def test_totals_per_repository_and_week(self):
        rows = [{"repo": "Vandox", "kind": "squad", "merged_at": "2026-10-17T10:00:00Z", "tier": "security",
                 "tokens": 1_000_000, "fix_pushes": 0, "sonar": 0, "ci_failures": 0},
                {"repo": "Vandox", "kind": "squad", "merged_at": "2026-10-18T10:00:00Z", "tier": "security",
                 "tokens": 2_000_000, "fix_pushes": 2, "sonar": 3, "ci_failures": 1},
                {"repo": "Vandox", "kind": "manual", "merged_at": "2026-10-18T10:00:00Z", "tier": None,
                 "tokens": None, "fix_pushes": 5, "sonar": None, "ci_failures": 4}]
        line = report.totals(rows)[2]
        self.assertIn("| Vandox | 2026-W42 | 2 | 1/2 | 1/2 | 0.50 | security 1.50 M |", line)


if __name__ == "__main__":
    unittest.main()
