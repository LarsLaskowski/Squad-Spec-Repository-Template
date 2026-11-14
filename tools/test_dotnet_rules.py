"""Unit tests for profiles/dotnet/managed/.squad/tools/dotnet-rules.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types
import unittest

from test_squad_tools import TOOLS, write

PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", "dotnet")
SCRIPT = os.path.join(PROFILE, "managed", ".squad", "tools", "dotnet-rules.py")
SEED = os.path.join(PROFILE, "seed", ".editorconfig")
BASELINE = """# The .NET rule baseline (a test copy)

[*.cs]

# Code style
csharp_style_namespace_declarations = file_scoped:error

# Diagnostics: S
# == false is the binding style
dotnet_diagnostic.S1125.severity = none
dotnet_diagnostic.S3776.severity = error

[**/*.Tests/**.cs]

# Diagnostics: S
dotnet_diagnostic.S107.severity = none
"""
SONAR_BLOCK = "# squad:sonar-rules begin — generated\ndotnet_diagnostic.S1192.severity = error\n# squad:sonar-rules end\n"
EDITORCONFIG = "root = true\n\n[*]\nindent_style = space\n\n[*.cs]\nindent_size = 4\n\n" + SONAR_BLOCK


def load(pending=None):
    sys.modules.pop("analyzer_common", None)
    values = {"BASE_REF": "main"} | ({"DOTNET_RULES_PENDING": pending} if pending is not None else {})
    sys.modules["squad_settings"] = types.SimpleNamespace(**values)
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("dotnet_rules", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DotnetRulesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        write("baseline.editorconfig", BASELINE)

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def run_script(self, *argv, pending=None, baseline="baseline.editorconfig", global_baseline=None):
        module = load(pending)
        module.BASELINE = os.path.abspath(baseline)
        if global_baseline:
            module.GLOBAL_BASELINE = os.path.abspath(global_baseline)
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

    def test_the_blocks_land_before_the_sonar_block_and_at_the_end(self):
        write(".editorconfig", EDITORCONFIG)
        code, out = self.run_script("--check")
        self.assertEqual(code, 1, out)
        self.assertEqual(self.read(), EDITORCONFIG, "--check writes nothing")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        text = self.read()
        general, rest = text.split("# squad:dotnet-rules end")
        self.assertIn("[*.cs]\nindent_size = 4\n\n# squad:dotnet-rules begin", general, "inside the [*.cs] section")
        self.assertIn("# == false is the binding style\ndotnet_diagnostic.S1125.severity = none\n", general,
                      "the baseline's reasons come along")
        self.assertTrue(rest.startswith("\n\n# squad:sonar-rules begin"), "before the sonar-rules block")
        self.assertTrue(text.endswith("[**/*.Tests/**.cs]\n# Diagnostics: S\ndotnet_diagnostic.S107.severity = none\n"
                                      "# squad:dotnet-rules-paths end\n"), "the paths block ends the file")
        self.assertNotIn("The .NET rule baseline (a test copy)", text, "the baseline's own heading stays out")
        self.assertEqual(self.run_script("--check")[0], 0)
        self.assertEqual(self.run_script()[0], 0)
        self.assertEqual(self.read(), text, "a second run changes nothing")

    def test_the_block_follows_the_files_own_settings_when_the_sonar_block_is_in_a_later_section(self):
        write(".editorconfig", "root = true\n\n[*.{cs,razor}]\nindent_size = 4\n\n[*.cs]\n"
                               "csharp_prefer_braces = true:warning\n\n" + SONAR_BLOCK)
        self.assertEqual(self.run_script()[0], 0)
        text = self.read()
        self.assertLess(text.index("csharp_prefer_braces = true:warning"), text.index("# squad:dotnet-rules begin"),
                        "the block comes later and wins over a leftover of the file")
        self.assertIn("# squad:dotnet-rules end\n\n# squad:sonar-rules begin", text)

    def test_a_changed_baseline_rewrites_the_blocks_in_place(self):
        write(".editorconfig", EDITORCONFIG + "\n[**/Migrations/*.cs]\ngenerated_code = true\n")
        self.run_script()
        write("baseline.editorconfig", BASELINE.replace("S3776.severity = error", "S3776.severity = warning"))
        self.assertEqual(self.run_script("--check")[0], 1)
        self.assertEqual(self.run_script()[0], 0)
        text = self.read()
        self.assertEqual(text.count("# squad:dotnet-rules begin"), 1)
        self.assertEqual(text.count("# squad:dotnet-rules-paths begin"), 1)
        self.assertIn("S3776.severity = warning", text)
        self.assertLess(text.index("[**/Migrations/*.cs]"), text.index("# squad:dotnet-rules-paths begin"))

    def test_a_file_without_a_cs_section_gets_one_and_keeps_its_line_endings(self):
        write(".editorconfig", "root = true\r\n\r\n[*.md]\r\ntrim_trailing_whitespace = false", newline="")
        self.assertEqual(self.run_script()[0], 0)
        text = self.read()
        self.assertIn("\r\n\r\n[*.cs]\r\n# squad:dotnet-rules begin", text)
        self.assertTrue(text.endswith("# squad:dotnet-rules-paths end"), "no final newline where the file had none")
        self.assertNotIn("\n", text.replace("\r\n", ""))

    def test_a_pending_rule_is_lowered_with_its_issue(self):
        write(".editorconfig", EDITORCONFIG)
        pending = {"S3776": "#123", "S107": "#7", "csharp_style_namespace_declarations": "o/r#3", "S2325": "#9"}
        code, out = self.run_script(pending=pending)
        self.assertEqual(code, 0, out)
        text = self.read()
        self.assertIn("# pending: #123 (DOTNET_RULES_PENDING)\ndotnet_diagnostic.S3776.severity = suggestion\n", text)
        self.assertIn("# pending: o/r#3 (DOTNET_RULES_PENDING)\ncsharp_style_namespace_declarations = file_scoped:suggestion\n",
                      text)
        self.assertIn("dotnet_diagnostic.S107.severity = none\n", text, "a pending rule that is off stays off")
        self.assertIn("# pending: #9 (DOTNET_RULES_PENDING)\ndotnet_diagnostic.S2325.severity = suggestion\n", text,
                      "a rule the baseline does not set is lowered too (CA1848 is on only through AnalysisLevel)")
        self.assertLess(text.index("S2325.severity = suggestion"), text.index("# squad:dotnet-rules end"))
        general = text.split("# squad:dotnet-rules end")[0]
        self.assertIn("# pending: #7 (DOTNET_RULES_PENDING)\ndotnet_diagnostic.S107.severity = suggestion\n", general,
                      "a rule only a section of paths sets is lowered for the other C# files")
        self.assertEqual(self.run_script("--check")[0], 1, "once it is fixed and out of the list, the block is outdated")

    def test_a_pending_rule_of_the_global_config_goes_into_the_pending_global_config(self):
        # #393: MSTEST0001 has no location, so only a global config with a higher global_level can lower it.
        write(".editorconfig", EDITORCONFIG)
        write("global.globalconfig", "# managed\nis_global = true\n\ndotnet_diagnostic.MSTEST0001.severity = error\n\n"
                                     "dotnet_diagnostic.S1125.severity = none\n")
        code, out = self.run_script(pending={"MSTEST0001": "#12", "S3776": "#3"}, global_baseline="global.globalconfig")
        self.assertEqual(code, 0, out)
        with open(".squad/dotnet-rules-pending.globalconfig", encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertIn("is_global = true\nglobal_level = 101\n", text)
        self.assertTrue(text.endswith("\n# pending: #12 (DOTNET_RULES_PENDING)\n"
                                      "dotnet_diagnostic.MSTEST0001.severity = suggestion\n"), text)
        self.assertNotIn("S3776", text, "a rule with a location is lowered in .editorconfig alone")
        self.assertEqual(self.run_script("--check", pending={"MSTEST0001": "#12", "S3776": "#3"},
                                         global_baseline="global.globalconfig")[0], 0)
        code, out = self.run_script("--check", pending={"S3776": "#3"}, global_baseline="global.globalconfig")
        self.assertEqual(code, 1, "once the rule is met and out of the list, the pending config is outdated")
        self.assertIn("the pending global config is missing or out of date", out)
        self.assertEqual(self.run_script(pending={}, global_baseline="global.globalconfig")[0], 0)
        with open(".squad/dotnet-rules-pending.globalconfig", encoding="utf-8") as handle:
            self.assertNotIn("dotnet_diagnostic", handle.read(), "nothing pending: the header alone")

    def test_a_crlf_checkout_of_the_pending_global_config_stays_current(self):
        # A CRLF repository (`* text=auto eol=crlf`) checks the file out with CRLF: it is current, and rewritten in kind.
        write(".editorconfig", EDITORCONFIG)
        write("global.globalconfig", "is_global = true\n\ndotnet_diagnostic.MSTEST0001.severity = error\n")
        self.assertEqual(self.run_script(pending={}, global_baseline="global.globalconfig")[0], 0)
        with open(".squad/dotnet-rules-pending.globalconfig", encoding="utf-8", newline="") as handle:
            text = handle.read()
        write(".squad/dotnet-rules-pending.globalconfig", text.replace("\n", "\r\n"), newline="")
        code, out = self.run_script("--check", pending={}, global_baseline="global.globalconfig")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.run_script(pending={"MSTEST0001": "#4"}, global_baseline="global.globalconfig")[0], 0)
        with open(".squad/dotnet-rules-pending.globalconfig", encoding="utf-8", newline="") as handle:
            text = handle.read()
        self.assertIn("MSTEST0001.severity = suggestion\r\n", text)
        self.assertNotIn("\n", text.replace("\r\n", ""), "the rewrite keeps CRLF")

    def test_a_pending_entry_without_an_issue_is_refused(self):
        write(".editorconfig", EDITORCONFIG)
        for pending in ({"S3776": "later"}, {"S3776": ""}, {"not a rule": "#1"}, ["S3776"], {"s1192": "#14"}):
            code, out = self.run_script(pending=pending)
            self.assertEqual(code, 1, pending)
            self.assertIn("REFUSED: DOTNET_RULES_PENDING", out, pending)
            self.assertEqual(self.read(), EDITORCONFIG, "nothing is written")

    def test_a_block_under_a_section_of_a_path_is_refused(self):
        text = ("root = true\n\n[*.cs]\nindent_size = 4\n\n[**/Migrations/*.cs]\ngenerated_code = true\n"
                "# squad:dotnet-rules begin\n# squad:dotnet-rules end\n")
        write(".editorconfig", text)
        code, out = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: the dotnet-rules block stands under [**/Migrations/*.cs]", out)
        self.assertEqual(self.read(), text)

    def test_a_paths_block_before_the_other_blocks_is_refused(self):
        text = ("root = true\n\n# squad:dotnet-rules-paths begin\n# squad:dotnet-rules-paths end\n\n[*.cs]\n"
                + SONAR_BLOCK)
        write(".editorconfig", text)
        code, out = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("the dotnet-rules-paths block comes before the sonar-rules block", out)

    def test_a_pending_entry_for_a_rule_the_baseline_switches_off_is_refused(self):
        write(".editorconfig", EDITORCONFIG)
        code, out = self.run_script(pending={"S1125": "#15"})
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: DOTNET_RULES_PENDING: S1125 is off in the baseline (none)", out)
        self.assertEqual(self.read(), EDITORCONFIG)

    def test_the_sonar_block_lands_after_the_dotnet_rules_block_not_in_the_paths_block(self):
        write(".editorconfig", "root = true\n\n[*]\nindent_style = space\n")
        self.assertEqual(self.run_script()[0], 0)
        with open(".editorconfig", encoding="utf-8") as handle:
            text = handle.read()
        rules = load()
        updated = rules.SECTIONS.render(text, ["dotnet_diagnostic.S1192.severity = error"])
        self.assertLess(updated.index("# squad:dotnet-rules end"), updated.index("# squad:sonar-rules begin"))
        self.assertLess(updated.index("# squad:sonar-rules end"), updated.index("# squad:dotnet-rules-paths begin"))
        write(".editorconfig", updated)
        self.assertEqual(self.run_script("--check")[0], 0, "dotnet-rules.py accepts the layout")

    def test_the_template_baseline_has_no_trailing_whitespace(self):
        with open(load().BASELINE, encoding="utf-8") as handle:
            self.assertEqual([line for line in handle.read().splitlines() if line != line.rstrip()], [],
                             "an editor that trims it would make the blocks look outdated")

    def test_a_missing_baseline_is_refused(self):
        write(".editorconfig", EDITORCONFIG)
        code, out = self.run_script(baseline="missing.editorconfig")
        self.assertEqual(code, 1)
        self.assertIn("is missing or holds no section", out)

    def test_severities_are_only_ever_lowered_to_a_suggestion(self):
        tool = load()
        for value, expected in (("error", "suggestion"), ("Warning", "suggestion"), ("suggestion", "suggestion"),
                                ("none", "none"), ("true:error", "true:suggestion"), ("false:silent", "false:silent"),
                                ("all", "all")):
            self.assertEqual(tool.lowered(value), expected, value)

    def test_the_seed_gets_both_blocks_around_the_sonar_block(self):
        with open(SEED, encoding="utf-8") as handle:
            write(".editorconfig", handle.read())
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        text = self.read()
        self.assertLess(text.index("# squad:dotnet-rules end"), text.index("# squad:sonar-rules begin"))
        self.assertLess(text.index("# squad:sonar-rules end"), text.index("# squad:dotnet-rules-paths begin"))
        self.assertEqual(text.count("# squad:dotnet-rules begin"), 1, "the seed's markers are used, not doubled")

    def test_the_template_baseline_is_readable(self):
        tool = load()
        with open(tool.BASELINE, encoding="utf-8") as handle:
            general, paths, _ = tool.wanted(handle.read(), {})
        self.assertIn("dotnet_diagnostic.S1125.severity = none", general, "== false is the binding style")
        self.assertIn("**/*.Tests/**.cs", [glob for glob, _ in paths])


if __name__ == "__main__":
    unittest.main()
