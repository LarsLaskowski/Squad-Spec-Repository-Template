#!/usr/bin/env python3
"""The .NET rule baseline: merge the analyzer configuration of every active `dotnet` consumer, the stricter setting
winning, into one EditorConfig file the template distributes (#337, #339).

For each `active` repository of `consumers.json` with the `dotnet` profile it reads, at `origin/main` of its clone (by
default the folder of the repository's name next to this one; `--target OWNER/NAME=PATH` names another):

- `.editorconfig`: every setting of a section that applies to all C# files (`[*]`, `[*.cs]`, `[*.{cs,vb}]`, …) except
  the generated `squad:sonar-rules` block, whose rules `sonar-rules.py` writes from the SonarQube Cloud profile; a
  section of a path (`[tests/**.cs]`, `[**/Migrations/*.cs]`) is listed as the project's exception, not merged, except
  a code-style or formatting option in it, which only makes sense for every file and is read as such, with a warning;
- every `*.ruleset` (the stricter severity of several, so Debug and Release give the Release one);
- `NoWarn` in project and build files, and assembly-wide `[assembly: SuppressMessage]` without a `Target`: the rule
  is off (`none`) in that repository.

Merging, per setting: a diagnostic's severity is the highest any repository gives it (`none` < `silent` < `suggestion`
< `warning` < `error`), except that a rule switched off (`none`, `silent`) where it is set and left at the analyzer's
default elsewhere is left out of the baseline: the default is the stricter. A code-style option takes the highest
severity, but its value (`file_scoped`, `crlf`, a naming style) must be the same everywhere; a difference is a conflict.

`tools/dotnet-baseline/decisions.json` holds the owner's decisions (#338): a value per setting, or `null` to leave it
out, each with its reason, and the sections of paths the baseline carries for every repository. A decision replaces
the merged value and resolves a conflict; its reason is written as a comment above the line.

`tools/dotnet-baseline/analyzer-ids.txt` lists the rule ids the analyzers in use know. `--record-ids` writes it: it
reads the versions of Reihitsu.Analyzer, SonarAnalyzer.CSharp and MSTest(.Analyzers) from every consumer's
`Directory.Packages.props` and its SDK from `global.json`, downloads those packages from nuget.org and reads the SDK's
analyzers from the installed SDK of that feature band (`dotnet --list-sdks`). A rule of a recorded family (`RH`, `S`,
`CA`, `IDE`, `MSTEST`) the analyzers do not know is never written; it is listed. `CS` and other families are not checked.

The result is `tools/dotnet-baseline/baseline.editorconfig`, the input of the rules block (#341). The report lists the
open conflicts, the rules switched off in one repository only, the rules dropped as unknown, the project exceptions
and, per repository, how many settings the baseline tightens or adds (`--verbose`: each of them).

Usage, from the template repository's root:
    python3 tools/dotnet-baseline.py [--check] [--verbose] [--target OWNER/NAME=PATH]
    python3 tools/dotnet-baseline.py --record-ids [--target OWNER/NAME=PATH]

Exit code 0 when the baseline was written or is current, 1 when a conflict is open or `--check` finds the file out of
date, 2 NOT CHECKED (a consumer's clone, its origin/main, an analyzer package or an SDK is missing), 4 wrong usage.
"""
import argparse
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ElementTree  # noqa: S405  # nosec B405
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools", "dotnet-baseline")
DECISIONS = os.path.join(DATA, "decisions.json")
IDS = os.path.join(DATA, "analyzer-ids.txt")
BASELINE = os.path.join(DATA, "baseline.editorconfig")
CURRENT, FAILED, NOT_CHECKED, USAGE = 0, 1, 2, 4
PROFILE = "dotnet"
REF = "origin/main"
NUGET = "https://api.nuget.org/v3-flatcontainer"
MSTEST_ANALYZERS = "MSTest.Analyzers"
# The analyzer package each of the consumers' packages brings (the MSTest metapackage brings MSTest.Analyzers).
ANALYZER_PACKAGES = {"reihitsu.analyzer": "Reihitsu.Analyzer", "sonaranalyzer.csharp": "SonarAnalyzer.CSharp",
                     "mstest.analyzers": MSTEST_ANALYZERS, "mstest": MSTEST_ANALYZERS}
