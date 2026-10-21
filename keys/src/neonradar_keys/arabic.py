"""Arabic-script name rules (research note names-addresses.md 5.3 to 5.5, credited to the
character rules of CAMeL Tools, MIT)."""

from __future__ import annotations

import re

from neonradar_keys.text import nfkc

# Tashkeel, shadda, sukun, superscript alef and Quranic marks (research note 5.3, step 2).
_MARKS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e8\u06ea-\u06ed\u08d3-\u08ff]"
)
_MAP = str.maketrans(
    {
        **dict.fromkeys("آأإٱٲٳ", "ا"),  # alef forms
        **dict.fromkeys("ىیےئ", "ي"),  # alef maqsura, Farsi yeh, yeh barree, yeh with hamza
        "ة": "ه",  # ta marbuta
        "ؤ": "و",  # waw with hamza
        "ک": "ك",  # keheh
        **dict.fromkeys("ءـ", None),  # hamza, tatweel
        **dict.fromkeys(
            "\u200c\u200d\u200e\u200f\u061c", None
        ),  # zero-width joiners and direction marks
        **{chr(0x0660 + i): str(i) for i in range(10)},
        **{chr(0x06F0 + i): str(i) for i in range(10)},
    }
)
ARTICLE_EXCEPTIONS = frozenset({"الله", "الهام", "الياس", "اليسع"})
HONORIFICS = frozenset(
    {
        "الشيخ",
        "شيخ",
        "الشيخه",
        "الحاج",
        "حاج",
        "الحاجه",
        "الدكتور",
        "الدكتوره",
        "د",
        "المهندس",
        "المهندسه",
        "الاستاذ",
        "الاستاذه",
    }
)
NASAB = frozenset({"بن", "ابن", "بنت"})
_SKELETON = {
    "ب": "b",
    "ت": "t",
    "ث": "t",
    "ج": "j",
    "ح": "h",
    "خ": "k",
    "د": "d",
    "ذ": "d",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "s",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "z",
    "ع": "",
    "غ": "g",
    "ف": "f",
    "ق": "k",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "",
    "ي": "",
    "ا": "",
    "پ": "b",
    "چ": "j",
    "گ": "g",
    "ڤ": "f",
}


def ar_normalize(text: str) -> str:
    """NFKC; marks and tatweel removed; alef, yeh, heh and waw forms unified."""
    return _MARKS.sub("", nfkc(text)).translate(_MAP)


def arabic_rules(tokens: list[str]) -> list[str]:
    """Token rules for casefolded Arabic tokens (article detection needs the raw form)."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        raw = tokens[i]
        token = ar_normalize(raw)
        following = tokens[i + 1] if i + 1 < len(tokens) else None
        if token in ("عبد", "ابو") and following is not None:
            out.append(token + ar_normalize(following))  # same key as the joined spelling
            i += 2
            continue
        if token in NASAB and i > 0:
            i += 1
            continue
        out.append(_strip_article(raw))
        i += 1
    return [t for t in out if t]


def _strip_article(raw: str) -> str:
    token = ar_normalize(raw)
    starts = raw.startswith("ال") or raw.startswith("ٱل")
    if starts and len(token) - 2 >= 3 and token not in ARTICLE_EXCEPTIONS:
        return token[2:]
    return token


def arabic_skeleton(token: str) -> str:
    """Consonant skeleton of a normalised Arabic token, comparable with latin.latin_skeleton."""
    if token.startswith("عبدال") and len(token) > 5:
        token = "عبد" + token[5:]
    skeleton = "".join(_SKELETON.get(c, "") for c in token)
    if skeleton.endswith("h") and token.endswith("ه"):
        skeleton = skeleton[:-1]
    return re.sub(r"(.)\1+", r"\1", skeleton)
