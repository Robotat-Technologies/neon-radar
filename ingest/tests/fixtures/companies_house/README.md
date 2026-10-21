# Companies House test fixtures (synthetic)

Synthetic response bodies shaped like the documented Companies House Public Data API
resources (`docs/research/2026-10-16/sources-ch-gleif.md` A2): a company profile, two pages of
officers and one page of persons with significant control. No real company, person, officer
id or address appears here: company numbers start with `SYN` (never a Companies House
format), officer and PSC ids contain `SYN`, and the names were checked against the public
Companies House search on 21 October 2026 (operator decision OD-12; results in the M1.8a pull
request).

`records-SYN00001.expected.json` is the C1 output the mapping must produce from these bodies.
It holds `gbch-` ids because it is what the Companies House mapping writes; it is a JSON
array, never a committed `.ftm.jsonl` file (PHASE-1.md M1.8 common rules).
