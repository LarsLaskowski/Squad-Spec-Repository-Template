"""Unit tests for profiles/dotnet/managed/.squad/tools/dotnet_major.py: run `python3 -m unittest discover tools`."""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest

from test_squad_tools import write

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", "dotnet", "managed", ".squad",
                      "tools", "dotnet_major.py")
GLOBAL_JSON = '{\n  // the SDK of the solution\n  "sdk": { "version": "10.0.100", "rollForward": "latestFeature" }\n}\n'


def load():
    spec = importlib.util.spec_from_file_location("dotnet_major", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project(framework, tag="TargetFramework"):
    return f"<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <{tag}>{framework}</{tag}>\n" \
           f"  </PropertyGroup>\n</Project>\n"


class DotnetMajorTest(unittest.TestCase):
    def setUp(self):
        self.tool = load()
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def check(self, *files):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ok = self.tool.check(sorted(files))
        return ok, output.getvalue()

    def test_one_major_everywhere_passes(self):
        write("global.json", GLOBAL_JSON)
        write("src/App/App.csproj", project("net10.0"))
        write("src/Win/Win.csproj", project("net10.0-windows;netstandard2.0", "TargetFrameworks"))
        write("Dockerfile", 'ARG BASE_SDK="mcr.microsoft.com/dotnet/sdk:10.0-alpine"\n'
                            "FROM ${BASE_SDK} AS build\nFROM mcr.microsoft.com/dotnet/aspnet:10.0.14-alpine@sha256:ab\n")
        ok, out = self.check("global.json", "src/App/App.csproj", "src/Win/Win.csproj", "Dockerfile")
        self.assertTrue(ok, out)
        self.assertIn(".NET major: 10 everywhere (4 target framework(s), image(s) and script path(s); global.json "
                      "(SDK 10) names it)", out)

    def test_a_new_project_on_the_next_major_fails(self):
        write("global.json", GLOBAL_JSON)
        write("src/App/App.csproj", project("net10.0"))
        write("src/New/New.csproj", project("net11.0"))
        ok, out = self.check("global.json", "src/App/App.csproj", "src/New/New.csproj")
        self.assertFalse(ok)
        self.assertIn("src/New/New.csproj:3: net11.0 is .NET 11, but global.json (SDK 10) names .NET 10", out)
        self.assertNotIn("App.csproj", out)

    def test_an_image_on_the_next_major_fails_also_from_a_tag_argument(self):
        write("Directory.Build.props", project("net10.0"))
        write("deploy/Dockerfile", 'ARG BASE_RUNTIME_IMAGE="mcr.microsoft.com/dotnet/aspnet"\n'
                                   'ARG BASE_RUNTIME_TAG="11.0-noble-chiseled"\n'
                                   "FROM ${BASE_RUNTIME_IMAGE}:${BASE_RUNTIME_TAG}\n")
        ok, out = self.check("Directory.Build.props", "deploy/Dockerfile")
        self.assertFalse(ok)
        self.assertIn("deploy/Dockerfile:2: mcr.microsoft.com/dotnet/aspnet:11.0-noble-chiseled is .NET 11, but the "
                      "target frameworks name .NET 10", out)

    def test_without_global_json_the_projects_must_agree(self):
        write("a.csproj", project("net10.0"))
        write("b.csproj", project("net10.0;net11.0", "TargetFrameworks"))
        ok, out = self.check("a.csproj", "b.csproj")
        self.assertFalse(ok)
        self.assertIn("the target frameworks name 10, 11 and no global.json fixes one", out)

    def test_global_json_on_another_major_than_the_projects_fails(self):
        write("global.json", GLOBAL_JSON.replace("10.0.100", "11.0.100"))
        write("a.csproj", project("net10.0"))
        ok, out = self.check("global.json", "a.csproj")
        self.assertFalse(ok)
        self.assertIn("a.csproj:3: net10.0 is .NET 10, but global.json (SDK 11) names .NET 11", out)

    def test_a_script_or_workflow_on_another_major_fails(self):
        # Censio#158: release-check.sh kept `net10.0-windows` after the projects moved on.
        write("global.json", GLOBAL_JSON.replace("10.0.100", "11.0.100"))
        write("a.csproj", project("net11.0-windows"))
        write(".github/scripts/release-check.sh", 'exe="bin/Release/net10.0-windows/App.exe"\n'
                                                  'tag="v10.0.0"  # a version tag, no moniker\n')
        write(".github/workflows/release.yml", "      - run: ls out/net11.0-windows/\n      - run: echo dotnet10.0\n")
        write("tools/pack.ps1", "$out = 'publish/net10.0'\n")
        write("docs/build.md", "Built for net10.0.\n")
        ok, out = self.check("global.json", "a.csproj", ".github/scripts/release-check.sh",
                             ".github/workflows/release.yml", "tools/pack.ps1", "docs/build.md")
        self.assertFalse(ok)
        self.assertIn(".github/scripts/release-check.sh:1: net10.0-windows is .NET 10, but global.json (SDK 11) names "
                      ".NET 11", out)
        self.assertIn("tools/pack.ps1:1: net10.0 is .NET 10", out)
        self.assertNotIn("release.yml", out, "the workflow names the repository's major")
        self.assertNotIn(":2:", out, "a version tag and a longer word are no monikers")
        self.assertNotIn("build.md", out, "documentation is not read")

    def test_properties_build_arguments_and_other_images_are_not_read(self):
        write("a.csproj", project("$(AppTargetFramework)") + project("net48"))
        write("Dockerfile", "FROM ${BASE_SDK} AS build\nFROM golang:1.25\nFROM alpine:3.24\n")
        ok, out = self.check("a.csproj", "Dockerfile")
        self.assertTrue(ok, out)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
