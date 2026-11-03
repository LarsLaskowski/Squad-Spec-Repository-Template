"""Unit tests for core/.squad/tools/session-usage.py: run `python3 -m unittest discover tools`."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools", "session-usage.py")
SESSION = "0d1e2f30-aaaa-4bbb-8ccc-123456789abc"


def response(message_id, model, inputs, output, read, write):
    usage = {"input_tokens": inputs, "output_tokens": output, "cache_read_input_tokens": read,
             "cache_creation_input_tokens": write}
    return {"type": "assistant", "message": {"id": message_id, "model": model, "usage": usage,
                                             "content": [{"type": "text", "text": "secret text"}]}}


def write_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for item in items:
            handle.write((item if isinstance(item, str) else json.dumps(item)) + "\n")


class TestSessionUsage(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.project = os.path.join(self.dir.name, "projects", "-home-someone-repo")

    def run_script(self, session=SESSION, *args):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.dir.name)
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        if session:
            env["CLAUDE_CODE_SESSION_ID"] = session
        return subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True, text=True)

    def write_session(self):
        main = os.path.join(self.project, SESSION + ".jsonl")
        write_jsonl(main, [
            {"type": "user", "message": {"content": "hello"}},
            response("msg_1", "claude-sonnet-5-5", 10, 200, 3000, 400),
            response("msg_1", "claude-sonnet-5-5", 10, 200, 3000, 400),  # one record per content block
            "not json",
            {"type": "cost-state", "totalCostUSD": 0.5, "totalAPIDuration": 1000, "totalLinesAdded": 1,
             "totalLinesRemoved": 0},
            response("msg_2", "claude-sonnet-5-5", 5, 100, 1000, 0),
            {"type": "cost-state", "totalCostUSD": 26.8, "totalAPIDuration": 4_800_000, "totalLinesAdded": 424,
             "totalLinesRemoved": 12},
        ])
        agents = os.path.join(self.project, SESSION, "subagents")
        write_jsonl(os.path.join(agents, "agent-a1.jsonl"), [response("msg_3", "claude-opus-5-5", 1, 50, 7000, 900)])
        write_jsonl(os.path.join(agents, "agent-a2.jsonl"), [response("msg_4", "claude-opus-5-5", 2, 60, 8000, 100)])
        write_jsonl(os.path.join(agents, "agent-a3.jsonl"), [response("msg_5", "claude-haiku-5-5", 3, 7, 0, 0)])
        for name, kind in (("a1", "squad-dev"), ("a2", "squad-dev"), ("a3", "Explore | <b>")):
            with open(os.path.join(agents, f"agent-{name}.meta.json"), "w", encoding="utf-8") as handle:
                json.dump({"agentType": kind}, handle)

    def test_sums_the_session_and_its_subagents_per_model(self):
        self.write_session()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| claude-sonnet-5-5 | 15 | 300 | 4,000 | 400 |", result.stdout)
        self.assertIn("| claude-opus-5-5 | 3 | 110 | 15,000 | 1,000 |", result.stdout)
        self.assertIn("| **Total** | 21 | 417 | 19,000 | 1,400 |", result.stdout)

    def test_groups_subagents_by_their_type(self):
        self.write_session()
        out = self.run_script().stdout
        self.assertIn("| squad-dev | 2 | claude-opus-5-5 | 3 | 110 | 15,000 | 1,000 |", out)
        self.assertIn("| unknown | 1 | claude-haiku-5-5 | 3 | 7 | 0 | 0 |", out, "an odd agent type is not printed")
        self.assertIn("| **Total** | 3 | | 6 | 117 | 15,000 | 1,000 |", out)

    def test_reports_the_last_cost_snapshot_without_estimating(self):
        self.write_session()
        out = self.run_script().stdout
        self.assertIn("**Cost (last snapshot):** $26.80 · API time 1 h 20 min · lines +424 −12", out)
        self.assertNotIn("$0.50", out)

    def test_prints_no_transcript_text_and_no_path(self):
        self.write_session()
        out = self.run_script().stdout
        for private in ("secret text", "hello", "someone", self.dir.name, SESSION):
            self.assertNotIn(private, out)

    def test_without_subagents_and_snapshot(self):
        write_jsonl(os.path.join(self.project, SESSION + ".jsonl"), [response("m", "claude-opus-5-5", 1, 2, 3, 4)])
        out = self.run_script().stdout
        self.assertIn("No subagent was launched in this session.", out)
        self.assertIn("**Cost:** no cost snapshot in the transcript yet.", out)

    def test_no_transcript_is_not_provided(self):
        self.write_session()
        for session in (None, "other-session", "../" + SESSION):
            result = self.run_script(session)
            self.assertEqual(result.returncode, 2, session)
            self.assertEqual(result.stdout.strip(), "not provided (no Claude Code session transcript found)")

    def test_session_option_overrides_the_environment(self):
        self.write_session()
        self.assertEqual(self.run_script("other-session", "--session", SESSION).returncode, 0)


if __name__ == "__main__":
    unittest.main()
