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


def load(severity=None):
    sys.modules.pop("analyzer_common", None)
    values = {"BASE_REF": "main"} | ({"SONAR_RULES_SEVERITY": severity} if severity else {})
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

    def run_script(self, *argv, sonar=None, severity=None):
        module = load(severity)
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
        self.assertIn("3 rule(s) beyond it at suggestion, 1 switched off", out)
        self.assertIn("left out of the block: S107, S1192", out)
        text = self.read()
        block = text.split("[tests/**.cs]")[0]
        self.assertIn("dotnet_diagnostic.S3776.severity = suggestion\ndotnet_diagnostic.S1125.severity = none\n"
                      "# squad:sonar-rules end\n\n[tests/**.cs]", text, "inside [*.cs], before the next section")
        self.assertNotIn("S107.severity = suggestion", block, "the test section's own setting")
        self.assertNotIn("S1192.severity = suggestion", block, "the file's own choice")
        self.assertNotIn("roslyn", text)
        self.assertEqual(self.run_script("--check")[0], 0)

    def test_a_changed_profile_rewrites_the_block_in_place(self):
        write(".editorconfig", EDITORCONFIG)
        self.run_script()
        code, _ = self.run_script("--check", sonar=fake_sonar(project=PROJECT | {"S101"}))
        self.assertEqual(code, 1)
        self.run_script(sonar=fake_sonar(project=PROJECT | {"S101"}), severity="error")
        text = self.read()
        self.assertEqual(text.count("# squad:sonar-rules begin"), 1)
        self.assertIn("dotnet_diagnostic.S101.severity = error\ndotnet_diagnostic.S3776.severity = error\n", text)

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

    def test_an_unknown_severity_is_a_usage_error(self):
        self.assertEqual(self.run_script(severity="fatal")[0], 4)


if __name__ == "__main__":
    unittest.main()
