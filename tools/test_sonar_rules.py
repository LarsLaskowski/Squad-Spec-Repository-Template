"""Unit tests for profiles/dotnet/managed/.squad/tools/sonar-rules.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types
import unittest

from test_squad_tools import TOOLS, write

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", "dotnet", "managed", ".squad",
                      "tools", "sonar-rules.py")
CORE = {"S1125", "S1144", "S1172"}
PROJECT = {"S1144", "S1172", "S107", "S3776", "S1192"}
EDITORCONFIG = """root = true

[*]
indent_style = space

[*.cs]
dotnet_diagnostic.RH0396.severity = none
dotnet_diagnostic.S1192.severity = none

[tests/**.cs]
dotnet_diagnostic.S107.severity = none
"""


def load(pending=None):
    sys.modules.pop("analyzer_common", None)
    values = {"BASE_REF": "main"} | ({"DOTNET_RULES_PENDING": pending} if pending is not None else {})
    sys.modules["squad_settings"] = types.SimpleNamespace(**values)
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("sonar_rules", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ApiError(OSError):
    pass


def fake_sonar(key="org_project", project=PROJECT, core=CORE, fail=False):
    """A stand-in for sonar-check.py: the project key and the three endpoints sonar-rules.py reads."""
    rules = {"own": project, "core": core}

    def api(path, params, token=None):
        if fail:
            raise ApiError("HTTP 403 for GET components/show")
        if path == "components/show":
            return {"component": {"key": key, "organization": "org"}}
        if "project" in params:
            return {"profiles": [{"key": "own", "name": "Sonar way comprehensive"}]}
        return {"profiles": [{"key": "core", "name": "Sonar way core", "isBuiltIn": True},
                             {"key": "own", "name": "Sonar way comprehensive", "isBuiltIn": True}]}

    def paged(path, params, field, token=None):
        if (path, field) != ("rules/search", "rules"):
            raise ApiError(f"unexpected read {path}")
        return [{"key": f"csharpsquid:{rule}"} for rule in rules[params["qprofile"]]] + [{"key": "roslyn:S1"}]

    return types.SimpleNamespace(project_key=lambda: key, api=api, paged=paged, ApiError=ApiError,
                                 NotChecked=type("NotChecked", (Exception,), {}))


class SonarRulesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def run_script(self, *argv, sonar=None, pending=None):
        module = load(pending)
        module.sonar_check = lambda: sonar or fake_sonar()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = module.main(list(argv))
            except SystemExit as stop:
                code = stop.code
        return code, output.getvalue()

    def read(self):
        with open(".editorconfig", encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_the_block_lands_in_the_cs_section_and_leaves_the_files_own_rules_alone(self):
        write(".editorconfig", EDITORCONFIG)
        code, out = self.run_script("--check")
        self.assertEqual(code, 1, out)
        self.assertEqual(self.read(), EDITORCONFIG, "--check writes nothing")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("3 rule(s) beyond it at error, 1 switched off", out)
        self.assertIn("left out of the block: S1192", out)
        text = self.read()
        block = text.split("[tests/**.cs]")[0]
        self.assertIn("dotnet_diagnostic.S3776.severity = error\ndotnet_diagnostic.S1125.severity = none\n"
                      "# squad:sonar-rules end\n\n[tests/**.cs]", text, "inside [*.cs], before the next section")
        self.assertIn("S107.severity = error", block, "an override under tests/ is no choice for the rest")
        self.assertNotIn("S1192.severity", block.split("# squad:sonar-rules begin")[1], "the file's own choice")
        self.assertNotIn("roslyn", text)
        self.assertEqual(self.run_script("--check")[0], 0)

    def test_only_a_section_of_every_cs_file_is_the_files_own_choice(self):
        tool = load()
        for glob in ("*", "**", "*.cs", "**.cs", "*.{cs,vb}", "{*.cs,*.vb}", "*.{cs,razor}", "*.[cC][sS]"):
            self.assertTrue(tool.every_cs_file(f"[{glob}]"), glob)
        for glob in ("*.g.cs", "*.{g,designer}.cs", "*Tests.cs", "Program.cs", "tests/**.cs", "**/Migrations/*.cs",
                     "*.csproj", "*.md"):
            self.assertFalse(tool.every_cs_file(f"[{glob}]"), glob)
        self.assertFalse(tool.cs_section("[*]"), "the block goes into a section of the C# files alone")
        self.assertTrue(tool.cs_section("[*.{cs,razor}]"))

    def test_a_rule_off_for_every_file_stays_out_and_one_off_for_some_names_goes_in(self):
        write(".editorconfig", "root = true\n\n[*]\ndotnet_diagnostic.S3776.severity = none\n\n[*.cs]\n"
                               "indent_size = 4\n\n[*Tests.cs]\ndotnet_diagnostic.S107.severity = none\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        block = self.read().split("[*Tests.cs]")[0].split("# squad:sonar-rules begin")[1]
        self.assertNotIn("S3776", block, "[*] is the project's choice for every C# file")
        self.assertIn("S107.severity = error", block, "[*Tests.cs] is no choice for the rest")
        self.assertNotIn("WARNING", out)

    def test_a_narrower_section_before_the_block_is_reported(self):
        write(".editorconfig", "root = true\n\n[tests/**.cs]\ndotnet_diagnostic.S107.severity = none\n\n[*.cs]\n"
                               "indent_size = 4\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING: [tests/**.cs] sets S107 before the block", out)
        self.assertEqual(self.run_script("--check")[1].count("WARNING"), 1, "also once the block exists")

    def test_a_section_the_block_does_not_override_is_not_reported(self):
        write(".editorconfig", "root = true\n\n[*.vb]\ndotnet_diagnostic.S107.severity = none\n\n[tests/**.cs]\n"
                               "dotnet_diagnostic.S3776.severity = error\n\n[*.cs]\nindent_size = 4\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertNotIn("WARNING", out, "no C# file under [*.vb]; [tests/**.cs] sets the block's own value")

    def test_a_changed_profile_rewrites_the_block_in_place(self):
        write(".editorconfig", EDITORCONFIG)
        self.run_script()
        code, _ = self.run_script("--check", sonar=fake_sonar(project=PROJECT | {"S101"}))
        self.assertEqual(code, 1)
        self.run_script(sonar=fake_sonar(project=PROJECT | {"S101"}))
        text = self.read()
        self.assertEqual(text.count("# squad:sonar-rules begin"), 1)
        self.assertIn("dotnet_diagnostic.S101.severity = error\ndotnet_diagnostic.S107.severity = error\n"
                      "dotnet_diagnostic.S3776.severity = error\n", text)
        self.assertTrue(text.endswith("[tests/**.cs]\ndotnet_diagnostic.S107.severity = none\n"),
                        "the path's own override stays after the block, so it still wins there")

    def test_a_pending_rule_is_written_as_a_suggestion(self):
        write(".editorconfig", EDITORCONFIG)
        code, out = self.run_script(pending={"S3776": "#123"})
        self.assertEqual(code, 0, out)
        text = self.read()
        self.assertIn("dotnet_diagnostic.S3776.severity = suggestion\n", text, "pending until #123")
        self.assertIn("dotnet_diagnostic.S107.severity = error\n", text)

    def test_a_file_without_a_cs_section_gets_one_and_keeps_its_line_endings(self):
        write(".editorconfig", "root = true\r\n\r\n[*.md]\r\ntrim_trailing_whitespace = false\r\n", newline="")
        self.assertEqual(self.run_script()[0], 0)
        text = self.read()
        self.assertIn("\r\n[*.cs]\r\n# squad:sonar-rules begin", text)
        self.assertTrue(text.endswith("# squad:sonar-rules end\r\n"))
        self.assertNotIn("\n\n", text.replace("\r\n", "|"))

    def test_without_a_key_or_access_nothing_is_checked(self):
        write(".editorconfig", EDITORCONFIG)
        code, out = self.run_script(sonar=fake_sonar(key=None))
        self.assertEqual(code, 2)
        self.assertIn("NOT CHECKED: no SonarQube project key", out)
        code, out = self.run_script(sonar=fake_sonar(fail=True))
        self.assertEqual(code, 2)
        self.assertIn("HTTP 403", out)
        self.assertEqual(self.read(), EDITORCONFIG)


if __name__ == "__main__":
    unittest.main()