PACKAGE_VERSION = re.compile(r"<PackageVersion\b[^>]*>", re.IGNORECASE)
VERSION = re.compile(r"\d+(?:\.\d+){1,3}(?:-[0-9A-Za-z.]+)?")

SEVERITIES = ("none", "silent", "suggestion", "warning", "error")
RANK = {name: rank for rank, name in enumerate(SEVERITIES)}
OFF = RANK["silent"]
# Severity words some consumers write that .NET does not know (ReSharper's `hint`) or spells otherwise.
ALIASES = {"hint": "silent", "info": "suggestion", "hidden": "silent"}
RULESET_ACTIONS = {"none": "none", "hidden": "silent", "info": "suggestion", "warning": "warning", "error": "error"}
SONAR_BEGIN = "# squad:sonar-rules begin"
SONAR_END = "# squad:sonar-rules end"
DIAGNOSTIC = re.compile(r"^dotnet_diagnostic\.(?P<id>[A-Z]+\d+)\.severity$", re.IGNORECASE)
RULE_ID = re.compile(r"^(?P<family>[A-Z]+)\d+$")
NO_WARN = re.compile(r"<NoWarn>(?P<ids>[^<]*)</NoWarn>", re.IGNORECASE)
SUPPRESSION = re.compile(r'\[assembly:\s*SuppressMessage\(\s*"[^"]*"\s*,\s*"(?P<id>[A-Za-z]+\d+)(?::[^"]*)?"(?P<rest>[^\]]*)\]')
OPTION_PREFIXES = ("csharp_", "dotnet_style_", "dotnet_naming_", "dotnet_sort_", "dotnet_separate_",
                   "dotnet_code_quality", "indent_", "tab_width", "end_of_line", "insert_final_newline")
# The analyzer assemblies whose rule ids --record-ids reads, by a part of the file name, and the family each owns.
FAMILIES = (("Reihitsu.Analyzer", "RH"), ("SonarAnalyzer.CSharp", "S"), (MSTEST_ANALYZERS, "MSTEST"),
            ("NetAnalyzers", "CA"), ("CodeStyle", "IDE"))
GROUPS = (("Files", ("charset", "end_of_line", "insert_final_newline", "trim_trailing_whitespace", "indent_", "tab_width")),
          ("Formatting", ("csharp_new_line", "csharp_indent", "csharp_space", "csharp_preserve")),
          ("Naming", ("dotnet_naming_",)),
          ("Code style", ("csharp_", "dotnet_")))
HEADER = ("# The .NET rule baseline: written by tools/dotnet-baseline.py from the active dotnet consumers of consumers.json\n"
          "# and tools/dotnet-baseline/decisions.json; never edited by hand. The stricter setting wins (#337, #338).\n")


class NotChecked(Exception):
    """A consumer could not be read; the message says why."""


