"""Unit tests for core/.squad/tools/squad-notes.py: run `python3 -m unittest discover tools`."""
import os
import subprocess
import sys
import tempfile
import unittest

from test_squad_tools import SESSION_ID, TOOLS, load_script, prompt, write, write_jsonl

REPORT = ("Objections:\n\n1. minor — replace `Items.Count == 0` with `Items is []` in *Approach*.\n"
          "2. minor — the README line says \"three\" where the spec says \"four\".\n\nVERDICT: OBJECTIONS 0 major, 2 minor\n")
PLAN = "# Plan: export\n\n## Approach\n\nWrite rows.\n"


def said(message_id, text, tools=()):
    """An assistant record with a text block and, optionally, tool uses."""
    content = [{"type": "text", "text": text}] + [{"type": "tool_use", "id": tool, "name": "Read", "input": {}}
                                                  for tool in tools]
    return {"type": "assistant", "timestamp": "2026-01-02T10:00:00Z", "message": {"id": message_id, "content": content}}


class TestSquadNotes(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = os.path.join(self.dir.name, "repo")
        self.plan = os.path.join(self.root, "specs", "issue-5", "plan.md")
        write(self.plan, PLAN)
        self.session = os.path.join(self.dir.name, "config", "projects", "-repo", SESSION_ID)
        write_jsonl(self.session + ".jsonl", [])
        write_jsonl(os.path.join(self.session, "subagents", "agent-da1.jsonl"), [
            prompt("2026-01-02T10:00:00Z"), said("m1", "Reading the plan first.", tools=["t1"]),
            said("m2", REPORT[:12]), said("m2", REPORT[13:]),
            prompt("2026-01-02T10:05:00Z", "a later question"), said("m3", "An answer to the question only.")])

    def run_notes(self, *args, stdin=None):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=os.path.join(self.dir.name, "config"),
                   CLAUDE_CODE_SESSION_ID=SESSION_ID)
        return subprocess.run([sys.executable, os.path.join(TOOLS, "squad-notes.py"), *args], cwd=self.root,
                              input=stdin, capture_output=True, text=True, check=False, env=env)

    def text(self, path=None):
        with open(path or self.plan, encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_a_piped_report_is_appended_verbatim_without_its_verdict_line(self):
        done = self.run_notes("issue-5", "challenge", "--stdin", stdin=REPORT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.text(), PLAN + "\n## Challenge notes\n\n" + REPORT.split("\n\nVERDICT")[0] + "\n")
        self.assertIn("4 line(s) written verbatim", done.stdout)

    def test_the_report_is_read_from_the_last_message_of_the_agents_round(self):
        transcript = os.path.join(self.session, "subagents", "agent-da1.jsonl")
        reader = load_script("squad-notes")
        self.assertEqual(reader.last_report(transcript), "An answer to the question only.", "the latest round")
        write_jsonl(transcript, [prompt("2026-01-02T10:00:00Z"), said("m1", "Reading first.", tools=["t1"]),
                                 said("m2", REPORT[:12]), said("m2", REPORT[13:])])
        done = self.run_notes("specs/issue-5", "security", "--agent-id", "da1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("## Security notes\n\nObjections:\n\n1. minor — replace `Items.Count == 0` with `Items is []`",
                      self.text())
        self.assertNotIn("Reading first", self.text(), "an earlier message of the round is no report")
        self.assertNotIn("VERDICT", self.text())

    def test_a_report_handed_back_through_the_tool_call_wins_over_the_narration(self):
        # A subagent of a cloud session hands its report back with SubagentHandback; its last text is narration.
        transcript = os.path.join(self.session, "subagents", "agent-sec1.jsonl")
        call = said("m2", "Let me look at the tool diffs first.")
        call["message"]["content"].append({"type": "tool_use", "id": "h1", "name": "SubagentHandback",
                                           "input": {"message": "1. a note\n\nVERDICT: APPROVED\n"}})
        write_jsonl(transcript, [prompt("2026-01-02T10:00:00Z"), call, said("m3", "Done.")])
        done = self.run_notes("issue-5", "security", "--agent-id", "sec1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(self.text().endswith("## Security notes\n\n1. a note\n"), self.text())

    def test_an_existing_section_gets_the_notes_below_its_last_line_and_crlf_is_kept(self):
        write(self.plan, PLAN + "\n## Security notes\n\n1. earlier note\n\n## Later\n\ntext\n", newline="\r\n")
        done = self.run_notes("issue-5", "security", "--stdin", stdin="2. a second note\n\nVERDICT: APPROVED\n")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("## Security notes\r\n\r\n1. earlier note\r\n\r\n2. a second note\r\n\r\n## Later\r\n", self.text())
        self.assertNotIn("\n\n", self.text().replace("\r\n", ""), "no bare line feed")

    def test_the_leads_docs_result_is_written_whole_as_result_md(self):
        # Censio#185: a 20-line edit with a code block did not fit the first log row.
        result = "Tier: docs\n\nEdit `docs/a.md`, replace\n\n```bash\nrun it\n```\n\nRESULT: DONE\n"
        self.assertEqual(self.run_notes("issue-5", "result", "--stdin", stdin=result).returncode, 1, "no log.md yet")
        write(os.path.join(self.root, "specs", "issue-5", "log.md"), "| Date |\r\n")
        done = self.run_notes("issue-5", "result", "--stdin", stdin=result)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.text(os.path.join(self.root, "specs", "issue-5", "result.md")),
                         result.replace("\n", "\r\n"), "verbatim, the RESULT line kept, CRLF as log.md")
        self.assertEqual(self.run_notes("issue-5", "result", "--stdin", stdin="just narration").returncode, 1)

    def test_spec_folder_and_empty_reports_are_checked(self):
        write(os.path.join(self.root, "specs", "feature-7", "spec.md"), "# Spec\n")
        done = self.run_notes("feature-7", "challenge", "--stdin", "--spec",
                              stdin="- minor: a scenario\nVERDICT: OBJECTIONS 0 major, 1 minor\n")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(self.text(os.path.join(self.root, "specs", "feature-7", "spec.md")).endswith(
            "## Challenge notes\n\n- minor: a scenario\n"))
        self.assertEqual(self.run_notes("../etc", "challenge", "--stdin", stdin="x").returncode, 1)
        self.assertEqual(self.run_notes("issue-5", "challenge", "--stdin", stdin="VERDICT: NO OBJECTIONS\n").returncode, 1)
        narration = self.run_notes("issue-5", "challenge", "--stdin", stdin="Let me look at the tool diffs first.\n")
        self.assertEqual(narration.returncode, 1)
        self.assertIn("carries no VERDICT line", narration.stdout)
        missing = self.run_notes("issue-5", "challenge", "--agent-id", "nobody")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("pipe the report in with --stdin", missing.stderr)
        self.assertEqual(self.run_notes("issue-5", "challenge").returncode, 2, "a source is required")


if __name__ == "__main__":
    unittest.main()
