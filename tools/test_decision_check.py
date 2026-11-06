"""Unit tests for core/.squad/tools/decision-check.py (release tags of a repository without local ones):
run `python3 -m unittest discover tools`."""
import importlib.util
import os
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


if __name__ == "__main__":
    unittest.main()
