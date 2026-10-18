#!/usr/bin/env python3
"""Plan gate: the structure of a squad work folder checked by a script instead of remembered by a reviewer.

Run by the orchestrator after every Lead launch that writes or revises the work folder (steps 2 and 3), before
any other member reads it; a finding goes back to the Lead (mode `revise`), without a challenge round.

Checks, in the work folder `specs/<folder>/`:

- **Feature** (`spec.md` exists): every section of the spec template is filled — *Problem*, *Scenarios*,
  *Errors and edge cases*, *Non-functional requirements*, *Acceptance criteria*, *Out of scope*, *Open
  questions*, *Area documents* ("none" counts as filled, template text does not); scenarios `S<n>` and edge cases
  `E<n>` are numbered and each one is named by an acceptance criterion or listed under *Out of scope*; every
  open question is answered (`Answered:`) or the section says "none"; `plan.md` defines no acceptance criterion
  of its own; every criterion of the spec has a row in the plan's *Tests per criterion* and in `tasks.md`, and
  neither names a criterion the spec does not define.
- **Bug fix** (no `spec.md`): `plan.md` defines its acceptance criteria, and each has a row in *Tests per
  criterion*.
- **Both:** the *Tier* line names a tier; every row of *Verified facts* has evidence and a status
  (`confirmed`, `refuted`, or `unverified` with the measurement that settles it, starting with `to verify:`); no
  template placeholder is left (`<title>`, `AC1: ...`, a row of `...`). A plan longer than `PLAN_MAX_WORDS`
  (`squad_settings.py`, default 4000) is reported as a warning: a long plan costs every member that reads it.

A criterion without a test, in a plan whose *Verification without tests* section covers it, counts as covered.

With `--spec` only `spec.md` is checked: after the Lead's mode `spec`, before the spec challenge.

Usage, from the repository root:
    python3 .squad/tools/plan-check.py <work folder name, e.g. feature-12-export or issue-34> [--spec]

Exit code 0 when the work folder passes, 1 otherwise.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squad_settings as settings  # noqa: E402  (per-repository settings next to this script)

PLAN_MAX_WORDS = getattr(settings, "PLAN_MAX_WORDS", 4000)
TIERS = ("trivial", "standard", "security")
STATUSES = ("confirmed", "refuted", "unverified")
SPEC_SECTIONS = ["Problem", "Scenarios", "Errors and edge cases", "Non-functional requirements",
                 "Acceptance criteria", "Out of scope", "Open questions", "Area documents"]
CRITERION = re.compile(r"^\s*- \[[ xX]\] (AC\d+):", re.M)
CRITERION_REF = re.compile(r"\bAC\d+\b")
CASE = re.compile(r"^\s*- ([SE]\d+):", re.M)
CASE_REF = re.compile(r"\b[SE]\d+\b")
ELLIPSIS = r"(?:\.\.\.|\u2026)"
PLACEHOLDERS = [re.compile(p) for p in (r"<title>", r"Issue #<number>", rf"\bAC\d+: {ELLIPSIS}\s*$",
                                         rf"^\s*- [SE]\d+: {ELLIPSIS}\s*$", rf"^\|.*\|\s*{ELLIPSIS}\s*\|")]
EMPTY_CELLS = ("", "-", "...", "\u2026")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def read(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read()


def resolve_folder(root, folder):
    """The work folder under `specs/`, found in the directory listing so the argument never becomes a path."""
    wanted = folder.strip().replace("\\", "/").rstrip("/")
    wanted = wanted[len("specs/"):] if wanted.startswith("specs/") else wanted
    specs = os.path.join(root, "specs")
    if not os.path.isdir(specs):
        return None
    for name in sorted(os.listdir(specs)):
        if name == wanted and name not in ("_template", ".", "..") and os.path.isdir(os.path.join(specs, name)):
            return os.path.join(specs, name)
    return None


def sections(text):
    """{heading: body} for every `## ` section, without the template's guidance comments."""
    result, current = {}, None
    for line in COMMENT.sub("", text).splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            result[current] = []
        elif current is not None:
            result[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in result.items()}


def filled(body):
    """True when a section holds more than the template's guidance, which stands in HTML comments."""
    return bool(COMMENT.sub("", body or "").strip())


def table_rows(body):
    """The data rows of the first Markdown table in a section, as lists of stripped cells."""
    rows = []
    for line in (body or "").splitlines():
        if not line.strip().startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        rows.append(cells)
    return rows[1:]


def check_placeholders(name, text, errors):
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in PLACEHOLDERS):
            errors.append(f"{name}: template placeholder left: {line.strip()}")


def check_spec(spec, errors):
    """The spec's sections; returns its criterion ids."""
    parts = sections(spec)
    for section in SPEC_SECTIONS:
        if not filled(parts.get(section)):
            errors.append(f"spec.md: section *{section}* is missing or empty (write \"none\" when nothing applies)")
    criteria = CRITERION.findall(parts.get("Acceptance criteria", ""))
    if len(criteria) != len(set(criteria)):
        errors.append("spec.md: an acceptance criterion id is used twice")
    cases = CASE.findall(parts.get("Scenarios", "") + "\n" + parts.get("Errors and edge cases", ""))
    covered = set(CASE_REF.findall(parts.get("Acceptance criteria", ""))) | set(
        CASE_REF.findall(parts.get("Out of scope", "")))
    for case in cases:
        if case not in covered:
            errors.append(f"spec.md: {case} is named by no acceptance criterion and not listed under *Out of scope*")
    questions = parts.get("Open questions", "")
    if questions.strip().lower() not in ("none", "none."):
        for line in questions.splitlines():
            if line.strip().startswith("- ") and "Answered:" not in line:
                errors.append(f"spec.md: open question without `Answered:`: {line.strip()}")
    return set(criteria)


