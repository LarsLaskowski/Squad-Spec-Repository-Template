---
name: squad-upstream-cycle
description: Use when the user wants the full template maintenance cycle — collect the squad lessons (issues labelled squad-upstream or squad, and unlabelled issues about the squad) from every active consumer of consumers.json, move them here as issues and close the originals with a link, fix them all in one pull request, prepare the release pull request, and after the owner has created the release roll the template out to every active consumer. Resumes at the phase the cycle is in.
---

# Squad upstream cycle

The whole path of a squad lesson from a consumer repository back into it: **collect → move → fix → release PR →
(owner releases) → rollout**. It follows `AGENTS.md` (*Golden rules*, *Releases*, *Writing rules*) and `README.md`
(*Changing the template*, *Rolling out a change*); this skill only orders the steps and adds the search for lessons
that carry no label. Invoking it is the user's approval for every pull request named below, here and in the
consumers, and for moving and closing the consumers' issues — nothing else. It never merges a pull request, never
creates a tag or release, and never pushes to `main`.

Rules that hold throughout:

- Everything written to GitHub or into a repository is in **English**; the report to the user is in the user's language.
- The consumers are the `active` entries of `consumers.json`; `legacy` ones are left out. Add each with `add_repo`
  (`read` for phases 1–2 if `gh` can read them, `push` for moving issues and for the rollout).
- Work on the branch the session prescribes, otherwise on a new branch off the latest `origin/main`; commit and push
  after every completed step.
- Every pull request is opened as a draft, then subscribed to (`subscribe_pr_activity`) and driven until CI, the
  `sonarqube` job and the review are green; then it is marked ready and the owner merges it.

## Phase 0 — Where the cycle stands

On every invocation, first find the phase, then continue there (a session that resumes after a summary does the same):

| State found | Continue at |
| ----------- | ----------- |
| A release tag `vYYYY.MM.N` on `origin` newer than the `tag` in some active consumer's `.squad/template.json`, and no open refresh PR there for it | Phase 6 |
| An open `[Docs] Release …` pull request here | Phase 5 (drive it) |
| A merged release PR whose version has no tag on `origin` yet | Phase 5, last step (wait for the owner) |
| An open lesson pull request of this cycle here | Phase 4 (drive it) |
| Open issues labelled `squad` here that no merged PR closed | Phase 3 |
| Otherwise | Phase 1 |

`git fetch origin --tags` before reading tags. Tell the user in one line which phase you start at and why.

## Phase 1 — Collect

For every active consumer:

1. **Labelled.** `python3 tools/squad-report.py --upstream` lists the open `squad-upstream` issues of every active
   consumer and, below them, the open `squad` issues that name a template-managed file. Also list every open issue
   labelled `squad` there (`list_issues` with `labels: ["squad"]`).
2. **Unlabelled.** So no lesson is lost when the label is missing, read the title and body of every other open issue
   of the consumer (all of them, paginated — not a keyword search alone). A candidate is an issue about the squad's
   rules, agents, skills, tools, hooks or the template: it names a path under `.squad/`, `.claude/agents/`,
   `.claude/skills/`, `.claude/hooks/`, `specs/` templates, `docs/decisions/process.md`, the template part of
   `AGENTS.md`, a squad role (Orchestrator, Lead, PM, Tester, Developer, Reviewer, Security, Code Officer), a squad
   tool (`squad-next.py`, `squad-log.py`, `gate-stamp.py`, `plan-check.py`, `config-check.py`, …), a squad run or
   working record, a refresh, or starts with `[Squad]`.
3. **Classify** every issue found by the files its fix would change, as `.squad/tools/lesson-label.py` does
   (`python3 core/.squad/tools/lesson-label.py <path> …` from here): a managed file or the template part of a marked
   file → **move** (phase 2); only the consumer's own knowledge (`.squad/stack.md`, `.squad/project.md`,
   `squad_settings.py`, a project block, a seeded file) → **stays** in the consumer as `squad` (add the label to an
   unlabelled one, `issue_write`); both → split: the template part moves, the rest stays, each naming the other.
   Only where the classification needs a judgment you cannot make from the text, ask the user once, all such issues
   in one `AskUserQuestion` (title, URL, your proposal).

Show the user the table — consumer, issue, label found, decision, reason — before phase 2, and continue without
waiting for an answer unless a question is open.

## Phase 2 — Move and close

1. Before creating anything, search this repository's issues (open and closed) for a link to the source issue, so a
   rerun never creates a duplicate.
