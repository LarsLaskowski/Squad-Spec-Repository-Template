"""Unit tests for core/.squad/tools/squad-log.py and scope-check.py: run `python3 -m unittest discover tools`."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
import unittest.mock as mock
import urllib.parse

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")


def load_script(name):
    sys.modules.pop("analyzer_common", None)  # it reads squad_settings once, at import
    sys.modules["squad_settings"] = types.SimpleNamespace(BASE_REF="main")
    sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(TOOLS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


def write(path, text, newline="\n"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)


class TestSquadLog(unittest.TestCase):
    def setUp(self):
        self.script = load_script("squad-log")
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "log.md")

    def tearDown(self):
        self.dir.cleanup()

    def test_row_follows_the_files_line_ending(self):
        write(self.path, "| Date | Step | Member | Result |\r\n| - | - | - | - |", newline="")
        self.script.append_row(self.path, "1 Intake", "Orchestrator", "branch created", today="2026-01-02")
        with open(self.path, "rb") as handle:
            data = handle.read()
        self.assertTrue(data.endswith(b"| - | - | - | - |\r\n| 2026-01-02 | 1 Intake | Orchestrator | branch created |\r\n"))

    def test_resolve_log_matches_a_folder_under_specs_only(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, "specs", "issue-7", "log.md"), "| Date |\n")
        write(os.path.join(root, "secret", "log.md"), "| Date |\n")
        expected = os.path.join(root, "specs", "issue-7", "log.md")
        self.assertEqual(self.script.resolve_log(root, "issue-7"), expected)
        self.assertEqual(self.script.resolve_log(root, "specs/issue-7/"), expected)
        for bad in ("../secret", "specs/../secret", "/etc", "issue-8", "..", "secret"):
            self.assertIsNone(self.script.resolve_log(root, bad), bad)

    def test_launch_trailer_and_summary(self):
        write(self.path, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        self.script.append_row(self.path, "2 Plan", "Lead", "plan written", today="2026-01-02",
                               launch=("opus/high", 37445, 6, 57))
        self.script.append_row(self.path, "2 Plan", "Devil's Advocate", "2 objections | 1 minor", today="2026-01-02",
                               launch=("sonnet/high", 12000, 3, 20))
        self.script.append_row(self.path, "2 Plan", "Lead", "revised", today="2026-01-02", launch=("opus/high", 8000, 2, 10))
        self.script.append_row(self.path, "7 Code check", "Orchestrator", "gates pass", today="2026-01-02")
        table = self.script.summary(self.path)
        self.assertIn("| Devil's Advocate | sonnet/high | 1 | 12,000 | 3 | 20 |", table)
        self.assertIn("| Lead | opus/high | 2 | 45,445 | 8 | 67 |", table)
        self.assertIn("| **Total** | | 3 | 57,445 | 11 | 87 |", table)

    def test_amend_last_adds_the_trailer_once(self):
        write(self.path, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        self.script.append_row(self.path, "2 Plan", "Lead", "plan written", today="2026-01-02")
        self.script.append_row(self.path, "2 Plan", "Devil's Advocate", "a|b", today="2026-01-02")
        self.script.append_row(self.path, "2 Plan revise", "Lead", "revised", today="2026-01-02")
        row = self.script.amend_last(self.path, "Lead", ("opus/high", 8000, 2, 10))
        self.assertEqual(row, "| 2026-01-02 | 2 Plan revise | Lead | revised (opus/high · 8,000 tokens · 2 tool uses · 10 s) |")
        self.assertIsNone(self.script.amend_last(self.path, "Lead", ("opus/high", 1, 1, 1)), "amended twice")
        self.assertIsNone(self.script.amend_last(self.path, "Tester", ("sonnet/medium", 1, 1, 1)), "no such row")
        row = self.script.amend_last(self.path, "Devil's Advocate", ("sonnet/high", 12000, 3, 20))
        self.assertEqual(row, "| 2026-01-02 | 2 Plan | Devil's Advocate | a\\|b "
                              "(sonnet/high · 12,000 tokens · 3 tool uses · 20 s) |")
        with open(self.path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("| 2026-01-02 | 2 Plan | Lead | plan written |\n", text)
        self.assertIn("| Lead | opus/high | 1 | 8,000 | 2 | 10 |", self.script.summary(self.path))
        self.assertIn("| **Total** | | 2 | 20,000 | 5 | 30 |", self.script.summary(self.path))

    def test_amend_last_keeps_crlf(self):
        write(self.path, "| Date |\r\n| - |\r\n| 2026-01-02 | 6 Implement | Dev | done |\r\n", newline="")
        self.script.amend_last(self.path, "Dev", ("sonnet/medium", 500, 1, 2))
        with open(self.path, "rb") as handle:
            data = handle.read()
        self.assertEqual(data, b"| Date |\r\n| - |\r\n| 2026-01-02 | 6 Implement | Dev | done "
                               b"(sonnet/medium \xc2\xb7 500 tokens \xc2\xb7 1 tool uses \xc2\xb7 2 s) |\r\n")

    def test_replace_last_corrects_an_existing_trailer(self):
        write(self.path, "| Date |\r\n| - |\r\n", newline="")
        self.script.append_row(self.path, "2 Plan", "Lead", "plan written", today="2026-01-02",
                               launch=("opus/high", 1, 0, 0))
        self.script.append_row(self.path, "6 Implement", "Dev", "done", today="2026-01-02")
        self.assertIsNone(self.script.amend_last(self.path, "Dev", ("sonnet/medium", 5, 1, 1), replace=True),
                          "no trailer to replace")
        row = self.script.amend_last(self.path, "Lead", ("opus/high", 37445, 6, 57), replace=True)
        self.assertEqual(row, "| 2026-01-02 | 2 Plan | Lead | plan written (opus/high · 37,445 tokens · 6 tool uses · 57 s) |")
        with open(self.path, "rb") as handle:
            self.assertIn(row.encode() + b"\r\n| 2026-01-02 | 6 Implement | Dev | done |\r\n", handle.read())
        self.assertIn("| **Total** | | 1 | 37,445 | 6 | 57 |", self.script.summary(self.path))

    def test_cli_refuses_placeholder_metrics_and_replaces_a_trailer(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-lead.md"), "---\nmodel: opus\neffort: high\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n| 2026-01-02 | 2 Plan | Lead | plan (opus/high · 9 tokens · 0 tool uses · 0 s) |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True,
                                  text=True, check=False)
        metrics = ["--agent", "squad-lead", "--tool-uses", "0", "--seconds", "0"]
        for placeholder in ("0", "1", "999"):
            self.assertEqual(run("3 Review", "Lead", "x", "--tokens", placeholder, *metrics).returncode, 2, placeholder)
        self.assertEqual(run("--amend-last", "Lead", "--tokens", "1500", *metrics).returncode, 1)
        both = run("--amend-last", "Lead", "--replace-last", "Lead", "--tokens", "1500", *metrics)
        self.assertEqual(both.returncode, 2)
        done = run("--replace-last", "Lead", "--tokens", "1500", *metrics)
        self.assertEqual(done.returncode, 0, done.stderr)
        with open(log, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "| Date |\n| 2026-01-02 | 2 Plan | Lead | plan "
                                            "(opus/high · 1,500 tokens · 0 tool uses · 0 s) |\n")

    def test_cli_rounds_decimal_seconds_and_refuses_non_numbers(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-lead.md"), "---\nmodel: opus\neffort: high\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(seconds):
            return subprocess.run([sys.executable, script, "issue-1", "2 Plan", "Lead", "plan", "--agent", "squad-lead",
                                   "--tokens", "1500", "--tool-uses", "1", "--seconds", seconds], cwd=root,
                                  capture_output=True, text=True, check=False)
        done = run("495.4")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("· 495 s)", done.stdout)
        self.assertIn("· 496 s)", run("495.6").stdout)
        for bad in ("abc", "nan", "inf", "-1"):
            self.assertEqual(run(bad).returncode, 2, bad)

    def test_agent_launch_reads_the_agent_file(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-lead.md"),
              "---\nname: squad-lead\ndescription: Lead.\nmodel: opus\neffort: high\n---\n\n# Lead\n")
        write(os.path.join(root, ".claude", "agents", "squad-dev.md"), "---\nname: squad-dev\nmodel: sonnet\n---\n")
        self.assertEqual(self.script.agent_launch(root, "squad-lead"), "opus/high")
        self.assertEqual(self.script.agent_launch(root, "squad-lead.md"), "opus/high")
        self.assertIsNone(self.script.agent_launch(root, "squad-dev"), "no effort")
        for bad in ("squad-tester", "../agents/squad-lead", "/etc/passwd", ".."):
            self.assertIsNone(self.script.agent_launch(root, bad), bad)

    def test_row_carries_the_time_of_day(self):
        write(self.path, "| Date |\n")
        row = self.script.append_row(self.path, "1 Intake", "Orchestrator", "branch created")
        self.assertRegex(row, r"^\| \d{4}-\d{2}-\d{2} \d{2}:\d{2} \| 1 Intake \| Orchestrator \| branch created \|$")
        self.assertIsNotNone(self.script.amend_last(self.path, "Orchestrator", ("opus/high", 5000, 1, 2)))

    def test_summary_measures_the_orchestrator_from_timed_rows(self):
        write(self.path, "| Date | Step | Member | Result |\n| - | - | - | - |\n"
                         "| 2026-01-01 | 0 Old | Orchestrator | date-only row, not timed |\n")
        self.script.append_row(self.path, "1 Intake", "Orchestrator", "branch", today="2026-01-02 13:05")
        self.script.append_row(self.path, "2 Plan", "Lead", "plan", today="2026-01-02 13:20",
                               launch=("opus/medium", 50000, 9, 600))
        self.script.append_row(self.path, "7 Code check", "Orchestrator", "format check fails", today="2026-01-02 13:30")
        self.script.append_row(self.path, "7 Code check", "Orchestrator", "gates pass", today="2026-01-02 13:40")
        self.script.append_row(self.path, "8 Review", "Reviewer", "clean", today="2026-01-02 13:45",
                               launch=("opus/medium", 30000, 5, 300))
        table = self.script.summary(self.path)
        self.assertIn("| **Total** | | 2 | 80,000 | 14 | 900 |", table)
        self.assertIn("| Orchestrator | 2,400 | 1,500 | 2 |", table)
        write(self.path, "| Date |\n| 2026-01-02 | 2 Plan | Lead | plan (opus/high · 9,000 tokens · 1 tool uses · 5 s) |\n")
        self.assertNotIn("Wall time", self.script.summary(self.path), "date-only record has no orchestrator table")

    def test_continued_launch_logs_the_rounds_share(self):
        write(self.path, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        self.assertIsNone(self.script.previous_tokens(self.path, "Reviewer"), "no launch yet")
        self.assertIsNone(self.script.continued_launch(self.path, "Reviewer", ("opus/medium", 5000, 1, 1)))
        self.script.append_row(self.path, "8 Review", "Reviewer", "2 findings", today="2026-01-02 13:00",
                               launch=("opus/medium", 137666, 38, 279))
        self.script.append_row(self.path, "8 Security diff", "Security", "APPROVED", today="2026-01-02 13:00",
                               launch=("opus/medium", 89977, 16, 120))
        # The notification of a continued agent reports its tokens since the first launch (139,230), its tool
        # uses and seconds for the round alone.
        share = self.script.continued_launch(self.path, "Reviewer", ("opus/medium", 139230, 2, 21))
        self.assertEqual(share, ("opus/medium", 1564, 2, 21, True, None))
        row = self.script.append_row(self.path, "8 Review delta", "Reviewer", "APPROVE (continued)",
                                     today="2026-01-02 13:05", launch=share)
        self.assertTrue(row.endswith("(opus/medium · 1,564 tokens · 2 tool uses · 21 s · continued) |"), row)
        # A second continuation subtracts the fresh launch and the first continuation together.
        share = self.script.continued_launch(self.path, "Reviewer", ("opus/medium", 150000, 5, 100))
        self.assertEqual(share, ("opus/medium", 10770, 5, 100, True, None))
        self.script.append_row(self.path, "8 Review delta 2", "Reviewer", "APPROVE", today="2026-01-02 13:10",
                               launch=share)
        share = self.script.continued_launch(self.path, "Security", ("opus/medium", 98025, 2, 12))
        self.assertEqual(share, ("opus/medium", 8048, 2, 12, True, None))
        # A token figure below the earlier total was already the round alone and is kept.
        self.assertEqual(self.script.continued_launch(self.path, "Security", ("opus/medium", 5000, 1, 9)),
                         ("opus/medium", 5000, 1, 9, True, None))
        self.script.append_row(self.path, "3 Confirm", "Security", "APPROVED", today="2026-01-02 13:10", launch=share)
        table = self.script.summary(self.path)
        self.assertIn("| Reviewer | opus/medium | 3 (2 continued) | 150,000 | 45 | 400 |", table)
        self.assertIn("| Security | opus/medium | 2 (1 continued) | 98,025 | 18 | 132 |", table)
        self.assertIn("| **Total** | | 5 (3 continued) | 248,025 | 63 | 532 |", table)
        self.assertNotIn("Incomplete", table)

    def test_cli_logs_a_continuation_and_refuses_two_members_in_one_row(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-reviewer.md"), "---\nmodel: opus\neffort: medium\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n| 2026-01-02 13:00 | 8 Review | Reviewer | 1 finding "
                   "(opus/medium · 100,000 tokens · 30 tool uses · 200 s) |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True,
                                  text=True, check=False)
        usage = ["--agent", "squad-reviewer", "--tokens", "101500", "--tool-uses", "2", "--seconds", "30"]
        two = run("8 Review", "Reviewer / Security", "both approve", *usage)
        self.assertEqual(two.returncode, 2, two.stderr)
        self.assertIn("one row per launch", two.stderr)
        self.assertEqual(run("8 Review", "Reviewer, Security", "x").returncode, 2)
        self.assertEqual(run("8 Review", "Reviewer and Security", "x").returncode, 2)
        self.assertEqual(run("8 Review delta", "Reviewer", "APPROVE", "--continued").returncode, 2, "no usage")
        self.assertEqual(run("3 Confirm", "Security", "APPROVED", "--continued", *usage).returncode, 1,
                         "no earlier usage of Security")
        done = run("8 Review delta", "Reviewer", "APPROVE", "--continued", *usage)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.rstrip().endswith("(opus/medium · 1,500 tokens · 2 tool uses · 30 s · continued) |"),
                        done.stdout)
        self.assertEqual(run("8 Review delta 2", "Reviewer", "APPROVE").returncode, 0)
        amended = run("--amend-last", "Reviewer", "--continued", "--agent", "squad-reviewer", "--tokens", "103000",
                      "--tool-uses", "1", "--seconds", "10")
        self.assertEqual(amended.returncode, 0, amended.stderr)
        self.assertIn("(opus/medium · 1,500 tokens · 1 tool uses · 10 s · continued) |", amended.stdout)
        complete = run("--summary")
        self.assertEqual(complete.returncode, 0, complete.stdout)
        self.assertIn("| Reviewer | opus/medium | 3 (2 continued) | 103,000 | 33 | 240 |", complete.stdout)
        # A wrong continued trailer is replaced against the totals before it, not against itself.
        replaced = run("--replace-last", "Reviewer", "--continued", "--agent", "squad-reviewer", "--tokens", "104000",
                       "--tool-uses", "2", "--seconds", "20")
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertIn("(opus/medium · 2,500 tokens · 2 tool uses · 20 s · continued) |", replaced.stdout)
        self.assertIn("| Reviewer | opus/medium | 3 (2 continued) | 104,000 | 34 | 250 |", run("--summary").stdout)

    def test_continuation_at_another_step_warns_unless_it_names_its_round(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-dev.md"), "---\nmodel: sonnet\neffort: medium\n---\n")
        write(os.path.join(root, "specs", "issue-1", "log.md"),
              "| Date |\n| 2026-01-02 13:00 | 4 Skeleton | Dev | built (sonnet/medium · 60,000 tokens · 10 tool uses "
              "· 300 s) |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True,
                                  text=True, check=False)
        usage = ["--agent", "squad-dev", "--tokens", "90000", "--tool-uses", "5", "--seconds", "60"]
        implement = run("6 Implement", "Dev", "done", "--continued", *usage)
        self.assertEqual(implement.returncode, 0, implement.stderr)
        self.assertIn("WARNING: '6 Implement' continues Dev's launch of step '4 Skeleton'", implement.stdout)
        self.assertIn("first launch of another mode is a fresh launch", implement.stdout)
        for quiet in ("4 Skeleton fix", "7 Fix", "8 Delta"):
            self.assertNotIn("WARNING", run(quiet, "Dev", "done", "--continued", *usage).stdout, quiet)
        self.assertEqual(run("9 Approve", "Dev", "pending", "--agent", "squad-dev").returncode, 0)
        amended = run("--amend-last", "Dev", "--continued-from", "4 Skeleton", *usage)
        self.assertEqual(amended.returncode, 0, amended.stderr)
        self.assertIn("WARNING: '9 Approve' continues Dev's launch of step '4 Skeleton'", amended.stdout)

    def test_continued_from_subtracts_the_continued_launch_only(self):
        write(self.path, "| Date |\n")
        implement, docs = "6 Implement (rows 9-14)", "6 Docs (rows 15-18)"
        self.script.append_row(self.path, "4 Skeleton", "Dev", "built", today="2026-01-02 13:00",
                               launch=("sonnet/medium", 60000, 10, 300))
        self.script.append_row(self.path, implement, "Dev", "done", today="2026-01-02 14:00",
                               launch=("sonnet/medium", 400000, 80, 1800))
        self.script.append_row(self.path, docs, "Dev", "done", today="2026-01-02 14:30",
                               launch=("sonnet/medium", 181167, 20, 275))
        # The implement agent is continued: its tokens since its first launch are 404,178.
        self.assertIsNone(self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 404178, 5, 317),
                                                       origin="6 Review"), "no fresh launch of that step")
        share = self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 404178, 5, 317), origin=implement)
        self.assertEqual(share, ("sonnet/medium", 4178, 5, 317, True, implement))
        row = self.script.append_row(self.path, "7 Fix", "Dev", "fixed", today="2026-01-02 15:00", launch=share)
        self.assertTrue(row.endswith("(sonnet/medium · 4,178 tokens · 5 tool uses · 317 s · continued from "
                                     "6 Implement (rows 9-14)) |"), row)
        # A plain continuation still belongs to the last fresh launch (docs), not to the implement chain …
        share = self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 190000, 3, 40))
        self.assertEqual(share[1], 8833)
        self.script.append_row(self.path, "8 Fix docs", "Dev", "fixed", today="2026-01-02 15:10", launch=share)
        # … and the next continuation of the implement agent subtracts that chain with its own continuation.
        share = self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 410000, 4, 90), origin=implement)
        self.assertEqual(share[1], 5822)
        self.script.append_row(self.path, "8 Fix 2", "Dev", "fixed", today="2026-01-02 15:20", launch=share)
        self.assertIn("| Dev | sonnet/medium | 6 (3 continued) | 660,000 | 122 | 2822 |", self.script.summary(self.path))
        # A replaced continuation is computed against its chain without itself.
        share = self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 411000, 4, 90), skip_last=True,
                                             origin=implement)
        self.assertEqual(share[1], 6822)
        self.assertIn("continued from 6 Implement (rows 9-14)) |",
                      self.script.amend_last(self.path, "Dev", share, replace=True))
        # A step with a pipe stays one cell, in the row and in the trailer.
        self.script.append_row(self.path, "6 A | B", "Dev", "done", today="2026-01-02 16:00",
                               launch=("sonnet/medium", 50000, 5, 50))
        share = self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 52000, 1, 5), origin="6 A | B")
        row = self.script.append_row(self.path, "7 Fix", "Dev", "a | b", today="2026-01-02 16:05", launch=share)
        self.assertTrue(row.endswith("| a \\| b (sonnet/medium · 2,000 tokens · 1 tool uses · 5 s · continued from "
                                     "6 A \\| B) |"), row)
        self.assertEqual(self.script.continued_launch(self.path, "Dev", ("sonnet/medium", 53000, 1, 5),
                                                      origin="6 A | B")[1], 1000)

    def test_cli_continued_from(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-dev.md"), "---\nmodel: sonnet\neffort: medium\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n"
                   "| 2026-01-02 13:00 | 6 Implement | Dev | done (sonnet/medium · 100,000 tokens · 30 tool uses · 900 s) |\n"
                   "| 2026-01-02 14:00 | 6 Docs | Dev | done (sonnet/medium · 50,000 tokens · 10 tool uses · 200 s) |\n")

        def run(*args):
            return subprocess.run([sys.executable, os.path.join(TOOLS, "squad-log.py"), "issue-1", *args], cwd=root,
                                  capture_output=True, text=True, check=False)
        usage = ["--agent", "squad-dev", "--tokens", "104000", "--tool-uses", "4", "--seconds", "60"]
        missing = run("7 Fix", "Dev", "fixed", "--continued-from", "6 Review", *usage)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("no fresh launch of Dev with usage at step '6 Review'", missing.stdout)
        done = run("7 Fix", "Dev", "fixed", "--continued-from", "6 Implement", *usage)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("(sonnet/medium · 4,000 tokens · 4 tool uses · 60 s · continued from 6 Implement) |", done.stdout)
        self.assertEqual(run("7 Fix 2", "Dev", "fixed").returncode, 0)
        amended = run("--amend-last", "Dev", "--continued-from", "6 Implement", "--agent", "squad-dev", "--tokens",
                      "105000", "--tool-uses", "2", "--seconds", "30")
        self.assertIn("(sonnet/medium · 1,000 tokens · 2 tool uses · 30 s · continued from 6 Implement) |",
                      amended.stdout)
        self.assertIn("| Dev | sonnet/medium | 4 (2 continued) | 155,000 | 46 | 1190 |", run("--summary").stdout)

    def test_squad_prefixed_cells_of_non_launches_are_written_as_their_exact_cells(self):
        for given, wanted in (("squad-orchestrator", "Orchestrator"), ("Squad-User", "User"), ("orchestrator", "Orchestrator"),
                              ("product manager", "Product Manager"), ("squad-lead", "squad-lead"), ("Lead", "Lead")):
            self.assertEqual(self.script.canonical_member(given), wanted, given)
        self.assertIsNone(self.script.canonical_member(None))
        root = os.path.join(self.dir.name, "repo")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n")
        result = subprocess.run([sys.executable, os.path.join(TOOLS, "squad-log.py"), "issue-1", "7 Gates",
                                 "squad-orchestrator", "ran"], cwd=root, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = subprocess.run([sys.executable, os.path.join(TOOLS, "squad-log.py"), "issue-1", "--summary"],
                                 cwd=root, capture_output=True, text=True, check=False)
        self.assertEqual(summary.returncode, 0, summary.stdout + summary.stderr)
        with open(log, encoding="utf-8") as handle:
            self.assertIn("| 7 Gates | Orchestrator | ran |", handle.read())

    def test_first_row_replaces_the_placeholder_heading(self):
        for folder, heading in (("issue-3", "issue #3"), ("feature-incidents-view", "feature incidents-view")):
            path = os.path.join(self.dir.name, folder, "log.md")
            write(path, "# Log: <issue #number | feature name>\n\nIntro\n\n| Date |\n")
            self.script.append_row(path, "1 Intake", "Orchestrator", "branch")
            self.script.append_row(path, "2 Plan", "Orchestrator", "plan")
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertTrue(text.startswith(f"# Log: {heading}\n\nIntro"), text)
            self.assertEqual(text.count("# Log:"), 1)

    def test_a_log_with_its_own_heading_is_left_alone(self):
        write(self.path, "# Log: custom\n\n| Date |\n")
        self.script.append_row(self.path, "1 Intake", "Orchestrator", "branch")
        with open(self.path, encoding="utf-8") as handle:
            self.assertTrue(handle.read().startswith("# Log: custom\n"))

    def test_product_manager_and_user_rows_are_not_launches(self):
        write(self.path, "| Date |\n"
                         "| 2026-01-02 13:00 | 1 Intake | Orchestrator | branch |\n"
                         "| 2026-01-02 13:05 | 2 Plan | Lead | plan (opus/high · 50,000 tokens · 9 tool uses · 300 s) |\n"
                         "| 2026-01-02 13:30 | 2 Escalation | Product Manager | option B |\n"
                         "| 2026-01-02 14:00 | 7 Reference host | User | 1.4 s on the reference host |\n")
        table = self.script.summary(self.path)
        self.assertNotIn("Incomplete", table)
        self.assertIn("| **Total** | | 1 | 50,000 | 9 | 300 |", table)

    def test_summary_lists_launch_rows_without_usage(self):
        root = os.path.join(self.dir.name, "repo")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n"
                   "| 2026-01-02 13:00 | 1 Intake | Orchestrator | branch |\n"
                   "| 2026-01-02 13:10 | 2 Plan | squad-lead | done (opus/medium · 50,000 tokens · 9 tool uses · 500 s) |\n"
                   "| 2026-01-02 13:12 | 2 Challenge | squad-devils-advocate, squad-security | both fine |\n"
                   "| 2026-01-02 13:20 | 8 Review | squad-reviewer | APPROVE (23,965 tokens · 6 tool uses · 27 s) |\n"
                   "| 2026-01-02 13:21 | 9 PR approval | Orchestrator | approved by checklist |\n")
        result = subprocess.run([sys.executable, os.path.join(TOOLS, "squad-log.py"), "issue-1", "--summary"],
                                cwd=root, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("| **Total** | | 1 | 50,000 | 9 | 500 |", result.stdout)
        self.assertIn("**Incomplete:** 2 launch row(s) without usage", result.stdout)
        self.assertIn("`2 Challenge · squad-devils-advocate, squad-security`, `8 Review · squad-reviewer`", result.stdout)
        self.assertIn("| Orchestrator | 1,260 | 760 | 0 |", result.stdout, "a trailer without model/effort counts as missing")

    def test_summary_fails_on_commits_after_the_pr_without_a_review_row(self):
        root = os.path.join(self.dir.name, "repo")
        os.makedirs(root)

        def commit(message, when, *paths, remove=False):
            env = {**os.environ, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when}
            for args in (["rm", "-q", "-r", *paths] if remove else ["add", *paths], ["commit", "-q", "-m", message]):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                                *args], cwd=root, env=env, check=True, capture_output=True)

        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=root, check=True)
        write(os.path.join(root, "specs", "issue-1-fix", "log.md"), "| Date |\n")
        write(os.path.join(root, "a.py"), "a = 1\n")
        commit("intake", "2026-01-02T13:00:00Z", "specs", "a.py")
        commit("remove the work folder", "2026-01-02T14:00:00Z", "specs", remove=True)
        write(os.path.join(root, "a.py"), "a = 2\n")
        commit("fix a Sonar finding", "2026-01-02T15:00:00Z", "a.py")
        log = ("| 2026-01-02 13:00 | 1 Intake | Orchestrator | branch |\n"
               "| 2026-01-02 14:50 | 11 Sonar | squad-code-officer | fixed (haiku/low · 9,000 tokens · 3 tool uses · 20 s) |\n")

        def summary(text):
            return subprocess.run([sys.executable, os.path.join(TOOLS, "squad-log.py"), "issue-1", "--summary",
                                   "--stdin"], cwd=root, input=text, capture_output=True, text=True, check=False)
        result = summary(log)
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("Unreviewed after the PR: 1 commit(s)", result.stderr)
        self.assertNotIn("Unreviewed", result.stdout, "the posted tables stay clean")
        reviewed = log + ("| 2026-01-02 15:05 | 11 Review delta | squad-reviewer | APPROVE "
                          "(opus/medium · 20,000 tokens · 4 tool uses · 40 s) |\n")
        self.assertEqual(summary(reviewed).returncode, 0, "a delta review after the last fix clears it")
        verbatim = log + "| 2026-01-02 15:00 | 11 Fix | Orchestrator | verbatim fix of a doc sentence |\n"
        self.assertEqual(summary(verbatim).returncode, 0, "a verbatim fix needs no delta round")
        early = log + ("| 2026-01-02 14:55 | 11 Review delta | squad-reviewer | APPROVE "
                       "(opus/medium · 20,000 tokens · 4 tool uses · 40 s) |\n")
        self.assertEqual(summary(early).returncode, 4, "a review before the last fix does not cover it")
        env = {**os.environ, "GIT_COMMITTER_DATE": "2026-01-02T16:00:00Z", "GIT_AUTHOR_DATE": "2026-01-02T16:00:00Z"}
        for args in (["checkout", "-q", "-b", "main", "HEAD~2"], ["commit", "-q", "--allow-empty", "-m", "main moved"],
                     ["checkout", "-q", "work"], ["merge", "-q", "--no-edit", "--no-ff", "main"]):
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                           cwd=root, env=env, check=True, capture_output=True)
        self.assertEqual(summary(reviewed).returncode, 0, "a merge of the base branch is no fix to review")

    def test_orchestrator_counts_parallel_launches_once(self):
        write(self.path, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        self.script.append_row(self.path, "1 Intake", "Orchestrator", "branch", today="2026-01-02 13:00")
        self.script.append_row(self.path, "2 Challenge", "Devil's Advocate", "minor", today="2026-01-02 13:10",
                               launch=("sonnet/medium", 40000, 10, 600))
        self.script.append_row(self.path, "3 Plan security", "Security", "APPROVED", today="2026-01-02 13:10",
                               launch=("opus/medium", 60000, 12, 300))
        self.script.append_row(self.path, "4 Skeleton", "Dev", "built", today="2026-01-02 13:18",
                               launch=("sonnet/medium", 50000, 8, 240))
        self.script.append_row(self.path, "9 PR approval", "Orchestrator", "approved", today="2026-01-02 13:20")
        table = self.script.summary(self.path)
        self.assertIn("| **Total** | | 3 | 150,000 | 30 | 1140 |", table)
        # 13:00–13:10 the two parallel launches (600 s once), 13:14–13:18 the Dev (240 s): 360 s uncovered.
        self.assertIn("| Orchestrator | 1,200 | 360 | 0 |", table)

    def test_amend_with_step_reaches_an_earlier_row_of_the_member(self):
        write(self.path, "| Date |\n")
        self.script.append_row(self.path, "2 Plan", "Lead", "plan", today="2026-01-02 13:00",
                               launch=("opus/medium", 50000, 9, 500))
        self.script.append_row(self.path, "2 Challenge", "Devil's Advocate", "minor", today="2026-01-02 13:05")
        self.script.append_row(self.path, "3 Plan security", "Security", "CHANGES_REQUIRED", today="2026-01-02 13:05")
        self.script.append_row(self.path, "2 Plan revise", "Lead", "revised", today="2026-01-02 13:09")
        self.script.append_row(self.path, "3 Plan security delta", "Security", "APPROVED", today="2026-01-02 13:10")
        self.assertIsNone(self.script.amend_last(self.path, "Security", ("opus/medium", 1500, 1, 1), step="3 Review"),
                          "no row of that step")
        row = self.script.amend_last(self.path, "Security", ("opus/medium", 45751, 7, 108), step="3 Plan security")
        self.assertEqual(row, "| 2026-01-02 13:05 | 3 Plan security | Security | CHANGES_REQUIRED "
                              "(opus/medium · 45,751 tokens · 7 tool uses · 108 s) |")
        self.assertIsNone(self.script.amend_last(self.path, "Security", ("opus/medium", 1500, 1, 1), step="3 Plan security"),
                          "amended twice")
        # The member's last row is untouched and can still be amended without a selector, as a continuation
        # whose share is computed from the rows before it.
        share = self.script.continued_launch(self.path, "Security", ("opus/medium", 70000, 4, 52), step="3 Plan security delta")
        self.assertEqual(share, ("opus/medium", 24249, 4, 52, True, None))
        row = self.script.amend_last(self.path, "Security", share, step="3 Plan security delta")
        self.assertIn("APPROVED (opus/medium · 24,249 tokens · 4 tool uses · 52 s · continued) |", row)
        row = self.script.amend_last(self.path, "Lead", ("opus/medium", 20000, 5, 60), step="2 Plan revise")
        self.assertIn("| 2 Plan revise | Lead | revised (opus/medium · 20,000 tokens · 5 tool uses · 60 s) |", row)
        with open(self.path, encoding="utf-8") as handle:
            self.assertIn("| 2 Plan | Lead | plan (opus/medium · 50,000 tokens · 9 tool uses · 500 s) |", handle.read())
        self.assertIn("| Security | opus/medium | 2 (1 continued) | 70,000 | 11 | 160 |", self.script.summary(self.path))

    def test_unreported_launch_is_counted_and_named_not_summed(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-devils-advocate.md"), "---\nmodel: sonnet\neffort: medium\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n"
                   "| 2026-01-02 13:00 | 1 Intake | Orchestrator | branch |\n"
                   "| 2026-01-02 13:10 | 2 Plan | Lead | done (opus/medium · 50,000 tokens · 9 tool uses · 500 s) |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True,
                                  text=True, check=False)
        self.assertEqual(run("2 Challenge", "Devil's Advocate", "0 major, 2 minor", "--unreported", "--agent",
                             "squad-devils-advocate").returncode, 2, "--unreported is an amend option")
        self.assertEqual(run("2 Challenge", "Devil's Advocate", "0 major, 2 minor", "--step", "2 Plan").returncode, 2,
                         "--step is an amend option")
        self.assertEqual(run("2 Challenge", "Devil's Advocate", "0 major, 2 minor").returncode, 0)
        self.assertEqual(run("--amend-last", "Devil's Advocate", "--unreported", "--agent", "squad-devils-advocate",
                             "--tokens", "5000", "--tool-uses", "1", "--seconds", "1").returncode, 2, "no numbers")
        self.assertEqual(run("--amend-last", "Devil's Advocate", "--unreported").returncode, 2, "needs the model")
        self.assertEqual(run("--replace-last", "Devil's Advocate", "--unreported", "--agent",
                             "squad-devils-advocate").returncode, 2, "replace needs numbers")
        marked = run("--amend-last", "Devil's Advocate", "--unreported", "--agent", "squad-devils-advocate")
        self.assertEqual(marked.returncode, 0, marked.stderr)
        self.assertIn("| 2 Challenge | Devil's Advocate | 0 major, 2 minor (sonnet/medium · usage not reported) |",
                      marked.stdout)
        again = run("--amend-last", "Devil's Advocate", "--unreported", "--agent", "squad-devils-advocate")
        self.assertEqual(again.returncode, 1, "marked once")
        self.assertIn("--replace-last", again.stdout)
        complete = run("--summary")
        self.assertEqual(complete.returncode, 0, complete.stdout)
        self.assertIn("| Devil's Advocate | sonnet/medium | 1 | 0 | 0 | 0 |", complete.stdout)
        self.assertIn("| **Total** | | 2 | 50,000 | 9 | 500 |", complete.stdout)
        self.assertIn("**Without reported usage:** 1 launch(es)", complete.stdout)
        self.assertIn("`2 Challenge · Devil's Advocate`", complete.stdout)
        self.assertNotIn("**Incomplete:**", complete.stdout)
        replaced = run("--replace-last", "Devil's Advocate", "--agent", "squad-devils-advocate", "--tokens", "33612",
                       "--tool-uses", "9", "--seconds", "20")
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertIn("(sonnet/medium · 33,612 tokens · 9 tool uses · 20 s) |", replaced.stdout)
        self.assertNotIn("Without reported usage", run("--summary").stdout)
        self.assertIn("| **Total** | | 2 | 83,612 | 18 | 520 |", run("--summary").stdout)

    def test_rows_of_members_that_are_no_launch_take_no_metrics(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-lead.md"), "---\nmodel: opus\neffort: medium\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n| 2026-01-02 13:00 | 1 Intake | Orchestrator | branch |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True,
                                  text=True, check=False)
        self.assertEqual(run("2 Escalation", "Product Manager", "option B").returncode, 0)
        for args in (("2 Escalation", "Product Manager", "option B", "--agent", "squad-lead", "--tokens", "5000",
                      "--tool-uses", "1", "--seconds", "1"),
                     ("--amend-last", "Product Manager", "--unreported"),
                     ("--amend-last", "product manager", "--unreported", "--agent", "squad-lead"),
                     ("--replace-last", "User", "--agent", "squad-lead", "--tokens", "5000", "--tool-uses", "1",
                      "--seconds", "1"),
                     ("--amend-last", "Orchestrator", "--unreported", "--agent", "squad-lead"),
                     ("3 Intake", "Orchestrator", "x", "--tool-uses", "3"),
                     ("3 Intake", "User", "x", "--seconds", "9")):
            result = run(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertIn("is no launch", result.stderr)
        summary = run("--summary")
        self.assertEqual(summary.returncode, 0, summary.stdout)
        self.assertNotIn("Incomplete", summary.stdout)

    def test_agent_alone_marks_the_launch_pending_until_its_usage_is_amended(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-lead.md"), "---\nmodel: opus\neffort: medium\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True, text=True,
                                  check=False)

        self.assertEqual(run("2 Plan", "Lead", "plan", "--agent", "squad-lead").returncode, 0)
        with open(log, encoding="utf-8") as handle:
            self.assertIn("plan (opus/medium · usage pending) |", handle.read())
        summary = run("--summary")
        self.assertEqual(summary.returncode, 3)
        self.assertIn("2 Plan · Lead", summary.stdout)
        self.assertEqual(run("--amend-last", "Lead", "--agent", "squad-lead", "--tokens", "37445", "--tool-uses", "6",
                             "--seconds", "57").returncode, 0)
        with open(log, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("plan (opus/medium · 37,445 tokens · 6 tool uses · 57 s) |", text)
        self.assertNotIn("pending", text)
        self.assertEqual(run("--summary").returncode, 0)

    def test_pending_rows_take_amend_replace_unreported_and_continued(self):
        root = os.path.join(self.dir.name, "repo")
        write(os.path.join(root, ".claude", "agents", "squad-dev.md"), "---\nmodel: sonnet\neffort: medium\n---\n")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date | Step | Member | Result |\n| - | - | - | - |\n")
        script = os.path.join(TOOLS, "squad-log.py")

        def run(*args):
            return subprocess.run([sys.executable, script, "issue-1", *args], cwd=root, capture_output=True, text=True,
                                  check=False)

        numbers = ["--tool-uses", "5", "--seconds", "60"]
        self.assertEqual(run("6 Implement", "Dev", "done", "--agent", "squad-dev", "--tokens", "100000", *numbers)
                         .returncode, 0)
        self.assertEqual(run("8 Fix", "Dev", "fixed", "--launch", "sonnet/medium").returncode, 0)
        amended = run("--amend-last", "Dev", "--agent", "squad-dev", "--tokens", "120000", *numbers, "--continued")
        self.assertEqual(amended.returncode, 0, amended.stdout + amended.stderr)
        with open(log, encoding="utf-8") as handle:
            self.assertIn("fixed (sonnet/medium · 20,000 tokens · 5 tool uses · 60 s · continued) |", handle.read())
        self.assertEqual(run("9 Fix", "Dev", "again", "--agent", "squad-dev").returncode, 0)
        self.assertEqual(run("--amend-last", "Dev", "--unreported", "--agent", "squad-dev").returncode, 0)
        replaced = run("--replace-last", "Dev", "--agent", "squad-dev", "--tokens", "150000", *numbers, "--continued")
        self.assertEqual(replaced.returncode, 0, replaced.stdout + replaced.stderr)
        with open(log, encoding="utf-8") as handle:
            self.assertIn("again (sonnet/medium · 30,000 tokens · 5 tool uses · 60 s · continued) |", handle.read())
        self.assertEqual(run("10 Fix", "Dev", "more", "--agent", "squad-dev").returncode, 0)
        self.assertEqual(run("--amend-last", "Dev", "--unreported", "--agent", "squad-dev").returncode, 0)
        self.assertEqual(run("11 Fix", "Dev", "last", "--launch", "sonnet/medium").returncode, 0)
        self.assertEqual(run("12 Review", "Dev", "x", "--launch", "sonnet/medium").returncode, 0)
        pending = run("--replace-last", "Dev", "--step", "11 Fix", "--agent", "squad-dev", "--tokens", "160000",
                      *numbers)
        self.assertEqual(pending.returncode, 0, pending.stdout + pending.stderr)
        self.assertIn("last (sonnet/medium · 160,000 tokens · 5 tool uses · 60 s) |", pending.stdout)
        self.assertEqual(run("--summary").returncode, 3, "the last row is still pending")
        with open(log, encoding="utf-8") as handle:
            without_pending = "".join(line for line in handle if "12 Review" not in line)
        stdin = subprocess.run([sys.executable, script, "issue-1", "--summary", "--stdin"], cwd=root,
                               input=without_pending, capture_output=True, text=True, check=False)
        self.assertEqual(stdin.returncode, 0, stdin.stderr)
        self.assertIn("| **Total** |", stdin.stdout)
        self.assertEqual(run("1 Intake", "Orchestrator", "branch", "--agent", "squad-dev").returncode, 2)

    def test_tool_uses_or_seconds_alone_are_an_incomplete_set(self):
        root = os.path.join(self.dir.name, "repo")
        log = os.path.join(root, "specs", "issue-1", "log.md")
        write(log, "| Date |\n")
        for extra in (("--tool-uses", "4"), ("--seconds", "9"), ("--tool-uses", "4", "--seconds", "9")):
            result = subprocess.run([sys.executable, os.path.join(TOOLS, "squad-log.py"), "issue-1", "3 Test",
                                     "squad-tester", "t", *extra], cwd=root, capture_output=True, text=True,
                                    check=False)
            self.assertEqual(result.returncode, 2, extra)
            self.assertIn("go together", result.stderr)
        with open(log, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "| Date |\n")

    def test_controls_pipes_and_newlines_are_escaped(self):
        write(self.path, "| Date |\n")
        row = self.script.append_row(self.path, "2 Plan", "Lead", "a|b\nsecond \u202e line\tend", today="2026-01-02")
        self.assertEqual(row, "| 2026-01-02 | 2 Plan | Lead | a\\|b<br>second U+202E line end |")


class TestScopeCheck(unittest.TestCase):
    def setUp(self):
        self.script = load_script("scope-check")
        self.previous = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        git("init", "-q", "-b", "main")
        write("docs/CONTRIBUTING.md", "# Contributing\n\ntemplate text\n<!-- project:begin areas -->\nold\n"
              "<!-- project:end areas -->\nmore template text\n")
        write("README.md", "# Readme\n")
        write("src/a.go", "package a\n")
        write(".squad/stack.md", "# Stack\n")
        git("add", ".")
        git("commit", "-q", "-m", "base")
        git("checkout", "-q", "-b", "work")

    def tearDown(self):
        os.chdir(self.previous)
        self.dir.cleanup()

    def errors(self, tier=None, no_specs=False):
        base = self.script.merge_base()
        return self.script.check(self.script.changed_files(base), base, tier, no_specs)

    def test_base_that_is_not_an_ancestor_of_head_is_stale(self):
        self.assertFalse(self.script.base_is_stale())
        git("checkout", "-q", "main")
        write("README.md", "# Readme\n\nmain moved on\n")
        git("commit", "-q", "-am", "main moved")
        git("checkout", "-q", "work")
        write("src/a.go", "package a\n\nvar X = 1\n")
        git("commit", "-q", "-am", "work")
        self.assertTrue(self.script.base_is_stale())

    def test_clean_product_change_passes(self):
        write("src/a.go", "package a\n\nvar X = 1\n")
        write("specs/issue-1/log.md", "| Date |\n")
        self.assertEqual(self.errors(tier="standard"), [])

    def test_squad_files_are_reported_but_stack_and_project_are_allowed(self):
        write(".squad/routing.md", "# Routing\n")
        write(".squad/stack.md", "# Stack\n\nchanged\n")
        write("CLAUDE.md", "# x\n")
        found = self.errors()
        self.assertEqual([e.split(":")[0] for e in found], [".squad/routing.md", "CLAUDE.md"])

    def test_agents_md_and_its_mirror_change_only_in_project_blocks(self):
        text = "# Rules\n\ntemplate rule\n<!-- project:begin about -->\nold\n<!-- project:end about -->\n"
        for path in ("AGENTS.md", ".github/copilot-instructions.md"):
            write(path, text)
        git("add", "-A")
        git("commit", "-q", "-m", "instructions")
        git("branch", "-f", "main")
        for path in ("AGENTS.md", ".github/copilot-instructions.md"):
            write(path, text.replace("old", "new"))
        self.assertEqual(self.errors(tier="docs"), [], "a project block may change, also in the docs tier")
        write("AGENTS.md", text.replace("template rule", "edited rule").replace("old", "new"))
        self.assertEqual([e.split(":")[0] for e in self.errors()], ["AGENTS.md"])
        write("AGENTS.md", text.replace("old", "new"))
        write(".github/copilot-instructions.md", text)
        self.assertTrue(any("differ in the project block 'about'" in e for e in self.errors()),
                        "a block changed in one file only")
        write("AGENTS.md", text.replace("old", "new") + "<!-- project:begin extra -->\nx\n<!-- project:end extra -->\n")
        self.assertTrue(any("project block 'extra'" in e for e in self.errors()), "a block in one file only")
        os.remove("AGENTS.md")
        write(".github/copilot-instructions.md", text.replace("old", "new"))
        self.assertTrue(any("added or deleted" in e for e in self.errors()), "deleting AGENTS.md is no product change")

    def test_a_fork_never_changes_the_rules_not_even_a_project_block(self):
        text = "# Rules\n\n<!-- project:begin about -->\nold\n<!-- project:end about -->\n"

        class Fork:
            def before(self, path):
                return text

            def after(self, path):
                return text.replace("old", "new")
        found = self.script.check(["AGENTS.md"], None, None, False, Fork())
        self.assertTrue(found and "squad or instruction file" in found[0], found)

    def test_marked_file_edit_inside_project_block_passes_outside_fails(self):
        write("docs/CONTRIBUTING.md", "# Contributing\n\ntemplate text\n<!-- project:begin areas -->\nnew\n"
              "<!-- project:end areas -->\nmore template text\n")
        self.assertEqual(self.errors(), [])
        write("docs/CONTRIBUTING.md", "# Contributing\n\nedited template text\n<!-- project:begin areas -->\nnew\n"
              "<!-- project:end areas -->\nmore template text\n")
        self.assertIn("outside its <!-- project:", self.errors()[0])

    def test_control_character_in_markdown_is_reported(self):
        write("docs/decisions/0001-x.md", "# 0001\n\ntext \u202e here\n")
        self.assertIn("U+202E", self.errors()[0])

    def test_working_record_after_step_10_is_reported(self):
        write("specs/issue-1/plan.md", "# Plan\n")
        self.assertEqual(self.errors(no_specs=False), [])
        self.assertIn("working record still in the diff", self.errors(no_specs=True)[0])

    def test_docs_tier_allows_only_product_documentation(self):
        write("README.md", "# Readme\n\nmore\n")
        write("docs/guide.md", "# Guide\n")
        write("specs/issue-1/log.md", "| Date |\n")
        self.assertEqual(self.errors(tier="docs"), [])
        write("docs/areas/core.md", "# Core\n")
        write("src/a.go", "package a\n// comment\n")
        found = self.errors(tier="docs")
        self.assertEqual([e.split(":")[0] for e in found], ["docs/areas/core.md", "src/a.go"])

    def test_patch_tier_checks_the_line_budget(self):
        write("src/a.go", "package a\n\nvar X = 1\n")
        write("specs/issue-1/log.md", "".join(f"| row {n} |\n" for n in range(50)))
        self.assertEqual(self.errors(tier="patch"), [])
        write("src/b.go", "".join(f"var V{n} = {n}\n" for n in range(29)))
        found = self.errors(tier="patch")
        self.assertEqual(len(found), 1, found)
        self.assertIn("31 changed lines outside specs/", found[0])
        self.assertEqual(self.errors(tier="standard"), [], "the budget applies to tier patch only")


class TestScopeCheckPullRequest(unittest.TestCase):
    """The pull request mode: files and texts come from the GitHub API, nothing is checked out."""

    BLOCKS = ("# Contributing\n\ntemplate text\n<!-- project:begin areas -->\n{}\n<!-- project:end areas -->\n"
              "more template text\n")

    def setUp(self):
        self.script = load_script("scope-check")
        self.calls = []
        self.before = {"docs/CONTRIBUTING.md": self.BLOCKS.format("old"), "README.md": "# Readme\n"}
        self.after = {}
        self.files = []
        self.script.api_get = self.fake_api

    def fake_api(self, path, token, raw=False):
        self.calls.append(path)
        if "/contents/" in path:
            name, ref = path.split("/contents/")[1].split("?ref=")
            return (self.before if ref == "mergebase" else self.after).get(urllib.parse.unquote(name))
        if "/files?" in path:
            return json.dumps(self.files if "page=1" in path else [])
        if "/compare/" in path:
            return json.dumps({"merge_base_commit": {"sha": "mergebase"}})
        return json.dumps({"head": {"sha": "headsha", "repo": {"full_name": "fork/repo"}}, "base": {"sha": "basesha"}})

    def errors(self, files, no_specs=False):
        self.files = [{"filename": name} for name in files]
        source = self.script.PullRequestSource("owner/repo", 7, "token")
        return self.script.check(source.changed_files(), source.merge_base, None, no_specs, source)

    def test_product_change_passes_and_reads_the_fork_by_sha(self):
        self.after["src/a.go"] = "package a\n"
        self.assertEqual(self.errors(["src/a.go"]), [])
        self.assertIn("/repos/owner/repo/compare/basesha...headsha", self.calls)

    def test_squad_file_is_reported_and_a_rename_counts_under_the_old_name(self):
        self.files = [{"filename": "docs/x.md", "previous_filename": ".claude/settings.json"}]
        source = self.script.PullRequestSource("owner/repo", 7, "token")
        found = self.script.check(source.changed_files(), source.merge_base, None, False, source)
        self.assertEqual([e.split(":")[0] for e in found], [".claude/settings.json"])

    def test_marked_file_edit_outside_blocks_is_reported_inside_passes(self):
        self.after["docs/CONTRIBUTING.md"] = self.BLOCKS.format("new")
        self.assertEqual(self.errors(["docs/CONTRIBUTING.md"]), [])
        self.after["docs/CONTRIBUTING.md"] = self.BLOCKS.format("new").replace("template text", "edited")
        self.assertIn("outside its <!-- project:", self.errors(["docs/CONTRIBUTING.md"])[0])

    def test_control_character_in_markdown_and_working_record_are_reported(self):
        self.after["docs/a.md"] = "text \u202e here\n"
        self.after["specs/issue-1/log.md"] = "| Date |\n"
        found = self.errors(["docs/a.md", "specs/issue-1/log.md"], no_specs=True)
        self.assertEqual(len(found), 2, found)
        self.assertIn("U+202E", found[0])

    def test_deleted_file_has_no_text_after_and_is_not_an_edit_outside_blocks(self):
        self.assertEqual(self.errors(["docs/CONTRIBUTING.md"]), [])

    def test_contents_path_is_quoted(self):
        self.after["docs/a b.md"] = "# A\n"
        self.errors(["docs/a b.md"])
        self.assertIn("/repos/fork/repo/contents/docs/a%20b.md?ref=headsha", self.calls)

    def test_repository_name_from_the_api_is_checked(self):
        with self.assertRaises(SystemExit):
            self.script.checked_repository("../../etc")

    def test_pages_are_read_until_a_short_page(self):
        self.script.api_get = lambda path, token, raw=False: json.dumps(
            [{"filename": f"f{n}.txt"} for n in range(100)] if path.endswith("page=1") else [{"filename": "last.txt"}])
        source = self.script.PullRequestSource.__new__(self.script.PullRequestSource)
        source.repository, source.number, source.token = "owner/repo", 7, "token"
        self.assertEqual(len(source.changed_files()), 101)

    def test_tier_cannot_be_combined_with_a_pull_request(self):
        argv = ["scope-check.py", "--pull-request", "7", "--tier", "docs"]
        with mock.patch.object(sys, "argv", argv), self.assertRaises(SystemExit) as raised:
            self.script.main()
        self.assertEqual(raised.exception.code, 2)

    def test_pull_request_mode_needs_the_environment(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit):
            self.script.pull_request_source(7)


if __name__ == "__main__":
    unittest.main()
