"""Human-only commands (PHASE-2.md M2.2 deliverable 13, G10).

`require_terminal(command)` stops a command when standard input is not a terminal, so only a
person at a keyboard labels pairs, reviews possible matches or browses real data
(`er label` and `er review` in M2.10c, `api serve --real` in M2.12). Never wrap such a command
in `script`, `expect`, `unbuffer` or `faketty` to get past it.
"""

import sys


class TerminalRequired(Exception):
    """Raised inside `redact.guard`, which prints the message and exits with code 2."""

    exit_code = 2
    counts_only = True  # a fixed text that names the command only


def require_terminal(command: str) -> None:
    stdin = sys.stdin
    if stdin is None or not stdin.isatty():
        raise TerminalRequired(
            f"neonradar {command} is for a person at a terminal, and standard input is not a"
            " terminal here, so it does not run (PHASE-2.md G10)"
        )
