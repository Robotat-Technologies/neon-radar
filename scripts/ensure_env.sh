#!/usr/bin/env bash
# Create .env from .env.example with a generated NEO4J_PASSWORD (PHASE-1.md M1.4).
# Does nothing when .env already exists. Never prints the password (guardrail G6).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$root/.env"
example="$root/.env.example"

if [ -e "$env_file" ] || [ -L "$env_file" ]; then
  # grep -q prints nothing, so the file's contents never reach the terminal.
  grep -q '^NEO4J_PASSWORD=.\{8,\}' "$env_file" 2>/dev/null ||
    echo "ensure_env: .env has no NEO4J_PASSWORD; edit or delete it and re-run" >&2
  exit 0
fi

# In a linked git worktree, share the main checkout's .env: all checkouts run the same Compose
# project and so the same database, whose password is fixed when the database is first created.
common="$(git -C "$root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
gitdir="$(git -C "$root" rev-parse --path-format=absolute --git-dir 2>/dev/null || true)"
if [ -n "$common" ] && [ "$common" != "$gitdir" ]; then
  main_root="$(dirname "$common")"
  if [ -e "$main_root/.env" ]; then
    ln -s "$main_root/.env" "$env_file"
    echo "Linked .env to the main checkout's .env."
    exit 0
  fi
  echo "ensure_env: this is a linked git worktree; run 'bash scripts/ensure_env.sh'" \
    "in the main checkout ($main_root) first" >&2
  exit 1
fi

if [ ! -f "$example" ]; then
  echo "ensure_env: $example is missing" >&2
  exit 1
fi

if command -v openssl >/dev/null 2>&1; then
  password="$(openssl rand -hex 16)"
else
  password="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
fi
if [ "${#password}" -ne 32 ]; then
  echo "ensure_env: could not generate a password (needs openssl or python3)" >&2
  exit 1
fi

umask 077
tmp="$(mktemp "$root/.env.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    NEO4J_PASSWORD=*) printf 'NEO4J_PASSWORD=%s\n' "$password" ;;
    *) printf '%s\n' "$line" ;;
  esac
done <"$example" >"$tmp"
if ! grep -q '^NEO4J_PASSWORD=[0-9a-f]\{32\}$' "$tmp"; then
  echo "ensure_env: $example has no NEO4J_PASSWORD= line; .env not created" >&2
  exit 1
fi
mv "$tmp" "$env_file"
trap - EXIT
echo "Created .env with a generated NEO4J_PASSWORD (not shown). Edit .env to pick a memory profile."
