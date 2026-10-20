#!/usr/bin/env bash
# PostToolUse(Edit|Write): format the file Claude just wrote. Always exits 0.
set -uo pipefail
file="$(jq -r '.tool_input.file_path // empty')"
[ -z "$file" ] || [ ! -f "$file" ] && exit 0
case "$file" in
  *.py)
    uv run --no-sync ruff format --quiet "$file" >/dev/null 2>&1
    ;;
  */ui/*.ts|*/ui/*.vue|*/ui/*.css|*/ui/*.json)
    ( cd "${CLAUDE_PROJECT_DIR:-.}/ui" && npx --no-install prettier --write "$file" >/dev/null 2>&1 )
    ;;
esac
exit 0
