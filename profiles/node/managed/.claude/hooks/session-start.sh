#!/bin/bash
# SessionStart hook for Claude Code on the web (Node/TypeScript profile): installs the dependencies so
# the squad can type-check, lint, format, test and check coverage. Idempotent; does nothing outside
# remote sessions.
set -euo pipefail

if [[ "${CLAUDE_CODE_REMOTE:-}" != "true" ]]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