2. `python3 tools/squad-report.py --upstream --move` moves the `squad-upstream` issues in one batch. Every other issue
   that moves (a `squad` or unlabelled one) is moved the same way by hand with the GitHub tools: a new issue here,
   labelled `squad`, title `[Squad] <lesson> (from <owner/repo>#<n>)` (keep an existing `[Squad]` title), the
   original body and a link back. Without `gh` write access, move all of them this way.
3. Close each source issue (`state_reason: "completed"`) with a comment linking the new issue here: "Moved to
   <URL>; fixed in the template and rolled out with its next release." A split issue stays open with the part that
   stays and a link to the moved part.

## Phase 3 — Fix

All open `squad` issues here (the moved ones and any already open) are fixed in **one** pull request.

1. Read every issue and the run it links before changing anything; a lesson that contradicts another or needs a
   product decision goes to the user (one `AskUserQuestion` for all), never decided by guessing.
2. Fix each lesson following `AGENTS.md`: a deterministic step in the tool that can check it (with tests in
   `tools/test_*.py`), judgment in the one rule file that owns the rule, the evidence in `docs/squad-rationale.md`,
   `core/` stack- and project-neutral. One commit per issue (subject ≤ 80 characters, naming the issue).
3. One line per change under `## Unreleased` in `CHANGELOG.md`: `- [Area] what changes for the targets (#issue)`.
4. `pip install complexipy==9.0.0` if missing, then `python3 tools/template-check.py` and `python3 -m pytest tools`
   must pass. Note the word-count deltas, the sentences that left the rule files and shared 20-word runs it reports:
   the PR description answers each (`AGENTS.md`, *Writing rules*).
5. Open the draft PR here: title `[Core] Fix the squad lessons of the <consumers> runs` (another area if only that
   area changed), 3–5 English sentences, a `Closes #n` line per issue, the template-check report items, and the
   evidence an outside-tool statement needs (`AGENTS.md`, *Releases*). Subscribe and drive it (*Rules that hold
   throughout*); a Sonar finding is fixed and its rule added to `SONAR_RULES` where `template-check.py` can detect it.

## Phase 4 — Wait for the merge

The owner merges. When the merge event arrives, check on `origin/main` that every issue of phase 3 is closed; reopen
nothing silently — a still-open one goes back to phase 3 in a new PR. Then phase 5.

## Phase 5 — Release pull request

On an up-to-date checkout of `origin/main` (`AGENTS.md`, *Releases*):

1. `python3 tools/sonar-local.py` must pass.
2. `python3 tools/rollout-check.py` must pass; it needs a clone of every active consumer next to this repository
   (clone the ones `add_repo` attached there, or name them with `--target OWNER/NAME=PATH`). Add `--build` when a
   `dotnet` consumer's rule baseline changed.
3. One `squad-reviewer` pass (charter `core/.claude/agents/squad-reviewer.md`) over `git diff <last tag>..origin/main`
   limited to what the targets receive.
4. A finding of any of the three is fixed first in a pull request of its own (phase 3 and 4 for that PR alone), then
   this phase starts again from step 1.
5. On a new branch: `python3 tools/release.py prepare`, commit, open the draft PR `[Docs] Release vYYYY.MM.N` with the
   version's `CHANGELOG.md` section as the description, subscribe and drive it.
6. After its merge, tell the user: create the release on GitHub (*Releases*, *Draft a new release*), tag
   `vYYYY.MM.N` on `main` at the merge commit `<sha>`, the version's `CHANGELOG.md` section as its notes. Then end the
   turn; the owner says when it exists, or invokes this skill again (phase 0 finds it).

## Phase 6 — Rollout

1. `git fetch origin --tags` and check `git rev-parse vYYYY.MM.N^{commit}` equals the release PR's merge commit; on a
   mismatch stop and tell the user.
2. For each active consumer, run the `adopt-template` skill as a refresh from a checkout of the tag — one consumer
   after the other, each with its own draft PR `[Docs] Update the squad from Squad-Spec-Repository-Template` naming
   the release, labelled `ignore-for-release`, subscribed and driven as that skill says. The refresh also moves any
   `squad-upstream` issue filed since phase 1 (that skill, step 1); such issues wait for the next cycle.
3. A refresh that stops on something the release brought is fixed here first (a fix PR and a fix release), never in
   the consumer.

## Report

At the end of every phase that waits for the owner, and at the end of the cycle, tell the user: the issues moved
(source → new), those kept in the consumers and why, the lesson PR, the release PR and version, the refresh PR per
consumer with its state, and anything that stopped or needs the owner (a merge, the release, a repository setting).
