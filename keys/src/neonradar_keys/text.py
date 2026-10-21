"""Script detection and Latin folding of single tokens."""

from __future__ import annotations

import re
import unicodedata

from anyascii import anyascii
from normality import ascii_text
from rigour.text.scripts import text_scripts

# Modifier letters and quotes that normality.ascii_text turns into "?" (research note 12).
_APOSTROPHES = re.compile("[\u02bb-\u02bf\u2018\u2019\u0060\u00b4]")


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def scripts(text: str) -> set[str]:
    """Unicode scripts of the letters and digits in the text (for example {"Latin", "Arabic"})."""
    return set(text_scripts(text))


def latin_token(token: str) -> str:
    """Lower-case ASCII form of one token: ICU folding for Latin, anyascii for other scripts."""
    token = _APOSTROPHES.sub("", token)
    found = scripts(token)
    if found <= {"Latin"}:
        return ascii_text(token).lower().replace("?", "")
    return anyascii(token).lower()
