#!/usr/bin/env python3
"""SonarSource's open Python analyzer, run locally before a release (`AGENTS.md`, *Releases*).

SonarQube Cloud's analysis of a pull request can miss what its analysis of `main` reports after the merge, and a
release carries every such finding into the code analysis of each target. This tool runs the checks of the open
`sonar-python-plugin` with the rules the consumers' quality profile activates over every Python file a target
receives (`core/`, `profiles/`, `multi/`, `seed/`) and over the template's own `tools/`, so a finding is fixed before
`python3 tools/release.py prepare`.

    python3 tools/sonar-local.py                  # every file; fetches the profile's rules from SonarQube Cloud
    python3 tools/sonar-local.py PATH …           # only these files or directories
    python3 tools/sonar-local.py --rules FILE     # the rule keys from a file (one per line), no SonarQube request

It needs Java 17 or later (`java` on PATH). The plugin and its two dependencies are downloaded once from Maven Central
into the cache directory (`--cache`, default `~/.cache/squad-sonar-local`) and checked against pinned SHA-256 sums;
Maven Central rate-limits, so a download is retried with backoff. The rules are the `python:` rules active in the
quality profile `PROFILE` of the organization `ORGANIZATION`; the closed rule repositories (`pythonsecurity`,
`pythonbugs`, …) cannot run locally. A private profile needs a credential: a network secret of the cloud environment
for sonarcloud.io, or `SONAR_TOKEN`. `tools/SonarLocal.java` loads the plugin's check classes and runs them; a check
scoped to main code skips the test files (`test_*.py`), as SonarQube Cloud does.

Exit code 0 when no file but a test file has an issue, 1 on an issue in a non-test file or a file that does not parse,
2 when the analysis cannot run (no Java, a failed download or request, a harness error).
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "tools", "SonarLocal.java")
SCANNED_DIRS = ["core", "profiles", "multi", "seed", "tools"]
MAVEN = "https://repo.maven.apache.org/maven2"
PLUGIN = ("org.sonarsource.python", "sonar-python-plugin", "5.32.0.37250",
          "f659212a6846a0044a88d98f2ac6a744ad151cddee8be953b8cdd4fb74a21641")
ARTIFACTS = [
    PLUGIN,
    ("org.sonarsource.api.plugin", "sonar-plugin-api", "14.2.0.5584",
     "a4a54e1781759f647ffbfbbb0cebaa833243ff36e7da244c181825469cd5d645"),
    ("org.slf4j", "slf4j-api", "2.0.17", "7b751d952061954d5abfed7181c1f645d336091b679891591d63329c622eb832"),
]
SONAR_HOST = "https://sonarcloud.io"
ORGANIZATION = "networlddev"
PROFILE = "AZ6SwXCXNtdzQiT7rg_6"  # "Sonar way comprehensive", the consumers' Python quality profile
REPOSITORY = "python"
PAGE_SIZE = 500
RETRIES = 5
BACKOFF_SECONDS = 2
RETRIED_STATUS = (429, 500, 502, 503, 504)
TIMEOUT = 120
HARNESS_TIMEOUT = 1800


class CannotRun(Exception):
    """The analysis cannot run; the message says why."""


def default_cache():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "squad-sonar-local")


def maven_url(group, artifact, version):
    return f"{MAVEN}/{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.jar"


def fetch(url, headers=None, sleep=time.sleep):
    """The body of an https:// GET, retried with doubling backoff on a rate limit, a server error or a broken
    connection."""
    if not url.startswith("https://"):
        raise CannotRun(f"refusing a non-https URL: {url}")
    # Only an https:// URL reaches urllib (checked above), so no file:// or custom scheme can be opened.
    request = urllib.request.Request(url)  # noqa: S310  # nosec B310
    for name, value in (headers or {}).items():  # never forwarded to another host on a redirect
        request.add_unredirected_header(name, value)
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310  # nosec B310
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in RETRIED_STATUS or attempt == RETRIES - 1:
                raise CannotRun(f"HTTP {error.code} for GET {url}") from error
        except OSError as error:  # URLError and timeouts included
            if attempt == RETRIES - 1:
                raise CannotRun(f"GET {url} failed: {error}") from error
        sleep(BACKOFF_SECONDS * 2 ** attempt)
    raise CannotRun(f"GET {url} failed")  # not reached: the last attempt returns or raises


def download_jars(cache, sleep=time.sleep):
    """The paths of the plugin and its dependencies in the cache, downloaded where missing or not matching their
    pinned SHA-256 sum."""
    os.makedirs(cache, exist_ok=True)
    paths = []
    for group, artifact, version, sha256 in ARTIFACTS:
        path = os.path.join(cache, f"{artifact}-{version}.jar")
        if not os.path.isfile(path) or file_sha256(path) != sha256:
            url = maven_url(group, artifact, version)
            data = fetch(url, sleep=sleep)
            if hashlib.sha256(data).hexdigest() != sha256:
                raise CannotRun(f"{url} does not match its pinned SHA-256 sum")
            with open(path + ".part", "wb") as handle:
                handle.write(data)
            os.replace(path + ".part", path)
        paths.append(path)
    return paths


def file_sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def auth_headers(token):
    """A Basic header for `SONAR_TOKEN`; without one the agent proxy may attach the credential itself."""
    return {"Authorization": "Basic " + base64.b64encode(f"{token}:".encode()).decode()} if token else {}


def active_rules(token=None, sleep=time.sleep):
    """The keys (`S1192`, …) of the `python:` rules active in the quality profile, every page."""
    keys, page = [], 1
    while True:
        params = {"organization": ORGANIZATION, "qprofile": PROFILE, "activation": "true", "ps": PAGE_SIZE, "p": page}
        url = f"{SONAR_HOST}/api/rules/search?{urllib.parse.urlencode(params)}"
        data = json.loads(fetch(url, auth_headers(token), sleep))
        rules = data.get("rules", [])
        keys += [rule["key"].split(":", 1)[1] for rule in rules if rule.get("key", "").startswith(REPOSITORY + ":")]
        if not rules or page * PAGE_SIZE >= data.get("total", 0):
            return sorted(set(keys))
        page += 1


def read_rules(path):
    """The rule keys of a file, one per line; a `python:` prefix is dropped."""
    with open(path, encoding="utf-8") as handle:
        return sorted({line.strip().removeprefix(REPOSITORY + ":") for line in handle if line.strip()})


def python_files(paths=None, root=ROOT):
    """The Python files to analyse, relative to `root`: the given files and directories, else `SCANNED_DIRS`."""
    found = set()
    for entry in paths or SCANNED_DIRS:
        full = os.path.join(root, entry)
        if os.path.isfile(full):
            found.add(os.path.relpath(full, root))
        for top, _, names in os.walk(full):
            found.update(os.path.relpath(os.path.join(top, name), root) for name in names if name.endswith(".py"))
    return sorted(found)


def is_test(path):
    return os.path.basename(path).startswith("test_")


def run_harness(jars, rules, files, root=ROOT):
    """The harness's stdout; `CannotRun` when Java is missing or the harness fails."""
    java = shutil.which("java")
    if not java:
        raise CannotRun("java is not on PATH (Java 17 or later is needed)")
    with tempfile.TemporaryDirectory() as work:
        rules_path, files_path = os.path.join(work, "rules.txt"), os.path.join(work, "files.txt")
        with open(rules_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(rules) + "\n")
        with open(files_path, "w", encoding="utf-8") as handle:
            handle.write("".join(f"{'test' if is_test(path) else 'main'}\t{path}\n" for path in files))
        command = [java, "-cp", os.pathsep.join(jars), HARNESS, jars[0], rules_path, files_path]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=HARNESS_TIMEOUT, check=False)
    if result.returncode != 0:
        raise CannotRun(f"the harness failed (exit {result.returncode}): {result.stderr.strip()[-2000:]}")
    return result.stdout


