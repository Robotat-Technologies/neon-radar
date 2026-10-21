"""Latin-side rules for Arabic-origin names and consonant skeletons (research note 5.4, 5.5)."""

from __future__ import annotations

import re


def _words(*parts: str) -> frozenset[str]:
    return frozenset(" ".join(parts).split())


ARTICLES = _words("al el ul ar ur as us ash ush at ut ad ud az uz an un")
NASAB = _words("bin ibn bint binti binte ben ould wuld")
HONORIFICS = _words("sheikh shaikh shaykh sheik haji hajji hajj alhaji alhaj haj")
_ABD = _words(
    "abd abdu abdul abdel abdal abdol abdil abdur abdar abdus abdas abdush abdash abdun abdan ",
    "abdud abdad abdut abdat abduz abdaz",
)
_ABD_JOINED = re.compile(
    r"^abd(?:ul|ol|el|al|il|ur|ar|us|as|ush|ash|ud|ad|ut|at|uz|az|un|an|u|e|a|o)?([a-z]{3,})$"
)
_ALLAH = _words("allah ullah ulla alla lah llah olah ollah ullahi")
_JOINED_ARTICLE = re.compile(r"^(?:al|el)([a-z]{3,})$")


def _abd(root: str) -> str:
    return "abdallah" if root in _ALLAH else "abd" + root


def latin_rules(tokens: list[str]) -> list[str]:
    """Join Abd and Abu compounds, drop articles and nasab particles (not as the first token)."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        has_next = i + 1 < len(tokens)
        if token in _ABD and has_next:
            j = i + 1
            if tokens[j] in ARTICLES and j + 1 < len(tokens):
                j += 1
            out.append(_abd(tokens[j]))
            i = j + 1
            continue
        joined = _ABD_JOINED.match(token)
        if joined and token not in ("abdou", "abdi"):
            out.append(_abd(joined.group(1)))
            i += 1
            continue
        if token in ("abu", "abou", "abo") and has_next:
            j = i + 1
            if tokens[j] in ARTICLES and j + 1 < len(tokens):
                j += 1
            out.append("abu" + tokens[j])
            i = j + 1
            continue
        if token in ARTICLES and len(tokens) > 1:
            i += 1
            continue
        if token in NASAB and i > 0:
            i += 1
            continue
        out.append(token)
        i += 1
    return out


def latin_skeleton(token: str) -> str:
    text = token.lower()
    for a, b in (
        ("kh", "k"),
        ("gh", "g"),
        ("sh", "s"),
        ("ch", "s"),
        ("dj", "j"),
        ("th", "t"),
        ("dh", "d"),
        ("ph", "f"),
        ("q", "k"),
        ("c", "k"),
        ("x", "ks"),
    ):
        text = text.replace(a, b)
    text = re.sub(r"(?<=[aeiou])h$", "", text)
    text = re.sub(r"[aeiouyw']", "", text)
    return re.sub(r"(.)\1+", r"\1", text)


def joined_article_root(token: str) -> str | None:
    """For a token like "alattar", the root after a joined article ("attar"), else None."""
    match = _JOINED_ARTICLE.match(token)
    return match.group(1) if match else None
