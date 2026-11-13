"""Unit tests for profiles/dotnet/managed/.squad/tools/analyzer-check.py: run `python3 -m unittest discover tools`."""
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", "dotnet", "managed", ".squad",
                     "tools")
CORE_TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")


def load():
    """analyzer-check.py with the target's squad_settings stubbed."""
    sys.modules["squad_settings"] = types.SimpleNamespace(SOLUTION="X.slnx", BASE_REF="origin/main")
    for path in (TOOLS, CORE_TOOLS):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location("dotnet_analyzer_check", os.path.join(TOOLS, "analyzer-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDiagnostics(unittest.TestCase):
    def test_a_diagnostic_without_a_location_counts_for_its_project(self):
        # Vandox#430: MSTEST0001 is reported without a location and the gate skipped it.
        tool = load()
        with tempfile.TemporaryDirectory() as root:
            log = os.path.join(root, "tests", "A.Tests", "obj", "roslyn.sarif")
            os.makedirs(os.path.dirname(log))
            results = [{"ruleId": "MSTEST0001", "level": "note", "message": {"text": "parallelization"}},
                       {"ruleId": "S1", "level": "warning", "message": {"text": "x"}, "locations": [
                           {"physicalLocation": {"artifactLocation": {"uri": os.path.join(root, "src", "B.cs")},
                                                 "region": {"startLine": 4}}}]},
                       {"ruleId": "S2", "suppressions": [{"kind": "inSource"}]}]
            with open(log, "w", encoding="utf-8") as handle:
                json.dump({"runs": [{"results": results}]}, handle)
            cwd = os.getcwd()
            os.chdir(root)
            try:
                found = sorted(tool.diagnostics(os.path.realpath(root)))
            finally:
                os.chdir(cwd)
        self.assertEqual(found, [("src/B.cs", 4, "S1", "warning", "x"),
                                 ("tests/A.Tests/", 0, "MSTEST0001", "note", "parallelization")])
        self.assertTrue(tool.in_changed_file("tests/A.Tests/", {"tests/A.Tests/ATests.cs"}))
        self.assertFalse(tool.in_changed_file("tests/A.Tests/", {"src/B.cs"}), "an unchanged project does not gate")
        self.assertTrue(tool.in_changed_file("src/B.cs", {"src/B.cs"}))
        self.assertTrue(tool.in_changed_file("./", {"Program.cs"}), "a project at the repository root")


if __name__ == "__main__":
    unittest.main()
