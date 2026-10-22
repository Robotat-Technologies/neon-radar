#!/usr/bin/env python3
"""PreToolUse hook: keep real records out of the agent's context (PHASE-2.md G9, M2.0).

Bash: a command line that names data/cache/real or data/cache/spikes (directly, through a
glob, through any path containing cache/real or cache/spikes, or as the current folder,
which cd and pushd change as the line runs) may only run listing and housekeeping programs
(ls, du, wc, stat, find without actions, mkdir, rm, ...), the git subcommands in GIT_SAFE
without the flags that read files outside the index, and the project's own commands
(uv run neonradar ..., make ...), which print counts only. Nobody may cd into data/,
data/cache/ or a real-data folder, recursive readers (grep -r, rg --no-ignore, tar, zip,
rsync, cp -r, find -exec) may not run over a folder that holds real data, and git never
runs with --no-index, --untracked or --no-exclude-standard. A command that names the real
Neo4j instance (neo4j-real, database realdata, ports 7475, 7688 and 8001, NR_NEO4J_REAL_*,
NEO4J_REAL_PASSWORD) may only be uv run neonradar, make, or docker compose up, start, stop,
down or ps. Human-only commands (neonradar er label, er review, api serve --real) and the
terminal wrappers script, expect, unbuffer and faketty are always blocked. Shell downloaders
(curl, wget, http, https, xh, aria2c) follow the WebFetch rule below, and docker compose
config (without --quiet or a listing flag) and docker inspect are blocked, because they
print passwords from .env.
Read, Grep and Glob: no path, glob or pattern may name data/cache/real, data/cache/spikes,
data/cache/holdout or data/cache/heldout.
WebFetch: list, register and leak data files and pages about real people are blocked;
schemas (.xsd), API descriptions (swagger, openapi) and documentation pass.
Neo4j MCP: allowed, because the default instance holds synthetic data only (PHASE-2.md
M2.11), unless .mcp.json names the real instance.
Holdout (PHASE-3.md G11, M3.0): data/cache/holdout, where the human holdout run writes, is
protected like data/cache/real, and more strictly: a command line that names it (a path in
it, or it as the current folder) may only run the read-only git subcommands, which see
tracked files only; listing programs and the project's own commands are blocked too.
neonradar eval run --split test (in any position, with = or a space) is human-only.
Held-out questions and models (PHASE-4.md G15, G16, M4.0): data/cache/heldout is closed as
data/cache/holdout is. Human-only: copilot bench with --file, any copilot command with
--model-router, copilot model-check unless its last --digest is empty, every ollama command
(also through a launcher or a shell script), docker compose with the llm profile or naming
its ollama service, and NR_COPILOT_MODEL_ROUTER set on a command line to anything but off.
Case: macOS and Windows file systems ignore case, so data/cache/REAL is data/cache/real.
Every path and mark is compared casefolded, and the human-only commands are matched
without regard to case (the program name too: NeonRadar runs neonradar there).
Exit 2 blocks the call and shows the reason. Standard library only; Python 3.9 or later.
It stops accidents, not a determined person: the permission rules, CLAUDE.md and the people
who run the project remain responsible.
"""

import fnmatch
import json
import os
import re
import shlex
import sys
from urllib.parse import urlsplit

PROTECTED = ("data/cache/real", "data/cache/spikes", "data/cache/holdout", "data/cache/heldout")
MARKS = ("cache/real", "cache/spikes", "cache/holdout", "cache/heldout")
# The human holdout run's output (PHASE-3.md G11) and the held-out questions (PHASE-4.md G16):
# closed even to listing programs.
CLOSED = ("data/cache/holdout", "data/cache/heldout")
CLOSED_MARKS = ("cache/holdout", "cache/heldout")
ANCESTORS = (".", "data", "data/cache")


def words(*parts):
    return frozenset(" ".join(parts).split())


