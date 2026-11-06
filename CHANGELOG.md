# Changelog

What each release of the template brings to the repositories that use it (`consumers.json`). Every pull request that
changes what a target receives adds a line under *Unreleased*; a release turns those lines into a version section and
is tagged (`AGENTS.md`, *Releases*). Changes before the first release are in the history of `main`.

## Unreleased

- [Tools] `squad-log.py --agent-id` reads a launch's model, effort, tokens per kind, tool uses and seconds from the
  subagent's transcript; `--summary` adds a price-weighted table per role with the orchestrator's share, and
  `session-usage.py` a weighted column (#234)
- [Core] Squad lessons are filed in the run's own repository (`squad-upstream` for a template-managed file, `squad`
  for project knowledge); `squad-log.py --summary` requires the step-12 lessons row and lists the lesson candidates
  (#239)
- [Tools] `.squad/template.json` records the template's release tag, and `squad-log.py --summary` prints it (#249)
