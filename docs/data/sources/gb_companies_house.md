# Companies House (`gb_companies_house`)

The production loader for the UK register of companies (PHASE-2.md M2.3). It replaces the
Phase 1 spike (`docs/data/spikes/companies-house.md`). Facts about the files come from the
research note `docs/research/2026-10-18/bulk-sources-loading.md` (sections 2 to 5 and 10).

## Products and cadence

| Product | Files | Cadence | Milestone |
|---|---|---|---|
| `companies` | Free Company Data Product: `BasicCompanyData-<yyyy-mm-dd>-partN_M.zip`, listed on `https://download.companieshouse.gov.uk/en_output.html`, about 70 MB a part | Monthly, compiled to the end of the previous month (note 2.1) | M2.3a |
| `psc` | PSC snapshot: `psc-snapshot-<yyyy-mm-dd>_<N>of<M>.zip`, listed on `https://download.companieshouse.gov.uk/en_pscdata.html`, about 2.2 GB in 33 parts on 17 October 2026 | Daily, compiled to the end of the previous day, files replaced every morning (note 3.1) | M2.3b |
| officers | REST API, per company, within a request budget | On demand, cached | M2.3c |

`neonradar data fetch` takes, for each product the profile needs, the newest snapshot date for
which every part is listed and downloads the parts to
`data/cache/real/sources/gb_companies_house/<product>/<date>/`; a cut download resumes part by
part. It fetches `companies` always and `psc` only when the profile's `psc` block is enabled;
a product whose discovery fails (for example a PSC page without a complete snapshot) stops
only itself, and the command exits 1 after the other product has downloaded. The two
products rotate separately, so a daily PSC download
never removes the monthly company parts. Companies House says the bulk files are "provided
free of charge and will not be supported" (note 2.1).

## What is loaded

`neonradar ingest build --profile <p> --dataset gb_companies_house` runs these steps (one or
more with `--step`):

- `index`: every live company's number, name, postcode district, category, status and
  country of origin in `companies.sqlite`, a work file under `data/cache/real/work/`.
