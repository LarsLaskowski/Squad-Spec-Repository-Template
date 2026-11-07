# Changelog

What each release of the template brings to the repositories that use it (`consumers.json`). Every pull request that
changes what a target receives adds a line under *Unreleased*; a release turns those lines into a version section and
is tagged (`AGENTS.md`, *Releases*). Changes before the first release are in the history of `main`.

## Unreleased

- [Tools] `gate-stamp.py`, `figure-check.py`, `decision-check.py` and `squad-log.py` pass SonarQube Cloud's Python
  rules again (python:S6019, S5850, S8786, S7632, S3776), so a refresh no longer fails a target's quality gate (#261)
- [Tools] `squad-log.py --agent-id` reads a launch's model, effort, tokens per kind, tool uses and seconds from the
  subagent's transcript; `--summary` adds a price-weighted table per role with the orchestrator's share, and
  `session-usage.py` a weighted column (#234)
- [Core] Squad lessons are filed in the run's own repository (`squad-upstream` for a template-managed file, `squad`
  for project knowledge); `squad-log.py --summary` requires the step-12 lessons row and lists the lesson candidates
  (#239)
- [Tools] `.squad/template.json` records the template's release tag, and `squad-log.py --summary` prints it (#249)
- [Core] `.squad/project.md` is a pointer file: entries name files and link their area document or record, and
  `config-check.py` warns above `PROJECT_MAX_WORDS`; `decision-check.py` warns about an unreleased record past
  `RECORD_MAX_WORDS` or `RECORD_MAX_OPTIONS` and an area document past `AREA_MAX_WORDS` (new settings in
  `squad_settings.py`), and an unreleased record is extended only for the same decision (#236)
- [Core] The squad's process decisions are the managed `docs/decisions/process.md` instead of numbered records; a
  refresh retires the process records older versions added once (`adopt-template` step 8) (#247)
- [Tools] `figure-check.py` lists the documentation lines that still state a value the diff changed; the Dev runs it
  with the documentation and step 7 runs it again (`FIGURE_TRIVIAL`, `FIGURE_EXCLUDES` in `squad_settings.py`) (#237)
- [Tools] `squad-next.py` prints the orchestrator's next step with its exact launch, and `gate-stamp.py` runs the
  step-7 gates of the tier and logs them with the head SHA; step 9 (`--verify`) and `squad-log.py --summary` (exit 6)
  refuse a head without a passing stamp (#238)
- [Core] The squad's rule files are consolidated without changing a rule: repetitions point to the one place a rule
  lives, and procedure the tools enforce (`squad-next.py`, `gate-stamp.py`, `squad-log.py`, `plan-check.py`, the
  Git and file guards) is a pointer to the tool (#234–#250)
