"""Unit tests for tools/rollout-check.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import json
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

    def test_the_release_notes_must_leave_the_squads_pull_requests_out(self):
        seeded = "changelog:\n  exclude:\n    labels:\n      - ignore-for-release\n  categories:\n    - title: Bugs\n"
        self.assertTrue(tool.excludes_release_label(seeded))
        self.assertTrue(tool.excludes_release_label("changelog:\n  exclude:\n    labels: [ignore-for-release]\n"))
        self.assertTrue(tool.excludes_release_label("changelog:\n  exclude:\n    labels:\n      - \"ignore-for-release\""
                                                    "  # squad\n"))
        self.assertFalse(tool.excludes_release_label("changelog:\n  categories:\n    - title: Other\n      labels:\n"
                                                     "        - ignore-for-release\n"), "a category is no exclusion")
        self.assertFalse(tool.excludes_release_label("changelog:\n  exclude:\n    labels:\n      - skip\n"))
        with tempfile.TemporaryDirectory() as target:
            self.assertIn("no .github/release.yml", tool.release_notes_findings(target)[0])
            os.makedirs(os.path.join(target, ".github"))
            with open(os.path.join(target, tool.RELEASE_YML), "w", encoding="utf-8") as handle:
                handle.write("changelog:\n  exclude:\n    labels:\n      - skip\n")
            self.assertIn("does not exclude the label ignore-for-release", tool.release_notes_findings(target)[0])
            with open(os.path.join(target, tool.RELEASE_YML), "w", encoding="utf-8") as handle:
                handle.write(seeded)
            self.assertEqual(tool.release_notes_findings(target), [])

    def test_the_dotnet_config_findings_are_folded_for_the_report(self):
        output = (".NET config: dotnet-tools.json: move it to .config/dotnet-tools.json\n"
                  ".NET config: .editorconfig:43: [*.cs] sets csharp_prefer_braces outside the dotnet-rules block; x\n"
                  ".NET config: .editorconfig:44: [*.cs] sets csharp_style_var_elsewhere outside the dotnet-rules block; x\n"
                  "FAIL\n")
        drift = tool.config_drift(output)
        self.assertEqual(drift[0], "dotnet-tools.json: move it to .config/dotnet-tools.json")
        self.assertIn("2 rule(s) or code-style option(s) for every C# file outside the dotnet-rules block (lines 43, 44)",
                      drift[1])

    def test_the_build_rehearsal_reads_the_solution_lowers_errors_and_counts_rules(self):
        with tempfile.TemporaryDirectory() as target:
            os.makedirs(os.path.join(target, ".squad", "tools"))
            with open(os.path.join(target, tool.SETTINGS), "w", encoding="utf-8") as handle:
                handle.write('BASE_REF = "origin/main"\nSOLUTION = "App.slnx"\n')
            self.assertEqual(tool.solution_of(target), "App.slnx")
            with open(os.path.join(target, ".editorconfig"), "w", encoding="utf-8", newline="") as handle:
                handle.write("dotnet_diagnostic.S1.severity = error\r\ncsharp_prefer_braces = true:error\r\n"
                             "dotnet_diagnostic.S2.severity = none\r\n")
            tool.lower_errors(target)
            with open(os.path.join(target, ".editorconfig"), encoding="utf-8", newline="") as handle:
                self.assertEqual(handle.read(), "dotnet_diagnostic.S1.severity = warning\r\n"
                                 "csharp_prefer_braces = true:warning\r\ndotnet_diagnostic.S2.severity = none\r\n")
            for project, results in (("A", [{"ruleId": "S1"}, {"ruleId": "RH1"}]),
                                     ("B", [{"ruleId": "S1"}, {"ruleId": "S1", "suppressions": [{"kind": "inSource"}]}])):
                os.makedirs(os.path.join(target, project, "obj"))
                with open(os.path.join(target, project, "obj", tool.SARIF_NAME), "w", encoding="utf-8") as handle:
                    json.dump({"runs": [{"results": results}]}, handle)
            self.assertEqual(tool.sarif_counts(target), {"S1": 2, "RH1": 1}, "a suppressed result is not counted")

    def test_the_dotnet_steps_report_a_refusal_as_a_finding_and_no_sonar_access_as_a_note(self):
        outputs = {tool.DOTNET_RULES: (1, "REFUSED: the dotnet-rules block stands under [x]"),
                   tool.SONAR_RULES: (2, "NOT CHECKED: no SonarQube project key"),
                   tool.DOTNET_CONFIG: (1, ".NET config: Directory.Build.props: no <TargetFramework>\nFAIL\n")}
        original = tool.run
        tool.run = lambda args, cwd=None, timeout=None: outputs[args[1]]
        try:
            findings, notes = tool.dotnet_rehearsal("target", build=True)
        finally:
            tool.run = original
        self.assertEqual(len(findings), 1, "a refusal stops the build rehearsal")
        self.assertIn("dotnet-rules.py refuses the target", findings[0])
        self.assertTrue(any("sonar-rules.py NOT CHECKED" in note for note in notes))
        self.assertIn("the refresh fixes by hand: Directory.Build.props: no <TargetFramework>", notes)

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
