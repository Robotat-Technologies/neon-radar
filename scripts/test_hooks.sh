#!/usr/bin/env bash
# Self-test for the Claude Code hooks in .claude/hooks (docs/build/PHASE-1.md, M1.2).
# Pipes sample hook input into each hook, prints PASS or FAIL per case, and exits 1 if any
# case fails. Needs bash 3.2 or later, git, jq and python3. It never uses the network, and
# the frozen-contract cases tag a temporary clone, never this repository.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$ROOT/.claude/hooks"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BRANCH=p1/m1-4-local-stack
NL=$'\n'
passed=0
failed=0

report() { # report <status, 0 means pass> <description>
  if [ "$1" -eq 0 ]; then
    passed=$((passed + 1))
    echo "PASS  $2"
  else
    failed=$((failed + 1))
    echo "FAIL  $2"
  fi
}

expect_exit() { # expect_exit <wanted exit code> <description> <input json> <command...>
  local want="$1" desc="$2" input="$3" got
  shift 3
  printf '%s' "$input" | "$@" >/dev/null 2>&1
  got=$?
  [ "$got" -eq "$want" ]
  report $? "$desc (exit $got, want $want)"
}

for tool in git jq python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "FAIL  prerequisite: $tool is not installed"
    exit 1
  fi
done

echo "== files"
for file in .claude/hooks/guard_git.py .claude/hooks/guard-contracts.sh \
  .claude/hooks/format-file.sh .claude/hooks/guard_real_data.py scripts/test_hooks.sh; do
  [ -x "$ROOT/$file" ]
  report $? "executable: $file"
done
tags_before="$(git -C "$ROOT" tag -l 'contracts-v*')"

edit_input() { # edit_input <file path>
  jq -n --arg f "$1" '{tool_name: "Edit", tool_input: {file_path: $f}}'
}

echo "== guard-contracts.sh (a temporary clone stands in for the repository)"
CLONE="$TMP/clone"
git clone -q --no-checkout "$ROOT" "$CLONE"
git -C "$CLONE" tag -d contracts-v1.0.0 >/dev/null 2>&1 || true

contracts() { # contracts <wanted exit code> <description> <path in the clone> [VAR=value]
  local want="$1" desc="$2" file="$3"
  shift 3
  expect_exit "$want" "guard-contracts: $desc" "$(edit_input "$CLONE/$file")" \
    env -u NR_ALLOW_CONTRACT_CHANGE CLAUDE_PROJECT_DIR="$CLONE" "$@" "$HOOKS/guard-contracts.sh"
}

contracts 0 "edit ui/src/x.ts, no tag" ui/src/x.ts
contracts 0 "edit contracts/x.py, no tag" contracts/x.py
git -C "$CLONE" tag contracts-v1.0.0
contracts 2 "edit contracts/x.py, tag contracts-v1.0.0" contracts/x.py
contracts 0 "edit contracts/x.py, tag, NR_ALLOW_CONTRACT_CHANGE=1" contracts/x.py \
  NR_ALLOW_CONTRACT_CHANGE=1
contracts 2 "edit graph/schema/migrations/0002_x.cypher, tag" \
  graph/schema/migrations/0002_x.cypher
contracts 0 "edit ui/src/x.ts, tag" ui/src/x.ts
expect_exit 0 "guard-contracts: input without file_path" '{"tool_name": "Edit", "tool_input": {}}' \
  env CLAUDE_PROJECT_DIR="$CLONE" "$HOOKS/guard-contracts.sh"

echo "== format-file.sh (always exits 0)"
printf '# note\n' >"$TMP/note.md"
expect_exit 0 "format-file: input without file_path" '{"tool_name": "Write", "tool_input": {}}' \
  env CLAUDE_PROJECT_DIR="$TMP" "$HOOKS/format-file.sh"
expect_exit 0 "format-file: missing file" "$(edit_input "$TMP/missing.py")" \
  env CLAUDE_PROJECT_DIR="$TMP" "$HOOKS/format-file.sh"
expect_exit 0 "format-file: Markdown file" "$(edit_input "$TMP/note.md")" \
  env CLAUDE_PROJECT_DIR="$TMP" "$HOOKS/format-file.sh"