OPERATORS = frozenset(["&&", "||", ";", "|", "&", "\n", "(", ")"])
SAFE = words(
    "ls du df wc stat file mkdir rm rmdir touch test [ echo printf true false sleep date pwd",
    "which type find",
)
GIT_SAFE = words("status log diff show grep ls-files blame rev-parse check-ignore branch")
GIT_NEVER = ("--no-index", "--untracked", "--no-exclude-standard")
GIT_NOT_ON_REAL = ("-F", "--file", "-f", "--pathspec-from-file")
TEXT_FLAGS = words("-m --message --title -t --body -b --notes --subject")
FIND_ACTIONS = words("-exec -execdir -ok -okdir -fprint -fprint0 -fprintf -fls")
INTERPRETERS = words(
    "python python3 node ruby perl bash sh zsh duckdb sqlite3 uv uvx jq awk gawk sed"
)
WRAPPERS = words("script expect unbuffer faketty")
FETCHERS = words("curl wget http https xh aria2c")
CONFIG_SAFE = words("--quiet -q --services --profiles --volumes --images")
BARE_HOST = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?::[0-9]+)?(?:/|$)")
COMPOSE_OK = words("up start stop down ps")
COMPOSE_VALUE_OPTIONS = words(
    "-f --file -p --project-name --profile --env-file --project-directory --ansi --progress",
    "--parallel",
)
UV_VALUE_OPTIONS = words(
    "--env-file --with --python -p --package --directory --project --group --extra --index"
)
REAL_INSTANCE = re.compile(
    r"neo4j-real|\brealdata\b|NR_NEO4J_REAL|NEO4J_REAL_PASSWORD"
    r"|(?<![0-9])(?:7475|7688|8001)(?![0-9])"
)
HUMAN_ONLY = re.compile(
    r"\bneonradar(?:_cli)?\b(?:\s+-\S+)*\s+(?:er\s+(?:-\S+\s+)*(?:label|review)\b"
    r"|api\s+serve\b[^;&|]*?\s--real\b"
    r"|eval\s+(?:-\S+\s+)*run\b[^;&|]*?\s--split(?:=|\s+)test\b)",
    re.IGNORECASE,
)
# PHASE-4.md G15 and G16: the held-out run and the model are human-only (check_models)
MODEL_SCRIPT = re.compile(
    r"(?m)(?:^|[;&|(`'\"]|\b(?:exec|sudo|nohup|env|command)\s)[ \t]*ollama\s"
    r"|\bneonradar(?:_cli)?\b(?:[ \t]+-\S+)*[ \t]+copilot\b[^\n;&|]*?"
    r"(?:\s--file\b|\s--model-router\b|\smodel-check\b)"
    r"|--profile(?:=|[ \t]+)['\"]?(?:llm|\*)|COMPOSE_PROFILES=\S*(?:llm|\*)"
    r"|NR_COPILOT_MODEL_ROUTER=(?!['\"]?(?:0|false|off|no|n|f)?['\"]?(?:\s|$))",
    re.IGNORECASE,
)
SHELLS = words("bash sh zsh dash ksh")
LAUNCHERS = words(
    "env nohup exec sudo doas timeout nice time xargs command watch caffeinate stdbuf"
)
COMPOSE_STARTS = words("up start run create pull restart exec")
ROUTER_OFF = ("", "0", "false", "off", "no", "n", "f")
MODEL_REASON = "the held-out run and models are human-only (PHASE-4.md G15, G16): ask a human"
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
WEB_DATA = (
    # (host, path prefix, mode): "all" blocks every path under the prefix, "files" only data files
    ("sanctionslist.fcdo.gov.uk", "/", "all"),
    ("sanctionslistservice.ofac.treas.gov", "/", "all"),
    ("treasury.gov", "/ofac/downloads/", "all"),
    ("scsanctions.un.org", "/", "all"),
    ("webgate.ec.europa.eu", "/fsd/fsf/public/files", "all"),
    ("download.companieshouse.gov.uk", "/", "files"),
    ("api.company-information.service.gov.uk", "/", "all"),
    ("find-and-update.company-information.service.gov.uk", "/company/", "all"),
    ("find-and-update.company-information.service.gov.uk", "/officers/", "all"),
    ("find-and-update.company-information.service.gov.uk", "/search", "all"),
    ("goldencopy.gleif.org", "/storage/", "all"),
    ("goldencopy.gleif.org", "/api/v2/golden-copies/", "files"),
    ("api.gleif.org", "/api/", "all"),
    ("offshoreleaks-data.icij.org", "/", "all"),
    ("offshoreleaks.icij.org", "/nodes/", "all"),
    ("offshoreleaks.icij.org", "/search", "all"),
    ("data.opensanctions.org", "/", "all"),
    ("www.opensanctions.org", "/entities/", "all"),
    ("www.opensanctions.org", "/search", "all"),
    ("members-api.parliament.uk", "/api/", "all"),
)
DATA_FILE = re.compile(r"\.(?:zip|gz|bz2|csv|tsv|txt|xml|json|jsonl|xlsx?|ods|odt|parquet)$", re.I)