- `psc-index` (when the profile's `psc` block is enabled): a first pass over the PSC
  snapshot into `corporate_pscs.sqlite`: every corporate and legal-person PSC with its
  company, outcome (below) and normalised number, and every PSC statement value without
  `ceased_on`, super-secure kind and exemption key, by company.
- `slice`: the profile's companies in `slice.csv` (below), and `slice.json` with the snapshot
  date, the sample seed and the SHA-256; the `companies` step refuses (exit 2) a slice built
  from another snapshot than the newest download.
- `companies`: a `Company` record per company in the slice (`gbch-co-<number>`) with its
  name, number, category (`legalForm`), status, jurisdiction, incorporation date, SIC codes
  (`sector`), previous names, accounts category (`nr.accounts_category`) and, once M2.3b has
  merged, its PSC statements (`nr.psc_statements`); and one `Address` record per distinct
  registered office address key (`gbch-addr-<hash of the key>`, the key computed from the
  `full` text as FollowTheMoney cleans it, as the graph loader does), linked with the role
  `registered`. The care-of line is never loaded: it can name a person.
- `psc` (when the `psc` block is enabled): a second pass over the snapshot, writing the
  PSCs of the slice companies and their interests (below). Lines of other companies are
  counted, not loaded.

The work indexes are deleted after a successful build (records validated and swapped in)
that ran the `companies` or `psc` step, unless `--keep-work` is given; `slice.csv` and
`slice.json` stay (with the PSC snapshot date when the expansion ran, since the daily PSC
snapshot changes the slice too). A `psc` step run on its own keeps the previous company
records, which its links point to; a `companies` step run without the `psc` step writes the
company records only, so run both after a new slice. The `psc` step refuses (exit 2) a slice
built from another PSC snapshot than the newest PSC download. A PSC's address gets the same
key rule as a registered office, so a PSC at a slice company's registered office links to
that company's `Address` record.

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
3. the PSC expansion (profile block `psc`): from those companies, the companies that are
   `resolved` corporate PSCs of a slice company, up to `parent_depth` levels (reason
   `parent`, even outside the districts), then, for `child_depth` levels, the companies in
   the index whose `resolved` corporate PSC is already in the slice (reason `child`);
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

## People with significant control

The snapshot holds one JSON object per line, `{"company_number": ..., "data": {...}}`; a
line without `company_number` is a totals record (note 3.2). When a totals record is present,
the data lines read must equal the sum of its three counts, and the summary reports
`totals_check` as `passed`, `failed` or `absent`, with `snapshot_date`. Unknown kinds and
unknown `natures_of_control` values are counted by value, never dropped silently.

| `data.kind` | Record |
|---|---|
| `individual-person-with-significant-control`, `individual-beneficial-owner` | `Person`: name, given, middle and family names, month and year of birth (`yyyy-mm`), nationalities, country of residence, service address (role `service`) |
| `corporate-entity-person-with-significant-control`, `corporate-entity-beneficial-owner` | `Company`: name, legal form, registration number and jurisdiction (below), address (role `registered`) |
| `legal-person-person-with-significant-control`, `legal-person-with-significant-control`, `legal-person-beneficial-owner` | `Organization`: name, legal form, jurisdiction, address |
| `super-secure-person-with-significant-control`, `super-secure-beneficial-owner` | none: the kind goes to the company's `nr.psc_statements` (a ceased one is skipped) |
| `persons-with-significant-control-statement` | none: the statement value, unchanged, goes to `nr.psc_statements` unless `ceased_on` is set |
| `exemptions` | none: each exemption key goes to `nr.psc_statements` |

PSC record ids are `gbch-psc-<last path segment of data.links.self>`. PSCs with `ceased_on`
are skipped and counted unless the profile sets `psc.include_ceased: true` (then their links
get an `endDate`). A PSC none of whose `natures_of_control` values is known gets no record.
A beneficial owner with `is_sanctioned: true` gets the topic `sanction`: it is recorded as
sanctioned on the register of overseas entities at Companies House (as declared by the
overseas entity; it may be out of date) (note 3.7).

**Interests.** Each PSC's `natures_of_control` values in one company are grouped by kind,
measure, capacity and held right (`natures.py`); each group becomes one `Ownership` (owner
the PSC, asset the company; shares or surplus assets) or one `Control` (voting rights, the
right to appoint and remove directors, significant influence or control, a nominee, or
control over a trust or firm), with the raw values in `role` and `nr.natures_of_control`,
`notified_on` as `startDate` and `ceased_on` as `endDate`. Share and voting bands follow the
statute, not the API's long descriptions (note 4.2): "more than 25% but not more than 50%" is
`(25, 50]`, "more than 50% but less than 75%" is `(50, 75)`, "75% or more" is `[75, 100]`, and
an overseas entity's "more than 25%" is `(25, 100]`, stored as `nr.share_pct_min`,
`nr.share_pct_max` and the two exclusive flags; voting rights keep their band on the
`Control`. A person who controls a trust or firm whose trustees or members hold shares does
not own those shares (the `-as-trust` and `-as-firm` values; note 4.3): that is a `Control` of
type `trust-or-firm` that keeps the band of what the trust or firm holds, and a direct holding
of the same person is a separate `Ownership`. Only an overseas entity's beneficial owner who is
a trustee holds the right itself (`shares (as trustee)`).

**Corporate PSCs.** When the registration fields say Companies House (`identification.py`,
written from the rule in note 3.6), the registration number is normalised to the 8-character
Companies House form and the jurisdiction is `gb`; otherwise the number stays as given and the
jurisdiction is the ISO code of `country_registered`. The outcome against the company index
(`resolved`, `name_mismatch`, `number_not_found`, `no_number`, `non_uk`) is counted in the
summary, with the ISO codes of non-UK registrations (unmapped values counted, never shown),
and only `resolved` PSCs drive the slice expansion. The outcome decides no merge: the resolver
applies its own rule (PHASE-2.md 7.1.2, D1).

**Not loaded.** Usual residential addresses, days of birth, the care-of line, other
forenames, honours, identity verification details (counted as
`with_identity_verification_details`, never read), a statement's linked PSC name, the `etag`
and the links other than the PSC's own id are never read. The source writes an individual's
title in front of `name`: when `name` starts with `name_elements.title`, the loader removes it
(`titles_removed`); when it does not, `name` is kept as given and counted (`titles_kept`), so
the reviewer sees whether any title is left. A PSC's address gets the country the source
names; unlike a registered office, it is never assumed to be `gb`.

## Personal data

The company file itself can hold personal data: a company name or a previous name can be a
person's name, and a registered office can be a home address. The officer product (M2.3c)
holds names, months of birth and nationalities.

From the PSC snapshot, the loader keeps, for the slice companies only: an individual's name
(without the title), forename, middle name and surname, month and year of birth,
nationalities, country of residence and service address; a corporate or legal-person PSC's
name, legal form, registration number, jurisdiction and address; whether a beneficial owner
is recorded as sanctioned; each interest's natures of control, band and dates; and the
company's statement values. The downloads themselves cover every UK company: about 2.2 GB a
version, and the data manager keeps the two newest complete versions, so up to about 4.4 GB
of all-UK PSC data can sit under `data/cache/real/sources/` until retention or a purge
removes it (only when a profile enables the `psc` block).
Companies House's personal information charter says that organisations using register data
"then become controllers of your personal data" and "must establish how they comply with the
data protection law" (note 10, source B12). Every real run therefore passes the real-data gate
(`docs/data/real-data-handling.md`), keeps its files under `data/cache/real/` for
`access.real_data_days`, and prints counts only.