[ "$(cat "$TMP/note.md")" = "# note" ]
report $? "format-file: Markdown file left unchanged"

echo "== guard_git.py"
P1="$TMP/repo-p1"
MAIN="$TMP/repo-main"
git init -q "$P1" && git -C "$P1" symbolic-ref HEAD "refs/heads/$BRANCH"
git init -q "$MAIN" && git -C "$MAIN" symbolic-ref HEAD refs/heads/main

bash_input() { # bash_input <command> <cwd> [agent id]
  jq -n --arg c "$1" --arg d "$2" --arg a "${3:-}" \
    '{tool_name: "Bash", tool_input: {command: $c}, cwd: $d}
     + (if $a == "" then {} else {agent_id: $a, agent_type: "builder"} end)'
}

guard() { # guard <wanted exit code> <repository> <command> [agent id]
  local label="${3//$NL/ \\n }"
  [ -n "${4:-}" ] && label="$label [in a subagent]"
  [ "$2" = "$MAIN" ] && label="$label [on main]"
  expect_exit "$1" "guard_git: $label" "$(bash_input "$3" "$2" "${4:-}")" \
    python3 "$HOOKS/guard_git.py"
}

# Multi-line cases from the spec.
IFS= read -r -d '' HEREDOC_COMMIT <<'CASE' || true
git commit -m "$(cat <<'EOF'
feat(agent): add the hooks

It's the guard for pushes.
EOF
)"
CASE
IFS= read -r -d '' PR_COMMENT <<'CASE' || true
gh pr comment 12 --body "Thanks for the review.
It's fixed in the next commit.
Done"
CASE
IFS= read -r -d '' CAT_HEREDOC <<'CASE' || true
cat > notes.txt <<'EOF'
it's a digit thing
EOF
CASE
guard 0 "$P1" "${HEREDOC_COMMIT%$NL}"
guard 0 "$P1" "${PR_COMMENT%$NL}"
guard 0 "$P1" "${CAT_HEREDOC%$NL}"

# Merges inside a subagent (OD-3): builders never merge, whatever the form.
guard 2 "$P1" "gh pr merge 12 --merge" agent-1
guard 0 "$P1" "gh pr merge 12 --merge"
guard 0 "$P1" "git push -u origin $BRANCH" agent-1
guard 2 "$P1" "gh pr merge 4 --merge 2>&1" agent-1

# One case per line: <wanted exit code> <p1|main> <command>. The repository is on branch
# BRANCH (p1) or main; P1DIR is its path; \n starts a new line of the command.
while read -r want repo cmd; do
  case "$want" in '' | '#'*) continue ;; esac
  cmd="${cmd//BRANCH/$BRANCH}"
  cmd="${cmd//P1DIR/$P1}"
  cmd="${cmd//\\n/$NL}"
  if [ "$repo" = main ]; then guard "$want" "$MAIN" "$cmd"; else guard "$want" "$P1" "$cmd"; fi
