"""Unit tests for profiles/dotnet/managed/.squad/tools/dotnet_config.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import types
import unittest

from test_squad_tools import TOOLS, write

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", "dotnet", "managed", ".squad",
                      "tools", "dotnet_config.py")
BUILD_PROPS = """<Project>
  <PropertyGroup>
    <TargetFramework>net11.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <Deterministic>false</Deterministic>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Reihitsu.Analyzer" PrivateAssets="all" />
    <PackageReference Include="SonarAnalyzer.CSharp" PrivateAssets="all" />
  </ItemGroup>
</Project>
"""
PACKAGES_PROPS = """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Reihitsu.Analyzer" Version="1.2.0" />
    <PackageVersion Include="NodaTime" Version="3.3.7" />
  </ItemGroup>
</Project>
"""
TOOLS_JSON = '{"version": 1, "isRoot": true, "tools": {"reihitsu.cli": {"version": "1.2.0", "commands": ["reihitsu-format"]}}}'
APP = '<Project Sdk="Microsoft.NET.Sdk">\n  <ItemGroup>\n    <PackageReference Include="NodaTime" />\n' \
      '  </ItemGroup>\n</Project>\n'
WINDOWS = '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <TargetFramework>net11.0-windows</TargetFramework>\n' \
          '  </PropertyGroup>\n</Project>\n'
SEED = os.path.join(os.path.dirname(SCRIPT), "..", "..", "..", "seed", ".editorconfig")


def load(pending=None):
    for name in ("analyzer_common", "dotnet_config"):
        sys.modules.pop(name, None)
    values = {"BASE_REF": "main"} | ({"DOTNET_RULES_PENDING": pending} if pending is not None else {})
    sys.modules["squad_settings"] = types.SimpleNamespace(**values)
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("dotnet_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DotnetConfigTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        subprocess.run(["git", "init", "-q"], check=True)
        for path, text in (("Directory.Build.props", BUILD_PROPS), ("Directory.Packages.props", PACKAGES_PROPS),
                           (".config/dotnet-tools.json", TOOLS_JSON), (".gitattributes", "* text=auto eol=crlf\n"),
                           ("src/App/App.csproj", APP), ("src/Win/Win.csproj", WINDOWS),
                           ("src/App/Widget.cs", "namespace App;\n")):
            write(path, text)
        with open(SEED, encoding="utf-8") as handle:
            write(".editorconfig", handle.read())
        self.write_blocks()

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def write_blocks(self, pending=None):
        rules = load(pending).dotnet_rules()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rules.main([]), 0)

    def findings(self, pending=None):
        return load(pending).findings()

    def assertFinds(self, part, pending=None):
        found = self.findings(pending)
        self.assertTrue(any(part in finding for finding in found), f"{part!r} not in {found}")

    def test_a_repository_on_the_shared_structure_and_rules_passes(self):
        self.assertEqual(self.findings(), [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertTrue(load().check())
        self.assertIn("one build structure and the template's rules", output.getvalue())

    def test_a_repository_from_the_seeds_passes_once_its_target_framework_is_filled(self):
        seed = os.path.dirname(SEED)
        for rel, target in (("Directory.Build.props", "Directory.Build.props"),
                            ("Directory.Packages.props", "Directory.Packages.props"),
                            (".config/dotnet-tools.json", ".config/dotnet-tools.json"), ("gitattributes", ".gitattributes")):
            with open(os.path.join(seed, rel), encoding="utf-8") as handle:
                write(target, handle.read().replace("{{TODO: target framework, e.g. net10.0}}", "net11.0"))
        self.assertEqual(self.findings(), [], "the seeds and dotnet_config.py name the same structure")

    def test_a_target_framework_in_a_project_file_is_reported(self):
        write("src/App/App.csproj", APP.replace("<ItemGroup>", "<PropertyGroup><TargetFramework>net11.0</TargetFramework>"
                                                "</PropertyGroup>\n  <ItemGroup>"))
        self.assertFinds("src/App/App.csproj: <TargetFramework>net11.0</TargetFramework> belongs in Directory.Build.props")

    def test_a_platform_of_another_major_or_no_central_target_framework_is_reported(self):
        write("src/Win/Win.csproj", WINDOWS.replace("net11.0-windows", "net10.0-windows"))
        self.assertFinds("src/Win/Win.csproj: <TargetFramework>net10.0-windows")
        write("Directory.Build.props", BUILD_PROPS.replace("<TargetFramework>net11.0</TargetFramework>", ""))
        self.assertFinds("Directory.Build.props: no <TargetFramework>")

    def test_a_missing_or_weakened_switch_is_reported(self):
        write("Directory.Build.props", BUILD_PROPS.replace("<TreatWarningsAsErrors>true", "<TreatWarningsAsErrors>false")
              .replace("    <AnalysisLevel>latest-recommended</AnalysisLevel>\n", ""))
        found = self.findings()
        self.assertIn("Directory.Build.props: <TreatWarningsAsErrors> must be true (found false)", found)
        self.assertIn("Directory.Build.props: <AnalysisLevel> must be latest-recommended (found nothing)", found)

    def test_a_switch_set_again_in_a_project_file_is_reported(self):
        write("src/App/App.csproj", APP.replace("<ItemGroup>", "<PropertyGroup><Nullable>disable</Nullable>"
                                                "</PropertyGroup>\n  <ItemGroup>"))
        self.assertFinds("src/App/App.csproj: <Nullable> is set once in Directory.Build.props")

    def test_a_missing_analyzer_is_reported(self):
        write("Directory.Build.props", BUILD_PROPS.replace('<PackageReference Include="SonarAnalyzer.CSharp" '
                                                           'PrivateAssets="all" />', ""))
        self.assertFinds('no <PackageReference Include="SonarAnalyzer.CSharp">')

    def test_a_version_outside_central_package_management_is_reported(self):
        write("src/App/App.csproj", APP.replace('<PackageReference Include="NodaTime" />',
                                                '<PackageReference Include="NodaTime" Version="3.3.7" />'))
        self.assertFinds("src/App/App.csproj: NodaTime has a version of its own")
        write("src/App/App.csproj", APP.replace('<PackageReference Include="NodaTime" />',
                                                '<PackageReference Include="NodaTime">\n<VersionOverride>3.0'
                                                '</VersionOverride>\n</PackageReference>'))
        self.assertFinds("src/App/App.csproj: NodaTime has a version of its own")
        write("Directory.Packages.props", PACKAGES_PROPS.replace(">true<", ">false<"))
        self.assertFinds("<ManagePackageVersionsCentrally> must be true")

    def test_the_tool_manifest_belongs_under_config_with_the_analyzers_version(self):
        write(".config/dotnet-tools.json", TOOLS_JSON.replace("1.2.0", "1.1.0"))
        self.assertFinds("reihitsu.cli 1.1.0 and Reihitsu.Analyzer 1.2.0")
        write("dotnet-tools.json", TOOLS_JSON)
        self.assertFinds("dotnet-tools.json: move it to .config")

    def test_lf_for_csharp_files_is_reported(self):
        write(".gitattributes", "* text=auto eol=lf\n")
        self.assertFinds(".gitattributes: C# files are checked out with CRLF")

    def test_rule_sets_switched_off_rules_and_assembly_wide_suppressions_are_reported(self):
        write("rules/App.ruleset", "<RuleSet />")
        write("src/App/App.csproj", APP.replace("<ItemGroup>", "<PropertyGroup><CodeAnalysisRuleSet>x.ruleset"
                                                "</CodeAnalysisRuleSet><NoWarn>$(NoWarn);NU1608;CS1591;SA1600</NoWarn>"
                                                "</PropertyGroup>\n  <ItemGroup>"))
        write("src/GlobalSuppressions.cs", '[assembly: SuppressMessage("C", "S2325:Static", Scope = "module")]\n'
              '[assembly: SuppressMessage("C", "S107:Many", Scope = "member", Target = "~M:App.Widget.Run")]\n')
        found = self.findings()
        self.assertIn("rules/App.ruleset: a rule set; the rules are the dotnet-rules block's", found)
        self.assertIn("src/App/App.csproj: <CodeAnalysisRuleSet>; the rules are the dotnet-rules block's", found)
        self.assertTrue(any("<NoWarn> switches off CS1591, SA1600;" in finding for finding in found),
                        "NU1608 is a NuGet warning, no analyzer rule")
        self.assertEqual(sum("assembly-wide SuppressMessage" in finding for finding in found), 1,
                         "a suppression with a Target is scoped")

    def test_an_outdated_block_or_a_rule_outside_the_blocks_is_reported(self):
        with open(".editorconfig", encoding="utf-8") as handle:
            text = handle.read()
        write(".editorconfig", text.replace("# squad:sonar-rules begin",
                                            "dotnet_diagnostic.S3776.severity = none\n# squad:sonar-rules begin"))
        self.assertFinds("[*.cs] sets dotnet_diagnostic.S3776.severity outside the dotnet-rules block")
        write(".editorconfig", text.replace("charset = utf-8", "charset = latin1", 1))
        self.assertFinds("[*] sets charset = latin1, the baseline utf-8")
        write(".editorconfig", text.replace("S1125.severity = none", "S1125.severity = error"))
        self.assertFinds("the dotnet-rules blocks are missing or out of date")

    def test_a_section_of_a_path_after_the_blocks_may_set_rules(self):
        with open(".editorconfig", encoding="utf-8") as handle:
            text = handle.read()
        write(".editorconfig", text + "\n[**/Migrations/*.cs]\ngenerated_code = true\ndotnet_diagnostic.S1192.severity = none\n")
        self.assertEqual(self.findings(), [])

    def test_a_pending_entry_for_a_rule_the_baseline_switches_off_is_refused(self):
        self.write_blocks(pending={"S1125": "#1"})
        self.assertFinds("DOTNET_RULES_PENDING: S1125 is off in the baseline", pending={"S1125": "#1"})

    def test_a_pending_entry_without_an_issue_is_reported(self):
        self.assertFinds("DOTNET_RULES_PENDING", pending={"S3776": "soon"})


if __name__ == "__main__":
    unittest.main()
