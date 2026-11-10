<!---
Title: `[area] Description` in English (areas: Core, Profile, Tools, Skill, Docs). The PR is merged with
Squash and merge, so the title and description are what reaches `main`.
-->

## 📖 Description

<!---
3–5 sentences in English: what changes and why. If the change comes from a squad run in another
repository, name that run (for example Vandox#123).
-->

## 🎫 Issues

<!--- For example: Closes #123 -->

## 💬 Reviewer Notes

<!---
Anything the reviewer should focus on, for example a changed rule in `core/` that every target repository
picks up with the next `adopt-template` run.
-->

## ✅ Checklist

<!--- Put an x in the boxes that apply. -->

- [ ] `python3 tools/template-check.py` passes.
- [ ] `ruff check .` and `python -m unittest discover tools` pass (if Python files changed).
- [ ] `core/` stays stack- and project-neutral; stack details live in `profiles/<stack>/`.
- [ ] A rule that states how an outside tool behaves (a rule id, an option, a version) has its evidence from a consumer's build below.
- [ ] [`README.md`](../README.md) is updated if the layout, a profile or a tool's behaviour changed.

## 🚀 Rollout

<!---
Target repositories that should get this change with `adopt-template`, or "none".
-->
