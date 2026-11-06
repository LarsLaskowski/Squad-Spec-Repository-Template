"""Unit tests for core/.squad/tools/figure-check.py (documentation that still states a value the diff changed):
run `python3 -m unittest discover tools`."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")
SCRIPT = os.path.join(TOOLS, "figure-check.py")


def load_script(**settings):
    sys.modules.pop("analyzer_common", None)  # it reads squad_settings once, at import
    sys.modules["squad_settings"] = types.SimpleNamespace(BASE_REF="main", **settings)
    sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("figure_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


DIFF = """diff --git a/src/config.py b/src/config.py
index 1..2 100644
--- a/src/config.py
+++ b/src/config.py
@@ -1,2 +1,2 @@
-MAX_MB = 512
--- a comment that looks like a header: 64
+MAX_MB = 1024
+# a comment
@@ -9,0 +10 @@ def helper():
+    return 7
diff --git a/old file.py b/old file.py
deleted file mode 100644
--- a/old file.py\t
+++ /dev/null
@@ -1 +0,0 @@
-PORT = 8080
\\ No newline at end of file
"""


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_hunks_with_their_files_lines_and_content(self):
        hunks = self.script.parse_diff(DIFF)
        self.assertEqual([(h.path, h.line, h.removed, h.added) for h in hunks], [
            ("src/config.py", 1, ["MAX_MB = 512", "-- a comment that looks like a header: 64"],
             ["MAX_MB = 1024", "# a comment"]),
            ("src/config.py", 10, [], ["    return 7"]),
            ("old file.py", 1, ["PORT = 8080"], []),
        ])

    def test_values_are_numbers_and_quoted_constants(self):
        found = self.script.values(['x = foo(512, 1_000, 0.75, "30s", 8.0.1) # v2 sha256 x86 0x1F 1e6',
                                    'key = "APP_PORT"; route = "/api/v1"; name = "maxRetries"; verb = "GET"',
                                    'text = "hello"; other = "World"; short = "ab"; mode = "fast mode"'])
        self.assertEqual(found, {"512", "1000", "0.75", "30", "30s", "8.0.1", "APP_PORT", "/api/v1", "maxRetries",
                                 "GET"})

    def test_trivial_values_are_left_out(self):
        self.assertEqual(self.script.values(["a = [0, 1, 2, 5, 9, 10, 100, 11]"]), {"11"})
        custom = load_script(FIGURE_TRIVIAL=["11", 512])
        self.assertEqual(custom.values(["a = [5, 11, 512]"]), {"5"})

    def test_old_values_per_file_with_their_place_and_new_value(self):
        hunks = self.script.parse_diff(DIFF)
        changes = self.script.old_values(hunks)
        self.assertEqual(sorted(changes), ["512", "64", "8080"])
        self.assertEqual((changes["512"][0].path, changes["512"][0].line, changes["512"][0].new), ("src/config.py", 1, "1024"))
        self.assertEqual((changes["64"][0].line, changes["64"][0].new), (2, None))
        self.assertEqual((changes["8080"][0].path, changes["8080"][0].new), ("old file.py", None))

    def test_a_value_moved_within_its_file_is_no_old_value(self):
        hunks = [self.script.Hunk("a.py", 3, ["LIMIT = 4096"], []), self.script.Hunk("a.py", 40, [], ["LIMIT = 4096"]),
                 self.script.Hunk("b.py", 1, [], ["OTHER = 300"]), self.script.Hunk("c.py", 1, ["X = 300"], [])]
        self.assertEqual(sorted(self.script.old_values(hunks)), ["300"], "a move inside a.py, a change in c.py")

    def test_the_new_value_of_the_same_kind(self):
        hunk = self.script.Hunk("a.py", 5, ['TIMEOUT = "30s"', "A = 12; B = 13"], ['TIMEOUT = "45s"', "A = 14; B = 15"])
        self.assertEqual(self.script.locate(hunk, "30").new, "45")
        self.assertEqual(self.script.locate(hunk, "30s").new, "45s")
        self.assertEqual(self.script.locate(hunk, "12").new, None, "two numbers changed in that line pair")
        self.assertEqual(self.script.locate(hunk, "12").line, 6)

    def test_exclusions_keep_their_magic(self):
        self.assertEqual(self.script.exclusion("tests/"), ":(exclude)tests/")
        self.assertEqual(self.script.exclusion(":(glob)tests/**/*.cs"), ":(exclude,glob)tests/**/*.cs")
        self.assertIsNone(self.script.exclusion(":!tests/fixtures"))
        self.assertIsNone(self.script.exclusion(":(exclude)tests/fixtures"))


class TestDocuments(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_a_marked_file_owns_its_project_blocks_only(self):
        text = "Template 512.\n<!-- project:begin overview -->\nOurs 512.\n<!-- project:end overview -->\nMore 512.\n"
        self.assertEqual(self.script.owned_lines("AGENTS.md", text), [(3, "Ours 512.")])
        self.assertEqual(len(self.script.owned_lines("README.md", text)), 5)

    def test_numbers_match_as_whole_tokens_with_separators_and_units(self):
        strings = [("APP_PORT", self.script.re.compile(self.script.STRING_EDGE.format("APP_PORT")))]
        numbers = {"512", "1000", "8.0.1"}
        match = self.script.matches
        self.assertEqual(match("up to 1,000 items, 512MB, version 8.0.1.", numbers, strings), ["1000", "512", "8.0.1"])
        self.assertEqual(match("5120 bytes, v512, 1.512, 8.0.12, 1,0000", numbers, strings), [])
        self.assertEqual(match("set `APP_PORT`, not APP_PORTS or MY_APP_PORT", numbers, strings), ["APP_PORT"])
        self.assertEqual(match("APP_PORT.", numbers, strings), ["APP_PORT"])


class TestRun(unittest.TestCase):
    """figure-check.py in a repository: the hits, and what it leaves out."""

    def git(self, *args):
        subprocess.run(["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                       capture_output=True)

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = self.dir.name
        self.git("init", "-q", "-b", "main")
        tools = os.path.join(self.repo, ".squad", "tools")
        for name in ("figure-check.py", "analyzer_common.py"):
            os.makedirs(tools, exist_ok=True)
            shutil.copyfile(os.path.join(TOOLS, name), os.path.join(tools, name))
        write(os.path.join(tools, "squad_settings.py"), 'BASE_REF = "main"\nCOVERAGE_EXCLUDES = ["tests/"]\n')
        write(os.path.join(self.repo, "src", "config.py"), 'MAX_MB = 512\nENV = "APP_PORT"\n')
        write(os.path.join(self.repo, "src", "moved.py"), "WORKERS = 64\n")
        write(os.path.join(self.repo, "tests", "test_config.py"), "assert LIMIT == 4096\n")
        write(os.path.join(self.repo, "package-lock.json"), '{"version": "3.3.3"}\n')
        documents = {
            "README.md": "# App\n\nThe cache holds 512 MB; set `APP_PORT`. 64 workers, 4096 tests, 3.3.3, 777.\n",
            "SECURITY.md": "Report within 512 hours.\n",
            "CHANGELOG.md": "Raised from 512.\n",
            "docs/CHANGELOG.md": "Raised from 512.\n",
            "docs/areas/cache.md": "- Limit: 512 MB.\n",
            "docs/areas/_template.md": "512\n",
            "docs/decisions/process.md": "512\n",
            "docs/decisions/0001-released.md": "Chose 512.\n",
            "docs/decisions/0002-unreleased.md": "Chose 512.\n",
            "docs/CONTRIBUTING.md": "Template 512.\n<!-- project:begin areas -->\nOurs 512.\n<!-- project:end areas -->\n",
            ".squad/project.md": "- Memory: 512 MB in src/config.py\n",
            "AGENTS.md": "Template 512.\n<!-- project:begin overview -->\nOverview 512.\n<!-- project:end overview -->\n",
            "src/notes.md": "512 here is not searched.\n",
        }
        for path, text in documents.items():
            write(os.path.join(self.repo, path), text)
        with open(os.path.join(self.repo, "docs", "logo.png"), "wb") as handle:
            handle.write(b"\x89PNG\0512\0")
        os.remove(os.path.join(self.repo, "docs", "decisions", "0002-unreleased.md"))
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.git("tag", "v1.0.0")
        write(os.path.join(self.repo, "docs", "decisions", "0002-unreleased.md"), "Chose 512.\n")
        self.git("checkout", "-qb", "work")

    def tearDown(self):
        self.dir.cleanup()

    def run_check(self):
        result = subprocess.run([sys.executable, os.path.join(self.repo, ".squad", "tools", "figure-check.py")],
                                cwd=os.path.join(self.repo, "docs"), capture_output=True, text=True, encoding="utf-8")
        return result.returncode, result.stdout

    def hits(self, output):
        return sorted(line.split(": states ")[0].removeprefix("WARNING: ") + " " + line.split(": states ")[1].split(",")[0]
                      for line in output.splitlines() if line.startswith("WARNING: "))

    def test_no_change_no_hit(self):
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Checked 0 changed values from 0 source files: 0 documentation lines to confirm or fix", output)

    def test_every_documentation_line_that_states_an_old_value(self):
        write(os.path.join(self.repo, "src", "config.py"), 'MAX_MB = 1024\nENV = "APP_HTTP_PORT"\n')
        write(os.path.join(self.repo, "tests", "test_config.py"), "assert LIMIT == 8192\n")
        write(os.path.join(self.repo, "package-lock.json"), '{"version": "3.3.4"}\n')
        write(os.path.join(self.repo, "src", "notes.md"), "Changed: 777.\n")
        self.git("mv", "src/moved.py", "src/renamed.py")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.hits(output), [
            ".squad/project.md:1 512", "AGENTS.md:3 512", "README.md:3 512", "README.md:3 APP_PORT",
            "SECURITY.md:1 512", "docs/CONTRIBUTING.md:3 512", "docs/areas/cache.md:1 512",
            "docs/decisions/0002-unreleased.md:1 512"])
        self.assertIn("which the diff changed in src/config.py:1 (now 1024) - confirm the sentence still holds or fix "
                      "it: \"The cache holds 512 MB; set `APP_PORT`. 64 workers, 4096 tests, 3.3.3, 777.\"", output)
        self.assertIn("Checked 2 changed values from 1 source files: 8 documentation lines to confirm or fix", output)

    def test_a_long_line_is_shortened_and_many_places_are_counted(self):
        write(os.path.join(self.repo, "README.md"), "512 " + "word " * 40 + "\n")
        for name in ("a", "b", "c", "d"):
            write(os.path.join(self.repo, "src", f"{name}.py"), "X = 512\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "more")
        self.git("branch", "-f", "main")
        for name in ("a", "b", "c", "d"):
            write(os.path.join(self.repo, "src", f"{name}.py"), "X = 513\n")
        _, output = self.run_check()
        line = next(line for line in output.splitlines() if line.startswith("WARNING: README.md"))
        self.assertIn(" and 1 more - ", line)
        self.assertTrue(line.endswith(': "512 ' + "word " * 19 + '…"'), line)

    def test_dates_svg_and_other_uses_in_the_file(self):
        write(os.path.join(self.repo, "src", "dates.py"), "SINCE = 2025\nTIMEOUT = 30\nRETRY = 30\n")
        write(os.path.join(self.repo, "docs", "areas", "history.md"),
              "| 0001 | Topic | Accepted | 2025-01-01 |\nSupported since 2025.\nTimeout 30 s.\n")
        write(os.path.join(self.repo, "docs", "diagram.svg"), '<svg width="2025"/>\n')
        self.git("add", "-A")
        self.git("commit", "-qm", "dates")
        self.git("branch", "-f", "main")
        write(os.path.join(self.repo, "src", "dates.py"), "SINCE = 2026\nTIMEOUT = 30\nRETRY = 45\n")
        _, output = self.run_check()
        self.assertEqual(self.hits(output), ["docs/areas/history.md:2 2025", "docs/areas/history.md:3 30"])
        self.assertIn("src/dates.py:3 (now 45; still used elsewhere in that file)", output)

    def test_a_released_record_with_a_name_git_would_quote(self):
        name = "0003-gr\u00f6\u00dfe limit.md"
        write(os.path.join(self.repo, "docs", "decisions", name), "Chose 512.\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "record")
        self.git("tag", "v1.1.0")
        self.git("branch", "-f", "main")
        write(os.path.join(self.repo, "src", "config.py"), 'MAX_MB = 1024\nENV = "APP_PORT"\n')
        _, output = self.run_check()
        self.assertNotIn("0003-gr", output, "released in v1.1.0")
        self.assertNotIn("0002-unreleased.md", output, "released in v1.1.0 as well")
        self.assertIn("WARNING: docs/areas/cache.md:1: states 512", output)

    def test_a_console_without_unicode_gets_no_traceback(self):
        write(os.path.join(self.repo, "README.md"), "Limit \u2265 512 MB \u2192 enough.\n")
        write(os.path.join(self.repo, "src", "config.py"), 'MAX_MB = 1024\nENV = "APP_PORT"\n')
        result = subprocess.run([sys.executable, os.path.join(self.repo, ".squad", "tools", "figure-check.py")],
                                cwd=self.repo, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="cp1252"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"WARNING: README.md:1: states 512", result.stdout)


if __name__ == "__main__":
    unittest.main()
