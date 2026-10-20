#!/usr/bin/env bash
# PreToolUse(Edit|Write): block edits to frozen contracts once tag contracts-v1.0.0 exists.
# Exit 2 blocks the tool call and shows the message to Claude. See CLAUDE.md rule 7.
set -uo pipefail
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
[ -z "$file" ] && exit 0
case "$file" in
  */contracts/*|*/graph/schema/*) ;;
  *) exit 0 ;;
esac
if ! git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse -q --verify "refs/tags/contracts-v1.0.0" >/dev/null 2>&1; then
  exit 0   # contracts are not frozen yet (Phase 1 authoring)
fi
if [ "${NR_ALLOW_CONTRACT_CHANGE:-}" = "1" ]; then
  exit 0   # the tech lead opened an approved contract-change session
fi
echo "Blocked: ${file} is a frozen contract (tag contracts-v1.0.0). Open a contract-change issue; the tech lead enables NR_ALLOW_CONTRACT_CHANGE=1 for the session after approval." >&2
exit 2