def parse_output(stdout):
    """(rules loaded, missing rule keys, issues as (path, line, rule, message)); a parse error is an issue of the
    rule `parse`."""
    loaded, missing, issues = 0, [], []
    for line in stdout.splitlines():
        kind, _, rest = line.partition("\t")
        fields = rest.split("\t")
        if kind == "RULES":
            loaded = int(fields[0])
        elif kind == "MISSING":
            missing.append(fields[0])
        elif kind == "ISSUE" and len(fields) >= 4:
            issues.append((fields[0], int(fields[1] or 0), f"{REPOSITORY}:{fields[2]}", fields[3]))
        elif kind == "PARSE" and len(fields) >= 3:
            issues.append((fields[0], int(fields[1] or 0), "parse", fields[2]))
    return loaded, missing, sorted(issues)


def report(loaded, missing, issues, files):
    """Print the findings and return the exit code: 1 when a non-test file has one."""
    if missing:
        print(f"NOTE: {len(missing)} active rule(s) have no check in sonar-python-plugin {PLUGIN[2]}: "
              f"{', '.join(missing)}")
    failing = [issue for issue in issues if not is_test(issue[0])]
    for path, line, rule, message in issues:
        print(f"{path}:{line}: {rule} {message}{'  (test file, not failing)' if is_test(path) else ''}")
    print(f"\n{loaded} rules over {len(files)} files: {len(failing)} issue(s) in non-test files, "
          f"{len(issues) - len(failing)} in test files: {'FAIL' if failing else 'PASS'}")
    return 1 if failing else 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Run SonarSource's open Python analyzer over the template's tools.")
    parser.add_argument("paths", nargs="*", help="files or directories relative to the repository root "
                                                 f"(default: {', '.join(SCANNED_DIRS)})")
    parser.add_argument("--rules", help="a file of rule keys, one per line, instead of the quality profile's")
    parser.add_argument("--cache", default=default_cache(), help="where the downloaded jars are kept")
    return parser.parse_args(argv)


def main(argv=None, sleep=time.sleep):
    args = parse_args(argv)
    files = python_files(args.paths)
    if not files:
        print("No Python file to analyse.")
        return 2
    try:
        rules = read_rules(args.rules) if args.rules else active_rules(os.environ.get("SONAR_TOKEN", ""), sleep)
        if not rules:
            raise CannotRun(f"no active '{REPOSITORY}:' rule in the quality profile {PROFILE}")
        jars = download_jars(args.cache, sleep)
        loaded, missing, issues = parse_output(run_harness(jars, rules, files))
    except (CannotRun, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"NOT CHECKED: {error}")
        return 2
    return report(loaded, missing, issues, files)


if __name__ == "__main__":
    sys.exit(main())
