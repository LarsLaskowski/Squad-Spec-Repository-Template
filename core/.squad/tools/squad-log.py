#!/usr/bin/env python3
"""Append one row to a squad working record's `log.md`, the way the pipeline wants it: one row per step,
today's date, the file's own line ending, no control character and no cell-breaking pipe or newline.

The orchestrator is the only writer of `log.md`; it records what the members report. This script keeps the
mechanics out of the orchestrator's hands:

- the row is `| <date> | <step> | <member> | <result> |`, appended after the last line, which gets its line
  ending first if it lacks one;
- the line ending follows the file (CRLF when the file uses it), so rows never end up with mixed endings;
- a `|` in a cell is written as `\\|`, a line break in the result as `<br>` (a Markdown table cell has one line);
- a control character (Unicode categories Cc, Cf, Zl, Zp other than tab and line break) is written as its
  escape (`U+202E`), never as the character itself; a tab becomes a space.

Usage, from anywhere inside the repository:
    python3 .squad/tools/squad-log.py <work folder> <step> <member> <result>

`<work folder>` is `specs/issue-12`, `issue-12` or a path to the folder; `<result>` may contain line breaks.
Exit code 0 when the row was written, 1 when the folder has no `log.md`.
"""
import datetime
import os
import re
import subprocess
import sys
import unicodedata

CONTROL_CATEGORIES = {"Cc", "Cf", "Zl", "Zp"}
KEEP = {"\t", "\n", "\r"}


def escape_controls(text):
    """Every control character other than tab and line break as `U+XXXX`."""
    return "".join(f"U+{ord(ch):04X}" if unicodedata.category(ch) in CONTROL_CATEGORIES and ch not in KEEP else ch
                   for ch in text)


def cell(text):
    text = escape_controls(text).replace("\t", " ")
    text = re.sub(r"\r\n|\r|\n", "<br>", text.strip())
    return text.replace("|", "\\|")


def resolve_log(root, folder):
    for candidate in (folder, os.path.join("specs", folder)):
        path = os.path.join(root, candidate, "log.md")
        if os.path.isfile(path):
            return path
    return None


def append_row(path, step, member, result, today=None):
    with open(path, "rb") as handle:
        data = handle.read()
    eol = b"\r\n" if b"\r\n" in data else b"\n"
    date = today or datetime.date.today().isoformat()
    row = f"| {date} | {cell(step)} | {cell(member)} | {cell(result)} |".encode()
    if data and not data.endswith((b"\n", b"\r\n")):
        data += eol
    with open(path, "wb") as handle:
        handle.write(data + row + eol)
    return row.decode()


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    folder, step, member, result = sys.argv[1:]
    toplevel = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    root = toplevel.stdout.strip() if toplevel.returncode == 0 else os.getcwd()
    path = resolve_log(root, folder)
    if path is None:
        print(f"No log.md in {folder} (create it from specs/_template/log.md first)")
        return 1
    print(append_row(path, step, member, result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
