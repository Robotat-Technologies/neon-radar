# D6 review: `fan_out_distribution`

**Reviewer:** @omar-alselek

**Pull request reviewed:** #88

**Reviewed commit:** `7a10445dcd001eaeee143f742f5baba18cd16e08`

**Scope:** the `fan_out_distribution` detector, its configuration, tests and related data-retrieval queries.

This review records what I checked, what I learned and what I found. It is not an approval of the pull request.

## What the detector is intended to do

The detector looks for an account that distributes money to multiple recipient accounts within a short period. It then checks for previous payment relationships between the distributor and recipients, and whether enough recipients paid or withdrew a substantial amount after receiving money.

With the default parameters, the detector evaluates each currency separately. A distribution window qualifies when:

- The account pays at least **10 different recipient accounts**.
- The payments total at least **5,000** in that currency.
- The distribution occurs within a **72-hour** window.
- No more than **20% of the recipients** had a payment relationship with the distributor during the previous **90 days**, in either direction.
- At least **50% of the recipients** meet the condition for paying or withdrawing at least **80% of what they received**, within the period examined by the code.
- The window starts at least 90 days after the first payment in the available data.

The last condition is intended to provide a look-back period before judging previous relationships. It does not by itself prove that the payment history of every account is complete.

The detector also calculates a pattern-strength score using the number of recipients, prior relationships, onward-payment share, and amount similarity or roundness. This score describes the strength of the match to the configured pattern; it is not a probability of wrongdoing.

A finding is a reason to examine the activity, not an accusation. Legitimate activity such as payroll or refunds can resemble parts of the pattern.

## Code and queries reviewed

I followed the main flow in `detect/src/neonradar_detect/detectors/fan_out_distribution.py`:

- `run` retrieves candidate accounts, payment times for account pairs and outgoing payments from recipients.
- `_evaluate` checks distribution windows separately by currency and applies the recipient, amount, relationship and onward-payment conditions.
- `_moved_on` checks outgoing payments against the amount a recipient received.
- `_finding` builds the finding, metrics, evidence edges, steps and pattern strength.

I also reviewed the `related_before` helper in `fan_in_collection.py` and these data-retrieval queries:

- `flows_by_outbound.cypher`
- `paid_time_range.cypher`
- `paid_times.cypher`
- `payments_from.cypher`

The candidate query first selects accounts with enough distinct payees in a fixed time bucket. The detector then evaluates its own sliding windows and applies the full conditions. With default parameters, the initial candidate threshold is five distinct payees in a bucket; the final distribution condition is ten distinct recipients.

## Finding 1: `round_unit = 0` is accepted but raises a division-by-zero error

**Status:** reproduced in memory and on an isolated Neo4j test database.

The typology configuration permits `0.0` as the minimum value for `round_unit`:

```yaml
round_unit:
  default: 100.0
  min: 0.0
  max: 1000.0
```

The catalog’s `params_for` validation accepted the override `{"round_unit": 0.0}`. However, when the detector found a qualifying synthetic distribution and began constructing the finding, it raised:

```text
ZeroDivisionError: division by zero
```

The `_round` function calculates a remainder using `round(unit * 100)` as the divisor. When `unit` is zero, that divisor is zero.

### Reproduction

1. Create synthetic payment history and a distribution that meets the detector’s default conditions.
2. Build the parameters through `catalog.params_for` with `round_unit` set to `0.0`.
3. Run the full detector.

The catalog accepted the parameter, but the detector raised `ZeroDivisionError` when building the finding. I reproduced this behaviour both in memory and in an isolated Neo4j test.

**Impact:** A value allowed by the configuration can stop the detector when a qualifying case reaches finding construction, instead of returning that finding.

The default value is `100.0`; the observed failure does not mean that the default configuration fails.

**Suggested follow-up:** Make the allowed parameter range and implementation consistent. The team can decide whether zero should be rejected or handled explicitly. The detector and typology are verbatim files from the code book, so the project’s specification workflow should be considered before changing them.

## Observation 2: an outgoing payment between two receipts is counted against both receipts

**Status:** behaviour reproduced in memory and on an isolated Neo4j test database. I did not find a clear statement in the reviewed specification that resolves how multiple receipts should be treated in this situation.

For each recipient, `_moved_on` sums the amounts received in the distribution window. It considers outgoing payments from the time of the **first receipt** until `onward_hours` after the **last receipt**.

I tested the following synthetic sequence for each recipient:

| Time | Activity |
|---|---|
| 10:00 | The recipient receives 100 from the distributor |
| 11:00 | The recipient pays 800 to another account |
| 12:00 | The recipient receives another 900 from the distributor |

The implementation sums the two receipts as **1,000** and counts the payment of **800** as meeting the default 80% condition, even though that outgoing payment happened before the second receipt.

When the sequence was repeated for ten synthetic recipients, the full detector produced **one finding** with:

```text
recipients: 10
onward_share: 1.0
```

The same behaviour was reproduced in an isolated Neo4j test.

This experiment does not establish the source of the outgoing money or prove that the implementation violates the intended design. The implementation may intentionally compare activity after the first receipt with the total received in the window. Documenting the intended treatment of multiple receipts and adding a test for it would make this behaviour clearer.

## Observation 3: the first-payroll test does not isolate the onward-payment condition

**Status:** test-coverage observation, supported by an additional in-memory experiment.

