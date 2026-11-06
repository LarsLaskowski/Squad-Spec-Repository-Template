"""Unit tests for core/.squad/tools/config-check.py (front matter without PyYAML, seed text left without its braces,
the members' guards declared in .claude/settings.json, the size of .squad/project.md): run
`python3 -m unittest discover tools`."""
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "core", ".squad", "tools", "config-check.py")
# Runs a script with `import yaml` failing, as on a machine without PyYAML.
WITHOUT_YAML = ("import runpy, sys; sys.modules['yaml'] = None; sys.argv = sys.argv[1:]; "
                "runpy.run_path(sys.argv[0], run_name='__main__')")

try:
    import yaml
except ImportError:
    yaml = None


def load_script(without_yaml=False):
    with mock.patch.dict(sys.modules, {"yaml": None} if without_yaml else {}):
        spec = importlib.util.spec_from_file_location("config_check", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# Front matter both parsers read, with the values expected for these keys.
VALID = [
    ('name: x\ndescription: "Use when: quoted, \\"escaped\\""', {"description": 'Use when: quoted, "escaped"'}),
    ("name: x\ndescription: it's a:b test # a comment", {"description": "it's a:b test"}),
    ("name: x\ndescription: first\n  second line", {"description": "first second line"}),
    ('name: x\ndescription: "a: b\n  c"', {"description": "a: b c"}),
    ("name: x\ndescription: 'it''s: fine'", {"description": "it's: fine"}),
    ("name: x\ndescription: >-\n  one\n  two\nmodel: opus", {"description": "one two", "model": "opus"}),
    ("name: x\ndescription: |\n  one\n  two", {"description": "one\ntwo"}),
    ("# a comment\nname: x\n\ndescription: y\ntools:\n  - Read\n  - Grep\neffort: medium",
     {"name": "x", "description": "y", "effort": "medium"}),
    ("name: x\ndescription:", {"name": "x", "description": None}),
]
# Front matter PyYAML refuses, and Claude Code drops the file for.
INVALID = [
    "name: x\ndescription: Use when: something",
    "name: x\ndescription: ends with a colon:",
    "name: x\ndescription: first\n  second: line",
    "name: x\n  description: y",
    'name: x\ndescription: "unterminated',
    'name: x\ndescription: "quoted" and more',
    "name: x\ndescription: @mention",
    "name: x\ndescription: `code`",
    "name: x\ndescription: - item",
    "name: x\njust a sentence",
    "name: x\ndescription:\tafter a tab",
    "name: x\ndescription: > text on the header line",
]


class TestFrontMatterWithoutYaml(unittest.TestCase):
    def setUp(self):
        self.script = load_script(without_yaml=True)

    def test_the_script_runs_without_pyyaml(self):
        self.assertIsNone(self.script.yaml)
        self.assertEqual(self.script.PARSE_ERRORS, (ValueError,))

    def test_valid_front_matter_reads_like_pyyaml(self):
        for text, expected in VALID:
            with self.subTest(text=text):
                data = self.script.parse_front_matter(text)
                self.assertEqual({key: data.get(key) for key in expected}, expected)
                if yaml:
                    parsed = yaml.safe_load(text)
                    self.assertEqual({key: parsed.get(key) for key in expected}, expected, "PyYAML reads it so")

    def test_front_matter_pyyaml_refuses_is_refused(self):
        for text in INVALID:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.script.parse_front_matter(text)
                if yaml:
                    with self.assertRaises(yaml.YAMLError, msg="PyYAML refuses it too"):
                        yaml.safe_load(text)

    def test_an_error_names_its_line_and_key(self):
        with self.assertRaisesRegex(ValueError, r"line 2: mapping values .*\('description'\)"):
            self.script.parse_front_matter("name: x\ndescription: Use when: something")

    def test_empty_front_matter_is_no_mapping(self):
        self.assertIsNone(self.script.parse_front_matter("# only a comment\n"))

    def test_the_templates_agents_and_skills_read_like_pyyaml(self):
        paths = glob.glob(os.path.join(ROOT, "core", ".claude", "agents", "*.md")) + \
            glob.glob(os.path.join(ROOT, "core", ".claude", "skills", "*", "SKILL.md")) + \
            glob.glob(os.path.join(ROOT, ".claude", "skills", "*", "SKILL.md"))
        self.assertGreater(len(paths), 10)
        with_yaml = load_script() if yaml else None
        for path in paths:
            with self.subTest(path=os.path.relpath(path, ROOT)):
                data = self.script.front_matter(path)
                self.assertTrue(data["description"])
                if with_yaml:
                    expected = with_yaml.front_matter(path)
                    self.assertEqual({k: data.get(k) for k in ("name", "description", "model", "effort", "tools")},
                                     {k: expected.get(k) for k in ("name", "description", "model", "effort", "tools")})

    def test_check_reports_a_broken_agent_and_passes_a_valid_one(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = os.path.join(folder, "squad-dev.md")
            write(broken, "---\nname: squad-dev\ndescription: Squad Dev: implements\nmodel: sonnet\neffort: medium\n"
                          "---\n\nBody.\n")
            valid = os.path.join(folder, "squad-tester.md")
            write(valid, "---\nname: squad-tester\ndescription: \"Squad Tester: writes tests\"\nmodel: sonnet\n"
                         "effort: medium\n---\n\nBody.\n")
            errors = []
            self.script.check(broken, "squad-dev", errors, agent=True)
            self.script.check(valid, "squad-tester", errors, agent=True)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("squad-dev.md: line 2: mapping values are not allowed here", errors[0])


class TestSeededBullets(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_the_list_holds_every_seed_bullet_that_starts_with_a_placeholder(self):
        starts = re.compile(r"^[ \t]*[-*+][ \t]+[`*]*\{\{TODO:")
        found = {}
        seeds = [os.path.join(ROOT, "seed")] + glob.glob(os.path.join(ROOT, "profiles", "*", "seed"))
        for seed in seeds:
            for path in glob.glob(os.path.join(seed, "**", "*.md"), recursive=True, include_hidden=True):
                for line in read(path).splitlines():
                    if starts.match(line):
                        text = re.sub(r"\{\{TODO:\s*(.*?)\}\}", r"\1", re.sub(r"^\s*[-*+]\s+", "", line)).strip()
                        found.setdefault(os.path.normpath(os.path.relpath(path, seed)), set()).add(text)
        listed = {os.path.normpath(path): set(bullets) for path, bullets in self.script.SEEDED_BULLETS.items()}
        self.assertEqual(listed, found)

    def test_a_bullet_left_as_the_seed_text_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "project.md")
            write(path, "## Integration surface\n\n- its interface\n- TODO: Registration and lifetime.\n"
                        "- the component list in docs/ARCHITECTURE.md\n- `FakeX` \u2013 what it stands in for\n"
                        "- `IClock` in `src/Time.cs`, registered as a singleton\n- {{TODO: the test double}}\n"
                        "Its interface, prose and no bullet.\n")
            errors = []
            self.script.check_seeded_bullets(path, {self.script.bullet_key(b) for b in
                                                    self.script.SEEDED_BULLETS[os.path.join(".squad", "project.md")]},
                                             errors)
        self.assertEqual([error.split(": ", 1)[0].rsplit(":", 1)[1] for error in errors], ["3", "4", "5", "6"])
        self.assertIn("'its interface' is the seed's placeholder text without its braces", errors[0])

    def test_an_earlier_seed_bullet_is_still_reported(self):
        with tempfile.TemporaryDirectory() as repo:
            cwd = os.getcwd()
            os.chdir(repo)
            try:
                write(self.script.PROJECT_FILE, "## Guarantees\n\n"
                                                "- guarantee — [decision NNNN](../docs/decisions/NNNN-title.md)\n"
                                                "- guarantee — [decision NNNN](../docs/decisions/NNNN-title.md), "
                                                "[area](../docs/areas/area.md)\n")
                errors = []
                self.script.check_project_files(errors)
            finally:
                os.chdir(cwd)
        self.assertEqual(sorted(e.split(": '")[0] for e in errors if "placeholder text" in e),
                         [os.path.join(".squad", "project.md") + ":3", os.path.join(".squad", "project.md") + ":4"])


class TestSettingsFile(unittest.TestCase):
    """A squad_settings.py that does not load is an error of config-check.py; decision-check.py keeps its defaults."""

    def test_a_broken_settings_file_is_reported_once(self):
        script = load_script()
        with tempfile.TemporaryDirectory() as repo:
            cwd = os.getcwd()
            os.chdir(repo)
            try:
                errors = []
                script.check_settings_file(errors)
                self.assertEqual(errors, [], "no file: reported as a missing required file instead")
                write(script.SETTINGS_FILE, "COVERAGE_THRESHOLD = (\n")
                script.check_settings_file(errors)
                script.check_profiles({"profiles": ["go", "dotnet"], "profile": "go"}, errors)
            finally:
                os.chdir(cwd)
        self.assertEqual(len([e for e in errors if "squad_settings.py: does not load (SyntaxError" in e]), 1, errors)

    def test_decision_check_runs_with_a_broken_settings_file(self):
        with tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", repo], check=True)
            tools = os.path.join(repo, ".squad", "tools")
            write(os.path.join(tools, "squad_settings.py"), "AREA_MAX_WORDS = (\n")
            with open(os.path.join(ROOT, "core", ".squad", "tools", "decision-check.py"), encoding="utf-8") as handle:
                write(os.path.join(tools, "decision-check.py"), handle.read())
            result = subprocess.run([sys.executable, os.path.join(tools, "decision-check.py")], cwd=repo,
                                    capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Checked 0 decision records: PASS", result.stdout)


@unittest.skipUnless(yaml, "PyYAML is needed to compare the two parsers")
class TestTargetWithoutYaml(unittest.TestCase):
    """A freshly applied target: config-check.py reports the same without PyYAML as with it."""

    def run_check(self, without_yaml):
        script = os.path.join(self.target, ".squad", "tools", "config-check.py")
        command = [sys.executable, "-c", WITHOUT_YAML, script] if without_yaml else [sys.executable, script]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual("without PyYAML" in result.stdout.splitlines()[-1], without_yaml)
        return result.returncode, [line for line in result.stdout.splitlines() if line and not line.startswith("Checked")]

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.target = self.dir.name
        subprocess.run(["git", "init", "-q", self.target], check=True)
        applied = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "apply-template.py"), "--target",
                                  self.target, "--profile", "go"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(applied.returncode, 0, applied.stderr)

    def tearDown(self):
        self.dir.cleanup()

    def test_both_parsers_report_the_same(self):
        project = os.path.join(self.target, ".squad", "project.md")
        write(project, read(project).replace("{{TODO: its interface}}", "its interface"))
        agent = os.path.join(self.target, ".claude", "agents", "squad-dev.md")
        write(agent, re.sub(r"^description: .*$", "description: Squad Dev: implements", read(agent), count=1, flags=re.M))
        with_yaml, without_yaml = self.run_check(False), self.run_check(True)
        self.assertEqual((without_yaml[0], [line.split(": ", 1)[0] for line in without_yaml[1]]),
                         (with_yaml[0], [line.split(": ", 1)[0] for line in with_yaml[1]]),
                         "the same findings at the same places; only the parser's wording differs")
        self.assertEqual(with_yaml[0], 1)
        self.assertTrue(any("squad-dev.md: " in line for line in with_yaml[1]))
        self.assertTrue(any("'its interface' is the seed's placeholder text" in line for line in with_yaml[1]))
        self.assertFalse([line for line in with_yaml[1] if "placeholder" not in line and "squad-dev.md" not in line])


class TestSquadGuards(unittest.TestCase):
    """.claude/settings.json runs each of the members' guards for the tools it checks."""

    def setUp(self):
        self.script = load_script()
        self.seed = json.loads(read(os.path.join(ROOT, "seed", ".claude", "settings.json")))

    def test_each_guard_is_required_for_its_tools(self):
        for script, tools in self.script.SQUAD_GUARDS:
            self.assertTrue(self.script.declares_hook(self.seed, script, tools), script)
        file_guard = self.script.FILE_GUARD
        only_write = {"hooks": {"PreToolUse": [{"matcher": "Write|MultiEdit", "hooks": [
            {"type": "command", "command": "python3 .claude/hooks/file-guard.py"}]}]}}
        self.assertFalse(self.script.declares_hook(only_write, file_guard, ("Write", "Edit")), "Edit is not in the matcher")
        no_command = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|MultiEdit|NotebookEdit", "hooks": [
            {"type": "command", "command": "python3 .claude/hooks/git-guard.py"}]}]}}
        self.assertFalse(self.script.declares_hook(no_command, file_guard, ("Write", "Edit")))
        for odd in ({"hooks": {"PreToolUse": [5, {"matcher": 7}, {"matcher": "Write", "hooks": 5}]}},
                    {"hooks": {"PreToolUse": 5}}, {"hooks": []}, {}):
            self.assertFalse(self.script.declares_hook(odd, file_guard, ("Write",)), odd)

    def test_settings_without_the_file_guard_are_reported(self):
        old = {"hooks": {"PreToolUse": [self.seed["hooks"]["PreToolUse"][0]]}}
        with tempfile.TemporaryDirectory() as repo:
            for script, _ in self.script.SQUAD_GUARDS:
                write(os.path.join(repo, script), "")
            write(os.path.join(repo, self.script.CLAUDE_SETTINGS), json.dumps(old))
            errors = []
            cwd = os.getcwd()
            os.chdir(repo)
            try:
                self.script.check_guards(errors)
            finally:
                os.chdir(cwd)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("file-guard.py", errors[0])


