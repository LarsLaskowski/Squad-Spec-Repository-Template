"""Unit tests for tools/dotnet-baseline.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dotnet-baseline.py")
spec = importlib.util.spec_from_file_location("dotnet_baseline", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

EDITORCONFIG = """# comment
\ufeffroot = true

[*]
end_of_line = crlf

[*.md]
trim_trailing_whitespace = false

[*.{cs,vb}]
csharp_style_namespace_declarations = file_scoped:Warning
csharp_style_var_elsewhere = true:hint
dotnet_diagnostic.rh0001.severity = Warning
# squad:sonar-rules begin — generated
dotnet_diagnostic.S3776.severity = error
# squad:sonar-rules end

[**/Migrations/*.cs]
generated_code = true
dotnet_diagnostic.S1192.severity = none
dotnet_style_readonly_field = true:error
"""
RULESET = """\ufeff<?xml version="1.0" encoding="utf-8"?>
<RuleSet Name="Rules" ToolsVersion="18.0">
  <Rules AnalyzerId="Reihitsu.Analyzer" RuleNamespace="Reihitsu.Analyzer">
    <Rule Id="RH0001" Action="Error" />
    <Rule Id="RH0002" Action="Info" />
    <Rule Id="CA1822" Action="Hidden" />
  </Rules>
</RuleSet>
"""


def config(name, **general):
    result = tool.Config(name)
    result.general = {key.replace("__", "."): value for key, value in general.items()}
    return result


def diagnostic(rule):
    return f"dotnet_diagnostic.{rule}.severity"


def git(root, *args):
    return subprocess.run(["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           *args], check=True, capture_output=True, text=True).stdout


class TestSections(unittest.TestCase):
    def test_a_section_every_csharp_file_reads_is_told_from_one_of_a_path(self):
        for glob in ("*", "*.cs", "*.{cs,vb}", "*.{cs,razor}"):
            self.assertEqual(tool.section_kind(glob), "all", glob)
        for glob in ("tests/**.cs", "**/Migrations/*.cs", "**/*.Tests/**.cs", "*.g.cs"):
            self.assertEqual(tool.section_kind(glob), "path", glob)
        for glob in ("*.md", "*.{json,yml,yaml,csproj}", "Makefile"):
            self.assertIsNone(tool.section_kind(glob), glob)

    def test_an_option_value_and_its_severity_are_split(self):
        self.assertEqual(tool.split_value("file_scoped:Warning"), ("file_scoped", "warning"))
        self.assertEqual(tool.split_value("true:hint"), ("true", "silent"), "ReSharper's hint is no .NET severity")
        self.assertEqual(tool.split_value("before_and_after"), ("before_and_after", None))
        self.assertEqual(tool.split_value("a:b"), ("a:b", None), "an unknown suffix is part of the value")

    def test_keys_are_normalized(self):
        self.assertEqual(tool.normalized_key(" dotnet_diagnostic.rh0001.Severity "), diagnostic("RH0001"))
        self.assertEqual(tool.normalized_key("CSharp_Style_Var_Elsewhere"), "csharp_style_var_elsewhere")


class TestReading(unittest.TestCase):
    def test_the_editorconfig_is_read_without_the_sonar_block_and_with_path_exceptions(self):
        result = tool.Config("x")
        tool.parse_editorconfig(result, EDITORCONFIG)
        self.assertEqual(result.general["end_of_line"], "crlf")
        self.assertEqual(result.general[diagnostic("RH0001")], "warning")
        self.assertEqual(result.general["csharp_style_var_elsewhere"], "true:hint", "the value is merged, not rewritten")
        self.assertNotIn(diagnostic("S3776"), result.general, "the sonar-rules block is generated, not a choice")
        self.assertNotIn("trim_trailing_whitespace", result.general, "a section of other files is not read")
        self.assertNotIn("root", result.general)
        self.assertEqual(result.paths["**/Migrations/*.cs"], {"generated_code": "true", diagnostic("S1192"): "none"})
        self.assertEqual(result.general["dotnet_style_readonly_field"], "true:error",
                         "a code-style option in a section of a path is read for every file")
        self.assertEqual(len(result.warnings), 1, "and that is warned about")

    def test_rule_sets_keep_the_stricter_action(self):
        result = tool.Config("x")
        tool.parse_ruleset(result, RULESET)
        tool.parse_ruleset(result, RULESET.replace('"Error"', '"Warning"').replace('"Info"', '"Error"'))
        self.assertEqual(result.general[diagnostic("RH0001")], "error")
        self.assertEqual(result.general[diagnostic("RH0002")], "error")
        self.assertEqual(result.general[diagnostic("CA1822")], "silent")

    def test_no_warn_and_assembly_wide_suppressions_switch_a_rule_off(self):
        self.assertEqual(tool.switched_off("<NoWarn>$(NoWarn);SA1204; cs1591,IDE0005</NoWarn>"),
                         ["SA1204", "CS1591", "IDE0005"])
        text = ('[assembly: SuppressMessage("Minor Code Smell", "S1125:Boolean literals", Justification = "x", '
                'Scope = "module")]\n'
                '[assembly: SuppressMessage("Major Code Smell", "S107:Too many", Justification = "x", Scope = "member", '
                'Target = "~M:A.B(System.Int32)")]\n')
        self.assertEqual(tool.suppressed(text), ["S1125"], "a suppression with a Target is scoped, not assembly-wide")

    def test_a_consumer_is_read_at_its_ref_with_editorconfig_over_rule_sets(self):
        with tempfile.TemporaryDirectory() as root:
            git(root, "init", "-q")
            files = {".editorconfig": "[*.cs]\ndotnet_diagnostic.RH0001.severity = none\n",
                     "rules/App.ruleset": RULESET,
                     "src/App/App.csproj": "<Project><PropertyGroup><NoWarn>SA1600</NoWarn></PropertyGroup></Project>",
                     "src/GlobalSuppressions.cs": '[assembly: SuppressMessage("C", "S2325:Static", Scope = "module")]\n'}
            for rel, text in files.items():
                os.makedirs(os.path.dirname(os.path.join(root, rel)) or root, exist_ok=True)
                with open(os.path.join(root, rel), "w", encoding="utf-8") as handle:
                    handle.write(text)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "x")
            with open(os.path.join(root, ".editorconfig"), "a", encoding="utf-8") as handle:
                handle.write("dotnet_diagnostic.RH0002.severity = none\n")
            result = tool.read_consumer("o/App", root, "HEAD")
            self.assertEqual(result.general[diagnostic("RH0001")], "none", ".editorconfig wins over a rule set")
            self.assertEqual(result.general[diagnostic("RH0002")], "suggestion", "the working tree is not read")
            self.assertEqual(result.general[diagnostic("SA1600")], "none")
            self.assertEqual(result.general[diagnostic("S2325")], "none")
            with self.assertRaises(tool.NotChecked):
                tool.read_consumer("o/App", root, "origin/main")

    def test_only_active_dotnet_consumers_are_read(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "consumers.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"consumers": [{"repository": "o/a", "profiles": ["go", "dotnet"], "status": "active"},
                                         {"repository": "o/b", "profiles": ["dotnet"], "status": "legacy"},
                                         {"repository": "o/c", "profiles": ["node"], "status": "active"}]}, handle)
            self.assertEqual(tool.dotnet_consumers(path), ["o/a"])


class TestMerging(unittest.TestCase):
    def test_the_highest_severity_wins(self):
        merged = tool.merge([config("a", dotnet_diagnostic__RH0001__severity="warning"),
                             config("b", dotnet_diagnostic__RH0001__severity="error")])
        self.assertEqual(merged.general[diagnostic("RH0001")], "error")

    def test_a_rule_switched_off_where_set_and_default_elsewhere_stays_at_the_default(self):
        merged = tool.merge([config("a", dotnet_diagnostic__CA1822__severity="silent"), config("b"), config("c")])
        self.assertNotIn(diagnostic("CA1822"), merged.general)
        self.assertEqual(merged.off_once[diagnostic("CA1822")], {"a": "silent"})

    def test_a_rule_every_repository_switches_off_stays_off(self):
        merged = tool.merge([config("a", dotnet_diagnostic__RH2102__severity="none"),
                             config("b", dotnet_diagnostic__RH2102__severity="none")])
        self.assertEqual(merged.general[diagnostic("RH2102")], "none")

    def test_a_rule_raised_once_is_raised(self):
        merged = tool.merge([config("a", dotnet_diagnostic__S1192__severity="error"), config("b")])
        self.assertEqual(merged.general[diagnostic("S1192")], "error")

    def test_an_option_keeps_its_value_and_takes_the_highest_severity(self):
        merged = tool.merge([config("a", csharp_style_var_elsewhere="true:suggestion"),
                             config("b", csharp_style_var_elsewhere="true:hint"),
                             config("c", csharp_prefer_braces="true:error"),
                             config("d", csharp_new_line_before_open_brace="all")])
        self.assertEqual(merged.general["csharp_style_var_elsewhere"], "true:suggestion")
        self.assertEqual(merged.general["csharp_prefer_braces"], "true:error")
        self.assertEqual(merged.general["csharp_new_line_before_open_brace"], "all")

    def test_different_values_are_a_conflict(self):
        merged = tool.merge([config("a", end_of_line="lf"), config("b", end_of_line="crlf")])
        self.assertEqual(merged.conflicts["end_of_line"], {"a": "lf", "b": "crlf"})
        self.assertNotIn("end_of_line", merged.general)

    def test_a_naming_rule_severity_is_a_severity(self):
        merged = tool.merge([config("a", **{"dotnet_naming_rule.fields.severity": "warning"}),
                             config("b", **{"dotnet_naming_rule.fields.severity": "error"})])
        self.assertEqual(merged.general["dotnet_naming_rule.fields.severity"], "error")

    def test_decisions_replace_the_merge_and_resolve_conflicts(self):
        merged = tool.merge([config("a", end_of_line="lf", dotnet_diagnostic__CA1822__severity="silent"),
                             config("b", end_of_line="crlf", dotnet_diagnostic__S1125__severity="error")])
        tool.apply_decisions(merged, {
            "settings": {"end_of_line": {"value": "crlf", "reason": "CRLF"},
                         "dotnet_diagnostic.ca1822.severity": {"value": None, "reason": "default"},
                         "dotnet_diagnostic.S1125.severity": {"value": "none", "reason": "== false"}},
            "sections": {"**/*.Tests/**.cs": {"dotnet_diagnostic.S107.severity": {"value": "none", "reason": "tests"}}}})
        self.assertEqual(merged.conflicts, {})
        self.assertEqual(merged.off_once, {})
        self.assertEqual(merged.general, {"end_of_line": "crlf", diagnostic("S1125"): "none"})
        self.assertEqual(merged.sections, {"**/*.Tests/**.cs": {diagnostic("S107"): "none"}})
        self.assertEqual(merged.reasons[diagnostic("S1125")], "== false")

    def test_a_rule_the_analyzers_do_not_know_is_dropped(self):
        merged = tool.merge([config("a", dotnet_diagnostic__RH4119__severity="error",
                                    dotnet_diagnostic__RH3001__severity="error",
                                    dotnet_diagnostic__CS8618__severity="error")])
        tool.drop_unknown(merged, {"RH3001", "S1125"})
        self.assertEqual(set(merged.general), {diagnostic("RH3001"), diagnostic("CS8618")},
                         "a family no analyzer was recorded for is kept")
        self.assertEqual(merged.dropped, {diagnostic("RH4119"): "error"})


class TestAnalyzerIds(unittest.TestCase):
    BINARY = ("S1125".encode("utf-16-le") + b"\x00\x00" + "XS999".encode("utf-16-le") + b"\x00\x00"
              + b"S3776\x00RS1234\x00\x0d" + "RH3001".encode("utf-16-le"))

    def test_ids_are_found_as_wide_and_plain_strings_but_not_inside_other_words(self):
        self.assertEqual(tool.ids_in(self.BINARY, "S"), {"S1125", "S3776"})
        self.assertEqual(tool.ids_in(self.BINARY, "RH"), {"RH3001"})

    def package(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("analyzers/SonarAnalyzer.CSharp.dll", self.BINARY)
            archive.writestr("analyzers/dotnet/cs/de/SonarAnalyzer.CSharp.resources.dll", "S9999".encode("utf-16-le"))
            archive.writestr("analyzers/dotnet/vb/SonarAnalyzer.CSharp.dll", "S7777".encode("utf-16-le"))
            archive.writestr("lib/Other.dll", "S8888".encode("utf-16-le"))
        return data.getvalue()

    def test_the_analyzers_in_use_are_read_from_the_consumers(self):
        props = ('<Project><ItemGroup>\n<PackageVersion Include="SonarAnalyzer.CSharp" Version="10.36.0.15337" />\n'
                 '<PackageVersion Version="4.5.2" Include="MSTest" />\n<PackageVersion Include="Reihitsu.Analyzer" '
                 'Version="$(Floating)" />\n<PackageVersion Include="NodaTime" Version="3.3.7" />\n</ItemGroup></Project>')
        self.assertEqual(tool.analyzer_versions(props), {("SonarAnalyzer.CSharp", "10.36.0.15337"),
                                                         ("MSTest.Analyzers", "4.5.2")},
                         "the MSTest metapackage brings MSTest.Analyzers; a version that is no version is skipped")
        self.assertEqual(tool.sdk_version('{"sdk": {"version": "11.0.100", "rollForward": "latestFeature"}}'), "11.0.100")
        self.assertIsNone(tool.sdk_version("not json"))
        self.assertIsNone(tool.sdk_version('{"sdk": {"version": "--help"}}'))

    def test_the_sdk_of_the_feature_band_is_taken(self):
        installed = {"11.0.100": "/d/sdk/11.0.100", "11.0.103": "/d/sdk/11.0.103", "11.0.200": "/d/sdk/11.0.200",
                     "10.0.404": "/d/sdk/10.0.404"}
        self.assertEqual(tool.sdk_folder("11.0.100", installed), "/d/sdk/11.0.103", "the newest patch of 11.0.1xx")
        self.assertEqual(tool.sdk_folder("10.0.400", installed), "/d/sdk/10.0.404")
        with self.assertRaises(tool.NotChecked):
            tool.sdk_folder("9.0.100", installed)

    def test_the_installed_sdks_are_read_from_dotnet(self):
        listing = "10.0.404 [/usr/lib/dotnet/sdk]\n11.0.100 [/usr/lib/dotnet/sdk]\nnot an sdk line\n--x [/tmp]\n"
        done = subprocess.CompletedProcess(["dotnet"], 0, stdout=listing, stderr="")
        with mock.patch.object(tool.subprocess, "run", return_value=done):
            self.assertEqual(tool.installed_sdks(), {"10.0.404": os.path.join("/usr/lib/dotnet/sdk", "10.0.404"),
                                                     "11.0.100": os.path.join("/usr/lib/dotnet/sdk", "11.0.100")})
        with mock.patch.object(tool.subprocess, "run", side_effect=OSError("no dotnet")):
            self.assertEqual(tool.installed_sdks(), {})

    def test_ids_are_recorded_from_the_packages_and_sdks_the_consumers_use(self):
        with tempfile.TemporaryDirectory() as root:
            clone = os.path.join(root, "App")
            os.makedirs(clone)
            git(clone, "init", "-q")
            with open(os.path.join(clone, "Directory.Packages.props"), "w", encoding="utf-8") as handle:
                handle.write('<Project><PackageVersion Include="SonarAnalyzer.CSharp" Version="1.0.0" /></Project>')
            with open(os.path.join(clone, "global.json"), "w", encoding="utf-8") as handle:
                handle.write('{"sdk": {"version": "11.0.100"}}')
            git(clone, "add", "-A")
            git(clone, "commit", "-qm", "x")
            git(clone, "update-ref", "refs/remotes/origin/main", "HEAD")
            analyzers = os.path.join(root, "sdk", "11.0.100", "Sdks", "Microsoft.NET.Sdk", "analyzers")
            os.makedirs(analyzers)
            for name, text in (("Microsoft.CodeAnalysis.NetAnalyzers.dll", "CA1822"), ("X.NetAnalyzers.resources.dll", "CA9999")):
                with open(os.path.join(analyzers, name), "wb") as handle:
                    handle.write(text.encode("utf-16-le"))
            fetched = []

            def fetch(package, version):
                fetched.append((package, version))
                return self.package()

            out = os.path.join(root, "ids.txt")
            with contextlib.redirect_stdout(io.StringIO()):
                tool.record_ids({"o/App": clone}, out, fetch=fetch,
                                sdks=lambda: {"11.0.100": os.path.join(root, "sdk", "11.0.100")})
            self.assertEqual(fetched, [("SonarAnalyzer.CSharp", "1.0.0")])
            self.assertEqual(tool.load_ids(out), {"S1125", "S3776", "CA1822"},
                             "only each analyzer's own family, without resource, VB or other assemblies")
            with open(out, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("SonarAnalyzer.CSharp 1.0.0: analyzers/SonarAnalyzer.CSharp.dll", text)
            self.assertIn("sdk/11.0.100/Sdks/Microsoft.NET.Sdk/analyzers/Microsoft.CodeAnalysis.NetAnalyzers.dll", text)

    def test_a_folder_that_is_no_repository_is_refused(self):
        with tempfile.TemporaryDirectory() as root, self.assertRaises(tool.NotChecked):
            tool.clone_root("o/App", root)

    def test_a_source_is_named_without_the_machine_part(self):
        self.assertEqual(tool.source_label("/usr/lib/dotnet/sdk/11.0.100/Sdks/x/A.NetAnalyzers.dll"),
                         "sdk/11.0.100/Sdks/x/A.NetAnalyzers.dll")
        self.assertEqual(tool.source_label("/opt/A.dll"), "A.dll")


class TestOutput(unittest.TestCase):
    def merged(self):
        merged = tool.merge([config("a", end_of_line="crlf", csharp_prefer_braces="true:error",
                                    dotnet_diagnostic__S107__severity="error", dotnet_diagnostic__S1125__severity="none",
                                    dotnet_diagnostic__RH0010__severity="error", dotnet_diagnostic__RH0002__severity="error")])
        tool.apply_decisions(merged, {"settings": {"dotnet_diagnostic.S1125.severity": {"value": "none", "reason": "why"}},
                                      "sections": {"**/*.Tests/**.cs": {"dotnet_diagnostic.S107.severity":
                                                                        {"value": "none", "reason": "tests"}}}})
        return merged

    def test_the_baseline_is_grouped_sorted_and_carries_the_reasons(self):
        text = tool.render(self.merged())
        self.assertTrue(text.startswith(tool.HEADER))
        body = text.splitlines()
        self.assertLess(body.index("end_of_line = crlf"), body.index("csharp_prefer_braces = true:error"))
        self.assertLess(body.index("dotnet_diagnostic.RH0002.severity = error"),
                        body.index("dotnet_diagnostic.RH0010.severity = error"), "rule ids sort by number")
        self.assertEqual(body[body.index("dotnet_diagnostic.S1125.severity = none") - 1], "# why")
        self.assertEqual(body[body.index("dotnet_diagnostic.S107.severity = none") - 1], "# tests")
        self.assertLess(body.index("[*.cs]"), body.index("[**/*.Tests/**.cs]"))
        self.assertEqual(text, tool.render(self.merged()), "the output is reproducible")

    def test_check_reports_an_outdated_file_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "baseline.editorconfig")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(tool.write_or_check("a\n", True, path))
                self.assertFalse(os.path.exists(path))
                self.assertTrue(tool.write_or_check("a\n", False, path))
                self.assertTrue(tool.write_or_check("a\n", True, path))
                self.assertFalse(tool.write_or_check("b\n", True, path))

    def test_the_changes_per_repository_are_counted(self):
        merged = self.merged()
        tightened, added = tool.changes(config("b", end_of_line="lf", csharp_prefer_braces="true:error"), merged)
        self.assertEqual(tightened, ["end_of_line: lf -> crlf"])
        self.assertIn("dotnet_diagnostic.RH0010.severity = error", added)


class TestDecisionsFile(unittest.TestCase):
    def test_every_decision_has_a_value_or_null_and_a_reason(self):
        decisions = tool.load_decisions()
        entries = list(decisions["settings"].items())
        entries += [item for settings in decisions["sections"].values() for item in settings.items()]
        for key, decision in entries:
            self.assertIn("value", decision, key)
            self.assertTrue(decision["value"] is None or isinstance(decision["value"], str), key)
            self.assertTrue(decision.get("reason"), f"{key} needs a reason")

    def test_the_binding_decisions_are_recorded(self):
        settings = tool.load_decisions()["settings"]
        self.assertEqual(settings["dotnet_diagnostic.S1125.severity"]["value"], "none", "== false is the style")
        self.assertEqual(settings["end_of_line"]["value"], "crlf")


if __name__ == "__main__":
    unittest.main()
