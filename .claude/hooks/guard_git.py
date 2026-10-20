#!/usr/bin/env python3
"""PreToolUse(Bash) hook: keep git pushes on milestone branches and merges in one exact form.

Blocks (exit 2, reason on stderr):
- force pushes of any kind, and pushes whose destination is not a p<phase>/ branch (main,
  tags, HEAD on main, deletions, all-branch, mirror and follow-tags pushes);
- every `gh pr merge` except `gh pr merge <number> --merge`, optionally with
  `--repo <owner>/<name>`, `--subject <text>` and `--body <text>`; and every `gh pr merge`
  at all inside a subagent (the hook input carries `agent_id`), so milestone builders never
  merge and only the main orchestrating session can (docs/build/operator-decisions.md
  OD-2, OD-3 and OD-9);
- `gh api` calls other than GET that merge, create, move or delete refs, commit files, post
  CI results, or change protection, rulesets, releases or settings;
- `gh repo edit|delete|rename|archive|unarchive|sync`, `gh release create|delete|edit`,
  `gh secret|variable set|delete|remove`, `gh workflow enable|disable`,
  `gh alias set|import`, `gh pr update-branch --rebase` and `gh pr close --delete-branch`;
- any of these commands where the hook cannot check it (inside quotes, `bash -c` or
  `$(...)`): run it as a simple command of its own, and pass text that mentions one with
  `git commit -F <file>` or `--body-file <file>`.
Everything else passes (exit 0). Standard library only; runs on Python 3.9 or later.
"""

import json
import os
import re
import shlex
import subprocess
import sys

BRANCH_OK = re.compile(r"^p\d+/[A-Za-z0-9._/-]+$")
OPERATORS = {"&&", "||", ";", "|", "&", "\n"}
FORCE_FLAGS = {
    "-f",
    "--force",
    "--mirror",
    "--all",
    "--branches",
    "--tags",
    "--follow-tags",
    "--delete",
    "-d",
    "--prune",
}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
WRAPPERS = {"command", "builtin", "exec", "nohup", "time", "noglob"}
ENV_VALUE_OPTIONS = {"-u", "-C", "-S", "--unset", "--chdir", "--split-string"}
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PR_NUMBER = re.compile(r"^[0-9]+$")
MERGE_USAGE = (
    "only `gh pr merge <number> --merge` (optionally with --repo <owner>/<name>, "
    "--subject <text>, --body <text>) is allowed"
)
MERGE_VALUE_FLAGS = {"--repo", "--subject", "--body"}
API_VALUE_FLAGS = {
    "-X",
    "--method",
    "-f",
    "--raw-field",
    "-F",
    "--field",
    "-H",
    "--header",
    "--input",
    "-q",
    "--jq",
    "-t",
    "--template",
    "-p",
    "--preview",
    "--cache",
    "--hostname",
}
API_BODY_FLAGS = {"-f", "--raw-field", "-F", "--field", "--input"}
API_BLOCKED_PATHS = re.compile(
    r"^repos/[^/]+/[^/]+/?$"
    r"|/(merges|merge-upstream|transfer|rulesets|releases|contents|statuses|check-runs"
    r"|check-suites|collaborators|teams|hooks|keys|environments|pages|topics|autolinks"
    r"|interaction-limits|invitations|vulnerability-alerts|automated-security-fixes"
    r"|private-vulnerability-reporting|secret-scanning|properties)(/|$)"
    r"|/pulls/[^/]+/merge$|/git/refs?(/|$)|/protection(/|$)|/branches/.+/rename$"
    r"|/(actions|dependabot|codespaces)/(secrets|variables|permissions|oidc)(/|$)"
    r"|/actions/workflows/[^/]+/(enable|disable)$|/code-scanning/default-setup"
    r"|^(orgs|user|users|teams|enterprises|organizations|admin)(/|$)"
)
API_BLOCKED_MUTATIONS = re.compile(
    r"\b(mergePullRequest|enablePullRequestAutoMerge|mergeBranch|updatePullRequestBranch"
    r"|createCommitOnBranch|(create|update|delete)Refs?|(create|update)CheckRun"
    r"|createCheckSuite|(create|update|delete)BranchProtectionRule"
    r"|(create|update|delete)RepositoryRuleset"
    r"|(update|archive|unarchive|delete|transfer)Repository\w*"
    r"|(update|delete)(Organization|Enterprise|Teams?)\w*)\b"
)
GH_BLOCKED = {
    "repo": {"edit", "delete", "rename", "archive", "unarchive", "sync"},
    "release": {"create", "delete", "edit"},
    "secret": {"set", "delete", "remove"},
    "variable": {"set", "delete", "remove"},
    "workflow": {"enable", "disable"},
    "alias": {"set", "import"},
}
GH_PR_GUARDED = {"merge", "update-branch", "close"}
_REPO_FLAG = r"(?:\s+(?:-R|--repo)(?:\s+|=)?\S+)*"
RAW_GUARDED = re.compile(
    r"\bgit(?:\s+(?:-C|-c|--git-dir|--work-tree|--namespace|--config-env)\s+\S+|\s+-\S+)*"
    r"\s+push\b"
    r"|\bgh\s+pr" + _REPO_FLAG + r"\s+(?:merge|update-branch|close)\b"
    r"|\bgh\s+api\b"
    r"|\bgh\s+(?:repo|release|secret|variable|workflow|alias)" + _REPO_FLAG + r"\s+[a-z-]+\b"
)