def marked(text):
    """True when `text` names a protected folder by its mark, in any letter case."""
    folded = text.casefold()
    return any(m in folded for m in MARKS)


def block(reason):
    sys.stderr.write("Blocked by .claude/hooks/guard_real_data.py: " + reason + "\n")
    sys.exit(2)


def project_dir():
    return (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).rstrip("/")


def strip_heredocs(command):
    """Remove heredoc bodies; block a body that feeds an interpreter and names real data."""
    lines = command.split("\n")
    kept, i = [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        match = HEREDOC.search(line)
        i += 1
        if not match:
            continue
        body = []
        while i < len(lines) and lines[i].strip() != match.group(2):
            body.append(lines[i])
            i += 1
        if i < len(lines):
            kept.append(lines[i])
            i += 1
        before = line[: match.start()]
        tokens = re.findall(r"[A-Za-z0-9_.\-/]+", before.split("|")[-1])
        names = {os.path.basename(w) for w in tokens} & INTERPRETERS
        text = "\n".join(body)
        if names and (
            marked(text)
            or REAL_INSTANCE.search(text)
            or HUMAN_ONLY.search(text)
            or MODEL_SCRIPT.search(text)
        ):
            block(
                "a script fed to " + ", ".join(sorted(names)) + " names real data, the real "
                "Neo4j instance, the held-out questions, a model command or a human-only command"
            )
    return "\n".join(kept)


def split_commands(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    commands, current = [], []
    for token in lexer:
        # an empty argument ("") is a token, not an operator (PHASE-4.md M4.0: --digest "")
        if token in OPERATORS or (token and set(token) <= set("&|;()")):
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands


def parse(command):
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


def absolute(value, cwd):
    """The value as a normalised absolute path, resolved against cwd (or the project)."""
    root = project_dir()
    value = value.replace("${CLAUDE_PROJECT_DIR}", root).replace("$CLAUDE_PROJECT_DIR", root)
    if value.startswith("~"):
        value = os.path.expanduser(value)
    if not value.startswith("/"):
        value = os.path.join(cwd or root, value)
    return os.path.normpath(value)


def relative(token, cwd):
    """The token as a path relative to the project directory, casefolded, or None. File
    systems that ignore case (macOS, Windows) open data/cache/REAL as data/cache/real, so
    every comparison with a protected folder works on the casefolded path."""
    value = token.split("=", 1)[1] if token.startswith("-") and "=" in token else token
    if not value or value.startswith("-") or "\n" in value:
        return None
    root = project_dir().casefold()
    value = absolute(value, cwd).casefold()
    if value == root:
        return "."
    if value.startswith(root + "/"):
        return value[len(root) + 1 :]
    return None


def inside(rel, folders=PROTECTED):
    return rel is not None and any(rel == p or rel.startswith(p + "/") for p in folders)


def names_holdout(token, cwd):
    """True when a token names data/cache/holdout or data/cache/heldout, or something inside
    either (PHASE-3.md G11, PHASE-4.md G16)."""
    folded = token.casefold()
    return any(m in folded for m in CLOSED_MARKS) or inside(relative(token, cwd), CLOSED)


def glob_reaches(pattern, protected, double_star=True):
    """True when a glob's leading segments can match the protected folder's segments."""
    pat, prot = pattern.split("/"), protected.split("/")
    for i, segment in enumerate(prot):
        if i >= len(pat):
            return False
        if pat[i] == "**":
            return double_star or i > 0
        if not fnmatch.fnmatch(segment, pat[i]):
            return False
    return True


def touches(token, cwd):
    """True when a token names a protected folder, something inside one, or a glob that can."""
    if marked(token):
        return True
    rel = relative(token, cwd)
    if rel is None:
        return False
    if inside(rel):
        return True
    return any(ch in rel for ch in "*?[") and any(glob_reaches(rel, p) for p in PROTECTED)


def checked_tokens(tokens):
    """Tokens that may be paths: for git and gh, values of message-like flags are text."""
    if program(tokens)[0] not in ("git", "gh"):
        return list(tokens)
    out, skip = [], False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in TEXT_FLAGS:
            skip = True
            continue
        if any(token.startswith(flag + "=") for flag in TEXT_FLAGS if flag.startswith("--")):
            continue
        out.append(token)
    return out


def program(tokens):
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens = tokens[1:]
    return (os.path.basename(tokens[0]), tokens[1:]) if tokens else ("", [])


def uv_run_target(args):
    """For `uv run [options] TARGET ...`, the target program, else None."""
    if args[:1] != ["run"]:
        return None
    rest, skip = args[1:], False
    for arg in rest:
        if skip:
            skip = False
            continue
        if arg in UV_VALUE_OPTIONS:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return os.path.basename(arg)
    return None


def compose_subcommand(args):
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in COMPOSE_VALUE_OPTIONS:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def project_command(name, args):
    return name in ("make", "neonradar") or (name == "uv" and uv_run_target(args) == "neonradar")


def allowed_on_real(name, args):
    if name in SAFE:
        return not (name == "find" and any(a in FIND_ACTIONS for a in args))
    if project_command(name, args):
        return True
    if name == "git":
        if any(a in GIT_NOT_ON_REAL or a.split("=", 1)[0] in GIT_NOT_ON_REAL for a in args):
            return False
        sub = [a for a in args if not a.startswith("-")]
        return bool(sub) and sub[0] in GIT_SAFE
    return False


def allowed_on_holdout(name, args):
    """Only the read-only git subcommands, which see tracked files (the holdout folder is
    ignored), may run on a line that names data/cache/holdout (PHASE-3.md G11)."""
    return name == "git" and allowed_on_real(name, args)


def allowed_on_real_instance(name, args):
    if project_command(name, args):
        return True
    if name == "git":  # git reads tracked files and history only (GIT_NEVER is checked first)
        sub = [a for a in args if not a.startswith("-")]
        return bool(sub) and sub[0] in GIT_SAFE
    if name == "docker" and args[:1] == ["compose"]:
        return compose_subcommand(args[1:]) in COMPOSE_OK
    if name == "docker-compose":
        return compose_subcommand(args) in COMPOSE_OK
    return False


def recursive(name, args):
    def short_flags(letters):
        return any(re.match(r"^-[a-zA-Z]+$", a) and any(c in a for c in letters) for a in args)

    if name in ("grep", "egrep", "fgrep"):
        return short_flags("rR") or any(
            a in ("--recursive", "--dereference-recursive") for a in args
        )
    if name == "rg":
        return any(
            a in ("--no-ignore", "--no-ignore-vcs", "-u", "-uu", "-uuu", "--unrestricted")
            for a in args
        )
    if name in ("ag", "ack", "tar", "zip", "rsync", "scp"):
        return True
    if name == "cp":
        return short_flags("rRa") or any(a in ("--recursive", "--archive") for a in args)
    if name == "find":
        return any(a in FIND_ACTIONS for a in args)
    return False


def walk(commands, cwd):
    """Each command with the folder it runs in, following cd, pushd and popd on the line."""
    root = project_dir()
    here = absolute(cwd, None) if cwd else root
    previous, stack, out = here, [], []
    for tokens in commands:
        name, args = program(tokens)
        out.append((tokens, name, args, here))
        targets = [a for a in args if not a.startswith("-")]
        if name in ("cd", "pushd"):
            if name == "pushd":
                stack.append(here)
            if not targets or targets[0] == "~":
                new = os.path.expanduser("~")
            elif targets[0] == "-":
                new = previous
            else:
                new = absolute(targets[0], here)
            previous, here = here, new
        elif name == "popd" and stack:
            previous, here = here, stack.pop()
    return out


def copilot_args(tokens):
    """The arguments after `neonradar [options] copilot` on a command (casefolded), or None."""
    for i, token in enumerate(tokens):
        if os.path.basename(token) not in ("neonradar", "neonradar_cli"):
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            j += 1
        if j < len(tokens) and tokens[j] == "copilot":
            return tokens[j + 1 :]
    return None


def has_flag(args, flag):
    return any(a == flag or a.startswith(flag + "=") for a in args)


def last_value(args, flag):
    """The value of the last `flag VALUE` or `flag=VALUE` in args, or None."""
    value = None
    for i, arg in enumerate(args):
        if arg == flag:
            value = args[i + 1] if i + 1 < len(args) else None
        elif arg.startswith(flag + "="):
            value = arg.split("=", 1)[1]
    return value


def check_models(tokens):
    """PHASE-4.md G15 and G16: the held-out run, the model router and the model runtime are
    human-only. Matched without regard to case, as the other human-only commands are."""
    tokens = [t.casefold() for t in tokens]
    name, args = program(tokens)
    rest = copilot_args(tokens) or []
    profiles = [b for a, b in zip(tokens, tokens[1:]) if a == "--profile"]
    profiles += [t.partition("=")[2] for t in tokens if t.startswith("--profile=")]
    for key, _, value in (t.partition("=") for t in tokens):
        if key == "compose_profiles" and {"llm", "*"} & set(value.split(",")):
            block(MODEL_REASON)
        if key == "nr_copilot_model_router" and value.strip() not in ROUTER_OFF:
            block(MODEL_REASON)
    compose = args[1:] if name == "docker" and args[:1] == ["compose"] else None
    compose = args if name == "docker-compose" else compose
    sub = compose_subcommand(compose) if compose is not None else None
    if (
        name == "ollama"
        or (name == "uv" and uv_run_target(args) == "ollama")
        or (name in LAUNCHERS and "ollama" in [os.path.basename(a) for a in args])
        or ((name in SHELLS or name == "eval") and MODEL_SCRIPT.search("\n".join(args)))
        or has_flag(rest, "--model-router")
        or ("bench" in rest and has_flag(rest, "--file"))
        or ("model-check" in rest and last_value(rest, "--digest") != "")
        or (compose is not None and {"llm", "*"} & set(profiles))
        or (sub in COMPOSE_STARTS and "ollama" in compose[compose.index(sub) + 1 :])
    ):
        block(MODEL_REASON)


def check_bash(command, cwd):
    command = strip_heredocs(command)
    commands = parse(command)
    if commands is None:
        if MODEL_SCRIPT.search(command):
            block(MODEL_REASON)
        if marked(command) or REAL_INSTANCE.search(command):
            block(
                "could not parse a command that names real data or the real Neo4j instance; "
                "use a simple ls, du or neonradar command"
            )
        return
    steps = walk(commands, cwd)
    line_touches = line_holdout = False
    for tokens, _name, _args, here in steps:
        if inside(relative(here, None)):
            line_touches = True
        if any(touches(t, here) for t in checked_tokens(tokens)):
            line_touches = True
        if inside(relative(here, None), CLOSED) or any(
            names_holdout(t, here) for t in checked_tokens(tokens)
        ):
            line_holdout = True
    for tokens, name, args, here in steps:
        text = " ".join(checked_tokens(tokens))
        if name in WRAPPERS:
            block(
                "'" + name + "' fakes a terminal; human-only commands must be run by a human "
                "in a real terminal (PHASE-2.md G10)"
            )
        if HUMAN_ONLY.search(text):
            block(
                "er label, er review, api serve --real and eval run --split test are "
                "human-only commands; ask the operator to run them in a terminal "
                "(PHASE-2.md G10, PHASE-3.md G11)"
            )
        check_models(checked_tokens(tokens))
        if name in FETCHERS:
            for arg in args:
                if "://" in arg:
                    check_url(arg, name)
                elif not arg.startswith("-") and BARE_HOST.match(arg):
                    check_url("https://" + arg, name)
        compose = None
        if name == "docker" and args[:1] == ["compose"]:
            compose = compose_subcommand(args[1:])
        elif name == "docker-compose":
            compose = compose_subcommand(args)
        if compose == "config" and not any(a in CONFIG_SAFE for a in args):
            block(
                "docker compose config prints the interpolated configuration, including "
                "passwords from .env (PHASE-1.md G6); use --quiet, --services or --profiles"
            )
        if name == "docker" and (
            args[:1] == ["inspect"] or args[:2] in (["container", "inspect"], ["volume", "inspect"])
        ):
            block("docker inspect prints container environments, including passwords from .env")
        if name in ("cd", "pushd"):
            targets = [a for a in args if not a.startswith("-")]
            if targets and (
                touches(targets[0], here) or relative(targets[0], here) in ANCESTORS[1:]
            ):
                block(
                    "do not cd into data/, data/cache/ or a real-data folder; "
                    "use paths from the project root"
                )
        if name == "git" and any(a in GIT_NEVER or a.split("=", 1)[0] in GIT_NEVER for a in args):
            block(
                "git with --no-index, --untracked or --no-exclude-standard reads files outside "
                "the index, including data/cache/; search tracked files with plain `git grep`"
            )
        if recursive(name, args):
            paths = [a for a in args if not a.startswith("-") and relative(a, here) is not None]
            if (
                name in ("grep", "egrep", "fgrep", "rg", "ag", "ack")
                and not paths[1:]
                and (name != "grep" or len(paths) <= 1)
            ):
                paths.append(".")
            if any(relative(a, here) in ANCESTORS or touches(a, here) for a in paths):
                block(
                    name + " would read into data/cache/real, data/cache/spikes, "
                    "data/cache/holdout or data/cache/heldout; use `git grep`, or name a "
                    "folder that does not contain them"
                )
        if REAL_INSTANCE.search(text) and not allowed_on_real_instance(name, args):
            block(
                "'" + name + "' on a command that names the real Neo4j instance (neo4j-real, "
                "ports 7475, 7688 and 8001). Only uv run neonradar, make and docker compose "
                "up, start, stop, down or ps may use it; the default instance (7687) and the "
                "API on port 8000 hold synthetic data"
            )
        if line_holdout and not allowed_on_holdout(name, args):
            block(
                "'" + name + "' on a command line that names data/cache/holdout, where the "
                "human holdout run writes (PHASE-3.md G11), or data/cache/heldout, where the "
                "held-out questions live (PHASE-4.md G16). Nothing but read-only git "
                "subcommands may name them; never generate, list or read a holdout world or a "
                "held-out question"
            )
        if line_touches and not allowed_on_real(name, args):
            block(
                "'" + name + "' on a command line that touches real data. Real records are read "
                "only by humans. Allowed: ls, du, wc, stat, find (no actions), rm, mkdir, "
                "git status, log, diff, show, grep, ls-files, blame, rev-parse, check-ignore, "
                "branch, uv run neonradar, make"
            )


def check_paths(tool, tool_input, cwd):
    """Read, Grep and Glob: refuse paths, globs and patterns that can reach real data."""
    keys = {"Read": ("file_path",), "Grep": ("path", "glob"), "Glob": ("path", "pattern")}[tool]
    here = absolute(cwd, None) if cwd else project_dir()
    search_root = here
    if isinstance(tool_input.get("path"), str) and tool_input["path"]:
        search_root = absolute(tool_input["path"].replace("\\", "/"), here)
    for key in keys:
        value = tool_input.get(key)
        if not isinstance(value, str) or not value:
            continue
        value = value.replace("\\", "/")
        if marked(value):
            block(
                tool + " may not name data/cache/real, data/cache/spikes, data/cache/holdout or "
                "data/cache/heldout (PHASE-2.md G9, PHASE-3.md G11, PHASE-4.md G16)"
            )
        if key == "glob":
            continue
        full = absolute(value, search_root if key == "pattern" else here)
        rel = relative(full, None)
        if marked(full) or inside(rel):
            block(
                tool + " may not read data/cache/real, data/cache/spikes, data/cache/holdout or "
                "data/cache/heldout (PHASE-2.md G9, PHASE-3.md G11, PHASE-4.md G16)"
            )
        if tool == "Grep" and key == "path" and rel in ANCESTORS[1:]:
            block("Grep over data/ or data/cache/ could reach real data; name another folder")
        if (
            rel
            and any(ch in rel for ch in "*?[")
            and any(glob_reaches(rel, p, double_star=False) for p in PROTECTED)
        ):
            block(
                tool + " pattern can reach data/cache/real, data/cache/spikes, data/cache/holdout "
                "or data/cache/heldout (PHASE-2.md G9, PHASE-3.md G11, PHASE-4.md G16)"
            )


def check_url(url, via="WebFetch"):
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        block("could not parse the URL")
        return
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    low = path.lower()
    if low.endswith(".xsd") or "swagger" in low or "openapi" in low:
        return
    for rule_host, prefix, mode in WEB_DATA:
        if host != rule_host and not host.endswith("." + rule_host):
            continue
        if not path.startswith(prefix):
            continue
        if mode == "files" and not DATA_FILE.search(path):
            continue
        block(
            via + " would bring list, register or leak data (or a page about real people) "
            "into the conversation; fetch documentation and schemas only, and let the loaders "
            "download data (PHASE-2.md G9)"
        )


def check_mcp():
    try:
        with open(os.path.join(project_dir(), ".mcp.json"), encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return
    if REAL_INSTANCE.search(text):
        block(
            ".mcp.json points the Neo4j MCP server at the real instance; it must use the "
            "default instance (bolt://localhost:7687), which holds synthetic data only"
        )


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    if tool.startswith("mcp__neo4j"):
        check_mcp()
    elif tool == "Bash":
        check_bash(str(tool_input.get("command") or ""), data.get("cwd"))
    elif tool in ("Read", "Grep", "Glob"):
        check_paths(tool, tool_input, data.get("cwd"))
    elif tool == "WebFetch":
        check_url(str(tool_input.get("url") or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
