"""Unit tests for tools/rollout-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rollout-check.py")
spec = importlib.util.spec_from_file_location("rollout_check", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

APPLY_OUTPUT = """updated    .squad/team.md
conflict   sonar-project.properties

3 files unchanged.

Not part of the template (review: migrate, keep as project-specific, or delete):
  .squad/tools/go-coverage-to-cobertura.py

References to removed files - fix by hand (link the replacement or drop the line):
  README.md:12: see .agents/skills/fix-issue
"""


def git(root, *args):
    return subprocess.run(["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           *args], check=True, capture_output=True, text=True).stdout


class TestParsing(unittest.TestCase):
    def test_the_report_sections_and_conflicts_are_read(self):
        self.assertEqual(tool.section(APPLY_OUTPUT, tool.REFERENCES), ["README.md:12: see .agents/skills/fix-issue"])
        self.assertEqual(tool.section(APPLY_OUTPUT, tool.UNKNOWN), [".squad/tools/go-coverage-to-cobertura.py"])
        self.assertEqual(tool.conflicts(APPLY_OUTPUT), ["sonar-project.properties"])
        self.assertEqual(tool.section("nothing\n", tool.REFERENCES), [])

    def test_clones_default_to_the_folder_next_to_the_template(self):
        paths = tool.clone_paths(["LarsLaskowski/Vandox", "LarsLaskowski/Seluna"], ["larslaskowski/seluna=../Elsewhere/seluna"])
        self.assertEqual(paths["LarsLaskowski/Vandox"], os.path.join(os.path.dirname(tool.ROOT), "Vandox"))
        self.assertEqual(paths["LarsLaskowski/Seluna"], os.path.abspath("../Elsewhere/seluna"))

    def test_the_active_consumers_come_from_consumers_json(self):
        consumers = tool.active_consumers()
        self.assertIn("LarsLaskowski/Vandox", consumers)
        self.assertNotIn("LarsLaskowski/F1-Telemetry", consumers, "legacy consumers stay out of the rollout")

    def test_an_unknown_template_commit_is_no_seed_list(self):
        self.assertIsNone(tool.changed_seeds("0" * 40, ["dotnet"]))
        self.assertIsNone(tool.changed_seeds(None, ["dotnet"]))


class TestConsumer(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_a_missing_clone_is_a_finding(self):
        findings, _ = tool.check_consumer(os.path.join(self.dir.name, "none"), False)
        self.assertIn("no clone at", findings[0])

    def test_a_consumer_without_a_template_record_is_a_finding_and_its_clone_stays_untouched(self):
        origin = os.path.join(self.dir.name, "origin.git")
        clone = os.path.join(self.dir.name, "clone")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", clone], check=True)
        with open(os.path.join(clone, "README.md"), "w", encoding="utf-8") as handle:
            handle.write("readme\n")
        git(clone, "add", "-A")
        git(clone, "commit", "-q", "-m", "start")
        git(clone, "remote", "add", "origin", origin)
        git(clone, "push", "-q", "origin", "main")
        findings, notes = tool.check_consumer(clone, True)
        self.assertEqual(notes, [])
        self.assertIn("no .squad/template.json on main", findings[0])
        self.assertEqual(git(clone, "status", "--porcelain"), "", "the rehearsal works on a scratch copy")

    def test_main_reports_every_consumer_and_fails_on_a_finding(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            named = "LarsLaskowski/PlexToJellyfinSync"
            skips = [option for repo in tool.active_consumers() if repo != named for option in ("--skip", repo)]
            code = tool.main(["--no-fetch", *skips, "--target",
                              f"LarsLaskowski/PlexToJellyfinSync={self.dir.name}/missing"])
        self.assertEqual(code, 1)
        self.assertIn("## LarsLaskowski/PlexToJellyfinSync: FAIL", out.getvalue())
        self.assertIn("Skipped: LarsLaskowski/Vandox", out.getvalue(), "every other active consumer is skipped")
        self.assertIn("(1 consumer(s) rehearsed)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
