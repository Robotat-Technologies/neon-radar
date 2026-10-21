"""Build keys/src/neonradar_keys/data/ar_symbols.json.gz from rigour's Wikidata name groups.

The source is rust/data/names/person_names.txt in github.com/opensanctions/rigour at the
tag that matches the pinned rigour version (MIT; the names come from Wikidata, CC0). Each
line is "form1, form2, ... => Qnnn". The index maps ar_normalize(form) of every form that
contains Arabic script to the sorted list of QIDs. Run it whenever the rigour pin changes:

    uv run python keys/scripts/build_ar_symbol_index.py --tag v2.5.0 \
        --sha256 be47a435969da3fa7311d8c682e462d6d20e6cf27cf90ad1473ce213c9a91c79
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from neonradar_keys.arabic import ar_normalize
from neonradar_keys.text import scripts

URL = (
    "https://raw.githubusercontent.com/opensanctions/rigour/{tag}/rust/data/names/person_names.txt"
)
OUT = Path(__file__).resolve().parents[1] / "src" / "neonradar_keys" / "data" / "ar_symbols.json.gz"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source", help="a local copy of person_names.txt instead of downloading")
    args = parser.parse_args()
    if args.source:
        data = Path(args.source).read_bytes()
    else:
        with urllib.request.urlopen(URL.format(tag=args.tag), timeout=60) as response:  # noqa: S310
            data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != args.sha256:
        print(f"sha256 mismatch: {digest}", file=sys.stderr)
        return 1
    groups: dict[str, set[str]] = {}
    for line in data.decode("utf-8").splitlines():
        forms, _, qid = line.rpartition("=>")
        qid = qid.strip()
        for form in forms.split(","):
            form = form.strip()
            if form and "Arabic" in scripts(form):
                groups.setdefault(ar_normalize(form), set()).add(qid)
    payload = {
        "source": URL.format(tag=args.tag),
        "sha256": digest,
        "licence": "MIT (OpenSanctions Datenbanken GmbH); name data from Wikidata (CC0)",
        "groups": {key: sorted(qids) for key, qids in sorted(groups.items())},
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with (
        OUT.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz,
    ):
        gz.write(text.encode("utf-8"))  # mtime=0 keeps the header free of the build time
    print(f"{len(groups)} keys written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