done <<'CASES'
# Spec: allowed
0 p1 git push -u origin BRANCH
0 p1 git push origin HEAD:BRANCH
0 p1 git push origin HEAD
0 p1 git push
0 p1 make check && git push -u origin BRANCH
0 p1 git -C . push origin p2/m2-1-loader
0 p1 gh pr create --base main --title x
0 p1 git status
0 p1 uv run pytest -q\ngh pr checks 7 --watch
# Spec: blocked
2 p1 git push origin main
2 p1 git push origin p1/x:main
2 p1 git push origin p1/x main
2 p1 git push origin HEAD:refs/heads/main
2 p1 git push origin +p1/x
2 p1 git push --force-with-lease origin p1/x
2 p1 git push -uf origin p1/x
2 p1 git push origin --delete p1/x
2 p1 git push origin :p1/x
2 p1 git push --tags
2 p1 FOO=1 git push origin main
2 p1 git status\ngit push origin main
2 p1 bash -c 'git push origin main'
2 p1 gh pr merge 12 --squash
2 p1 gh api -X PUT repos/o/r/pulls/12/merge
2 p1 gh repo edit --visibility public
2 main git push
2 main git push origin HEAD
2 main git push -u origin HEAD
# OD-9: the one allowed merge form (main session)
0 p1 gh pr merge --merge 12
0 p1 gh pr merge 12 --merge --repo robotat-com/neon-radar
0 p1 gh pr merge 12 --merge --repo=robotat-com/neon-radar
0 p1 gh pr --repo robotat-com/neon-radar merge 12 --merge
0 p1 gh pr merge 12 --merge --subject 'Merge M1.2' --body 'Reviewed and CI green.'
0 p1 gh pr merge 12 --merge && gh pr view 12 --json state
# OD-9: every other gh pr merge form
2 p1 gh pr merge
2 p1 gh pr merge 12
2 p1 gh pr merge --merge
2 p1 gh pr merge 12 --rebase
2 p1 gh pr merge 12 --merge --admin
2 p1 gh pr merge 12 --merge --auto
2 p1 gh pr merge 12 --merge --delete-branch
2 p1 gh pr merge 12 --merge -d
2 p1 gh pr merge 12 -m
2 p1 gh pr merge 12 -s
2 p1 gh pr merge 12 --merge --squash
2 p1 gh pr merge 12 --merge --merge
2 p1 gh pr merge 12 --merge --body-file notes.md
2 p1 gh pr merge 12 --merge --match-head-commit 1a2b3c
2 p1 gh pr merge 12 13 --merge
2 p1 gh pr merge https://github.com/o/r/pull/12 --merge
2 p1 gh pr merge 12 --merge --repo not-a-repo
2 p1 gh pr merge 12 --merge -R o/r
2 p1 gh pr -R o/r merge 12 --squash
2 p1 gh pr --repo=o/r merge 12 --auto --merge
2 p1 GH_REPO=o/r gh pr merge 12 --squash
2 p1 env gh pr merge 12 --squash
2 p1 bash -c 'gh pr merge 12 --merge'
2 p1 echo $(gh pr merge 12 --merge)
2 p1 gh pr view 12\ngh pr merge 12 --squash
2 p1 gh pr comment 12 --body 'next: gh pr merge 12 --merge'
# gh api: reads and pull request conversation stay allowed
0 p1 gh api repos/o/r/pulls/2
0 p1 gh api repos/{owner}/{repo}/pulls/2/merge
0 p1 gh api repos/o/r/branches/main/protection
0 p1 gh api -X GET search/issues -f q='repo:o/r is:open'
0 p1 gh api --paginate repos/o/r/pulls/2/comments --jq '.[].body'
0 p1 gh api repos/o/r/pulls/2/comments/5/replies -f body='Fixed in 1a2b3c.'
0 p1 gh api graphql -f query='query { viewer { login } }'
0 p1 gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "x"}) { clientMutationId } }'
# gh api: writes that merge, move or delete refs, or change protection or settings
2 p1 gh api --method PUT repos/o/r/pulls/12/merge
2 p1 gh api -XPUT repos/o/r/pulls/12/merge
2 p1 gh api repos/o/r/merges -f base=main -f head=p1/x
2 p1 gh api -X PATCH repos/o/r/git/refs/heads/main -f sha=1a2b3c -F force=true
2 p1 gh api -X POST repos/o/r/git/refs -f ref=refs/tags/contracts-v1.0.0 -f sha=1a2b3c
2 p1 gh api -X DELETE repos/o/r/git/refs/heads/p1/x
2 p1 gh api -X DELETE repos/o/r/git/refs/tags/contracts-v1.0.0
2 p1 gh api -X PUT repos/o/r/branches/main/protection --input protection.json
2 p1 gh api -X DELETE repos/o/r/branches/main/protection
2 p1 gh api -X POST repos/o/r/rulesets --input ruleset.json
2 p1 gh api -X PATCH repos/o/r -f visibility=public
2 p1 gh api -X DELETE repos/o/r
2 p1 gh api -X PUT repos/o/r/collaborators/someone
2 p1 gh api -X PUT repos/o/r/actions/secrets/KEY --input secret.json
2 p1 gh api -X POST repos/o/r/releases -f tag_name=contracts-v1.0.0
2 p1 gh api -X PUT repos/o/r/contents/README.md -f message=x -f content=eA== -f branch=main
2 p1 gh api -X POST repos/o/r/statuses/1a2b3c -f state=success -f context=python
2 p1 gh api -X PATCH orgs/o -f default_repository_permission=admin
2 p1 gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: "x"}) { clientMutationId } }'
2 p1 gh api graphql -F query=@mutation.graphql
2 p1 gh api -iX PUT repos/o/r/pulls/12/merge
2 p1 env gh api -X PUT repos/o/r/pulls/12/merge
2 p1 command gh api -X DELETE repos/o/r/git/refs/heads/p1/x
2 p1 /usr/local/bin/gh api -X PUT repos/o/r/pulls/12/merge
2 p1 bash -c 'gh api -X PUT repos/o/r/pulls/12/merge'
2 p1 gh pr view 12 && bash -c 'gh api -X PUT repos/o/r/pulls/12/merge'
# Other gh commands: allowed
0 p1 gh pr update-branch 12
0 p1 gh pr close 12
0 p1 gh pr view 12 --json state,mergeable
0 p1 gh release list
0 p1 gh repo view robotat-com/neon-radar
0 p1 gh secret list
0 p1 gh label create agent --color 7057ff --description x --force
# Other gh commands: blocked (settings, tags, history, remote branch deletion)
2 p1 gh repo delete o/r --yes
2 p1 gh repo rename neonradar2
2 p1 gh repo archive o/r --yes
2 p1 gh repo sync o/r --force
2 p1 gh release create contracts-v1.0.0
2 p1 gh release delete v0.1.0 --cleanup-tag
2 p1 gh pr update-branch 12 --rebase
2 p1 gh pr close 12 --delete-branch
2 p1 gh secret set ANTHROPIC_API_KEY
2 p1 gh variable set FOO --body bar
2 p1 gh workflow disable ci.yml
2 p1 gh alias set pm 'pr merge --squash'
# Pushes: more forms that stay allowed
0 p1 git push --set-upstream origin BRANCH
0 p1 git push origin refs/heads/BRANCH:refs/heads/BRANCH
0 p1 git -C P1DIR push origin BRANCH
0 p1 git push --dry-run origin BRANCH
# Pushes: more forms of force, delete, tag and all-branch pushes
2 p1 git push --branches
2 p1 git push --all origin
2 p1 git push --mirror origin
2 p1 git push --follow-tags origin BRANCH
2 p1 git push origin contracts-v1.0.0
2 p1 git push origin refs/tags/contracts-v1.0.0
2 p1 git push -d origin p1/x
2 p1 git push origin p1/x --force
2 p1 git push --force-if-includes origin p1/x
2 p1 git --work-tree . push origin main
2 p1 git -c alias.p=push p origin main
2 p1 env git push origin main
2 p1 /usr/bin/git push origin main
2 p1 git 'push' origin main
2 p1 git push -u origin BRANCH && bash -c 'git push origin main'
2 p1 git push origin HEAD:main --dry-run
2 p1 git commit -m 'docs: never git push to main'
# Redirections never name a ref or a pull request
0 p1 git push -u origin p1/m1-3-workspace 2>&1
0 p1 git push 2>&1 | tail -3
0 p1 git push -u origin HEAD 2>/dev/null
0 p1 git push -u origin BRANCH > /tmp/push.log 2>&1
0 p1 gh pr merge 4 --merge 2>&1
0 p1 gh pr merge 4 --merge >/dev/null
2 p1 git push origin main 2>&1
2 p1 git push origin 2>&1 main
2 p1 git push --force origin p1/x 2>&1
2 p1 git push origin main > /tmp/push.log 2>&1
2 p1 git push origin BRANCH '>' main
2 p1 gh pr merge 4 --squash 2>&1
2 p1 gh pr merge 4 2>&1
2 p1 gh pr merge 4>/dev/null --merge
2 p1 gh pr merge 4 --merge '>' 5
CASES

echo "== guard_real_data.py (PHASE-2.md M2.0, PHASE-3.md M3.0; the cases are in scripts/tests/test_guard_real_data.py)"
(cd "$ROOT" && uv run --no-sync pytest -q scripts/tests/test_guard_real_data.py >/dev/null)
report $? "guard_real_data.py (213 cases)"

[ "$(git -C "$ROOT" tag -l 'contracts-v*')" = "$tags_before" ]
report $? "this repository's contracts-v* tags are unchanged by the test"

echo
echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
