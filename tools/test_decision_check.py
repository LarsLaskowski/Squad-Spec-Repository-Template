"""Unit tests for core/.squad/tools/decision-check.py (release tags of a repository without local ones, size
warnings of records and area documents): run `python3 -m unittest discover tools`."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "core", ".squad", "tools", "decision-check.py")
RECORD = """# 0001: Topic

- **Status:** Accepted
- **Date:** 2026-01-01
- **Supersedes:** —

## Decision

Do it.
"""
INDEX = ("# Decision records\n\n<!-- project:begin index -->\n| # | Title | Status | Date |\n| - | ----- | ------ | ---- |\n"
         "| 0001 | Topic | Accepted | 2026-01-01 |\n<!-- project:end index -->\n")
AREAS = ("# Areas\n\n<!-- project:begin area-index -->\n| Area | Scope | Not here |\n| ---- | ----- | -------- |\n"
         "| [Storage](storage.md) | Scope. | Elsewhere. |\n<!-- project:end area-index -->\n")


def load_script():
    spec = importlib.util.spec_from_file_location("decision_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


class TestReleaseTagsOfTheRemote(unittest.TestCase):
    """A record without `Area:` once areas exist: its error depends on whether it may be released."""

    def git(self, *args, cwd=None):
        subprocess.run(["git", "-C", cwd or self.repo, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.dir.name, "repo")
        self.remote = os.path.join(self.dir.name, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", self.remote], check=True)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        write(os.path.join(self.repo, "docs", "decisions", "0001-topic.md"), RECORD)
        write(os.path.join(self.repo, "docs", "decisions", "README.md"), INDEX)
        write(os.path.join(self.repo, "docs", "areas", "README.md"), AREAS)
        write(os.path.join(self.repo, "docs", "areas", "storage.md"), "# Storage\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "records")
        self.git("remote", "add", "origin", self.remote)
        self.git("push", "-q", "origin", "HEAD:refs/heads/main")

    def tearDown(self):
        self.dir.cleanup()

    def run_check(self):
        result = subprocess.run([sys.executable, SCRIPT], cwd=self.repo, capture_output=True, text=True,
                                encoding="utf-8")
        return result.returncode, result.stdout

    def test_a_remote_without_release_tags_releases_nothing(self):
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertNotIn("WARNING", output)
        self.assertIn("0001-topic.md: no '- **Area:**' line", output)
        self.assertNotIn("possibly released", output)

    def test_release_tags_on_the_remote_only_are_a_warning(self):
        self.git("tag", "v1.0.0")
        self.git("push", "-q", "origin", "v1.0.0")
        self.git("tag", "-d", "v1.0.0")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("WARNING: no local 'v*' tags although the remote 'origin' has some", output)
        self.assertIn("git fetch origin main --tags", output)
        self.assertIn("possibly released", output)

    def test_a_remote_that_cannot_be_asked_is_a_warning(self):
        self.git("remote", "set-url", "origin", os.path.join(self.dir.name, "missing.git"))
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("WARNING: no local 'v*' tags and the remote 'origin' could not be asked", output)
        self.assertIn("possibly released", output)

    def test_every_remote_is_asked(self):
        other = os.path.join(self.dir.name, "other.git")
        subprocess.run(["git", "init", "-q", "--bare", other], check=True)
        self.git("remote", "add", "upstream", other)
        self.git("tag", "v1.0.0")
        self.git("push", "-q", "upstream", "v1.0.0")
        self.git("tag", "-d", "v1.0.0")
        warnings = []
        self.assertIsNone(load_script().check_freeze(self.repo, {}, [], warnings))
        self.assertIn("the remote 'upstream' has some", warnings[0])

    def test_a_remote_that_does_not_answer_in_time_cannot_be_asked(self):
        script = load_script()
        with mock.patch.object(script.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 30)):
            self.assertIsNone(script.remote_release_tags(self.repo, "origin"))

    def test_local_release_tags_are_checked_as_before(self):
        self.git("tag", "v1.0.0")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertNotIn("WARNING", output)
        self.assertIn("released without a '- **Area:**' line", output)


class TestProcessFile(unittest.TestCase):
    """docs/decisions/process.md, the squad's process decisions, is no record: never indexed, never checked."""

    def test_the_process_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", repo], check=True)
            decisions = os.path.join(repo, "docs", "decisions")
            write(os.path.join(decisions, "README.md"), INDEX)
            shutil.copyfile(os.path.join(ROOT, "core", "docs", "decisions", "process.md"),
                            os.path.join(decisions, "process.md"))
            with open(os.path.join(decisions, "process.md"), "a", encoding="utf-8") as handle:
                handle.write("\n- **Status:** Superseded by 0009\n\nSee [0009](0009-gone.md).\n" + "word " * 3000)
            write(os.path.join(decisions, "0001-topic.md"), RECORD.replace("Do it.", "Do it ([process](process.md))."))
            result = subprocess.run([sys.executable, SCRIPT], cwd=repo, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("process.md", result.stdout)
        self.assertIn("Checked 1 decision records: PASS", result.stdout)


def chain_record(number, title, status, supersedes="—"):
    return (f"# {number}: {title}\n\n- **Status:** {status}\n- **Date:** 2026-01-01\n- **Area:** —\n"
            f"- **Source:** Squad adopted from Squad-Spec-Repository-Template\n- **Supersedes:** {supersedes}\n\n"
            "## Decision\n\nIt holds.\n")


class TestProcessRecordMigration(unittest.TestCase):
    """adopt-template step 8 on the chain 0002 → 0022 → 0037 plus 0044 amending 0037: for every release point, the
    log passes decision-check.py after the migration."""

    TITLE = "Squad working records stay off main"
    CHAIN = [("0002", "Superseded by 0022", "—"), ("0022", "Superseded by 0037", "0002"), ("0037", "Accepted", "0022"),
             ("0044", "Accepted", "0037 (amends it)")]

    def git(self, *args):
        subprocess.run(["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                       capture_output=True)

    def commit_chain(self, decisions, released_upto):
        """The chain committed record by record, tagged after the record at `released_upto` (-1: never)."""
        self.git("init", "-q")
        for i, (number, status, supersedes) in enumerate(self.CHAIN):
            write(os.path.join(decisions, f"{number}-chain.md"), chain_record(number, self.TITLE, status, supersedes))
            self.git("add", "-A")
            self.git("commit", "-qm", number)
            if i == released_upto:
                self.git("tag", "v1.0.0")

    def retire(self, decisions, released):
        """Step 8: delete the unreleased records (with the ones they supersede), supersede the released ones still in
        force or superseded by a deleted one with record 0050; returns the index rows."""
        deleted = [n for n, _, _ in self.CHAIN if n not in released]
        for number in deleted:
            os.remove(os.path.join(decisions, f"{number}-chain.md"))
        retired = [n for n, status, _ in self.CHAIN if n in released
                   and (status == "Accepted" or status.removeprefix("Superseded by ") in deleted)]
        for number, _, supersedes in self.CHAIN:
            if number in retired:
                write(os.path.join(decisions, f"{number}-chain.md"),
                      chain_record(number, self.TITLE, "Superseded by 0050", supersedes))
        rows = [(n, "Superseded by 0050" if n in retired else s) for n, s, _ in self.CHAIN if n not in deleted]
        if retired:
            write(os.path.join(decisions, "0050-moved.md"), chain_record(
                "0050", "The squad's process decisions live in process.md", "Accepted", ", ".join(retired)))
            rows.append(("0050", "Accepted"))
        return rows

    def migrate(self, released_upto):
        """Records up to `released_upto` (an index into CHAIN) are released; then step 8 retires the chain."""
        with tempfile.TemporaryDirectory() as self.repo:
            decisions = os.path.join(self.repo, "docs", "decisions")
            self.commit_chain(decisions, released_upto)
            rows = self.retire(decisions, [number for number, _, _ in self.CHAIN[:released_upto + 1]])
            write(os.path.join(decisions, "README.md"), INDEX.replace(
                "| 0001 | Topic | Accepted | 2026-01-01 |\n",
                "".join(f"| {n} | Topic | {s} | 2026-01-01 |\n" for n, s in rows)))
            result = subprocess.run([sys.executable, SCRIPT], cwd=self.repo, capture_output=True, text=True,
                                    encoding="utf-8")
        return result.returncode, result.stdout

    def test_every_release_point_leaves_a_consistent_log(self):
        for released_upto in (-1, 1, 2, 3):
            with self.subTest(released=[n for n, _, _ in self.CHAIN[:released_upto + 1]]):
                code, output = self.migrate(released_upto)
                self.assertEqual(code, 0, output)


def record_text(number, options, words=0):
    """A record with `options` numbered options and `words` filler words in its context."""
    listed = "\n".join(f"{i}. **Option {i}** — pros / cons." for i in range(1, options + 1))
    return (f"# {number}: Topic\n\n- **Status:** Accepted\n- **Date:** 2026-01-01\n- **Area:** Storage\n"
            f"- **Supersedes:** —\n\n## Context\n\n{'word ' * words}\n\n## Options considered\n\n{listed}\n"
            "  - a nested note, no option\n\n## Decision\n\nOption 1.\n\n## Consequences\n\n- One.\n")


class TestSizeWarnings(unittest.TestCase):
    """Records and area documents past their limits are warnings that name the split; the check still passes."""

    def git(self, *args):
        subprocess.run(["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                       capture_output=True)

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = self.dir.name
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.decisions = os.path.join(self.repo, "docs", "decisions")
        write(os.path.join(self.decisions, "0001-topic.md"), record_text("0001", 2))
        write(os.path.join(self.decisions, "0002-topic.md"), record_text("0002", 9))
        write(os.path.join(self.decisions, "0003-topic.md"), record_text("0003", 2, words=1600))
        write(os.path.join(self.decisions, "README.md"), INDEX.replace(
            "| 0001 | Topic | Accepted | 2026-01-01 |\n",
            "".join(f"| {n} | Topic | Accepted | 2026-01-01 |\n" for n in ("0001", "0002", "0003"))))
        write(os.path.join(self.decisions, "_template.md"), "# NNNN\n\n" + "word " * 1600)
        write(os.path.join(self.repo, "docs", "areas", "README.md"), AREAS + "word " * 6000)
        write(os.path.join(self.repo, "docs", "areas", "storage.md"), "# Storage\n\n" + "word " * 5001)
        write(os.path.join(self.repo, "docs", "areas", "_template.md"), "word " * 6000)

    def tearDown(self):
        self.dir.cleanup()

    def run_check(self):
        result = subprocess.run([sys.executable, SCRIPT], cwd=self.repo, capture_output=True, text=True,
                                encoding="utf-8")
        return result.returncode, [line for line in result.stdout.splitlines() if line.startswith("WARNING: ")]

    def test_records_and_areas_past_their_limits_are_warnings(self):
        code, warnings = self.run_check()
        self.assertEqual(code, 0, warnings)
        self.assertEqual(len(warnings), 3, warnings)
        self.assertIn("0002-topic.md: ", warnings[0])
        self.assertIn(" and 9 options (RECORD_MAX_WORDS 1500, RECORD_MAX_OPTIONS 8) - split it into one record per "
                      "decision: ", warnings[0])
        self.assertIn("0003-topic.md: ", warnings[1])
        self.assertIn("words and 2 options", warnings[1])
        self.assertIn("docs/areas/storage.md: 5003 words (AREA_MAX_WORDS 5000) - split it: ", warnings[2])

    def test_a_released_record_is_never_split(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "records")
        self.git("tag", "v1.0.0")
        _, warnings = self.run_check()
        self.assertEqual([w for w in warnings if "decisions/" in w], [])
        write(os.path.join(self.decisions, "0004-topic.md"), record_text("0004", 9))
        write(os.path.join(self.decisions, "README.md"), INDEX.replace(
            "| 0001 | Topic | Accepted | 2026-01-01 |\n",
            "".join(f"| {n} | Topic | Accepted | 2026-01-01 |\n" for n in ("0001", "0002", "0003", "0004"))))
        _, warnings = self.run_check()
        self.assertEqual([w.split(":", 2)[1].strip() for w in warnings if "decisions/" in w],
                         ["docs/decisions/0004-topic.md"])

    def test_an_unknown_release_state_says_so(self):
        script = load_script()
        records = {"0002": {"rel": "docs/decisions/0002-topic.md", "text": record_text("0002", 9)}}
        warnings = []
        script.check_record_sizes(records, None, warnings)
        self.assertIn("unless it is released", warnings[0])

    def test_options_are_the_top_level_items_of_their_section(self):
        script = load_script()
        self.assertEqual(script.option_count(record_text("0001", 3)), 3)
        self.assertEqual(script.option_count("## Options considered\n\n- **A**\n- **B**\n\n## Decision\n\n1. x\n"), 2)
        self.assertEqual(script.option_count("## Decision\n\n1. x\n"), 0)

    def test_the_limits_come_from_the_settings(self):
        tools = os.path.join(self.repo, ".squad", "tools")
        script = os.path.join(tools, "decision-check.py")
        write(os.path.join(tools, "squad_settings.py"), "AREA_MAX_WORDS = 6000\nRECORD_MAX_OPTIONS = 9\n"
                                                          "RECORD_MAX_WORDS = 2000\n")
        shutil.copyfile(SCRIPT, script)
        result = subprocess.run([sys.executable, "-B", script], cwd=self.repo, capture_output=True, text=True,
                                encoding="utf-8")
        self.assertEqual([line for line in result.stdout.splitlines() if line.startswith("WARNING: ")], [])


if __name__ == "__main__":
    unittest.main()
