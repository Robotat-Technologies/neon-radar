# 0015. Merge policy for listed and leaked records

- **Status:** proposed
- **Date:** 2026-10-22
- **Deciders:** @robotat-com (data steward, project lead, tech lead)

## Context

Entity resolution joins records that describe the same real person or organisation into one node of the graph (`docs/build/PHASE-2.md` 7.1). Some records carry flags: a sanctions list entry carries the topic `sanction`, a PEP source carries `role.pep` (PHASE-2.md 7.1.1), and the graph loader turns a node's topics into the labels `:Sanctioned` and `:PEP` (PHASE-1.md 5.2, PHASE-2.md 7.1.4). Records from the ICIJ Offshore Leaks Database carry no flag, but every node that contains one shows that record among its sources, so a merge with a leak record presents a person or company as named in a leak.

A wrong merge between a listed record and an unlisted one puts a sanctions or PEP flag on a real person or company who is not on any list. A wrong merge with a leak record ties a real person to a leaked file. Either error is the most harmful one this project can make (guardrails G1 and G8 in PHASE-2.md 2.1). Name similarity is a weak signal for these records:

- ICIJ warns that "many people and entities have the same or similar names" and suggests confirming identities "based on addresses or other identifiable information" [icij_faq].
- The sanctions authorities treat a name match as the start of a check, not a result. OFSI writes that a name match "does not necessarily mean" that the person dealt with is the one on the list, and that matching all the information on the list is likely to be a target match [ofsi_general_guidance_2026]. OFAC asks whether only the first or last name matches and whether the party has a different date of birth, identification number or nationality, and it does not confirm matches itself [ofac_faq_5]. The research note `docs/research/2026-10-18/sanctions-peps.md` (section 9) quotes this guidance and the EU best practices on identifiers.

## Options considered

1. **Merge by probability like every other record.** The most recall, but a probabilistic score is mostly a name score for list and leak records, so a homonym gets a flag it does not have. Rejected.
2. **Never merge listed or leaked records with other sources.** No false flag through resolution, but a sanctioned company that is also in the register stays two unrelated nodes even when both carry the same company number.
3. **Merge only through identifiers with an exact name, or a confirmed human decision; show everything else as a possible match** (chosen, the policy in PHASE-2.md 7.1.4).

## Decision

We will apply the merge policy of PHASE-2.md 7.1.4, which `resolve/src/neonradar_resolve/cluster.py` implements and `resolve/tests/test_cluster.py` and `resolve/tests/test_policy.py` test:

- **P1.** Two clusters whose flag topics differ (a listed and an unlisted cluster, or clusters listed for different reasons, such as a PEP record and a sanctions record) merge only through a deterministic identifier rule (D1 to D5: UK company number, LEI, Companies House person number, UN reference, native id) whose two records also share an exact name key, or through a human `same` decision (D7) that a second reviewer or a senior reviewer confirmed.
- **P2.** A leaked record joins a record of another kind only in the same way.
- **Possible matches instead.** Every other link between such records becomes a possible match, which the graph stores as an unconfirmed `POSSIBLY_SAME_AS` link and every text describes as "not confirmed" (PHASE-2.md 7.2). A possible match never moves a flag, a topic, a name or any other property between nodes.
- **No flag across a possible match.** Because P1 compares flag topics, a probabilistic merge only joins clusters that already carry the same flag topics, so it never adds a flag topic to any record's entity.
- **P3 to P6** keep name-only, capped, below-threshold and cross-list matches apart in the same way (7.1.4).

The cost is recall: some true matches between a list entry and a register record stay two nodes joined by a possible match. The precision report counts them as possible matches (PHASE-2.md 7.3), and a reviewer can confirm them one by one.

### Choices for the deciders

Each choice has the spec's default, which this pull request builds. Changing one after acceptance needs all three deciders and voids the evaluation sample (PHASE-2.md 2.5 item 10, G10).

| Choice | Default (built) | Alternative |
|---|---|---|
| A pair that breaks a hard cannot-link rule (X1 to X6, X8) | Suppressed: never shown as a possible match, only written to `conflicts.jsonl` | Show it to reviewers anyway |
| A human `same` decision that crosses P1 or P2 | Applies only when two reviewers' newest lines say `same`, or one of them is in `people.er_senior_reviewers` | One reviewer is enough |
| Addresses (rule D6) | Merge across datasets by address key without P2, because addresses carry no flags | D6 within one dataset only |
| Two listed person records from different lists, linked by probability (P6) | Merge only with compatible birth years on both sides or a shared identifier | Stricter: a shared identifier or an exact full birth date |

The form of the Companies House person number rule (D3: the first 8 characters of `person_number` with the name check, or the number for blocking only) is the tech lead's choice and is recorded in ADR-0014 (M2.10b); OD-22 accepted the default for the build.

## Consequences

- No flag reaches a person or company through a similar name. Flags join other records only through an identifier with an exact name key or a confirmed human decision.
- Some true matches stay unmerged and appear as possible matches; recall of these pairs is measured on the synthetic benchmark (`neonradar er bench`, "policy-blocked true pairs recalled as possible matches", PHASE-2.md 7.1.7).
- Human review becomes part of resolution: `neonradar er review` (M2.10c) records decisions with the reviewer's handle, and a decision that crosses P1 or P2 waits for a second reviewer or a senior reviewer (`decisions_awaiting_second_review` in `run.json`).
- The benchmark marks list-style and leak-style synthetic records (`nr.synthetic_kind`), so the policy is tested on every pull request without real data.

## Sources

- `docs/build/PHASE-2.md` 0.5 decision 3, 2.1 (G1, G8, G10), 7.1.1 to 7.1.6, 7.2.
- `docs/research/2026-10-18/sanctions-peps.md` section 9 (name matching guidance from the authorities).
- [icij_faq], [ofsi_general_guidance_2026], [ofac_faq_5] in `docs/sources/bibliography.yaml`.