class TestProjectSize(unittest.TestCase):
    """.squad/project.md past PROJECT_MAX_WORDS is a warning, with the limit from squad_settings.py."""

    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        write(self.script.PROJECT_FILE, "# Project\n\n" + "word " * 1498)

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def warnings(self):
        found = []
        self.script.check_project_size(found)
        return found

    def test_the_default_limit_without_settings(self):
        self.assertEqual(self.warnings(), [], "1500 words: at the limit, not past it")
        write(self.script.PROJECT_FILE, "# Project\n\n" + "word " * 1600)
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("project.md: 1602 words (PROJECT_MAX_WORDS 1500)", warnings[0])
        self.assertIn("make every entry a pointer", warnings[0])

    def test_the_limit_from_the_settings(self):
        write(self.script.SETTINGS_FILE, "PROJECT_MAX_WORDS = 1000\n")
        self.assertIn("(PROJECT_MAX_WORDS 1000)", self.warnings()[0])
        write(self.script.SETTINGS_FILE, "PROJECT_MAX_WORDS = 3000\n")
        self.assertEqual(self.warnings(), [], "the file is loaded anew on every call")

    def test_a_broken_settings_file_leaves_the_default(self):
        write(self.script.PROJECT_FILE, "word " * 1501)
        write(self.script.SETTINGS_FILE, "PROJECT_MAX_WORDS = (\n")
        self.assertIn("(PROJECT_MAX_WORDS 1500)", self.warnings()[0])

    def test_no_project_file_no_warning(self):
        os.remove(self.script.PROJECT_FILE)
        self.assertEqual(self.warnings(), [])

    def test_decision_check_warnings_are_collected(self):
        script = os.path.join(".squad", "tools", "decision-check.py")
        write(script, "print('WARNING: docs/areas/a.md: 6000 words')\nprint('Checked 0 decision records: PASS')\n")
        errors, warnings = [], []
        self.script.check_decisions(errors, warnings)
        self.assertEqual((errors, warnings), ([], ["docs/areas/a.md: 6000 words"]))


if __name__ == "__main__":
    unittest.main()