`test_first_payroll_is_not_found_because_salaries_stay` creates payroll payments without adding an earlier payment through `k.history()`.

The detector skips windows that start less than `prior_days` after the first payment in the data. In this test, the lack of earlier history can prevent the payroll window from being evaluated. Therefore, the empty result alone does not establish that the onward-payment condition was the reason no finding appeared.

I tested these synthetic cases:

| Case | Findings |
|---|---:|
| No earlier history; employees spend 250 of 2,000 | 0 |
| Earlier history added; employees spend 250 of 2,000 | 0 |
| Earlier history added; employees spend 1,900 of 2,000 | 1 |

The additional cases support testing the onward-payment condition with sufficient earlier history. A test that explicitly sets up that history would make the payroll test’s purpose clearer.

## Boundary and behaviour checks

I ran additional checks with synthetic data. These results apply to the tested examples; they are not an exhaustive proof of all possible cases.

### Recipient count, total amount and prior relationships

| Case | Result |
|---|---|
| 9 recipients, with the other tested conditions met | No finding |
| 10 recipients, with the other tested conditions met | 1 finding |
| Total of 4,999.90, with five recipients paying onward | No finding |
| Total of exactly 5,000, with five recipients paying onward | 1 finding |
| Four out of ten recipients pay onward | No finding |
| Five out of ten recipients pay onward | 1 finding |
| Two out of ten recipients have a prior relationship | 1 finding |
| Three out of ten recipients have a prior relationship | No finding |

### Previous-payment boundaries

I tested `related_before` directly:

- A payment from the distributor to the recipient 30 days before the window counted as a prior relationship.
- A payment in the opposite direction also counted.
- A payment exactly 90 days before the window counted.
- A payment at the exact start of the distribution window did not count as a prior payment.

These checks concern payments available in the data. They do not establish whether the parties have a longer-standing relationship outside the period or records examined.

### Distribution and onward-payment time boundaries

In the examples tested:

- Ten recipients split into two groups, with the second group just before the end of the 72-hour distribution window, produced one finding.
- When the second group’s payments occurred exactly at the end of that window, they did not belong to the first window, and the example produced no finding.
- For a recipient who received one payment of 1,000, an onward payment of 799.99 did not meet the default 80% condition; 800 did.
- An onward payment exactly 72 hours after that receipt was counted; one a second later was not.

The distribution window and onward-payment check use different endpoint comparisons in these cases. The multiple-receipt behaviour is described separately above.

### Currency

In the in-memory examples:

- Five EUR recipients and five USD recipients did not together meet the requirement of ten recipients in one currency.
- Outgoing payments in USD did not satisfy the onward condition for an EUR distribution.

### Candidate selection

I tested a synthetic distribution split across two fixed candidate buckets: five recipients before the bucket boundary and five after it, while all ten fell within the detector’s sliding distribution window. The full detector selected one candidate and produced one finding. This case was tested in memory and on Neo4j.

I also tested the candidate limit with two accounts that each met the conditions in the example:

| `max_candidates` | Candidates returned | Findings |
|---:|---:|---:|
| 100,000 | 2 | 2 |
| 1 | 1 | 1 |

The limit is a configured work limit. When it is reached, additional accounts may not have been evaluated; a smaller result should not by itself be interpreted as evidence that no other accounts matched.

### Findings and evidence

In one synthetic example with ten recipients and ten onward payments, the detector returned:

- One finding.
- Ten recipients and an `onward_share` of 1.0.
- Twenty evidence edges: ten distribution payments and ten onward payments.
- Two evidence steps.
- The expected currency.

This verifies the result for that example; it is not a complete audit of every possible evidence graph.

## Test results

All additional experimental payment data was synthetic.

| Check | Result |
|---|---|
| Original Fan-out tests in memory | 3 passed |
| Original Fan-out tests on isolated Neo4j | 3 passed |
| Additional isolated Neo4j tests | 3 passed |
| M3.5c verbatim-file check | 9 of 9 files matched the code book; 0 recorded deviations |
| Typology index check | Passed |
| `make check` Python suite | 2,290 passed; 84 deselected |
| Separate contract test run | 522 passed |
| Contract generated-file check | 4 generated files matched the models |
| Cypher lint | 83 statements checked; 0 problems |
| UI unit tests | 57 passed in 10 test files |
| Python lint, formatting and type checking | Passed |
| UI lint, formatting and type checking | Passed |

The contract tests overlap with the Python test collection and should not be added to the 2,290 as an independent total.

The three additional Neo4j tests covered the distribution across fixed buckets, the payment between two receipts, and `round_unit = 0`. The zero-value test passed because it **expected and observed** `ZeroDivisionError`; it does not mean the issue was fixed.

## Review limits

- This review focused on Fan-out and was not a full review of the other detectors or ADR-0024.
- The original Fan-out tests and three additional cases were run on Neo4j. Other additional boundary cases were tested in memory or directly against the relevant Python helper.
- The PR’s broader human-review focus mentions opening two `synth-demo` alerts in Neo4j Browser. I did not perform that step. The existing local database showed three `circular_flow` alerts, so I did not replace its data or detection results.
- These checks provide evidence for the tested cases; they do not prove that the detector is free of other issues.

## AI involvement

I used AI assistance to explain the code, prepare synthetic experiments and organise these review notes. I ran the commands locally and reviewed the outputs.
