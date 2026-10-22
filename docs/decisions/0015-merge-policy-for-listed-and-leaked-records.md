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

- **P1.** Two clusters whose flag topics differ (a listed and an unlisted cluster, or clusters listed for different reasons, such as a PEP record and a sanctions record) merge only through a deterministic identifier rule (D1 to D5: UK company number, LEI, Companies House person number, UN reference, native id) whose two linked records also share an exact name key, or through a human `same` decision (D7) that a second reviewer or a senior reviewer confirmed. The name check compares the two linked records, not every record of the two clusters, so records that joined either cluster earlier come along (see "Properties the deciders should know").
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
| Addresses (rule D6) | Merge across datasets by address key without P2, because addresses carry no flags; each address links to the smallest record id of its key, and beyond 30 records the rest are refused (X7, property 3). Keys that are only a postcode (`N1 7GU\|`) also merge: open question F11 in `docs/build/phase-2-reconciliation.md` | D6 within one dataset only; skip postcode-only keys |
| Two listed person records from different lists, linked by probability (P6) | Merge only with compatible birth years on both sides or a shared identifier | Stricter: a shared identifier or an exact full birth date |
| A one-reviewer `same` decision followed by identifier links (property 1) | Interim guard in `run.py`: held back, and counted as awaiting a second review, when after the identifier links and the confirmed decisions its two records sit in clusters with different flag topics or leak status, or when, once it is applied, any record of its cluster ends up with other flag topics or leak status than in the run without any one-reviewer decision; when such a record sits outside every decision's cluster, all one-reviewer decisions are held back (fail closed). One-reviewer `different` decisions are not guarded (property 1) | A two-pass change to `cluster.py` (a spec change to 7.1.6) that judges D7 after D1 to D6 |
| The order of strict name checks (property 2) | 7.1.6's order (rule, then record ids), as the spec gives it | Remove the case `test_strict_name_check_outcome_depends_on_id_order` pins: take the links that cross P1 or P2 first, re-judging after every merge which links cross, or check the strict name key against every record of the cluster being joined (neither makes the whole clustering independent of order) |

The form of the Companies House person number rule (D3: the first 8 characters of `person_number` with the name check, or the number for blocking only) is the tech lead's choice and is recorded in ADR-0014 (M2.10b); OD-22 accepted the default for the build.

### Properties the deciders should know

Found in the M2.10a review on synthetic records (`resolve/tests/test_policy.py`); `docs/build/phase-2-reconciliation.md` 2.8 has the details.

1. **One reviewer and a later identifier link.** `cluster.py` (verbatim from PHASE-2.md 7.1.6) applies human decisions before D1 to D6 and judges the second-reviewer rule at that moment. A one-reviewer `same` decision between two unflagged records V and U is therefore applied, and a later D5 link from U to a listed record W (exact name) brings W's flag to V; with two decisions, the outcome also depended on which record id sorts first. A decision can also bring a flag to a third record: by merging two records it can make a later link break X5, X6, X8 or the X7 cap, so a record joins by D5 (no name check between clusters that do not cross) before a flag arrives through another link. Until the deciders choose, `run.py` runs the clustering once without the one-reviewer decisions, holds back each one whose two records then sit in clusters with different flag topics or leak status, applies the rest, and holds back again any whose cluster now holds a record with other flag topics or leak status than that record had without them (all of them if such a record sits outside every decision's cluster), until nothing changes; each one held back counts in `decisions_awaiting_second_review` (the tests `test_one_reviewer_*` in `test_policy.py`). A one-reviewer `different` decision is outside the guard, because the spec lets one reviewer keep two records apart (X8), and it too can move a flag to a third record: by keeping B from a listed record L2, it lets a record R with another name join B by D5 before a second listed record Z joins B by its own D5 link (`test_one_reviewer_different_decision_can_move_a_flag_today` pins this). The deciders may want `different` decisions under the same guard.
2. **The order of identifier links.** D1 links each record to the Companies House record of its number, and 7.1.6 takes links by record id. A registry record with a similar name ("Example Holdr Ltd") joins the company record by the ordinary name check if its link comes first; a list entry with the exact name then joins strictly, and the registry record ends up under the flag. If the list entry's link comes first, the registry record's link crosses P1 and fails the strict check, so it stays a possible match. UK, OFAC, UN and ICIJ ids sort after `gbch-` and EU ids before it, so the same facts give different results by list (`test_strict_name_check_outcome_depends_on_id_order`). Two rules remove this case: take the links that cross P1 or P2 before the others, re-judging after every merge which of the remaining links cross (without re-judging, a link C–L between two unflagged records that starts to cross once L joins a listed record M is still taken with the ordinary links, so a record R that joins C by a similar name first ends up with the flag), or check the strict name key against every record of the cluster being joined. With either, the registry record of the pinned case never ends up with the list entry's flag, whatever the ids. Neither makes the whole clustering independent of order: a company record linked by D1 to two list entries with the same flag, one with the exact name and one with a similar name, still takes in the second only if the first one's link comes first (after that the two clusters carry the same flag topics, so the ordinary name check applies). Both change `cluster.py`.
3. **Large address groups.** When more than 30 `Address` records share a key, the 29 that link first (by record id) merge with the smallest id and the rest are refused under X7: they stay separate address nodes, never possible matches.

## Consequences

- A flag joins another cluster only through an identifier link whose two linked records share an exact name key, or through a confirmed human decision; a probabilistic or similar-name link never carries one. Every record already in the other cluster comes along: records that joined it by D1 to D4 with a similar name, by D5 whatever their name (D5 has no name check between clusters that do not cross P1 or P2), or by a confirmed decision. Which records are already there when the flag arrives depends on the order of record ids (property 2).
- Some true matches stay unmerged and appear as possible matches; recall of these pairs is measured on the synthetic benchmark (`neonradar er bench`, "policy-blocked true pairs recalled as possible matches", PHASE-2.md 7.1.7).
- Human review becomes part of resolution: `neonradar er review` (M2.10c) records decisions with the reviewer's handle, and a decision that crosses P1 or P2 waits for a second reviewer or a senior reviewer (`decisions_awaiting_second_review` in `run.json`). Whether a one-reviewer decision crosses is judged after the identifier links and the confirmed decisions have run, for any record of the cluster it ends up in, by the interim guard in `run.py` (property 1); `cluster.py` alone judges it for the two records only, before the identifier links.
- The benchmark marks list-style and leak-style synthetic records (`nr.synthetic_kind`), so the policy is tested on every pull request without real data.

## Sources

- `docs/build/PHASE-2.md` 0.5 decision 3, 2.1 (G1, G8, G10), 7.1.1 to 7.1.6, 7.2.
- `docs/research/2026-10-18/sanctions-peps.md` section 9 (name matching guidance from the authorities).
- [icij_faq], [ofsi_general_guidance_2026], [ofac_faq_5] in `docs/sources/bibliography.yaml`.
