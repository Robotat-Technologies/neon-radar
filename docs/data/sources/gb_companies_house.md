# Companies House (`gb_companies_house`)

The production loader for the UK register of companies (PHASE-2.md M2.3). It replaces the
Phase 1 spike (`docs/data/spikes/companies-house.md`). Facts about the files come from the
research note `docs/research/2026-10-18/bulk-sources-loading.md` (sections 2 to 5 and 10).

## Products and cadence

| Product | Files | Cadence | Milestone |
|---|---|---|---|
| `companies` | Free Company Data Product: `BasicCompanyData-<yyyy-mm-dd>-partN_M.zip`, listed on `https://download.companieshouse.gov.uk/en_output.html`, about 70 MB a part | Monthly, compiled to the end of the previous month (note 2.1) | M2.3a |
| `psc` | PSC snapshot | Daily | M2.3b |
| officers | REST API, per company, within a request budget | On demand, cached | M2.3c |

`neonradar data fetch` takes the newest snapshot date for which every part is listed and
downloads the parts to `data/cache/real/sources/gb_companies_house/companies/<date>/`; a cut
download resumes part by part. The two products rotate separately, so a daily PSC download
never removes the monthly company parts. Companies House says the bulk files are "provided
free of charge and will not be supported" (note 2.1).

## What is loaded

`neonradar ingest build --profile <p> --dataset gb_companies_house` runs these steps (one or
more with `--step`):

- `index`: every live company's number, name, postcode district, category, status and
  country of origin in `companies.sqlite`, a work file under `data/cache/real/work/`.
- `slice`: the profile's companies in `slice.csv` (below).
- `companies`: a `Company` record per company in the slice (`gbch-co-<number>`) with its
  name, number, category (`legalForm`), status, jurisdiction, incorporation date, SIC codes
  (`sector`), previous names, accounts category (`nr.accounts_category`) and, once M2.3b has
  merged, its PSC statements (`nr.psc_statements`); and one `Address` record per distinct
  registered office address key (`gbch-addr-<hash of the key>`), linked with the role
  `registered`. The care-of line is never loaded: it can name a person.

Reading follows note 2.2 to 2.4: header cells are stripped (14 start with a space) and
columns mapped by name; a missing column stops the build; empty rows and rows with the wrong
number of fields are skipped and counted; strict UTF-8 (a mis-encoded release stops the
build with the part's name); only complete HTML character references are decoded, so
`A&B LIMITED` stays as it is; `dd/mm/yyyy` dates are parsed strictly and other values are
dropped and counted; an address field holding only punctuation, digits or a bare outward
postcode counts as missing (so a foreign numeric postcode or a number-only PO box is not
loaded).

## The slice

A profile's `companies` block (PHASE-2.md 7.8) decides which companies become records:

1. every seed (a seed missing from the index is reported as a count, never guessed);
2. for each postcode district, the companies whose registered office is in it, ordered by
   the sample hash `sha256("<sample_seed>|<company number>")`, the first `max_per_district`;
3. the PSC expansion (parents and children through corporate PSCs, M2.3b);
4. the cap `max_companies`, which removes expansion companies first (deepest level first,
   then the highest hash), then district companies (highest hash first), never a seed.

The same snapshot and seed give the same `slice.csv`; the summary prints its SHA-256
(`slice_sha256`), the count per reason, district and level, how many the cap removed, and
`top10_address_share`, the share of slice companies registered at one of the ten most common
addresses (a number only). A high share means a few addresses (often those of formation agents)
dominate the slice.

## Overseas companies

The jurisdiction is `gb`, except for numbers with these prefixes, whose jurisdiction is the
country of origin (`neonradar_keys.countries.country_code`; a value that does not map is
counted and left empty). Meanings from the Companies House URI customer guide (v1.1, May
2012, note 2.6 source B16, read on 22 October 2026) and, for `OE`, the community sources of
note 2.6:

| Prefix | Meaning |
|---|---|
| `FC` | Overseas company |
| `SF` | Overseas company registered in Scotland (before 1 October 2009) |
| `NF` | Overseas company registered in Northern Ireland (before 1 October 2009) |
| `OE` | Overseas entity (Register of Overseas Entities) |

## Personal data

The PSC and officer products (M2.3b, M2.3c) hold names, months of birth and nationalities.
Companies House's personal information charter says that organisations using register data
"then become controllers of your personal data" and "must establish how they comply with the
data protection law" (note 10, source B12). Every real run therefore passes the real-data gate
(`docs/data/real-data-handling.md`), keeps its files under `data/cache/real/` for
`access.real_data_days`, and prints counts only.