"""Unit tests for core/.squad/tools/analyzer_common.py (lint pass and Sonar shell rules): run
`python3 -m unittest discover tools`."""
import importlib.util
import os
import stat
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", ".squad", "tools")


def load_script():
    sys.modules["squad_settings"] = types.SimpleNamespace(BASE_REF="main")
    sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("analyzer_common", os.path.join(TOOLS, "analyzer_common.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT = """#!/bin/bash
set -euo pipefail

fail() {
  echo "::error::$1" >&2
  exit 1
}

arg_default() {
  sed -nE "s/^ARG ${1}=(.*)$/\\1/p" "$f"
}

absolute() {
  local path=$1
  printf '%s' "$path"
}

run_tool() {
  local input=$1 target=$2
  cat "$input" > "$target"
}

compose() { (cd "$dir" && docker compose "$@"); }

inspect() {
  docker inspect --format "$1" "$(container_id)"   # direct use: S7679
}

check() {
  if [[ -z "$2" ]]; then  # direct use: S7679
    return 1
  fi
  echo $3
}

if [ -n "$1" ]; then  # top level: S7688 but not S7679
  echo "$1"
fi
[[ -d "$dir" ]] || fail "missing"
test -f "$1" && grep -q "[ " "$1"
# a comment mentioning [ -f x ] and $1 inside f() { }
"""


class TestSonarShellRules(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_findings_match_the_sonar_rules(self):
        findings = self.script.sonar_shell_findings("x.sh", SCRIPT)
        lines = SCRIPT.splitlines()
        want = {
            (lines.index('  docker inspect --format "$1" "$(container_id)"   # direct use: S7679') + 1, "S7679"),
            (lines.index('  if [[ -z "$2" ]]; then  # direct use: S7679') + 1, "S7679"),
            (lines.index("  echo $3") + 1, "S7679"),
            (lines.index('if [ -n "$1" ]; then  # top level: S7688 but not S7679') + 1, "S7688"),
        }
        got = {(int(f.split("(")[1].split(")")[0]), "S7679" if "S7679" in f else "S7688") for f in findings}
        self.assertEqual(got, want, "\n".join(findings))

    def test_positional_word_boundaries(self):
        cases = {'  docker inspect --format "$1" "$(cid)"': 1, "  docker inspect --format $1": 1,
                 '  local a="$1" b=$2': 0, '  echo "::error::$1" >&2': 0, '  sed "s/${1}=//"': 0, "  x=${1}": 0,
                 '  run "${1}"': 1, '  run "$@" "$*"': 0, '  [[ -z "$2" ]] || return': 1, '  echo "$10"': 0,
                 "  echo ${10}": 1, "  echo $1;": 1, "  echo $1": 1, '  if [ -f "$x" ]; then': 0, "  f $1 $2": 2}
        for line, want in cases.items():
            self.assertEqual(len(list(self.script.positional_words(line))), want, repr(line))

    def test_single_bracket_detection(self):
        cases = {"if [ -f x ]; then": True, "[[ -f x ]]": False, '! [ -z "$x" ]': True, 'grep "[ " f': False,
                 "  [ -n x ] || exit": True, "a && [ -n x ]": True, "echo x[ ]": False}
        for line, want in cases.items():
            self.assertEqual(self.script.SINGLE_BRACKET.search(line) is not None, want, repr(line))

    def test_clean_script_has_no_finding(self):
        text = 'f() {\n  local a="$1" b=$2\n  echo "${a}:$b" "$@"\n}\nif [[ -f "$1" ]]; then echo ok; fi\n'
        self.assertEqual(self.script.sonar_shell_findings("x.sh", text), [])


class TestLinters(unittest.TestCase):
    def setUp(self):
        self.script = load_script()
        self.dir = tempfile.TemporaryDirectory()
        self.previous_path = os.environ["PATH"]
        os.environ["PATH"] = self.dir.name  # no real linter is visible to the tests

    def tearDown(self):
        os.environ["PATH"] = self.previous_path
        self.dir.cleanup()

    def fake_tool(self, name, exit_code):
        path = os.path.join(self.dir.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"#!/bin/sh\necho ran {name} \"$@\"\nexit {exit_code}\n")
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)

    def test_file_classes(self):
        self.assertTrue(self.script.is_shell("deploy/run.sh"))
        self.assertTrue(self.script.is_workflow(".github/workflows/ci.yml"))
        self.assertFalse(self.script.is_workflow(".github/dependabot.yml"))
        for path in ("Dockerfile", "deploy/backend/Dockerfile", "build/agent.Dockerfile", "Dockerfile.debug"):
            self.assertTrue(self.script.is_dockerfile(path), path)
        self.assertFalse(self.script.is_dockerfile("docs/Dockerfile.md"))

    def test_missing_linter_is_reported_not_failed(self):
        self.assertTrue(self.script.run_linter("shellcheck", "changed shell scripts", ["shellcheck", "--"], ["a.sh"]))
        self.assertTrue(self.script.run_linter("shellcheck", "changed shell scripts", ["shellcheck", "--"], []))

    def test_linter_result_decides(self):
        self.fake_tool("actionlint", 0)
        self.assertTrue(self.script.run_linter("actionlint", "changed workflows", ["actionlint"], ["ci.yml"]))
        self.fake_tool("hadolint", 1)
        self.assertFalse(self.script.run_linter("hadolint", "changed Dockerfiles", ["hadolint"], ["Dockerfile"]))


if __name__ == "__main__":
    unittest.main()