def block(reason):
    sys.stderr.write("Blocked by .claude/hooks/guard_git.py: " + reason + "\n")
    sys.exit(2)


def split_commands(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    commands, current = [], []
    for token in lexer:
        if token in OPERATORS or set(token) <= set("&|;"):
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands


def current_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def check_push(args, cwd):
    positional = []
    for arg in args:
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in FORCE_FLAGS or name.startswith("--force"):
                block("force, delete, mirror, tag and all-branch pushes are blocked (" + arg + ")")
        elif arg.startswith("-") and len(arg) > 1:
            if arg in FORCE_FLAGS or "f" in arg[1:] or "d" in arg[1:]:
                block("force and delete pushes are not allowed (" + arg + ")")
        else:
            positional.append(arg)
    refspecs = positional[1:]
    if not refspecs:
        branch = current_branch(cwd)
        if not BRANCH_OK.match(branch):
            block("a plain push from branch '" + branch + "' would not go to a p<phase>/ branch")
        return
    for spec in refspecs:
        if spec.startswith("+"):
            block("forced refspec '" + spec + "' is not allowed")
        src, _, dst = spec.partition(":")
        if ":" not in spec:
            dst = src
        if src == "" or dst == "":
            block("deleting a remote branch is not allowed ('" + spec + "')")
        if dst == "HEAD":
            dst = current_branch(cwd)
        dst = dst[len("refs/heads/") :] if dst.startswith("refs/heads/") else dst
        if not BRANCH_OK.match(dst):
            block("push destination '" + dst + "' is not a p<phase>/ milestone branch")


def check_merge(args, in_subagent):
    if in_subagent:
        block(
            "subagents never merge (OD-3); only the main orchestrating session runs "
            "`gh pr merge <number> --merge`"
        )
    seen, positional, i = set(), [], 0
    while i < len(args):
        arg = args[i]
        name, eq, value = arg.partition("=")
        if name in MERGE_VALUE_FLAGS:
            if not eq:
                i += 1
                value = args[i] if i < len(args) else ""
            if name in seen or (name == "--repo" and not REPO_NAME.match(value)):
                block(MERGE_USAGE + " (" + name + ")")
            seen.add(name)
        elif arg == "--merge" and arg not in seen:
            seen.add(arg)
        elif arg.startswith("-"):
            block(MERGE_USAGE + "; '" + arg + "' is not")
        else:
            positional.append(arg)
        i += 1
    if "--merge" not in seen or len(positional) != 1 or not PR_NUMBER.match(positional[0]):
        block(MERGE_USAGE)


def check_api(args):
    method, endpoint, has_body, unseen_body, texts, i = None, None, False, False, [], 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            name, eq, value = arg.partition("=")
            if name in API_VALUE_FLAGS and not eq:
                i += 1
                value = args[i] if i < len(args) else ""
        elif arg.startswith("-") and len(arg) > 1:
            name, value = arg[:2], arg[2:]
            if name in API_VALUE_FLAGS and not value:
                i += 1
                value = args[i] if i < len(args) else ""
            elif name not in API_VALUE_FLAGS and value:
                block("combined short flags in gh api cannot be checked ('" + arg + "')")
        else:
            if endpoint is None:
                endpoint = arg
            i += 1
            continue
        if name in ("-X", "--method"):
            method = value.upper()
        if name in API_BODY_FLAGS:
            has_body = True
            from_file = name == "--input" or (name in ("-F", "--field") and "=@" in value)
            unseen_body = unseen_body or from_file
            texts.append(value)
        i += 1
    method = method or ("POST" if has_body else "GET")
    if method in ("GET", "HEAD") or endpoint is None:
        return
    path = re.sub(r"^(https://api\.github\.com)?/+", "", endpoint).split("?", 1)[0]
    if path == "graphql":
        if unseen_body:
            block("a GraphQL query read from a file or stdin cannot be checked")
        if API_BLOCKED_MUTATIONS.search(" ".join(texts)):
            block("this GraphQL mutation merges, moves refs or changes protection or settings")
    elif API_BLOCKED_PATHS.search(path):
        block(
            "gh api " + method + " " + path + " merges, moves or deletes refs, commits files, "
            "posts CI results or changes protection or settings; the operator does that"
        )


def check_gh(args, in_subagent):
    """Check one gh command; return 1 if it belongs to a guarded family, else 0."""
    if not args:
        return 0
    group, rest, before = args[0], args[1:], []
    while rest and (rest[0] in ("-R", "--repo") or rest[0].startswith(("--repo=", "-R"))):
        take = 2 if rest[0] in ("-R", "--repo") else 1
        before, rest = before + rest[:take], rest[take:]
    sub = rest[0] if rest else ""
    tail = before + rest[1:]
    if group == "api":
        check_api(args[1:])
    elif group == "pr" and sub == "merge":
        check_merge(tail, in_subagent)
    elif group == "pr" and sub == "update-branch" and "--rebase" in tail:
        block("gh pr update-branch --rebase rewrites the branch, like a force-push")
    elif group == "pr" and sub == "close" and ("-d" in tail or "--delete-branch" in tail):
        block("deleting a remote branch is not allowed (gh pr close --delete-branch)")
    elif sub in GH_BLOCKED.get(group, ()):
        block("gh " + group + " " + sub + " changes repository settings, tags or history")
    guarded = group == "api" or group in GH_BLOCKED or (group == "pr" and sub in GH_PR_GUARDED)
    return 1 if guarded else 0


def strip_prefix(tokens):
    """Drop leading VAR=value assignments and wrappers such as env, command and nohup."""
    while tokens:
        program = os.path.basename(tokens[0])
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
            tokens = tokens[1:]
        elif program in WRAPPERS or program == "env":
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-"):
                takes_value = program == "env" and tokens[0] in ENV_VALUE_OPTIONS
                tokens = tokens[2:] if takes_value else tokens[1:]
        else:
            break
    return tokens


def check_command(tokens, cwd, in_subagent):
    """Check one simple command; return 1 if it was a guarded command that passed, else 0."""
    tokens = strip_prefix(tokens)
    if not tokens:
        return 0
    program = os.path.basename(tokens[0])
    if program == "git":
        i = 1
        while i < len(tokens) and tokens[i].startswith("-"):
            option, _, attached = tokens[i].partition("=")
            value = attached or (tokens[i + 1] if i + 1 < len(tokens) else "")
            if option in ("-c", "--config-env") and value.lower().startswith("alias."):
                block("git aliases defined on the command line are not allowed")
            i += 2 if tokens[i] in GIT_VALUE_OPTIONS else 1
        if i < len(tokens) and tokens[i] == "push":
            check_push(tokens[i + 1 :], cwd)
            return 1
    elif program == "gh":
        return check_gh(tokens[1:], in_subagent)
    return 0


def parse(command):
    """Token lists per simple command, or None when the shell syntax is too complex."""
    try:
        commands = []
        for line in command.replace("\\\n", " ").splitlines():
            commands.extend(split_commands(line))
        return commands
    except ValueError:
        pass
    try:
        return split_commands(command)
    except ValueError:
        return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    if "git" not in command and "gh" not in command:
        return 0
    in_subagent = bool(data.get("agent_id"))
    guarded = len(RAW_GUARDED.findall(re.sub(r"[\\'\"]", "", command)))
    commands = parse(command)
    if commands is None:
        if guarded:
            block("could not parse a command that pushes, merges or calls gh api; simplify it")
        return 0
    checked = 0
    for tokens in commands:
        checked += check_command(tokens, data.get("cwd"), in_subagent)
    if guarded > checked:
        block(
            "a push, merge or gh api/repo/release command appears where it cannot be checked "
            "(quoted text, bash -c, $(...)); run it as a simple command of its own, and pass "
            "text that mentions one with git commit -F <file> or --body-file <file>"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
