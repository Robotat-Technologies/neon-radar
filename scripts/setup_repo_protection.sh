#!/usr/bin/env bash
# Repository protection for NeonRadar (docs/build/PHASE-1.md M1.6; docs/build/ci.md).
#
# A person with admin rights on the repository runs this in their own terminal. Claude Code
# never runs it (CLAUDE.md rule 8): it refuses when CLAUDECODE is set, except with --dry-run,
# which sends nothing and only prints the requests. It prints what it changed and what it
# could not change, and exits 1 if anything was not changed.
#
# Needs bash 3.2 or later and gh, logged in as a repository admin.
set -uo pipefail

REQUIRED_CHECKS=(python integration ui hygiene) # the job ids in ci.yml and pr-hygiene.yml

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_repo_protection.sh [options]

  --repo OWNER/NAME        repository (default: the one gh finds from the git remote)
  --branch NAME            protected branch (default: main)
  --approvals N            approving reviews a pull request needs (default: 1)
  --no-code-owner-review   do not require a review from a code owner
  --dry-run                print the requests without sending them
  -h, --help               show this help

While one person holds every role (docs/build/operator-decisions.md OD-6), run it with
  --approvals 0 --no-code-owner-review
because GitHub never lets the author of a pull request approve it, and every pull request
is opened from that person's account.
EOF
}

repo=""
branch="main"
approvals=1
code_owner_review=true
dry_run=false

need_value() {
  if [ "$2" -lt 2 ]; then
    echo "$1 needs a value" >&2
    usage >&2
    exit 2
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) need_value "$1" $#; repo="$2"; shift 2 ;;
    --repo=*) repo="${1#*=}"; shift ;;
    --branch) need_value "$1" $#; branch="$2"; shift 2 ;;
    --branch=*) branch="${1#*=}"; shift ;;
    --approvals) need_value "$1" $#; approvals="$2"; shift 2 ;;
    --approvals=*) approvals="${1#*=}"; shift ;;
    --no-code-owner-review) code_owner_review=false; shift ;;
    --dry-run) dry_run=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -n "${CLAUDECODE:-}" ] && [ "$dry_run" != true ]; then
  echo "Refusing to run inside Claude Code: repository settings are changed by a person with" >&2
  echo "admin rights, in their own terminal (CLAUDE.md rule 8). --dry-run only prints the requests." >&2
  exit 2
fi

case "$approvals" in
  [0-6]) ;;
  *) echo "--approvals must be a number from 0 to 6, got '$approvals'" >&2; exit 2 ;;
esac
if ! [[ "$branch" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "--branch: unexpected branch name '$branch'" >&2
  exit 2
fi
if [ -z "$repo" ]; then
  if ! repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"; then
    echo "Could not find the repository with gh; pass --repo OWNER/NAME." >&2
    exit 2
  fi
fi
if ! [[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "--repo must look like OWNER/NAME, got '$repo'" >&2
  exit 2
fi

checks=""
for check in "${REQUIRED_CHECKS[@]}"; do
  checks="${checks:+$checks, }{\"context\": \"$check\"}"
done
protection="$(
  cat <<EOF
{
  "required_status_checks": {"strict": false, "checks": [$checks]},
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": $code_owner_review,
    "required_approving_review_count": $approvals
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
)"
secret_scanning='{"security_and_analysis": {"secret_scanning": {"status": "enabled"}, "secret_scanning_push_protection": {"status": "enabled"}}}'
codeql='{"state": "configured"}'

changed=0
not_changed=0
report=""

# step <description> <method> <API path> [JSON body]
step() {
  local what="$1" method="$2" path="$3" body="${4:-}" output reason status
  if [ "$dry_run" = true ]; then
    echo "WOULD SEND: $method $path   ($what)"
    if [ -n "$body" ]; then printf '%s\n' "$body"; fi
    return 0
  fi
  if [ -n "$body" ]; then
    output="$(printf '%s' "$body" | gh api --method "$method" -H "Accept: application/vnd.github+json" "$path" --input - 2>&1)"
  else
    output="$(gh api --method "$method" -H "Accept: application/vnd.github+json" "$path" 2>&1)"
  fi
  status=$?
  if [ "$status" -eq 0 ]; then
    changed=$((changed + 1))
    report="${report}  CHANGED      ${what}"$'\n'
    echo "CHANGED: $what"
  else
    not_changed=$((not_changed + 1))
    reason="$(printf '%s\n' "$output" | grep '^gh: ' | tail -n 1 | sed 's/^gh: //')"
    if [ -z "$reason" ]; then reason="$(printf '%s\n' "$output" | tail -n 1)"; fi
    report="${report}  NOT CHANGED  ${what}: ${reason}"$'\n'
    echo "NOT CHANGED: $what: $reason"
  fi
}

reviews="$approvals approving review(s)"
if [ "$code_owner_review" = true ]; then reviews="$reviews including a code owner"; fi
echo "Repository: $repo (branch $branch)"
if [ "$dry_run" = true ]; then echo "Dry run: nothing is sent to GitHub."; fi

step "branch protection on $branch: pull request with $reviews, stale approvals dismissed, checks ${REQUIRED_CHECKS[*]}, admins included, no force pushes or deletion" \
  PUT "repos/$repo/branches/$branch/protection" "$protection"
step "private vulnerability reporting" PUT "repos/$repo/private-vulnerability-reporting"
step "secret scanning with push protection" PATCH "repos/$repo" "$secret_scanning"
step "CodeQL default setup" PATCH "repos/$repo/code-scanning/default-setup" "$codeql"
step "Dependabot alerts" PUT "repos/$repo/vulnerability-alerts"
step "Dependabot security updates" PUT "repos/$repo/automated-security-fixes"

if [ "$dry_run" = true ]; then
  exit 0
fi
echo
echo "Summary for $repo: $changed changed, $not_changed not changed"
printf '%s' "$report"
if [ "$not_changed" -gt 0 ]; then
  echo "See docs/build/ci.md for what the GitHub plan allows and the interim controls."
  exit 1
fi
exit 0