class Usage(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(USAGE, f"{self.prog}: error: {message}\n")


# --- settings -----------------------------------------------------------------------------------------------------

def normalized_key(key):
    """`dotnet_diagnostic.<ID>.severity` with the id upper case, every other key lower case."""
    match = DIAGNOSTIC.match(key.strip())
    if match:
        return f"dotnet_diagnostic.{match['id'].upper()}.severity"
    return key.strip().lower()


def rule_id(key):
    """The rule id of a diagnostic key, or None."""
    match = DIAGNOSTIC.match(key)
    return match["id"] if match else None


def severity_of(word):
    """A severity word as .NET spells it, or None when it is none."""
    word = word.strip().lower()
    word = ALIASES.get(word, word)
    return word if word in RANK else None


def split_value(value):
    """(value, severity or None) of an option such as `true:warning`; a diagnostic's value is a severity alone."""
    head, colon, tail = value.rpartition(":")
    if colon and severity_of(tail):
        return head.strip(), severity_of(tail)
    return value.strip(), None


def expand(glob):
    """The alternatives of a section glob's `{a,b}` parts (one level, as the consumers use them)."""
    match = re.search(r"\{([^{}]*)\}", glob)
    if not match:
        return [glob]
    return [alternative for part in match[1].split(",")
            for alternative in expand(glob[:match.start()] + part + glob[match.end():])]


def section_kind(glob):
    """"all" for a section every C# file reads, "path" for one of some C# files, None for other files."""
    alternatives = expand(glob)
    if any(alternative in ("*", "*.cs") for alternative in alternatives):
        return "all"
    if any(alternative.endswith(".cs") for alternative in alternatives):
        return "path"
    return None


def is_severity(key):
    """A key whose value is a severity alone: a diagnostic's, or a naming rule's."""
    return bool(rule_id(key)) or key.endswith(".severity")


def is_option(key):
    return key.startswith(OPTION_PREFIXES)


class Config:
    """One repository's effective analyzer settings: `general` for every C# file, `paths` per section of a path."""

    def __init__(self, name):
        self.name = name
        self.general = {}
        self.paths = {}
        self.warnings = []

    def set_rule(self, key, severity, stronger=False):
        """Set a diagnostic; with `stronger`, only raise what is set (several rule sets)."""
        if stronger and key in self.general and RANK[self.general[key]] >= RANK[severity]:
            return
        self.general[key] = severity


def editorconfig_settings(text):
    """(section glob or None before the first section, key, value) of every setting outside the sonar-rules block."""
    glob, in_sonar = None, False
    for raw in text.splitlines():
        line = raw.replace("\ufeff", "").strip()
        in_sonar = (in_sonar or line.startswith(SONAR_BEGIN)) and not line.startswith(SONAR_END)
        section = re.match(r"^\[(.*)\]$", line)
        if section:
            glob = section[1]
        elif not in_sonar and line and line[0] not in "#;" and "=" in line:
            key, _, value = line.partition("=")
            yield glob, normalized_key(key), value.strip()


def parse_editorconfig(config, text):
    """Read `.editorconfig` into the config; the sonar-rules block is skipped."""
    moved = 0
    for glob, key, value in editorconfig_settings(text):
        kind = "all" if glob is None else section_kind(glob)
        if kind is None or key == "root":
            continue
        if kind == "path" and not is_option(key):
            config.paths.setdefault(glob, {})[key] = value
            continue
        moved += kind == "path"
        config.general[key] = (severity_of(value) or value) if is_severity(key) else value
    if moved:
        config.warnings.append(f"{moved} code-style or formatting option(s) of a section of a path read as settings "
                               "for every C# file (a section header that cuts them off from [*.cs]?)")


def parse_ruleset(config, text):
    """Read a rule set's actions into the config, keeping the stricter of several."""
    # The rule sets of the consumers' own repositories, read from their clones; the tool stays stdlib-only, so no defusedxml.
    for rule in ElementTree.fromstring(text.lstrip("\ufeff")).iter("Rule"):  # noqa: S314  # nosec B314
        action = RULESET_ACTIONS.get(rule.get("Action", "").lower())
        if action and rule.get("Id"):
            config.set_rule(f"dotnet_diagnostic.{rule.get('Id').upper()}.severity", action, stronger=True)


def switched_off(text):
    """The rule ids a project or build file's `NoWarn` lists."""
    ids = []
    for match in NO_WARN.finditer(text):
        ids += [part.upper() for part in re.split(r"[;,\s]+", match["ids"]) if RULE_ID.match(part.upper())]
    return ids


def suppressed(text):
    """The rule ids a file suppresses for a whole assembly (`SuppressMessage` without a `Target`)."""
    return [match["id"].upper() for match in SUPPRESSION.finditer(text) if "Target" not in match["rest"]]


# --- consumers ----------------------------------------------------------------------------------------------------

def git(clone, *args):
    """(exit code, output) of a git command run in a clone; the clone is the working directory, never an argument."""
    done = subprocess.run(["git", *args], cwd=clone, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout


def clone_root(name, path):
    """The real path of a consumer's clone, which must be the root of a git repository."""
    root = os.path.realpath(path)
    if not os.path.exists(os.path.join(root, ".git")):
        raise NotChecked(f"{name}: {root} is not the root of a git repository")
    return root


def read_consumer(name, clone, ref=REF):
    """The Config of one consumer at `ref` of its clone."""
    clone = clone_root(name, clone)
    code, listing = git(clone, "ls-tree", "-r", "--name-only", ref)
    if code != 0:
        raise NotChecked(f"{name}: no {ref} in {clone}")
    files = listing.splitlines()

    def show(path):
        return git(clone, "show", f"{ref}:{path}")[1]

    config = Config(name)
    for path in (path for path in files if path.endswith(".ruleset")):
        parse_ruleset(config, show(path))
    if ".editorconfig" in files:  # after the rule sets: a build gives .editorconfig precedence over them
        parse_editorconfig(config, show(".editorconfig"))
    for path in (path for path in files if path.endswith((".csproj", ".props", ".targets"))):
        for rule in switched_off(show(path)):
            config.set_rule(f"dotnet_diagnostic.{rule}.severity", "none")
    _, found = git(clone, "grep", "-l", "assembly: SuppressMessage", ref, "--", "*.cs")
    for path in (line.split(":", 1)[1] for line in found.splitlines() if ":" in line):
        for rule in suppressed(show(path)):
            config.set_rule(f"dotnet_diagnostic.{rule}.severity", "none")
    return config


def dotnet_consumers(path=None):
    """The repositories (`owner/name`) of the active consumers with the dotnet profile."""
    with open(path or os.path.join(ROOT, "consumers.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    return [entry["repository"] for entry in data.get("consumers", [])
            if entry.get("status") == "active" and PROFILE in entry.get("profiles", [])]


def clone_paths(consumers, targets):
    """{repository: clone path}, as `rollout-check.py` finds them."""
    spec = importlib.util.spec_from_file_location("rollout_check", os.path.join(ROOT, "tools", "rollout-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.clone_paths(consumers, targets)


# --- merging ------------------------------------------------------------------------------------------------------

class Merge:
    """The merged settings (`general`, in key order), the conflicts and the notes of a merge."""

    def __init__(self):
        self.general = {}
        self.conflicts = {}
        self.off_once = {}
        self.dropped = {}
        self.sections = {}
        self.reasons = {}


def merge_rule(merged, key, values, total):
    """A diagnostic: the highest severity; switched off where set and default elsewhere stays at the default."""
    highest = max(values.values(), key=lambda severity: RANK.get(severity, -1))
    if highest not in RANK:
        merged.conflicts[key] = values
    elif RANK[highest] <= OFF and len(values) < total:
        merged.off_once[key] = values
    else:
        merged.general[key] = highest


def merge_severity(merged, key, values):
    """A naming rule's severity: the highest."""
    highest = max(values.values(), key=lambda severity: RANK.get(severity, -1))
    if highest in RANK:
        merged.general[key] = highest
    else:
        merged.conflicts[key] = values


def merge_option(merged, key, values):
    """A code-style option: one value everywhere, the highest severity any repository gives it."""
    parts = {name: split_value(value) for name, value in values.items()}
    if len({value.lower() for value, _ in parts.values()}) > 1:
        merged.conflicts[key] = values
        return
    value = next(iter(parts.values()))[0]
    severities = [severity for _, severity in parts.values() if severity]
    merged.general[key] = f"{value}:{max(severities, key=RANK.get)}" if severities else value


def merge(configs):
    """Merge the consumers' general settings, the stricter winning."""
    merged = Merge()
    for key in sorted({key for config in configs for key in config.general}):
        values = {config.name: config.general[key] for config in configs if key in config.general}
        if rule_id(key):
            merge_rule(merged, key, values, len(configs))
        elif is_severity(key):
            merge_severity(merged, key, values)
        else:
            merge_option(merged, key, values)
    return merged


def load_decisions(path=DECISIONS):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def apply_decisions(merged, decisions):
    """Replace merged values by the decided ones (a `null` value leaves the setting out) and add decided sections."""
    for key, decision in decisions.get("settings", {}).items():
        key = normalized_key(key)
        merged.conflicts.pop(key, None)
        merged.off_once.pop(key, None)
        merged.general.pop(key, None)
        if decision.get("value") is not None:
            merged.general[key] = decision["value"]
            merged.reasons[key] = decision["reason"]
    for glob, settings in decisions.get("sections", {}).items():
        merged.sections[glob] = {normalized_key(key): decision["value"] for key, decision in settings.items()}
        merged.reasons.update({(glob, normalized_key(key)): decision["reason"] for key, decision in settings.items()})


def drop_unknown(merged, known):
    """Leave out every rule of a recorded family the analyzers do not know."""
    families = {RULE_ID.match(rule)["family"] for rule in known}
    for key in [key for key in merged.general if rule_id(key)]:
        rule = rule_id(key)
        if RULE_ID.match(rule) and RULE_ID.match(rule)["family"] in families and rule not in known:
            merged.dropped[key] = merged.general.pop(key)


# --- analyzer ids -------------------------------------------------------------------------------------------------

def ids_in(binary, family):
    """The rule ids of a family in an assembly: as UTF-16 string literals and as plain text."""
    letters = family.encode()
    wide = b"".join(re.escape(bytes([char])) + b"\x00" for char in letters)
    found = {match.decode("utf-16-le") for match in
             re.findall(rb"(?<![A-Za-z0-9]\x00)(" + wide + rb"(?:[0-9]\x00){3,5})(?![0-9]\x00)", binary)}
    found |= {match.decode() for match in re.findall(rb"(?<![A-Za-z0-9])(" + re.escape(letters) + rb"[0-9]{3,5})(?![0-9])",
                                                     binary)}
    return found


def family_of(name):
    return next((family for part, family in FAMILIES if part.lower() in os.path.basename(name).lower()), None)


def is_analyzer(name):
    """An analyzer assembly of a package: under `analyzers/`, C#, not a resource assembly."""
    return (name.startswith("analyzers/") and name.endswith(".dll") and not name.endswith(".resources.dll")
            and "/vb/" not in name)


def package_assemblies(data):
    """(name, bytes) of the analyzer assemblies in a package's bytes."""
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        for name in package.namelist():
            if is_analyzer(name):
                yield name, package.read(name)


def folder_assemblies(folder):
    """(path, bytes) of the assemblies in an SDK folder, resource assemblies left out."""
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        path = os.path.join(folder, name)
        if name.endswith(".dll") and not name.endswith(".resources.dll") and os.path.isfile(path):
            with open(path, "rb") as handle:
                yield path, handle.read()


def source_label(path):
    """An assembly's path without the machine's part: from the SDK folder on (`sdk/11.0.100/…`), else its name."""
    parts = path.replace(os.sep, "/").split("/")
    return "/".join(parts[parts.index("sdk"):]) if "sdk" in parts else os.path.basename(path)


def attribute(tag, name):
    found = re.search(name + r'="([^"]*)"', tag)
    return found.group(1) if found else None


def analyzer_versions(text):
    """{(analyzer package, version)} a `Directory.Packages.props` brings."""
    found = set()
    for tag in PACKAGE_VERSION.findall(text):
        package = ANALYZER_PACKAGES.get((attribute(tag, "Include") or "").lower())
        version = attribute(tag, "Version") or ""
        if package and VERSION.fullmatch(version):
            found.add((package, version))
    return found


def sdk_version(text):
    """The SDK version of a `global.json`, or None."""
    try:
        version = json.loads(text).get("sdk", {}).get("version", "")
    except (ValueError, AttributeError):
        return None
    return version if VERSION.fullmatch(version) else None


def analyzers_in_use(clones):
    """({(package, version)}, {SDK version}) of the consumers at origin/main."""
    packages, sdks = set(), set()
    for name, clone in clones.items():
        root = clone_root(name, clone)
        packages |= analyzer_versions(git(root, "show", f"{REF}:Directory.Packages.props")[1])
        sdk = sdk_version(git(root, "show", f"{REF}:global.json")[1])
        sdks |= {sdk} if sdk else set()
    return packages, sdks


def fetch_package(package, version):
    """A package's bytes from nuget.org; the id comes from ANALYZER_PACKAGES and the version matched VERSION."""
    lower = package.lower()
    url = f"{NUGET}/{lower}/{version}/{lower}.{version}.nupkg"
    try:
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310  # nosec B310
            return response.read()
    except OSError as error:
        raise NotChecked(f"{package} {version} could not be downloaded: {error}") from error


def installed_sdks():
    """{SDK version: its folder} of `dotnet --list-sdks`."""
    try:
        listing = subprocess.run(["dotnet", "--list-sdks"], capture_output=True, text=True, check=False).stdout
    except OSError:
        listing = ""
    sdks = {}
    for line in listing.splitlines():  # "11.0.100 [/usr/lib/dotnet/sdk]"
        version, _, base = line.strip().partition(" [")
        if VERSION.fullmatch(version) and base.endswith("]"):
            sdks[version] = os.path.join(base[:-1], version)
    return sdks


def sdk_folder(wanted, installed):
    """The installed SDK of the wanted one's feature band (`11.0.1xx`), as `rollForward: latestFeature` picks it."""
    band = wanted.split(".")[:2] + [wanted.split(".")[2][:1]]
    matching = [version for version in installed if version.split(".")[:2] + [version.split(".")[2][:1]] == band]
    if not matching:
        raise NotChecked(f"SDK {wanted} (or another of its feature band) is not installed")
    best = max(matching, key=lambda version: [int(part) for part in re.findall(r"\d+", version)])
    return installed[best]


def sdk_assemblies(folder):
    analyzers = os.path.join(folder, "Sdks", "Microsoft.NET.Sdk")
    yield from folder_assemblies(os.path.join(analyzers, "analyzers"))
    yield from folder_assemblies(os.path.join(analyzers, "codestyle", "cs"))


def record_ids(clones, out=IDS, fetch=fetch_package, sdks=installed_sdks):
    """Write the rule ids the analyzers the consumers use know, with the sources, to `out`."""
    packages, wanted = analyzers_in_use(clones)
    found = [(f"{package} {version}: {name}", binary) for package, version in sorted(packages)
             for name, binary in package_assemblies(fetch(package, version))]
    installed = sdks()
    found += [(source_label(path), binary) for sdk in sorted(wanted) for path, binary in
              sdk_assemblies(sdk_folder(sdk, installed))]
    known, sources = set(), []
    for label, binary in found:
        family = family_of(label)
        if family:
            known |= ids_in(binary, family)
            sources.append(label)
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Rule ids the analyzers in use know; written by tools/dotnet-baseline.py --record-ids from:\n")
        handle.writelines(f"#   {source}\n" for source in sources)
        handle.writelines(f"{rule}\n" for rule in sorted(known))
    print(f"{os.path.relpath(out, ROOT)}: {len(known)} rule ids from {len(sources)} assemblies")


def load_ids(path=IDS):
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip() and not line.startswith("#")}


# --- output -------------------------------------------------------------------------------------------------------

def group_of(key):
    rule = rule_id(key)
    if rule:
        return f"Diagnostics: {RULE_ID.match(rule)['family'] if RULE_ID.match(rule) else rule}"
    return next((title for title, prefixes in GROUPS if key.startswith(prefixes)), "Other")


def sort_key(key):
    rule = rule_id(key)
    match = RULE_ID.match(rule) if rule else None
    return (match["family"], int(rule[len(match["family"]):])) if match else (key, 0)


def section_lines(settings, reasons, scope=None):
    """The lines of one section, grouped, each decided line after a comment with its reason."""
    lines, current = [], None
    order = [title for title, _ in GROUPS] + ["Other"]
    for key in sorted(settings, key=lambda key: (group_of(key).startswith("Diagnostics"),
                                                 order.index(group_of(key)) if group_of(key) in order else 0,
                                                 group_of(key), sort_key(key))):
        if group_of(key) != current:
            current = group_of(key)
            lines += ["", f"# {current}"]
        reason = reasons.get((scope, key) if scope else key)
        if reason:
            lines.append(f"# {reason}")
        lines.append(f"{key} = {settings[key]}")
    return lines


def render(merged):
    lines = [HEADER.rstrip("\n"), "", "[*.cs]"] + section_lines(merged.general, merged.reasons)
    for glob in sorted(merged.sections):
        lines += ["", f"[{glob}]"] + section_lines(merged.sections[glob], merged.reasons, glob)
    return "\n".join(lines) + "\n"


def changes(config, merged):
    """(tightened, added) settings of one repository: a value the baseline changes, a setting it adds."""
    tightened, added = [], []
    for key, value in merged.general.items():
        own = config.general.get(key)
        if own is None:
            added.append(f"{key} = {value}")
        elif own.lower() != value.lower():
            tightened.append(f"{key}: {own} -> {value}")
    return tightened, added


def print_values(title, entries):
    if entries:
        print(f"\n{title}:")
        for key, values in entries.items():
            print(f"  {key}: " + ", ".join(f"{name.split('/')[-1]}={value}" for name, value in values.items()))


def report(configs, merged, verbose):
    for config in configs:
        for warning in config.warnings:
            print(f"WARNING {config.name}: {warning}")
    print_values("Open conflicts (decide in tools/dotnet-baseline/decisions.json)", merged.conflicts)
    print_values("Switched off in one repository, the analyzer's default elsewhere (left at the default)",
                 merged.off_once)
    if merged.dropped:
        print("\nLeft out, the analyzers in use do not know the rule (tools/dotnet-baseline/analyzer-ids.txt):")
        print("  " + ", ".join(rule_id(key) for key in merged.dropped))
    for config in configs:
        for glob, settings in config.paths.items():
            print(f"\nProject exception {config.name.split('/')[-1]} [{glob}]: "
                  + ", ".join(f"{key} = {value}" for key, value in settings.items()))
    print()
    for config in configs:
        tightened, added = changes(config, merged)
        print(f"{config.name}: {len(tightened)} setting(s) changed, {len(added)} added")
        for line in (tightened + added) if verbose else []:
            print(f"  {line}")


def write_or_check(text, check, path=BASELINE):
    current = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8", newline="") as handle:
            current = handle.read()
    if check:
        print(f"{os.path.relpath(path, ROOT)}: {'current' if current == text else 'missing or out of date'}")
        return current == text
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"{os.path.relpath(path, ROOT)}: written")
    return True


def main(argv=None):
    parser = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only report whether the baseline file is current")
    parser.add_argument("--verbose", action="store_true", help="list every setting the baseline changes or adds")
    parser.add_argument("--target", action="append", default=[], metavar="OWNER/NAME=PATH",
                        help="the clone of a consumer, when it is not the folder of its name next to this repository")
    parser.add_argument("--record-ids", action="store_true",
                        help="write analyzer-ids.txt from the analyzer packages and SDKs the consumers use")
    args = parser.parse_args(argv)
    clones = clone_paths(dotnet_consumers(), args.target)
    try:
        if args.record_ids:
            record_ids(clones)
            return CURRENT
        configs = [read_consumer(name, clone) for name, clone in clones.items()]
    except NotChecked as error:
        print(f"NOT CHECKED: {error}")
        return NOT_CHECKED
    merged = merge(configs)
    apply_decisions(merged, load_decisions())
    drop_unknown(merged, load_ids())
    report(configs, merged, args.verbose)
    current = write_or_check(render(merged), args.check)
    return FAILED if merged.conflicts or not current else CURRENT


if __name__ == "__main__":
    sys.exit(main())