def check_tests(plan_parts, criteria, errors):
    rows = table_rows(plan_parts.get("Tests per criterion"))
    named = {cell for row in rows for cell in CRITERION_REF.findall(row[0] if row else "")}
    without_tests = set(CRITERION_REF.findall(plan_parts.get("Verification without tests", "")))
    for criterion in sorted(criteria - named - without_tests):
        errors.append(f"plan.md: {criterion} has no row in *Tests per criterion* (nor in *Verification without tests*)")
    for criterion in sorted(named - criteria):
        errors.append(f"plan.md: *Tests per criterion* names {criterion}, which no acceptance criterion defines")
    for row in rows:
        if len(row) < 2 or row[1] in EMPTY_CELLS:
            errors.append(f"plan.md: *Tests per criterion* row without a test name: | {' | '.join(row)} |")


def check_facts(plan_parts, errors):
    for row in table_rows(plan_parts.get("Verified facts")):
        if len(row) < 3:
            errors.append(f"plan.md: *Verified facts* row needs claim, evidence and status: | {' | '.join(row)} |")
            continue
        claim, evidence, status = row[-3], row[-2], row[-1].lower()
        if evidence in EMPTY_CELLS:
            errors.append(f"plan.md: claim without evidence in *Verified facts*: {claim}")
        if status not in STATUSES:
            errors.append(f"plan.md: *Verified facts* status must be one of {', '.join(STATUSES)}: {claim}")
        elif status == "unverified" and not evidence.lower().startswith("to verify:"):
            errors.append(f"plan.md: unverified claim without `to verify:` and its measurement: {claim}")


def check_tasks(tasks, criteria, errors):
    rows = table_rows(tasks)
    named = {ref for row in rows for cell in row for ref in CRITERION_REF.findall(cell)}
    for criterion in sorted(criteria - named):
        errors.append(f"tasks.md: {criterion} is covered by no task")
    for criterion in sorted(named - criteria):
        errors.append(f"tasks.md: names {criterion}, which spec.md does not define")


def check_plan(plan, spec, errors):
    """plan.md against the tier, the facts and the criteria; returns the criteria of the work folder."""
    parts = sections(plan)
    tier = re.search(r"^Tier:\s*`?(\w+)`?([^\n]*)", plan, re.M)
    if not tier or tier.group(1) not in TIERS or tier.group(2).lstrip().startswith("|"):
        errors.append(f"plan.md: the *Tier* line must name exactly one of {', '.join(TIERS)}")
    own = set(CRITERION.findall(plan))
    if spec is None:
        criteria = own
        if not criteria:
            errors.append("plan.md: no acceptance criterion (`- [ ] AC1: …`) under *Acceptance criteria*")
    else:
        criteria = check_spec(spec, errors)
        for criterion in sorted(own):
            errors.append(f"plan.md: defines {criterion}; a feature's criteria live in spec.md only")
    check_tests(parts, criteria, errors)
    check_facts(parts, errors)
    return criteria


def check_spec_only(folder):
    """Findings for `spec.md` alone (step 2, before the plan is written)."""
    spec = read(os.path.join(folder, "spec.md"))
    if spec is None:
        return ["spec.md is missing"], []
    errors = []
    check_spec(spec, errors)
    check_placeholders("spec.md", spec, errors)
    return errors, []


def check(folder):
    """All findings for the work folder, and the warnings."""
    errors, warnings = [], []
    plan = read(os.path.join(folder, "plan.md"))
    spec = read(os.path.join(folder, "spec.md"))
    if plan is None:
        return ["plan.md is missing (tiers docs and patch write none: there is nothing to check)"], warnings
    criteria = check_plan(plan, spec, errors)
    for name, text in (("plan.md", plan), ("spec.md", spec)):
        if text is not None:
            check_placeholders(name, text, errors)
    if spec is not None:
        tasks = read(os.path.join(folder, "tasks.md"))
        if tasks is None:
            errors.append("tasks.md is missing")
        else:
            check_tasks(tasks, criteria, errors)
            check_placeholders("tasks.md", tasks, errors)
    words = len(plan.split())
    if words > PLAN_MAX_WORDS:
        warnings.append(f"plan.md has {words} words (PLAN_MAX_WORDS {PLAN_MAX_WORDS}): every member reads it — "
                        "cut what the code, the spec or a decision record already says")
    return errors, warnings


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    spec_only = "--spec" in argv
    names = [arg for arg in argv if arg != "--spec"]
    if len(names) != 1 or any(arg.startswith("-") for arg in names):
        print("Usage: python3 .squad/tools/plan-check.py <work folder> [--spec]")
        return 1
    folder = resolve_folder(os.getcwd(), names[0])
    if folder is None:
        print(f"No work folder {names[0]!r} under specs/")
        return 1
    errors, warnings = check_spec_only(folder) if spec_only else check(folder)
    for line in warnings:
        print(f"WARNING: {line}")
    for line in errors:
        print(line)
    print("PASS" if not errors else f"FAIL: {len(errors)} finding(s) — back to the Lead (mode `revise`)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
