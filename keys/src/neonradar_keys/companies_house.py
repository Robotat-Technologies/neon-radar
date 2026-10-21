"""Companies House "same as" name key (SI 2015/17 Schedule 3), approximate (research note 10)."""

from __future__ import annotations

import re
import unicodedata

from anyascii import anyascii

_SCHEDULE_2 = sorted(
    [
        "COMMUNITY INTEREST PUBLIC LIMITED COMPANY",
        "COMMUNITY INTEREST PLC",
        "CWMNI BUDDIANT CYMUNEDOL CYHOEDDUS CYFYNGEDIG",
        "CWMNI BUDDIANT CYMUNEDOL CCC",
        "CWMNI CYFYNGEDIG CYHOEDDUS",
        "PUBLIC LIMITED COMPANY",
        "COMMUNITY INTEREST COMPANY",
        "CWMNI BUDDIANT CYMUNEDOL",
        "RIGHT TO ENFRANCHISEMENT",
        "HAWL I RYDDFREINIAD",
        "RIGHT TO MANAGE",
        "CWMNI RTM CYFYNGEDIG",
        "UK ECONOMIC INTEREST GROUPING",
        "INVESTMENT COMPANY WITH VARIABLE CAPITAL",
        "CWMNI BUDDSODDI A CHYFALAF NEWIDIOL",
        "LIMITED LIABILITY PARTNERSHIP",
        "PARTNERIAETH ATEBOLRWYDD CYFYNGEDIG",
        "LIMITED PARTNERSHIP",
        "PARTNERIAETH CYFYNGEDIG",
        "OPEN-ENDED INVESTMENT COMPANY",
        "CWMNI BUDDSODDIAD PENAGORED",
        "CHARITABLE INCORPORATED ORGANISATION",
        "SEFYDLIAD ELUSENNOL CORFFOREDIG",
        "INDUSTRIAL AND PROVIDENT SOCIETY",
        "CO-OPERATIVE SOCIETY",
        "PROTECTED CELL COMPANY",
        "PCC LIMITED",
        "PCC LTD",
        "CWMNI UNEDAU GWARCHODEDIG",
        "CUG CYFYNGEDIG",
        "CUG CYF",
        "COMMUNITY BENEFIT SOCIETY",
        "ANGHYFYNGEDIG",
        "UNLIMITED",
        "CYFYNGEDIG",
        "LIMITED",
        "UKEIG",
        "LTD",
        "CYF",
        "PLC",
        "CCC",
        "CIC",
        "CBC",
        "RTE",
        "RTM",
        "LLP",
        "LP",
        "PC",
        "PAC",
        "CIO",
        "SEC",
    ],
    key=len,
    reverse=True,
)
_PARA_4 = [
    ("&", ["AND", "&"]),
    ("+", ["PLUS", "+"]),
    ("0", ["0", "ZERO", "O"]),
    ("1", ["1", "ONE"]),
    ("2", ["2", "TWO", "TO", "TOO"]),
    ("3", ["3", "THREE"]),
    ("4", ["4", "FOUR", "FOR"]),
    ("5", ["5", "FIVE"]),
    ("6", ["6", "SIX"]),
    ("7", ["7", "SEVEN"]),
    ("8", ["8", "EIGHT"]),
    ("9", ["9", "NINE"]),
    ("£", ["£", "POUND"]),
    ("€", ["€", "EURO"]),
    ("$", ["$", "DOLLAR"]),
    ("¥", ["¥", "YEN"]),
    ("%", ["%", "PER CENT", "PERCENT", "PER CENTUM", "PERCENTUM"]),
    ("@", ["@", "AT"]),
]
_PARA_5 = sorted(
    [
        "& CO",
        "& COMPANY",
        "BIZ",
        "CO UK",
        "CO.UK",
        "CO",
        "COM",
        "COMPANY",
        "EU",
        "GB",
        "GREAT BRITAIN",
        "NET",
        "NI",
        "NORTHERN IRELAND",
        "ORG UK",
        "ORG.UK",
        "ORG",
        "UK",
        "UNITED KINGDOM",
        "WALES",
        "& CWMNI",
        "A'R CWMNI",
        "CWMNI",
        "CYM",
        "CYMRU",
        "DU",
        "PF",
        "PRYDAIN FAWR",
        "Y DEYRNAS UNEDIG",
    ],
    key=len,
    reverse=True,
)


def _strip_trailing(text: str, items: list[str], separators: str) -> str:
    changed = True
    while changed:
        changed = False
        for item in items:
            for form in (item, f"({item})", f"[{item}]", f"{{{item}}}"):
                pattern = re.compile(r"(^|[" + separators + r"])" + re.escape(form) + r"[.\s]*$")
                if pattern.search(text):
                    shorter = pattern.sub(r"\1", text).rstrip(" .")
                    if shorter and shorter != text:
                        text, changed = shorter, True
    return text


def ch_same_as_key(name: str) -> str:
    """Key for comparing UK company names; use as a blocking key and as strong evidence only."""
    text = anyascii(unicodedata.normalize("NFKC", name)).upper()
    text = re.sub(r"\s+", " ", text).strip()
    text = _strip_trailing(text, _SCHEDULE_2, r"\s")
    for canonical, forms in _PARA_4:
        for form in sorted(forms, key=len, reverse=True):
            text = re.sub(r"(?:(?<=\s)|^)" + re.escape(form) + r"(?=\s)", canonical, text)
    text = _strip_trailing(text, _PARA_5, r"\s.@")
    text = re.sub(r"[^\w&+£€$¥%@\s]|_", "", text)
    text = re.sub(r"S$", "", text.strip())[:60]
    text = re.sub(r"^(?:(?:@|THE\s|WWW)\s*)+", "", text)
    return text.replace(" ", "")
