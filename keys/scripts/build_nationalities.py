"""Build keys/src/neonradar_keys/data/nationalities.csv (value, ISO alpha-2 country).

Inputs (both Open Government Licence v3.0): the Companies House list of nationalities from
"Nationalities and countries for company filings" (one value per line), and the FCDO
Geographical Names Index citizen names (tab-separated: ISO alpha-2 code, comma-separated
citizen names). Values not in OVERRIDES are mapped with rigour.territories.lookup_territory
without fuzzy matching. Usage:

    uv run python keys/scripts/build_nationalities.py ch_nationalities.txt fcdo_citizen_names.tsv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from rigour.territories import lookup_territory

OUT = Path(__file__).resolve().parents[1] / "src" / "neonradar_keys" / "data" / "nationalities.csv"
# Where rigour gives no code or a wrong one (names-addresses.md section 9), and the UK nations.
OVERRIDES = {
    "Anguillan": "ai",
    "Citizen of Antigua and Barbuda": "ag",
    "Bermudian": "bm",
    "Bhutanese": "bt",
    "Citizen of Bosnia and Herzegovina": "ba",
    "Bruneian": "bn",
    "Cape Verdean": "cv",
    "Cayman Islander": "ky",
    "Chadian": "td",
    "Comoran": "km",
    "Cook Islander": "ck",
    "Cymraes": "gb",
    "Cymro": "gb",
    "Citizen of the Dominican Republic": "do",
    "Guamanian": "gu",
    "Hong Konger": "hk",
    "Citizen of Kiribati": "ki",
    "Liechtenstein citizen": "li",
    "Martiniquais": "mq",
    "Montserratian": "ms",
    "Nauruan": "nr",
    "Palauan": "pw",
    "Papua New Guinean": "pg",
    "Pitcairn Islander": "pn",
    "Prydeinig": "gb",
    "Samoan": "ws",
    "Citizen of Seychelles": "sc",
    "Solomon Islander": "sb",
    "St Helenian": "sh",
    "Stateless": "",
    "Tristanian": "sh",
    "Turks and Caicos Islander": "tc",
    "Tuvaluan": "tv",
    "Vatican citizen": "va",
    "Citizen of Vanuatu": "vu",
    "Vincentian": "vc",
    "Wallisian": "wf",
    "Mauritian": "mu",
    "Congolese (Congo)": "cg",
    "Congolese (DRC)": "cd",
    "British": "gb",
    "English": "gb",
    "Scottish": "gb",
    "Welsh": "gb",
    "Northern Irish": "gb",
}


def code_for(value: str) -> str | None:
    if value in OVERRIDES:
        return OVERRIDES[value]
    territory = lookup_territory(value)
    if territory is None:
        return None
    code = territory.ftm_country or territory.code
    return code.split("-")[0] if code else None


def main() -> int:
    ch_path, fcdo_path = Path(sys.argv[1]), Path(sys.argv[2])
    rows: dict[str, str] = {}
    missing: list[str] = []
    for value in (v.strip() for v in ch_path.read_text(encoding="utf-8").splitlines()):
        if value:
            code = code_for(value)
            if code is None:
                missing.append(value)
            else:
                rows[value] = code
    for line in fcdo_path.read_text(encoding="utf-8").splitlines():
        code, _, names = line.partition("\t")
        for name in (n.strip() for n in names.split(",")):
            if name and name not in rows:
                rows[name] = code.strip().lower()
    if missing:
        print("no code for: " + ", ".join(missing), file=sys.stderr)
        return 1
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["value", "country"])
        for value in sorted(rows, key=str.casefold):
            writer.writerow([value, rows[value]])
    print(f"{len(rows)} values written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
