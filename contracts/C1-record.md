# C1: NeonRadar Record v1.0.0

The format that every loader and the synthetic generator write, and the only input the graph loader accepts. It is [FollowTheMoney](https://followthemoney.tech/) (FtM) 4.11 or later, so the files work with FtM tooling, plus a small, closed extension object `nr` for the few facts FtM cannot express.

- Status: version 1.0.0, **not frozen yet**. The tech lead freezes the four contracts at Gate 1 with the tag `contracts-v1.0.0` (`docs/build/PHASE-1.md` sections 5.0 and 8). After that, changes need an approved contract-change issue.
- Code: `neonradar_contracts.records` (validator, manifest), `neonradar_contracts.datasets` (registry), `neonradar_contracts.versions`.
- Command: `uv run neonradar contracts validate-records PATH... [--strict]`.
- Examples: `contracts/examples/c1/demo.ftm.jsonl` (valid in strict mode) and `contracts/examples/c1/invalid/` (one file per rule, each failing with exactly that rule).
- Source: `docs/build/PHASE-1.md` section 5.1, with the changes listed in [CHANGELOG.md](CHANGELOG.md).

## File format

- UTF-8, JSON Lines, one entity per line, file extension `.ftm.jsonl`.
- Each file has a sibling manifest: `<name>.ftm.jsonl` comes with `<name>.manifest.json` in the same folder.
- Each line is the output of FtM's `ValueEntity.to_dict()`: keys `id` (required), `schema` (required), `properties` (required; property name to list of strings), `datasets` (required), and optionally `referents`, `caption`, `first_seen`, `last_seen`, `last_change`, `nr`. FtM keeps the extra top-level key `nr` through `ValueEntity.from_dict()` and `to_dict()`. No other top-level key is allowed.

## Allowed schemata in v1

`Person`, `Company`, `Organization`, `LegalEntity`, `PublicBody`, `Address`, `BankAccount`, `Position`, `Ownership`, `Control`, `Directorship`, `Representation`, `Family`, `Associate`, `Membership`, `Employment`, `UnknownLink`, `Succession`, `Occupancy`, `Payment`, `Sanction`.

The validator rejects other schemata (rule R3). A loader that meets one skips it and counts it in the manifest under `counts.skipped`.

## Rules

`validate_record()` checks one record. `validate_batch()` checks the rules that need the whole load (the dangling references of R4 and the account holders of R8); a load is every file passed to one `validate-records` call.

| Rule | Statement |
|---|---|
| R1 | `id` matches `^(?P<prefix>[a-z][a-z0-9]{1,15})-(?P<rest>[A-Za-z0-9.-]{0,99}[A-Za-z0-9])$`, and `prefix` equals the `id_prefix` of the record's dataset in `contracts/datasets.yaml`. |
| R2 | `datasets` contains exactly one slug, and that slug exists in `contracts/datasets.yaml`. |
| R3 | The schema is one of the v1 schemata; `followthemoney.model[schema].validate(record)` passes; every property in `schema.required` is present and non-empty (FtM's own validator does not check missing required properties); every property name exists on the schema (FtM would drop unknown ones without a word). |
| R4 | Entity-typed properties hold record ids. References may point to records in other files of the same load. The graph loader reports dangling references; in strict mode (fixtures, CI) any dangling reference fails. |
| R5 | `Payment.date` is a full UTC timestamp `YYYY-MM-DDTHH:MM:SS` without an offset. All other dates (date-typed properties and `first_seen`, `last_seen`, `last_change`) are ISO 8601 and may be partial (`1979`, `1979-08`). |
| R6 | Synthetic consistency: dataset `nr_synthetic` if and only if id prefix `syn` if and only if `nr.synthetic` is `true`. Synthetic records must carry `nr`. Non-synthetic records must not set `nr.synthetic`. |
| R7 | `Payment` records (synthetic only in v1) have exactly one each of `payer`, `beneficiary`, `payerAccount`, `beneficiaryAccount`, `amount` (decimal string, at most two decimals, greater than zero) and `currency` (three upper-case letters, the shape of an ISO 4217 code), a `date` (R5), and `nr.channel`. |
| R8 | Every `BankAccount` is the `asset` of at least one `Ownership` whose `owner` is a `LegalEntity` in the same load (this becomes `HOLDS_ACCOUNT`). Synthetic account numbers use the form `NRSYN` plus 10 digits, and synthetic records never set `iban` or `bic`, so no synthetic account can collide with a real one. |
| R9 | No ground-truth labels anywhere in records, including `nr`: no typology, scenario, role-in-scenario or "illicit" field. Labels live in separate label files (Phase 3). The validator rejects any top-level key, `nr` key or property name that contains `typolog`, `scenario`, `illicit`, `lookalike`, `ground truth` or `label`. |
| R10 | Strings (keys and values, including `nr`) are Unicode NFC. Names keep their original script. Machine transliterations are never written into records (Phase 2 computes matching keys at load time); a validator cannot detect them, so reviewers check. |

Two more issue codes cover the envelope and the extension:

| Code | Meaning |
|---|---|
| `FORMAT` | A line is not one JSON object (reported with file and line number), a top-level key is unknown, or `caption` or `referents` has the wrong type. |
| `NR` | The `nr` object is malformed: not an object, an unknown key, a wrong value type, a missing `v`, a key on a schema the table below does not list, an `address_roles` key that is not in `addressEntity`, or `share_pct_min` greater than `share_pct_max`. |

The validator reports each problem once. It does not report a rule whose input already failed another rule: for example, a record whose id breaks R1 is not also checked for the id prefix in R6.

### Ids and references (R1, changed from the spec)

FtM stores a reference only if it matches `^[0-9a-zA-Z]([0-9a-zA-Z.-]*[0-9a-zA-Z])?$`. Its `add()` drops any other value without a word, and its validator rejects it. The spec's first R1 allowed `_` and `:` in the `rest` of an id, so some valid ids could never be referenced. R1 now allows letters, digits, dots and hyphens in `rest`, ending in a letter or digit, so every valid id can be referenced. This is a tech lead contract decision, taken before the freeze and listed for explicit sign-off at Gate 1 ([CHANGELOG.md](CHANGELOG.md)).

**Loaders must map source identifiers into this alphabet.** Companies House officer ids, for example, can contain `_`. Map such characters reversibly or hash the native id, keep it in a form the id rule allows, and keep the original value in `nr.source_ref`. Edge ids follow `docs/build/PHASE-1.md` 4.4 (`<prefix>-<schema in lowercase>-<first 20 hex of a SHA-1>`), which already fits.

## The `nr` extension object

A closed set of keys; unknown keys fail validation (`NR`, or `R9` if the key looks like a label).

| Key | Type | Used on | Meaning |
|---|---|---|---|
| `v` | string, required when `nr` is present | all | Record contract version, `"1.0"` |
| `synthetic` | boolean | all | `true` for synthetic records (R6) |
| `synthetic_kind` | `"registry"` or `"activity"` | synthetic records | Synthetic companies and people versus synthetic accounts and payments |
| `channel` | `"wire"`, `"card"`, `"cash_deposit"`, `"cash_withdrawal"`, `"internal"` | `Payment` | How the money moved. Cash deposits are payments from the bank branch's `cash_ledger` account. |
| `account_kind` | `"customer"` or `"cash_ledger"` | `BankAccount` | `cash_ledger` accounts belong to a synthetic bank branch and model cash in and out |
| `address_roles` | object, Address id to `"registered"`, `"service"`, `"residential"`, `"business"`, `"unknown"` | any `LegalEntity` with `addressEntity` | Role of each linked address (FtM has no role on `addressEntity`) |
| `source_ref` | string | any | The source's native identifier (Companies House `officer_id`, ICIJ `node_id`) |
| `natures_of_control` | list of strings | `Ownership`, `Control` | Raw Companies House PSC values |
| `share_pct_min`, `share_pct_max` | numbers in [0, 100] | `Ownership` | Parsed share band, for example 25 and 50 for "more than 25% but not more than 50%" |
| `is_nominee` | boolean | `Directorship` | True for nominee roles (for example Companies House `nominee-director`) |
| `consolidation` | `"direct"` or `"ultimate"` | `Ownership` | GLEIF accounting consolidation parent; becomes `CONSOLIDATES`, not `OWNS` |

## Examples

Three lines of `contracts/examples/c1/demo.ftm.jsonl` (all synthetic; the file holds ten records, so it validates in strict mode):

```json
{"id": "syn-co-0001", "schema": "Company", "datasets": ["nr_synthetic"], "properties": {"name": ["Falcon Ridge Trading Ltd"], "jurisdiction": ["gb"], "registrationNumber": ["SYN00001"], "incorporationDate": ["2019-04-02"], "addressEntity": ["syn-addr-0001"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "registry", "address_roles": {"syn-addr-0001": "registered"}}}
{"id": "syn-ownership-0002", "schema": "Ownership", "datasets": ["nr_synthetic"], "properties": {"owner": ["syn-co-0001"], "asset": ["syn-acct-0001"], "role": ["account holder"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "activity"}}
{"id": "syn-payment-000001", "schema": "Payment", "datasets": ["nr_synthetic"], "properties": {"payer": ["syn-co-0001"], "beneficiary": ["syn-co-0002"], "payerAccount": ["syn-acct-0001"], "beneficiaryAccount": ["syn-acct-0002"], "amount": ["9500.00"], "currency": ["EUR"], "date": ["2026-03-14T10:22:05"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "activity", "channel": "wire"}}
```

## Manifest

`<name>.manifest.json`, validated by `neonradar_contracts.records.Manifest` and written by `write_manifest()`, which computes the SHA-256, the record counts by schema, and the licence and synthetic flag from the registry:

```json
{
  "manifest_version": "1.0",
  "record_contract": "1.0.0",
  "dataset": "nr_synthetic",
  "files": [{"path": "nr_synthetic-20261023-demo-mini.ftm.jsonl", "sha256": "<hex>", "records": 412}],
  "created_at": "2026-10-23T09:00:00Z",
  "producer": {"name": "neonradar_ingest.synth", "version": "0.1.0", "git_sha": "<sha>"},
  "source": {"urls": [], "retrieved_at": null, "source_version": null},
  "licence": {"id": "Apache-2.0", "attribution": null},
  "counts": {"by_schema": {"Company": 24, "Person": 30, "Payment": 260}, "skipped": {}},
  "dependencies": {"followthemoney": "4.11.0"},
  "synthetic": true,
  "seed": 20261023,
  "notes": []
}
```

`files[].path` is relative to the manifest's folder and `created_at` is UTC with a `Z`. Unknown keys fail validation.

## Dataset registry

`contracts/datasets.yaml` lists every dataset with its slug, id prefix, licence, attribution, commercial-use and redistribution terms, personal-data flag, access and status. Loaders follow it (guardrail G7). The prefix `nr` is reserved for canonical resolved entities (Phase 2). Adding a dataset after the freeze is a minor change. The data steward approves every licence field before the freeze (GC-17).

## How to write a loader that emits C1

1. Create each entity with `ValueEntity`, not `model.make_entity`, whose output has no `datasets` and so fails R2:

   ```python
   import json
   from followthemoney import ValueEntity, model

   entity = ValueEntity(model["Company"], {"id": "gbch-co-01800000", "datasets": ["gb_companies_house"]})
   entity.add("name", "...")                       # values are cleaned; invalid ones are dropped
   entity.add("incorporationDate", "1984-03-02")
   line = json.dumps({**entity.to_dict(), "nr": {"v": "1.0", "source_ref": "01800000"}}, ensure_ascii=False)
   ```

2. Build ids as in `docs/build/PHASE-1.md` 4.4 and the id rule above: the dataset's `id_prefix`, a hyphen, then letters, digits, dots and hyphens.
3. Write one `json.dumps(...)` per line, UTF-8, `ensure_ascii=False`, strings in NFC.
4. Write Payment timestamps in UTC without an offset (`2026-03-14T10:22:05`). FtM drops an offset anyway; convert to UTC first.
5. Put labels, scores and scenario facts in separate label files, never in records.
6. Write the manifest with `write_manifest(path, dataset=..., producer=Producer(...))`.
7. Check the output: `uv run neonradar contracts validate-records <files> --strict`.
