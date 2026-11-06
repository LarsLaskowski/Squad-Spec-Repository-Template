"""Unit tests for tools/release.py: run `python3 -m unittest discover tools`."""
import contextlib
import datetime
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "release.py")
spec = importlib.util.spec_from_file_location("release", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

CHANGELOG = """# Changelog

Intro.

## Unreleased

- [Core] Second change (#3)
  continued on a second line
- [Tools] Third change (#4)

## v2026.11.1 — 2026-11-02

- [Core] First change (#1)
"""


def git(root, *args):
    return subprocess.run(["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           "-c", "tag.gpgsign=false", *args], check=True, capture_output=True, text=True).stdout


class TestChangelog(unittest.TestCase):
    def test_a_valid_changelog_passes(self):
        self.assertEqual(release.check(CHANGELOG), [])
        self.assertEqual(release.unreleased_entries(CHANGELOG), ["- [Core] Second change (#3)",
                                                                 "- [Tools] Third change (#4)"])

    def test_format_findings(self):
        cases = {
            "## v2026.11.1 — 2026-11-02\n\n- x\n": "first section must be '## Unreleased'",
            "## Unreleased\n\n## Release 1\n\n- x\n": "no release heading",
            "## Unreleased\n\n## v2026.11.1 — 2026-12-02\n\n- x\n": "another month than its date",
            "## Unreleased\n\n## v2026.11.1 — 2026-11-02\n\nnothing\n": "lists no change",
            "## Unreleased\n\n## v2026.11.1 — 2026-11-02\n\n- x\n\n## v2026.11.2 — 2026-11-09\n\n- y\n":
                "not older than the release above it",
            "## Unreleased\n\n## v2026.11.1 — 2026-11-02\n\n- x\n\n## v2026.11.1 — 2026-11-02\n\n- y\n": "appears twice",
        }
        for text, finding in cases.items():
            with self.subTest(finding=finding):
                self.assertTrue(any(finding in error for error in release.check(text)), release.check(text))

    def test_next_version_counts_the_month_in_changelog_and_tags(self):
        day = datetime.date(2026, 11, 9)
        self.assertEqual(release.next_version(CHANGELOG, [], day), "v2026.11.2")
        self.assertEqual(release.next_version(CHANGELOG, ["v2026.11.4", "v2026.10.9"], day), "v2026.11.5")
        self.assertEqual(release.next_version(CHANGELOG, [], datetime.date(2026, 12, 1)), "v2026.12.1")

    def test_prepare_moves_the_unreleased_lines_into_a_version_section(self):
        text = release.prepare(CHANGELOG, "v2026.11.2", datetime.date(2026, 11, 9))
        self.assertEqual(release.check(text), [])
        self.assertEqual(release.unreleased_entries(text), [])
        self.assertIn("## Unreleased\n\n## v2026.11.2 — 2026-11-09\n\n- [Core] Second change (#3)\n  continued on a "
                      "second line\n- [Tools] Third change (#4)\n\n## v2026.11.1 — 2026-11-02", text)
        self.assertEqual(release.releases(text)[0][:2], ("v2026.11.2", "2026-11-09"))


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.origin = os.path.join(self.dir.name, "origin.git")
        self.root = os.path.join(self.dir.name, "work")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", self.root], check=True)
        for key, value in (("user.name", "t"), ("user.email", "t@t"), ("tag.gpgsign", "false")):
            git(self.root, "config", key, value)  # `tag --create` runs plain git, as on a CI runner without a global identity
        git(self.root, "remote", "add", "origin", self.origin)
        self.write(CHANGELOG)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "start")
        git(self.root, "push", "-q", "origin", "main")
        git(self.root, "fetch", "-q", "origin")

    def write(self, text):
        with open(os.path.join(self.root, "CHANGELOG.md"), "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_command(self, function, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = function(*args, root=self.root)
        return code, out.getvalue()

    def test_prepare_refuses_an_empty_unreleased_section(self):
        self.write("# Changelog\n\n## Unreleased\n\n## v2026.11.1 — 2026-11-02\n\n- x\n")
        code, out = self.run_command(release.prepare_command, datetime.date(2026, 11, 9))
        self.assertEqual(code, 1)
        self.assertIn("nothing to release", out)

    def test_prepare_writes_the_next_version(self):
        code, out = self.run_command(release.prepare_command, datetime.date(2026, 11, 9))
        self.assertEqual(code, 0, out)
        with open(os.path.join(self.root, "CHANGELOG.md"), encoding="utf-8") as handle:
            self.assertIn("## v2026.11.2 — 2026-11-09", handle.read())

    def test_tag_prints_the_commands_creates_only_on_request_and_never_twice(self):
        code, out = self.run_command(release.tag_command, False)
        self.assertEqual(code, 0, out)
        self.assertIn("git push origin v2026.11.1", out)
        self.assertEqual(git(self.root, "tag", "--list"), "", "nothing is created without --create")
        code, out = self.run_command(release.tag_command, True)
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.root, "tag", "--list").split(), ["v2026.11.1"])
        self.assertIn("First change", git(self.root, "tag", "-n9", "v2026.11.1"))
        self.assertEqual(git(self.root, "ls-remote", "--tags", "origin"), "", "the tag is never pushed")
        code, out = self.run_command(release.tag_command, True)
        self.assertEqual((code, "exists already" in out), (1, True))

    def test_tag_refuses_a_checkout_other_than_origin_main(self):
        git(self.root, "commit", "-q", "--allow-empty", "-m", "local only")
        code, out = self.run_command(release.tag_command, False)
        self.assertEqual(code, 1)
        self.assertIn("not origin/main", out)

    def test_tag_refuses_a_version_origin_has(self):
        git(self.root, "tag", "v2026.11.1")
        git(self.root, "push", "-q", "origin", "v2026.11.1")
        git(self.root, "tag", "-d", "v2026.11.1")
        code, out = self.run_command(release.tag_command, False)
        self.assertEqual(code, 1)
        self.assertIn("origin has v2026.11.1 already", out)

    def test_the_repository_changelog_is_valid(self):
        with open(os.path.join(release.ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
            self.assertEqual(release.check(handle.read()), [])


if __name__ == "__main__":
    unittest.main()
