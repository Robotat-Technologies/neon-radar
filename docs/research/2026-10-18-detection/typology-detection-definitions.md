# NeonRadar phase 3: typology definitions for detection

Research date: Sunday 18 October 2026. Every web source in "Sources" was opened today, with WebFetch for government and publisher sites (the shell reaches only GitHub and package hosts) and with git for the one GitHub file; WebFetch returns extracts with quotes capped at about 125 characters, so long passages were read as consecutive segments and joined; where a page was too long for the tool, the official text was read from a mirror that reproduces it, marked "read via mirror"; footnote markers are dropped and curly quotes are written as straight quotes; anything not confirmed today is marked UNVERIFIED; local project files are marked "local".

## 0. Answers for the spec writer

1. **US structuring threshold.** A currency transaction report covers cash "of more than $10,000" [T2], aggregated for the same person "during any one business day" [T3]. So 10,000 exactly is below the threshold. The default band should be closed at the top: 9,000 to 10,000 inclusive.
2. **US structuring definition.** Structuring is defined by purpose, "in any amount", "on one or more days", and "need not exceed the $10,000 reporting threshold at any single financial institution on any single day" [T1]. A daily total above the threshold must be a strength factor, not a requirement. Use a multi-day window (default 7 days, a modelling choice).
3. **UK thresholds.** No UK source read today sets a bank cash report like the US one (UNVERIFIED as a negative). The UK thresholds are customer due diligence and dealer thresholds. Since 30 June 2026 they are in sterling [T31]: GBP 12,000 for occasional transactions and GBP 10,000 in cash for high value dealers, each "whether the transaction is executed in a single operation or in several operations which appear to be linked" [T29][T30]. HMRC treats cash payments "artificially" broken into smaller payments as linked [T34][T35].
4. **EU thresholds.** The AML Regulation (EU) 2024/1624 applies from 10 July 2027 [T58]. It sets EUR 10,000 for due diligence on occasional transactions, a EUR 10,000 cash payment limit, and an FIU report for cash payments or deposits above that limit made at banks, e-money issuers and payment service providers [T58]. AMLA's final draft standard (30 September 2026) lists criteria for linked transactions. It sets a one-month look-back for bureaux de change, money remitters and some crypto-asset services [T59].
5. **Bound semantics matter.** The US says "more than", the UK "at least" and "or more", the EU "at least" [T2][T29][T58]. Store each threshold with an inclusive or exclusive flag, as Phase 2 does for share bands.
6. **Pass-through dwell time.** No source gives hours. The sources say "little time elapsing" [T8], "Almost immediately" [T6], "within a few days of receipt" [T17] and "a small end-of-day balance" [T20]. A default of 72 hours and a residual of at most 10 percent are modelling choices anchored on "a few days".
7. **Layering.** No source gives a hop count, so 3 hops stays a modelling choice. Allow up to 20 percent total shrinkage: Europol puts professional launderers' fees at "5-20 % of the laundered sum" [T25]. The same figure supports the circular-flow return ratio of 0.8.
8. **Circular flow, same holder.** The variant is supported. Proxy networks return funds "to the accounts controlled by the initial clients" [T17]. Annex E flags a customer who is "both the ordering and beneficiary customer" [T22]. A country-level circle [T20] needs account country data that C2 does not hold.
9. **Fan-in.** Test "recently opened" or "used briefly" on the collector and first-layer accounts, not on the senders [T6][T18][T25]. Senders are often victims [T27]. One sourced number exists: one person opening accounts "at three or more financial institutions within 20 days" [T18].
10. **Dormancy.** No AML source states a period. UK statute calls a bank account dormant after 15 years without customer transactions [T38]; that is an unclaimed-balance rule, not an AML period. Keep 180 days as a modelling choice. The FFIEC flag is "an account with little activity" [T6], so model low activity, not zero activity. Guard against missing history that only looks like dormancy.
11. **Shell chain.** Use the Annex E shell company indicators [T22]. Sources give no number of layers. FinCEN: "Most shell companies are formed by individuals and businesses for legitimate reasons." [T11]
12. **Mass registration.** Exclude the three Companies House default addresses [T43]. Since 4 March 2024 a UK registered office must be an "appropriate address" [T40][T41]. A PO box is not allowed, but an agent's address is allowed if it meets the conditions [T42]. The count threshold is a modelling choice; use a percentile of the loaded data.
13. **Sanctions, US.** The test is 50 percent or more, added up across all blocked owners and programmes [T13]. Blocked status passes entity by entity (FAQ 401) [T13]. Ownership only: control does not count (FAQ 398) [T13], though OFAC asks for caution [T12].
14. **Sanctions, UK.** The test is more than 50 percent of shares or voting rights, or the right to appoint or remove a majority of the board, directly or indirectly, plus a control limb [T36][T37]. Indirect holdings pass only along a chain of "majority stake" links [T37]. OFSI does not add different designated persons' holdings together unless there is a joint arrangement [T36].
15. **Sanctions, EU.** The current Council guidance says "50% or more" of proprietary rights, not "more than 50%" [T61][T62]. Holdings are added together (the 30 plus 25 example) [T61][T63]. Control criteria (a) to (h) apply [T61][T62]. No chain rule is written down: pass status entity by entity, like OFAC, and label it an interpretation.
16. **Bands.** Compute a "certain" set and a "possible" set by fixed-point iteration on lower and upper bounds, with open or closed flags. Report three outcomes: met on the records, left open by the bands, not met on the records. Never multiply shares down a chain for these tests. Seed each test only with its own regime's list (UK: asset freeze designations).
17. **Formation agents and ACSPs.** The ACSP regime has been in force since 18 March 2025 [T44]. The rule that only ACSPs or verified persons may file is not in force: section 1067A is prospective [T45]. Companies House says "no earlier than November 2027" [T46]; its GOV.UK guidance still says November 2026 [T47]. Public officer data now names the ACSP that verified an officer [T51].
18. **Directors.** Identity verification has been required for new directors since 18 November 2025 [T48][T49]. Existing directors must verify by their next confirmation statement within "the period of 12 months beginning with 18th November 2025" [T49]. Verification proves identity, not independence. It does not reveal nominees.
19. **PEPs.** Use one family hop only: spouse or civil partner, children and their spouses or partners, parents (MLR 2017 reg 35(12)(b)) [T32], plus siblings (FCA) [T33]. Use one associate hop only, for joint or sole beneficial ownership or close business relations (reg 35(12)(c)) [T32]. Family and associate measures stop when the PEP leaves office (reg 35(11)) [T32]. The PEP stays in scope for at least 12 months (reg 35(9)) [T32]. Domestic PEPs start from a lower risk (reg 35(3A)) [T32].
20. **Cash commingling.** Compare with peers of the same sector and the same area. FFIEC compares with "similar restaurants in the area" [T7].
21. **TBML.** Keep it explainer only. About 80 percent of trade processed by banks is open account, and "no single stakeholder" holds the data needed [T19].
22. **Real entities.** Real entities receive only synthetic background activity [T73]. So every transaction-typology alert about a real entity is an artefact of the generator. Do not emit these alerts for real entities, or keep them in a review-only view.
23. **Wording.** Entity-facing headlines should describe the shape ("8 cash deposits between 9,000 and 10,000 USD within 4 days"), not the typology name. "Structuring" in US law contains "the purpose of evading" [T1]. A "grounds to investigate" meaning can itself be defamatory in England and Wales [T54].
24. **Data protection.** Profiling covers evaluating "reliability, behaviour" [T55]. UK GDPR Articles 22A to 22C, which replaced Article 22, have applied in full since 5 February 2026 [T55] (Article 22D not read today). An alleged offence is criminal offence data [T56]. By default, findings must not be open to "an indefinite number of natural persons" [T55]. Keep detectors as rules written by people (outside the AI Act definition, recital 12 [T66]). Do not publish real-entity alerts.
25. **PHASE-1.md 7.2 conflicts.** Seven entries disagree with the sources in some respect: structuring, circular_flow, fan_in_collection, dormant_reactivation, sanctions_exposure, pep_exposure and cash_commingling (section 17). The Phase 1 research note has three quotes to correct, and the brief's EU threshold is out of date (section 17.2).

## 1. structuring

**Definition (US).**
- The report: "Each financial institution other than a casino shall file a report of each deposit, withdrawal, exchange of currency or other payment or transfer, by, through, or to such financial institution which involves a transaction in currency of more than $10,000, except as otherwise provided in this section." [T2]
- Aggregation: "multiple currency transactions shall be treated as a single transaction" if the institution knows they are by or for the same person and they total more than $10,000 "during any one business day" [T3].
- The prohibition: "No person shall for the purpose of evading the transactions in currency reporting requirements of this chapter with respect to such transaction:" ... "(c) Structure (as that term is defined in § 1010.100(xx)) or assist in structuring, or attempt to structure or assist in structuring, any transaction with one or more domestic financial institutions." [T4]
- The regulatory definition, 31 CFR 1010.100(xx): "Structure (structuring). For purposes of § 1010.314, a person structures a transaction if that person, acting alone, or in conjunction with, or on behalf of, other persons, conducts or attempts to conduct one or more transactions in currency, in any amount, at one or more financial institutions, on one or more days, in any manner, for the purpose of evading the reporting requirements under §§ 1010.311, 1010.313, 1020.315, 1021.311 and 1021.313 of this chapter. "In any manner" includes, but is not limited to, the breaking down of a single sum of currency exceeding $10,000 into smaller sums, including sums at or below $10,000, or the conduct of a transaction, or series of currency transactions at or below $10,000. The transaction or transactions need not exceed the $10,000 reporting threshold at any single financial institution on any single day in order to constitute structuring within the meaning of this definition." [T1]
- FFIEC: "In addition, structuring may occur before a customer brings the funds to a bank." and "Even if structuring has not occurred, the bank should review the transactions for suspicious activity." [T5] FFIEC also mentions amounts "possibly in amounts less than the $3,000 recordkeeping threshold" for monetary instruments [T5].
- Smurfing: ""Smurfs" are teams of persons who, acting in conjunction with or on behalf of other persons, structure financial transactions for the purpose of evading the requirement to file a Currency Transaction Report." (FIN-2025-A003, footnote 35, p. 6) [T9]
- FATF: "The launderer deposits the money in amounts under the reporting threshold to avoid detection." (PML 2018, p. 19) [T17]. Placement "might be done by breaking up large amounts of cash into less conspicuous smaller sums that are then deposited directly into a bank account," [T16]
- Europol defines smurfing as "A money laundering method used to split illicit proceeds into smaller sums before placing these small amounts into the financial system to avoid suspicious transaction reporting." (EFECTA 2023, p. 12) [T25]. Note the aim is to avoid suspicion reports, not a fixed threshold.

**What UK sources say about cash just below thresholds.**
- MLR 2017 reg 27(2): due diligence applies to "an occasional transaction that amounts to £12,000 or more, whether the transaction is executed in a single operation or in several operations which appear to be linked." [T29]
- Reg 27(3): "A high value dealer must also apply customer due diligence measures if that dealer carries out an occasional transaction in cash that amounts to £10,000 or more, whether the transaction is executed in a single operation or in several operations which appear to be linked." [T29]
- Reg 14 defines a high value dealer by "a payment or payments in cash of at least £10,000 in total, whether the transaction is executed in a single operation or in several operations which appear to be linked;" [T30]
- These sums replaced euro figures on 30 June 2026 under The Money Laundering and Terrorist Financing (Amendment) Regulations 2026 (S.I. 2026/621), reg 14 [T31]. Reg 27(1)(b) now uses GBP 800 for transfers of funds [T29].
- HMRC: "A linked transaction can occur when a customer wants to break down cash payments:" ... "artificially from one payment into smaller payments" ... "to avoid detection and not follow the requirements under the Money Laundering Regulations" [T34]. On deposits into a dealer's business account from various locations: "Attention should be paid to the timings and frequency of these linked cash payments" and "they may be split up on purpose to avoid being noticed." [T34]
- HMRC treats multiple cash payments against one invoice that together exceed GBP 10,000 as linked "regardless of how long it takes to make this payment." [T35]
- No UK source read today sets a bank cash-deposit report like the US one (UNVERIFIED as a negative). UK reporting found today is suspicion based or tied to due diligence.

**What EU sources say.**
- AMLR Article 19(1)(b): due diligence "when carrying out an occasional transaction of a value of at least EUR 10 000, or the equivalent in national currency, whether that transaction is carried out in a single operation or through linked transactions, or a lower value laid down pursuant to paragraph 9;" [T58]
- AMLR Article 2: "'linked transactions' means two or more transactions with either identical or similar origin, destination and purpose, or other relevant characteristics, over a specific period;" [T58] (point number, about 20, UNVERIFIED).
- AMLR Article 80(1): "Persons trading in goods or providing services may accept or make a payment in cash only up to an amount of EUR 10 000 or the equivalent in national or foreign currency, whether the transaction is carried out in a single operation or in several operations which appear to be linked." [T58]
- Article 80(4) exempts "payments or deposits made at the premises of credit institutions", electronic money issuers and payment service providers, but: "Payments or deposits referred to in the first subparagraph, point (b) above the limit shall be reported to the FIU within the deadlines imposed by the FIU." [T58] Analysis: from 10 July 2027 this works like a cash deposit report above EUR 10,000. How FIUs apply the linked-operations wording to it is UNVERIFIED.
- Application: "It shall apply from 10 July 2027, except in relation to obliged entities referred to in Article 3, points (3)(n) and (o), to which it shall apply from 10 July 2029." [T58]
- AMLA's final draft standard under AMLR Article 19(9) (report dated 30 September 2026; still subject to Commission review) [T59]: the factsheet frames it as "To avoid circumvention of the thresholds mentioned in Article 19". Draft Article 3(1) lists criteria including "transactions performed or received by the same natural or legal person;", "customers who are family members;", "customers who are operating in concert;", "use of the same digital infrastructure;" and "transactions performed within a short time frame," "taking into account the nature of the business, including the speed and frequency with which transactions are typically carried out, and the size of the obliged entity." Draft Article 3(2): bureaux de change, money remitters and some crypto-asset service providers "at least take into account the criterion of a period of one month" [T59].
- EBA risk factor guidelines ask: "Are there grounds to suspect that the customer is trying to evade specific thresholds such as those set out in Article 11(b) of Directive (EU) 2015/849 and national law where applicable?" (Guideline 2, p. 29) [T60]

**Thresholds the detector must carry.**

| Rule set | Threshold | Is exactly 10,000 "below"? | Aggregation | Source |
|---|---|---|---|---|
| `us_ctr` | more than USD 10,000 | yes (not reported) | same person, one business day | [T2][T3] |
| `us_monetary_instruments` | USD 3,000 recordkeeping | n/a | not read today (UNVERIFIED rule text) | [T5][T6] |
| `uk_hvd` | GBP 10,000 or more in cash | no (caught) | "appear to be linked" | [T29][T30] |
| `uk_occasional` | GBP 12,000 or more | no (caught) | "appear to be linked" | [T29] |
| `eu_amlr_cdd` (from 10 July 2027) | at least EUR 10,000 | no (caught) | linked transactions | [T58] |
| `eu_amlr_cash_limit` (from 10 July 2027) | cash allowed "up to" EUR 10,000 | yes (allowed) | "appear to be linked" | [T58] |

**Red flags a graph can see (C2).**
- Many `PAID` edges with `channel = 'cash_deposit'` into one `Account`, each inside the band, within the window [T6]: "Currency is deposited or withdrawn in amounts just below identification or reporting thresholds."
- Deposits from several `cash_ledger` accounts (branches): "Deposits are structured through multiple branches of the same bank or by groups of people who enter a single branch at the same time." [T6]
- Deposits into several accounts of one holder or of linked holders: "Customer makes multiple and frequent currency deposits to various accounts that are purportedly unrelated." [T6]
- Consolidation and onward transfer: "A customer deposits funds into several accounts, usually in amounts of less than $3,000, which are subsequently consolidated into a master account and transferred outside of the country," [T6]
- Not visible in C2: who carried the cash, branch location, ATM use, safe deposit box visits, and above all the purpose, which the definition requires [T1].

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `rule_set` | `us_ctr` for USD accounts; `uk_hvd` for GBP; `eu_amlr_cdd` for EUR | thresholds above [T2][T29][T58]; the mapping by currency is a modelling choice |
| `threshold` | 10,000 in account currency | [T2][T30][T58] |
| `threshold_counts_as_below` | true for `us_ctr`; false for UK and EU rule sets | [T2][T29][T58] |
| `band_pct` | 10 | modelling choice; FFIEC says "just below" and "at or just under $10,000" with no width [T6] |
| `window_days` | 7 (30 for money-remitter or bureau accounts) | 7 is a modelling choice within "one or more days" [T1]; 30 follows the draft one-month criterion [T59] |
| `min_deposits` | 3 | modelling choice |
| `min_cash_sources` | 2, as a strength factor | multiple branches [T6] |
| `window_total_above_threshold` | strength factor, not a filter | [T1] |
| `secondary_threshold` | 3,000 for USD accounts, as a strength factor | [T5][T6] |

**Look-alikes and what tells them apart.**
- Cash businesses banking daily takings. FFIEC: "Most of these businesses are conducting legitimate business;" [T7]. Tell: amounts vary with trading days; one depositor at the home branch; a steady pattern over months; cash share consistent with the sector.
- ATM deposit limits. FFIEC flags "several bank deposits below a specified threshold" at an ATM [T6], so a machine limit makes the same shape. Tell: the cap sits at the machine limit, not near 10,000.
- Fixed weekly savings. Tell: one round amount on a fixed weekday, no onward transfer.
- Insurance or cash-in-transit caps (Phase 1 hypothesis; not checked today, UNVERIFIED). Tell: one carrier, regular schedule.

**What would make an alert misleading.**
- Applying the US band to UK or EU accounts. UK banks have no CTR to avoid (UNVERIFIED as a negative).
- Currency conversion at the wrong date moves amounts across the band.
- Real entities: their payments are synthetic background activity [T73]. Any alert on a real entity is an artefact.
- The name. "Structuring" means acting "for the purpose of evading" [T1]. A headline that names it about a real entity imputes purpose. Use a shape headline.
- A generator where every sub-threshold deposit is planted. The Phase 1 note warns that benign sub-threshold deposits must exist at realistic rates [T74].

## 2. rapid_pass_through

**Definition.**
- FinCEN funnel account: "An individual or business account in one geographic area that receives multiple cash deposits, often in amounts below the cash reporting threshold, and from which the funds are withdrawn in a different geographic area with little time elapsing between the deposits and withdrawals." (FIN-2014-A005) [T8]
- FATF and Egmont: "An account of a trade entity appears to be a "pay-through" or "transit" account with a rapid movement of high-volume transactions and a small end-of-day balance without clear business reasons," (TBML indicators 2021, p. 7) [T20]
- Annex E shell indicator: "Exclusively facilitates transit transactions and does not appear to generate wealth or income (transactions appear to flow through the company in a short period of time with little other perceived purpose)" (p. 185) [T22]
- FFIEC: "Many small, incoming transfers of funds are received, or deposits are made using checks and money orders. Almost immediately, all or most of the transfers or deposits are wired to another city or country in a manner inconsistent with the customer's business or history." [T6]

**Dwell time as the sources describe it.**

| Words | Source |
|---|---|
| "with little time elapsing between the deposits and withdrawals" | [T8] |
| "Almost immediately, all or most of the transfers or deposits are wired to another city or country" | [T6] |
| "a rapid movement of high-volume transactions and a small end-of-day balance" | [T20] |
| "transactions appear to flow through the company in a short period of time" | [T22] |
| "Most of the funds were transferred out or withdrawn within a few days of receipt," (PML Box 4, p. 23) | [T17] |
| "Funds are thereafter rapidly layered through a series of "pass-through" transactions" (para 28, p. 21); transactions "executed at near-instantaneous speeds" (p. 4) | [T18] |
| mule accounts "which remain open for a short period of time for quick transfer of funds" (p. 15) | [T25] |

No source gives a number of hours or days.

**Red flags a graph can see.**
- Inflow in a window that leaves again within the dwell limit, with a small residual [T20].
- Many inbound sources, few outbound beneficiaries: "Multiple accounts are used to collect and funnel funds to a small number of foreign beneficiaries, both persons and businesses, particularly in higher-risk locations." [T6]
- Debits unrelated to the holder's stated business: "the debits do not appear to be related to the stated business activity of the account holder." [T8] (graph proxy: counterparty sector against holder `sector`).
- A new account, or one used briefly [T6][T25].
- Not visible in C2: the geography of deposits and withdrawals, which defines a funnel account [T8]; depositors who "may have no detailed knowledge" of the account [T8]; pre-signed cheques [T8].

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `max_dwell_hours` | 72 | modelling choice anchored on "within a few days of receipt" [T17] |
| `min_pass_ratio` | 0.9 (outflow over inflow) | modelling choice; "small end-of-day balance" [T20] |
| `min_inbound_sources` | 3 | modelling choice |
| `max_outbound_beneficiaries` | 3, as a strength factor | modelling choice; "small number of foreign beneficiaries" [T6] |
| `window_days` | 7 | modelling choice |
| `min_inflow` | 10,000 in account currency | modelling choice |

**Look-alikes.** Payment service providers, payroll bureaus, escrow and client accounts, marketplace settlement and treasury sweeps (PHASE-1 7.2). Correspondent and intermediary accounts are pass-through by nature; Wolfsberg says intermediaries see "limited information" and should not carry the originator's obligations [T28]. Tells: `account_type` or `account_kind` (client money, settlement), references on payments, stable schedules, long history, counterparties that fit the business.

**Misleading alerts.** A one-bank view hides where money really ends. Timestamps are UTC, so "same day" depends on time zone. Missing `account_kind` makes every intermediary look like a conduit. Real-entity artefacts as in section 1.

## 3. layering_chain

**Definition.**
- FATF: in layering "the launderer engages in a series of conversions or movements of the funds to distance them from their source." Examples: "or the launderer might simply wire the funds through a series of accounts at various banks across the globe." and "In some instances, the launderer might disguise the transfers as payments for goods or services, thus giving them a legitimate appearance." [T16]
- FATF PML: proxy schemes "consist of multiple layers of shell companies in different jurisdictions" (p. 26); "The funds from different clients are mixed within the same accounts, which makes the tracing of funds" difficult (p. 18) [T17].
- Europol: "Multiple layers of shell companies set up in various jurisdictions, sometimes offshore" (p. 16) [T25].
- FATF and Egmont: "Adding numerous layers of ownership between an asset and the beneficial owner in different jurisdictions," (para 55, p. 27) [T21].
- FinCEN: "Multiple high-value payments or transfers between shell companies with no apparent legitimate business purpose." [T11]

**Red flags a graph can see.**
- A time-ordered `PAID` path of 3 or more hops through accounts of different holders, each hop quick, amounts kept within a fee range.
- Intermediaries with little other activity and no payroll or supplier pattern; Annex E lists "No personnel (or only a single person as a staff member)" and "Pays no taxes, superannuation, retirement fund contributions or social benefits" [T22].
- Intermediaries that share an address, agent or director: "Transacting businesses share the same address, provide only a registered agent's address, or raise other address-related inconsistencies." [T11]
- Payment purposes that are empty or only an invoice number: "Payments have no stated purpose, do not reference goods or services, or identify only a contract or invoice number." [T11]
- Hops across jurisdictions [T17][T25].

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_hops` | 3 | modelling choice (no source gives a count) |
| `max_hops` | 6 | modelling choice; C2 caps traversals at 8 |
| `max_hop_dwell_hours` | 72 | modelling choice, as section 2 [T17] |
| `min_end_to_end_retention` | 0.8 | Europol: fees are "5-20 % of the laundered sum" (p. 12) [T25]; it is a total, not per hop |
| `allow_split_merge` | true | modelling choice; mixing in the same accounts [T17] |
| `intermediary_max_other_paid_30d` | 5 | modelling choice |
| `shared_link_bonus` | shared address, agent or director | [T11][T22] |

**Look-alikes.** Intra-group treasury, multi-tier supply chains, correspondent hops [T28], fund structures. Tells: group links (`OWNS` above 50 percent, `CONSOLIDATES`), invoice references, periodic timing, intermediaries with payroll and suppliers.

**Misleading alerts.** Money is fungible and mixed [T17], so linking an inbound payment to an outbound one is an allocation rule (a modelling choice), not a fact. Partial visibility can make two unrelated payments look like one chain. Entity resolution errors change which holders count as "different".

## 4. circular_flow

**Definition.** Sources describe the circle at three levels.
- Countries: "Payments are routed in a circle" (then, after a dash in the original) "funds are sent out from one country and received back in the same country, after passing through another country or countries." (TBML indicators, p. 7) [T20]
- Accounts: under "The transaction:", Annex E lists one that "appears cyclical (outgoing and incoming transactions are similar in size and are sent to, and received from, the same accounts, indicating that outgoing funds are being returned with little loss)" and calls it round-robin (p. 186) [T22].
- Banks: "Suspicious movements of funds occur from one bank to another, and then funds are moved back to the first bank." [T6]

**The same-holder variant.** It is supported. FATF proxy networks, step 5: "Funds are returned to the accounts controlled by the initial clients," (p. 27) [T17]. Annex E: "The customer is both the ordering and beneficiary customer for multiple outgoing international funds transfers" (p. 185) [T22].

Variants for the detector:
- V1: back to the same account (Phase 1, M1.9b).
- V2: back to another account with the same `HOLDS_ACCOUNT` holder (resolved entity) [T17][T22].
- V3: back to an account of a company in the same ownership group (`OWNS` above 50 percent or `CONSOLIDATES`). Modelling choice with high look-alike risk.
- V4: back to the same country. Needs account country data; out of scope in C2.

**Starting parameters** (M1.9b defaults, kept).

| Parameter | Default | Basis |
|---|---|---|
| `min_hops` | 2 | Annex E "sent to, and received from, the same accounts" allows a two-hop loop [T22] |
| `max_hops` | 6 | modelling choice |
| `max_window_days` | 14 | modelling choice |
| `min_return_ratio` | 0.8 | "returned with little loss" [T22]; Europol fee range [T25] |
| `same_holder_variant` | on (V2) | [T17][T22] |
| `group_variant` | off by default (V3) | modelling choice |

**Look-alikes.** Refunds and reversals, loan drawdown and repayment, foreign exchange legs, cash pooling, dividends followed by capital injections (PHASE-1 7.2). For V2, the commonest look-alike is a person moving money between their own accounts through a wallet or broker. Tells: exact-amount reversals, loan or invoice references, counterparty type (payment service provider), regular schedules.

**Misleading alerts.** A false entity-resolution merge creates V2 loops between two different people. Multi-currency loops can show a false "loss". A V3 alert on a real group is routine treasury in most cases.

## 5. fan_in_collection

**Definition.**
- Europol: "A money mule is a person who receives money from a third party in their bank account and transfers it to another one or takes it out in cash and gives it to someone else, obtaining a commission for it." and "More than 90% of money mule transactions identified through the European Money Mule Actions are linked to cybercrime." [T27]
- FinCEN: a money mule is "a person who transfers illegally acquired money on behalf of or at the direction of another." (FIN-2020-A003, p. 5) [T10]. Mules may be unwitting ("unaware that he or she is part of a larger criminal scheme."), witting or complicit [T10].
- FATF PML: "Money mules may be knowingly complicit in the laundering of funds or work unwittingly, or negligently, on behalf of a PMLN or OCG." (p. 22) and "Bank accounts, opened by the mules, serve as the initial layering stage in the laundering process." (p. 24) [T17]

**Recently opened and briefly used accounts.**
- "Customer conducts large deposits and withdrawals during a short time period after opening and then subsequently closes the account or the account becomes dormant." [T6]
- "Some money mules might also only allow their accounts to be used for a specific and limited period of time" (para 28, p. 21) [T18]
- Mules "open several bank accounts in one or more countries, which remain open for a short period of time for quick transfer of funds" (p. 15) [T25]
- An FIU profile flagged "bank accounts opened by a single individual at three or more financial institutions within 20 days" (Box 23, p. 36) [T18]

**Mule ring indicators.**
- "hopping through accounts across different financial, remittance or payment service providers" (para 29, p. 21) [T18]
- "commonalities such as common banking transactions, data points (foreign contact information and device ID)" (Box 15, p. 26) and "the fraudulent transactions were performed via the same login IP addresses" (Box 20, p. 33) [T18]
- "Money mule recruiters are also known as mule 'herders.'" (para 24, p. 17) [T18]
- Recruitment: "Mules are recruited intensively through social media, particularly in fraud schemes." and "Investigations reveal recruitment of students, migrants, and vulnerable people in financial need." (p. 14) [T25]
- Holder profile: a customer who "reports their occupation during customer onboarding as a student, retiree, housewife, or other low-income occupation but has unexplained wealth." and one who "regularly deposits large volumes of cash or cashier's checks, or receives multiple wire, ACH, or P2P transfers for no business or apparent lawful purpose." (FIN-2025-A003, p. 9) [T9]

**Red flags a graph can see.** One account paid by many accounts with no earlier `PAID` in either direction; senders not connected to each other; a collector opened recently (`opening_date`) or active only briefly; onward transfer or cash withdrawal soon after; one holder with accounts at several banks opened close together; collectors that share senders or forward to the same aggregator (a ring). Not visible in C2: devices, IP addresses, contact details, occupation.

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_distinct_senders` | 10 | modelling choice |
| `window_days` | 7 | modelling choice |
| `no_prior_relation_lookback_days` | 90 | modelling choice |
| `collector_max_age_days` | 90, as a strength factor | modelling choice; sources say "short time period after opening" with no number [T6][T25] |
| `onward_ratio_min` | 0.8 within 72 hours | modelling choice, as section 2 |
| `multi_bank_min_banks` | 3 | Box 23 [T18] |
| `multi_bank_window_days` | 20 | Box 23 [T18] |
| `ring_method` | weakly connected components over the last 30 days of `PAID`, then Louvain | modelling choice (PHASE-1 7.2) |

**Look-alikes.** Charities and donation drives, crowdfunding, landlords, clubs, small online sellers, tutors, school fees (PHASE-1 7.2). Tells: long-lived collector of a matching type, periodic payments (monthly rent), references, money retained or spent on suppliers rather than forwarded.

**Misleading alerts.** Senders are often victims [T27]; text must never describe them as participants. A one-bank view hides the onward leg. Entity resolution errors can merge or split collectors.

## 6. fan_out_distribution

**Definition.**
- FinCEN: "An unusually large number and variety of beneficiaries receive wire transfers from one company." [T11]
- FFIEC: "Unusually large number and variety of beneficiaries are receiving funds transfers from one company." [T6]
- FATF and Egmont: "Incoming wire transfers to a trade-related account are split and forwarded to non-related multiple accounts that have little or no connection to commercial activity." (p. 7) [T20]

**Red flags a graph can see.** High out-degree in a short window; recipients without earlier payments; similar or round amounts; recipients that withdraw cash or forward money soon after; a fan-out that follows a fan-in (gather then scatter).

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_distinct_recipients` | 10 | modelling choice |
| `window_hours` | 72 | modelling choice |
| `amount_cv_max` | 0.2, as a strength factor | modelling choice |
| `round_amount_share` | 0.5, as a strength factor | modelling choice; the round-amount indicator in [T20] is about trade |
| `recipient_onward_hours` | 72 | modelling choice |
| `no_prior_relation_lookback_days` | 90 | modelling choice |

**Look-alikes.** Payroll, supplier batches, dividends, benefits, insurance payouts, refunds after a cancelled event, marketplace payouts. Tells: monthly periodicity, references (employee or invoice IDs), recipients with long histories who keep the money, a sender whose type fits (employer, insurer).

**Misleading alerts.** The Phase 1 generator gives real entities payroll fan-outs as background activity [T73]. A detector that cannot tolerate payroll will flag real employers.

## 7. dormant_reactivation

**What sources mean by dormant or inactive.**
- FFIEC: "Conversely, an account with little activity may suddenly experience large deposit and withdrawal activity." It also describes heavy use soon after opening, after which "the account becomes dormant." [T6]
- FATF and Egmont: "A newly formed or recently re-activated trade entity engages in high-volume and high-value trade activity," (p. 5) and "A trade entity has unexplained periods of dormancy." (p. 4) [T20]
- Annex E: legal persons that "have demonstrated a long period of inactivity following incorporation," "followed by a sudden and unexplained increase in financial activities" (p. 182), or that "receive large sums of capital funding quickly following incorporation/formation, which is spent or transferred elsewhere in a short period of time without commercial justification" (p. 183) [T22]
- Shelf company: one that "is considered to be an incorporated company that has inactive shareholders," "directors, and secretary and is left dormant for a longer period," (footnote 20, p. 23) [T21]

**Stated periods.** No AML source read today gives a period. Two UK statutes define dormancy for other purposes:
- Bank accounts: open throughout "the period of 15 years ending at that time" during which "no transactions have been carried out in relation to the account by or on the instructions of the holder of the account" (Dormant Bank and Building Society Accounts Act 2008, s 10) [T38]. This serves unclaimed balances, not AML.
- Companies: dormant "during any period in which it has no significant accounting transaction", meaning one "required by section 386 to be entered in the company's accounting records" (Companies Act 2006, s 1169) [T39]. Phase 2 carries the register's `accounts_category` (for example `DORMANT`) on `:Company` [T76].

**Red flags a graph can see.** A long gap of low activity, then a burst in and out; a new `DIRECTOR_OF`, `OWNS` or `HOLDS_ACCOUNT` start shortly before the burst; a newly incorporated company with large flows [T22]; a company filed as dormant that moves money.

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_gap_days` | 180 | modelling choice (PHASE-1 default; no source gives a period) |
| `gap_max_transactions` | 2 | modelling choice; "little activity" [T6] |
| `gap_max_amount` | 1,000 | modelling choice |
| `burst_window_days` | 14 | modelling choice |
| `burst_min_ratio` | 10 times the pre-gap monthly mean, or at least 50,000 | modelling choice |
| `change_event_window_days` | 30 | modelling choice |
| `new_company_window_days` | 90 | modelling choice; "quickly following incorporation/formation" [T22] |
| `require_history_before_gap` | true | modelling choice, against missing data |

**Look-alikes.** Seasonal businesses, people back from abroad, inheritances and property sales, genuine restarts and acquisitions, student accounts. Tells: the same season in earlier years; one large inflow from a solicitor or estate followed by slow spending; an acquisition visible in `OWNS`.

**Misleading alerts.** Left-censoring: an account whose history starts at the load date looks dormant. Null `opening_date`. A company's `accounts_category` describes a past accounting period, not today.

## 8. shell_chain

**Definition.**
- Shell company: "companies that are incorporated but which have no independent operations," "significant assets, ongoing business activities, or employees." (footnote 1, p. 12) [T21]
- Front company: "a fully functioning company with all the characteristics of a legitimate business, which ultimately serves" "to disguise and obscure the illicit financial activity being conducted." (footnote 22, p. 23) [T21]
- Nominees: "formal nominee shareholders and directors where the identity of the nominator is undisclosed" and "informal nominee shareholders and directors, such as close associates and family." (para 52, p. 26) [T21]
- Findings: "More than half of the case studies submitted in support of this report made use of complicated ownership structures, whereby control was affected through a combination of direct and indirect control." (para 56, p. 27); nominees "were identified in a large majority of case studies" (para 5, p. 7); "The majority of the case studies involved professional intermediaries." (para 6, p. 7) [T21]
- FinCEN: "Nominee Officers and Directors: Incorporators provide the shell company with nominees for all offices that appear in public records." [T11]
- Europol: "nominee directors are strawmen that appear on the paperwork, but do not operate independently." (p. 6) and "Strawmen are too often the legal window of shell and offshore companies." (p. 18) [T26]

**The FATF and Egmont 2018 indicators (Annex E, shell company indicators, pp. 184 to 185)** [T22]:
- "Nominee owners and directors:" "formal nominees (formal nominees may be "mass" nominees who are nominated agents for a large number of shell companies)" and "informal nominees, such as children, spouses, relatives or associates who do not appear to be involved in the running of the corporate enterprise."
- "Address of mass registration (usually the address of a TCSP that manages a number of shell companies on behalf of its customers)"
- "Only a post-box address (often used in the absence of professional TCSP services and in conjunction with informal nominees)"
- "No real business activities undertaken"
- "Exclusively facilitates transit transactions and does not appear to generate wealth or income (transactions appear to flow through the company in a short period of time with little other perceived purpose)"
- "No personnel (or only a single person as a staff member)"
- "Pays no taxes, superannuation, retirement fund contributions or social benefits"
- "Does not have a physical presence."
- Elsewhere in Annex E: directors or owners who "are listed against the accounts of other legal persons or arrangements," "indicating the use of professional nominees" (p. 182), and "family members with no role or involvement in the running of the business" "are listed as beneficial owners of legal persons or arrangements" (p. 184).
- Annex E says "this list is not exhaustive," "and other indicators may be identified." (p. 181)

**Red flags a graph can see.** An `OWNS` chain of 2 or more company layers; more than one jurisdiction; a top recorded owner that is a company with no recorded owner, a loop, or a `psc_statements` value saying no registrable person; `is_nominee` on `DIRECTOR_OF` or `OWNS`; directors with many appointments (section 12); a shared registered address (section 9) or agent (section 11); transit flows (section 2) and no payroll pattern; family members as directors (`FAMILY_OF`).

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_company_layers` | 2 | modelling choice; sources say "numerous layers" with no number [T21] |
| `max_hops` | 6 | modelling choice |
| `min_jurisdictions` | 2, as a strength factor | modelling choice; "different jurisdictions" [T17][T21] |
| `no_payroll_lookback_days` | 90 | modelling proxy for "No personnel" [T22] |
| `transit_ratio` | 0.9 within 72 hours | modelling proxy for transit transactions [T22] |

**Look-alikes.** FinCEN: "Most shell companies are formed by individuals and businesses for legitimate reasons." [T11]. Europol: "normal businesses may use the offshore legislation to ease formalities in international trade." (p. 14) [T26]. Holding companies, special purpose vehicles, funds, joint ventures, start-ups. Tells: real activity (payroll, suppliers, tax payments), group accounts, a natural person at the top.

**Misleading alerts.** UK registers do not flag nominees, so `is_nominee` will be rare outside leaked data. PSC data has gaps (exemptions, overseas owners) and is updated about once a year. Never call a real, named company a shell (PHASE-1 7.1 rule 4) [T73].

## 9. mass_registration_address

**Definition.**
- Annex E: "Address of mass registration (usually the address of a TCSP that manages a number of shell companies on behalf of its customers)" [T22]
- FATF and Egmont: "A trade entity is registered at an address that is likely to be a mass registration address, e.g. high-density residential buildings, post-box addresses, commercial buildings or industrial complexes," (p. 4) [T20]
- FATF: providing "a registered office; business address or accommodation" is a TCSP service (para 21, p. 8) [T23].

**UK registered office rules since the ECCT Act 2023.**
- Companies Act 2006 s 86: "A company must ensure that its registered office is at all times at an appropriate address." An address is appropriate if, "in the ordinary course of events", "(a) a document addressed to the company, and delivered there by hand or by post, would be expected to come to the attention of a person acting on behalf of the company, and (b) the delivery of documents there is capable of being recorded by the obtaining of an acknowledgement of delivery." [T40]
- Section 86 was substituted by ECCTA 2023 s 28 and is in force in full from 4 March 2024 (S.I. 2024/269) [T40][T41]. A change of address notice "must include a statement that the new address is an appropriate address" [T41].
- Companies House: "You're not able to use a Royal Mail PO Box", which also covers "equivalent services offered by other parties"; with an agent's address "you must make sure the address service they provide meets the requirements"; if the address is not appropriate it will "change the registered office address to a default address, held at Companies House", the company has 28 days to fix it, or Companies House "could start the process to strike the company off the register." [T42]
- Default addresses (Registrar's Rules, Volume 6, in force 4 March 2024): England and Wales "Companies House Default Address", "PO Box 4385", "Cardiff", "CF14 8LH"; Scotland PO Box 24238, Edinburgh, EH7 9HR; Northern Ireland PO Box 2381, Belfast, BT1 9DY [T43].

**Red flags a graph can see.** An `Address` with many `HAS_ADDRESS {role: 'registered'}` edges from companies; stronger when those companies pay each other ("Transacting businesses share the same address" [T11]), share directors, or were incorporated in bursts; a residential address with many companies [T20]; a PO box registered office [T22] (for UK companies after 4 March 2024 this is first a register data issue [T42]).

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_companies_at_address` | 25, and in the top 0.1 percent of loaded addresses | modelling choice |
| `count_active_only` | true | modelling choice |
| `exclude_addresses` | the three Companies House default addresses | [T43] |
| `intra_address_payment_bonus` | on | [T11] |
| `post_box_flag` | on | [T22][T42] |

**Look-alikes.** Registered agents: FATF describes "commercial registered agents" "that have numerous clients" (para 55, p. 19) and says "Whilst the majority of TCSPs appear to be established for legitimate purposes" (para 10, p. 5) [T23]. Serviced offices, accountants and law firms. Companies moved to a default address [T43]. Address normalisation errors. Tells: a known agent or office building, companies that do not pay each other, varied directors.

**Misleading alerts.** Weak `address_key` normalisation; historic addresses; dissolved companies; default addresses counted as one cluster.

## 10. sanctions_exposure

### 10.1 The three tests, quoted

**United States (OFAC).**
- Persons whose property is blocked "are considered to have an interest in all property and interests in property of an entity" "in which such blocked persons own, whether individually or in the aggregate, directly or indirectly, a 50 percent or greater interest." "Consequently, any entity owned in the aggregate, directly or indirectly, 50 percent or more by one or more blocked persons is itself considered to be a blocked person." Its property is blocked "regardless of whether the entity itself is listed" [T12].
- "U.S. persons are advised to act with caution when considering a transaction with a non-blocked entity in which one or more blocked persons has a significant ownership interest that is less than 50 percent or which one or more blocked persons may control by means other than a majority ownership interest." [T12]
- FAQ 398 (11 August 2020): "No. OFAC's 50 Percent Rule speaks only to ownership and not to control. An entity that is controlled (but not owned 50 percent or more) by one or more blocked persons is not considered automatically blocked pursuant to OFAC's 50 Percent Rule." [T13]
- FAQ 399: "Accordingly, if Blocked Person X owns 25 percent of Entity A, and Blocked Person Y owns another 25 percent of Entity A, Entity A is considered to be blocked." and "For the purpose of calculating aggregate ownership, the ownership interests of persons blocked under different OFAC sanctions programs are aggregated." [T13]
- FAQ 401: ""Indirectly," as used in OFAC's 50 Percent Rule, refers to one or more blocked persons' ownership of shares of an entity through another entity or entities that are 50 percent or more owned in the aggregate by the blocked person(s)." Its five examples [T13]:
  1. "Blocked Person X owns 50 percent of Entity A, and Entity A owns 50 percent of Entity B. Entity B is considered to be blocked."
  2. "Blocked Person X owns 50 percent of Entity A and 50 percent of Entity B. Entities A and B each own 25 percent of Entity C. Entity C is considered to be blocked."
  3. "Blocked Person X owns 50 percent of Entity A and 10 percent of Entity B. Entity A also owns 40 percent of Entity B. Entity B is considered to be blocked."
  4. "Blocked Person X owns 50 percent of Entity A and 25 percent of Entity B. Entities A and B each own 25 percent of Entity C. Entity C is not considered to be blocked."
  5. "Blocked Person X owns 25 percent of Entity A and 25 percent of Entity B. Entities A and B each own 50 percent of Entity C. Entity C is not considered to be blocked."
- FAQ 402: when combined ownership falls below 50 percent "the entity is no longer considered automatically to be a blocked entity", but property already blocked stays blocked [T13].
- 2026 supplement: "sham transactions do not terminate a blocked interest in property."; "Transfers by a blocked person to a family member or close associate can be evidence of a sham transaction."; it flags "unnecessarily complex legal structures without a discernible legitimate purpose" [T14].

**United Kingdom (statute and OFSI).**
- Russia (Sanctions) (EU Exit) Regulations 2019, reg 7(2), the first condition is that P "(a) holds directly or indirectly more than 50% of the shares in C, (b) holds directly or indirectly more than 50% of the voting rights in C, or (c) holds the right directly or indirectly to appoint or remove a majority of the board of directors of C." [T37]
- Reg 7(4), the control limb: "The second condition is that it is reasonable, having regard to all the circumstances, to expect that P would (if P chose to) be able, in most cases or in significant respects, by whatever means and whether directly or indirectly, to achieve the result that affairs of C are conducted in accordance with P's wishes." [T37]
- Schedule 1, para 9(1): "A person holds a share "indirectly" if the person has a majority stake in another person and that other person" "(a) holds the share in question, or (b) is part of a chain of persons" "(i) each of whom (other than the last) has a majority stake in the person immediately below it in the chain, and (ii) the last of whom holds the share." [T37]
- Para 9(3): A has a "majority stake" in B if "(a) A holds a majority of the voting rights in B, (b) A is a member of B and has the right to appoint or remove a majority of the board of directors of B, (c) A is a member of B and controls alone, pursuant to an agreement with other shareholders or members, a majority of the voting rights in B, or (d) A has the right to exercise, or actually exercises, dominant influence or control over B." [T37]
- Para 4(1): "more than 50% of the shares" means shares "of a nominal value exceeding (in aggregate) 50% of that share capital." Para 3: under a joint arrangement "each of them is treated as holding the combined shares or rights of both of them." Para 10: "A share held by a person as nominee for another is to be treated as held by the other (and not by the nominee)." [T37]
- OFSI section 4.1 (updated 12 May 2026) gives the same three circumstances and examples of control, including "having the ability to direct another entity in accordance with one's wishes." [T36]
- OFSI 4.1.4: "When making an assessment on ownership and control, OFSI would not simply aggregate different designated persons' holdings in a company, unless, for example, the shares or rights are subject to a joint arrangement between the designated parties or one party controls the rights of another." [T36]
- OFSI 4: such entities "may not be designated in their own right, so their names may not appear on the sanctions list." [T36]
- Only the Russia regulations were read; other UK regimes are expected to use the same wording (UNVERIFIED for each regime).

**European Union (Council guidance and regulation).**
- Best Practices 11623/24 (3 July 2024), para 63: "The criterion to be taken into account when assessing whether a legal person or entity is owned by another person or entity is the possession of 50% or more of the proprietary rights of an entity or having majority interest in it." [T61] Its footnote ties this to Regulation 2580/2001, whose Article 1(5) reads "being in possession of 50 % or more of the proprietary rights of a legal person, group or entity, or having a majority interest therein." [T62]
- Para 63: "When assessing ownership, the aggregated ownership of the entity should , also be taken into account." (stray comma in the original) "For example, if one designated person owns 30% of the entity and another designated persons owns 25% of the entity, the entity should, in principle, be considered as owned by designated persons." [T61]. Commission FAQ 8 (updated 5 September 2024) says the same [T63].
- Para 64 control criteria "could include, inter alia:" (a) "having the right or exercising the power to appoint or remove a majority of the members of the administrative, management or supervisory body"; (b) appointing such a majority solely through voting rights; (c) controlling a majority of voting rights by agreement; (d) a right to "dominant influence" by agreement or articles; (e) the power to exercise it "de facto"; (f) "having the right to use all or part of the assets of a legal person or entity;" (g) "managing the business of a legal person or entity on a unified basis, while publishing consolidated accounts;" (h) sharing liabilities or guaranteeing them [T61][T62].
- Para 65 and 66: the criteria mean control "unless the contrary can be established on a case by case basis." and "may be refuted on a case by case basis." [T61]
- Commission FAQ 9: control over a single entity "would impact its own subsidiaries, but not other subsidiaries in the wider group." [T63]. FAQ 43 (6 May 2026): control is "a factual assessment to be carried out by the relevant national competent authorities". FAQ 17: "sanctions on listed entities do not automatically extend to their board members." [T63]
- Correction to the brief: the current EU wording is "50% or more", not "more than 50 percent" [T61][T62].

### 10.2 How to compute it from bands

Inputs. `OWNS` edges carry `share_pct_min`, `share_pct_max`, `share_min_exclusive`, `share_max_exclusive` (C2 1.1) [T76]. `CONTROLS` edges carry a voting band in the same four properties, and a `control_type` [T76]. Companies House bands: "More than 25% but not more than 50%" is (25, 50]; "More than 50% but less than 75%" is (50, 75); "75% or more" is [75, 100] [T52]. Holdings of 25 percent or less are not on the PSC register.

Seed lists. Each regime uses only its own list: the OFAC SDN List for the US test; UK Sanctions List entries with an asset freeze (the XML `SanctionsImposedIndicators` include `AssetFreeze`, Phase 2 note 1.4) [T72]; the EU consolidated financial sanctions list for the EU test. Whether non-SDN OFAC lists use the same rule was not read today (UNVERIFIED).

Interval arithmetic.
- Sum of holdings: lower = sum of lower bounds, open if any lower bound is open; upper = sum of upper bounds, open if any is open, capped at 100 (closed). A missing upper bound counts as 100 and marks the result "unbounded".
- If the sum of lower bounds exceeds 100, flag a data inconsistency (often a double count of a direct and an indirect PSC entry).
- "At least 50" (US, EU): met if lower > 50, or lower = 50 (open or closed). Possible if upper > 50, or upper = 50 and closed. Otherwise not met.
- "More than 50" (UK): met if lower > 50, or lower = 50 and open. Possible if upper > 50. Otherwise not met.

US and EU algorithm (entity by entity, after FAQ 401; for the EU an interpretation).

```text
C = seed set   (certain)
P = seed set   (possible)
repeat until neither set changes:
  for each entity E (not a natural person) not in C:
    S = sum of OWNS(h -> E) where h in C, using lower bounds
    if S meets "at least 50": add E to C
  for each entity E not in P:
    S = sum of OWNS(h -> E) where h in P, using upper bounds
    if S can reach "at least 50": add E to P
result: E in C        -> met on the records
        E in P, not C -> the bands leave it open
        otherwise     -> not met on the records
```

The sets only grow, so the loop ends. A holder in C counts in full; a holder outside P counts zero. Nothing is multiplied.

UK algorithm (per designated person, no adding across persons).

```text
for each designated person X:
  M = {X}
  repeat: add entity B to M if some m in M has a majority stake in B:
          voting band met "more than 50", or an appointment right over the board
          (if no voting data, shares "more than 50" with flag votes_follow_shares)
  for each entity C:
    shares(X, C) = sum of OWNS(m -> C) for m in M, each in full
    votes(X, C)  = sum of voting CONTROLS(m -> C) for m in M
    board(X, C)  = any m in M with an appointment right over C
    owned or controlled if shares or votes meet "more than 50", or board
run once with lower bounds (met) and once with upper bounds (possible)
```

Summing X's direct holding with the holdings of companies in which X has a majority stake reads "directly or indirectly" with para 4 "(in aggregate)" and para 9 [T37]; it is an interpretation. A PSC "significant influence or control" entry is not the "dominant influence or control" of para 9(3)(d); do not treat it as a majority stake.

Control results are reported apart from ownership.
- US: any control link from an SDN entry gives "OFAC advises caution" wording [T12]; never "met" [T13].
- UK: an appointment right is the first condition, reg 7(2)(c), so it can be "met" [T37]. Other control (significant influence, a directorship) can only be "the control condition may need assessing; these records cannot decide it" [T36][T37].
- EU: an appointment right is criterion (a); a GLEIF `CONSOLIDATES` link from a listed parent fits criterion (g), "while publishing consolidated accounts" [T61][T62] (a NeonRadar reading). A directorship alone is not a criterion [T63].

### 10.3 Worked examples

| Case | US (at least 50, added up, passed on) | UK (more than 50, per person, majority-stake chains) | EU (50 or more, added up; chain by interpretation) |
|---|---|---|---|
| FAQ 401 example 1: X 50% of A; A 50% of B | A and B met | X's 50% is not a majority stake: A and B not met | A and B met |
| Example 2: X 50% of A and of B; A and B 25% each of C | C met (25 + 25) | not met | C met |
| Example 3: X 50% of A, 10% of B; A 40% of B | B met (10 + 40) | not met | B met |
| Example 4: X 50% of A, 25% of B; A and B 25% each of C | C not met (only A counts: 25) | not met | C not met |
| Example 5: X 25% of A and of B; A and B 50% each of C | C not met | not met | C not met |
| X (25, 50] of E | left open (upper 50 is closed) | not met (upper bound 50) | left open |
| X (50, 75) of E | met | met | met |
| X and Y, both listed, (25, 50] each of E | met: sum (50, 100] | not met unless a joint arrangement | met |
| X [75, 100] of A; A (25, 50] of B | A met; B left open | A met (if votes follow shares); B not met | A met; B left open |
| X (50, 75) of A; A (50, 75) of B | B met | B met through the majority-stake chain | B met |

Multiplying shares gets example 1 wrong (25 percent) and the last row wrong ((25, 56.25), "open" instead of met). This is why Phase 2 forbids presenting an effective share as a sanctions result [T75].

### 10.4 What may honestly be said

All lines below pass the PHASE-1 7.1 lint and avoid the Phase 2 never-write phrases ("is blocked", "falls under the 50 Percent Rule", "no sanctions exposure") [T73][T75].

- Met (US): "Recorded holdings of owners on the OFAC SDN List reach at least 50 percent of this company, counting in full any owner that itself reaches that level (the method in OFAC FAQ 401). This is a NeonRadar calculation from published share bands, not a finding by OFAC."
- Left open: "The published share bands cannot settle this. Recorded holdings of listed owners are more than 25 and at most 50 percent, and the OFAC test asks whether they reach 50 percent. The share register would settle it."
- Not met on the records: "Recorded holdings of listed owners are at most 40 percent. The PSC register does not record holdings of 25 percent or less, and the loaded sources may not cover every owner, so this says only what these records show."
- UK, no adding up: "Two people on the UK Sanctions List are each recorded with more than 25 and at most 50 percent of the shares. OFSI does not add different listed persons' holdings together unless they are held jointly or under a joint arrangement, and these records show neither."
- UK, board right: "A person on the UK Sanctions List is recorded with the right to appoint or remove a majority of the board. This is one of the conditions in the UK ownership and control test."
- US, control only: "A person listed by OFAC is recorded with control rights but no shareholding. The OFAC 50 Percent Rule counts ownership only (OFAC FAQ 398), and OFAC advises caution where listed persons may control an entity by other means."
- EU, met: "Owners on the EU consolidated list hold at least 50 percent on the recorded holdings, added together as the Council's Best Practices describe. This is a NeonRadar calculation, not a decision of an EU or national authority."

### 10.5 Red flags a graph can see beyond the test

- Largest holder: a designated person "has 40%, whereas the other shareholders each have 10%." (EU para 67(a)) [T61]
- Shares moved near the designation date: "A transfer of a relevant number of shares in the non-designated entity to a new owner shortly before or after" designation (para 67(c)); graph: `OWNS` end or start dates near `Sanction.start_date` [T61].
- Front persons: "A new owner is closely connected to the designated previous owner, e.g. a family member or former employee/business partner," (para 67(d)) [T61]; graph: `FAMILY_OF` between old and new owner. OFAC says the same of transfers "to a family member or close associate" [T14].
- Complex structures (para 67(e)) [T61][T14].

### 10.6 Starting parameters

| Parameter | Default | Basis |
|---|---|---|
| `max_hops` | 6 | modelling choice (PHASE-1 7.2) |
| `us_test` | at least 50, added up, passed entity by entity, ownership only | [T12][T13] |
| `uk_test` | more than 50 of shares or votes, or board right; per person; majority-stake chains | [T36][T37] |
| `eu_test` | 50 or more, added up; control criteria separate | [T61][T62][T63] |
| `votes_follow_shares` | on, and flagged in the alert | modelling choice |
| `unknown_upper_bound` | 100, flagged "unbounded" | modelling choice |
| `transfer_near_designation_days` | 90 | modelling choice; "shortly before or after" [T61] |

### 10.7 Look-alikes and misleading alerts

Look-alikes: name-matching errors (OFSI separates a "name match" from a "target match", Phase 2 note) [T72]; minority stakes; delisted parties; diffuse shareholding; lawful state-owned counterparties. Misleading: multiplying shares; mixing regimes or lists; treating control as ownership for OFAC; stale PSC data; double-counted indirect PSC entries; a listed record merged with an unlisted one (Phase 2 policy P1 keeps them apart) [T75]; the rules apply to entities, not to natural persons.

## 11. formation_agent_cluster

**Definition.**
- FATF: "TCSPs have often been used, wittingly or unwittingly, in the conduct of money laundering activities." [T23]. Listed TCSP services include "Acting as a formation agent of legal persons;" and acting as or arranging "a nominee shareholder for another person." (para 21, p. 8); risks include "The formation by TCSPs of shell companies that can then be used by money launderers." (para 77, p. 25) [T23]
- FATF PML: launderers "recruit nominees (e.g. front men) to register shell companies on behalf of the client" (p. 16) [T17]

**UK authorised corporate service providers (in force in part).**
- Companies Act 2006 s 1098A defines an ACSP. It has been in force since 18 March 2025 (S.I. 2025/349) [T44].
- Section 1067A, which limits who may deliver documents (for example an "Individual who is an authorised corporate service provider" or an "Individual whose identity is verified"), is in force only for its regulation-making power; the rest is prospective [T45].
- Companies House: ACSPs are "individuals or organisations that undertake anti-money laundering (AML) supervised activity"; filing for clients will be restricted to them from "no earlier than November 2027", and "We'll give at least 6 months' notice before this requirement comes into effect." (page modified 5 August 2026) [T46]
- GOV.UK guidance (updated 19 June 2026) still says "From no earlier than November 2026, you'll be able to file on behalf of clients as an authorised agent." and "In the future, all agents that file with Companies House on behalf of clients will need to register." [T47]. The two pages conflict; on 18 October 2026 the filing restriction is not in force either way. ACSPs "must keep records of any identity checks for 7 years." [T47]
- Public data: the officer record now has `identity_verification_details`, including `authorised_corporate_service_provider_name`, `anti_money_laundering_supervisory_bodies` and `identity_verified_on` [T51]. C2 does not hold these yet.

**Red flags a graph can see.** One agent with `REPRESENTS` edges to many companies; companies registered at the agent's address; incorporation dates in bursts; nominee directors or secretaries shared across them; payments among them [T11].

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_companies` | 10 incorporated within 30 days | modelling choice |
| `min_shared_officers` | 2 | modelling choice |
| `intra_cluster_payment_bonus` | on | [T11] |
| `acsp_grouping` | context only, never a trigger | modelling choice; [T51] |

**Look-alikes.** Company formation is a lawful trade. FATF: "Whilst the majority of TCSPs appear to be established for legitimate purposes" [T23]. ACSPs are AML-supervised by definition [T46].

**Misleading alerts.** ICIJ intermediary data comes from leaked files, and ICIJ says inclusion "is not intended to suggest or imply that they have engaged in illegal or improper conduct." [T67]. An ACSP name means that firm checked an identity; it does not mean it formed or runs the company. Large agents dominate raw counts.

## 12. recycled_directors

**Definition.**
- Annex E: formal nominees "may be "mass" nominees who are nominated agents for a large number of shell companies" (p. 184); directors or owners "listed against the accounts of other legal persons or arrangements," "indicating the use of professional nominees" (p. 182) [T22].
- Europol: "Strawmen may be associated with multiple legal entities." (EFECTA p. 16) [T25]
- Small numbers can matter: in one FATF case "two of the group's central figures hired 10 nominees to establish 25 shell companies." (PML Box 10, p. 30) [T17]

**UK identity verification for directors.**
- Companies Act 2006 s 167M(1): "An individual must not act as a director of a company unless the individual's identity is verified"; contravention is an offence (s 167M(3)) [T48].
- In force from 18 November 2025 by S.I. 2025/1118, reg 2(1)(g) [T48][T49].
- Existing directors: the company must deliver a verification statement with its next confirmation statement during "the period of 12 months beginning with 18th November 2025" (reg 4) [T49]. So the transition ends at the end of 17 November 2026, four days after Phase 3 ends.
- Companies House: "Since 8 April 2025, individuals have been able to voluntarily verify their identity"; "From 18 November 2025, Companies House will make identity verification a compulsory part of incorporation"; it expected "6 to 7 million individuals will need to verify their identity by mid-November 2026," [T50]
- Analysis: verification links appointments to one checked identity, which can help entity resolution. It says nothing about whether a director acts independently. A verified person can still be a nominee.

**Red flags a graph can see.** A person with many active `DIRECTOR_OF` edges; appointments that start and end in bursts; short tenures; directors who are `FAMILY_OF` the owner with no other role [T22]; payments between companies that share the director; the same director across companies at one mass registration address.

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `min_active_appointments` | 10 | modelling choice; PML Box 10 shows smaller counts can matter [T17] |
| `burst_min_appointments` | 5 within 30 days | modelling choice |
| `short_tenure_days` | 90 | modelling choice |
| `family_director_flag` | `FAMILY_OF` an owner, no other role | [T22] |
| `shared_director_payment_bonus` | on | modelling choice; [T11] |

**Look-alikes.** Professional directors in fund jurisdictions, company secretaries, directors across one group, corporate directors. Tells: appointments within one `OWNS` or `CONSOLIDATES` group, long tenures, no payments among the companies.

**Misleading alerts.** Different people with the same name merged by mistake (Phase 2 uses the Companies House person number); resigned appointments counted as active; dissolved companies.

## 13. pep_exposure

**Who counts.**
- FATF Recommendation 12: "The requirements for all types of PEP should also apply to family members or close associates of such PEPs." (p. 17) [T15]
- FATF 2013 guidance, para 11: "Family members are individuals who are related to a PEP either directly (consanguinity) or through marriage or similar (civil) forms of partnership." and "Close associates are individuals who are closely connected to a PEP, either socially or professionally." [T24]. Para 49 examples include "business partners or associates, especially those that share (beneficial) ownership of legal entities with the PEP, or who are otherwise connected (e.g., through joint membership of a company board)." [T24]
- MLR 2017 reg 35(12)(b): a "family member" of a PEP "includes" "a spouse or civil partner of the PEP;", "children of the PEP and the spouses or civil partners of the PEP's children;" and "parents of the PEP;" [T32]
- Reg 35(12)(c): a "known close associate" means "an individual known to have joint beneficial ownership of a legal entity or a legal arrangement or any other close business relations with a PEP;" or "an individual who has sole beneficial ownership of a legal entity or a legal arrangement which is known to have been set up for the benefit of a PEP;" [T32]
- Reg 35(15): a firm "need only have regard to information which is in its possession, or to credible information which is publicly available." [T32]
- FCA FG25/3 (July 2025): "We consider that this includes siblings of PEPs."; a wider circle "(such as aunts and uncles)" only for higher-risk PEPs, "This would not apply to lower risk PEPs."; "A family member of a PEP is not a PEP themselves purely as a consequence of being associated with a PEP."; "A known close associate of a PEP is not a PEP themselves" (pp. 14 to 15) [T33]

**How long.**
- Reg 35(9): requirements continue "for a period of at least 12 months after the date on which that person ceased to be entrusted with that public function;" or longer as the firm thinks fit [T32].
- Reg 35(11): when a PEP leaves office, "the relevant person is no longer required to apply the requirements in paragraphs (5) and (8) in relation to a family member or known close associate of that PEP (whether or not the period referred to in paragraph (9) has expired)." [T32]
- Reg 35(3A): for a domestic PEP "the starting point for the assessment is that the customer or potential customer presents a lower level of risk than a non-domestic PEP" [T32]
- FATF: "The handling of a client who is no longer entrusted with a prominent public function should be based on an assessment of risk and not on prescribed time limits." (para 44) [T24]
- OpenSanctions keeps national heads of state or government for 50 years after office, other national, intergovernmental and diplomatic roles for 20 years, and all other roles for 5 years: "These windows are therefore our judgment, not a regulatory requirement." [T69]
- FATF: "Being a PEP does not prejudge a link to criminal activities, or equate to being a criminal" (Annex 1) [T24]. Red flag: "Use of corporate vehicles (legal entities and legal arrangements) to obscure the beneficial owner." (Annex 1, para 4) [T24]

**Red flags a graph can see.** A `:PEP` node linked to the subject through at most one family hop and one associate hop, then `OWNS`, `CONTROLS` or `DIRECTOR_OF`; family members as directors or owners with no other role [T22]; corporate vehicles between the PEP and assets [T24]. `:RCA` nodes come from source data and are used as given.

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `family_relationships` | spouse, civil partner, child, child's spouse or civil partner, parent; sibling | [T32][T33] |
| `family_hops` | 1 | [T24][T32] |
| `associate_hops` | 1, only where the link shows joint ownership or close business relations | [T32] |
| `ownership_control_hops` | 3 | modelling choice |
| `pep_after_office_months` | 12 (configurable upwards) | [T32]; FATF prefers risk over fixed limits [T24] |
| `family_and_associate_after_office` | stop at the end of office | [T32] (35(11)); [T33] |
| `domestic_pep_priority` | lower | [T32] (35(3A)) |

**Look-alikes.** Homonyms; ordinary family relationships; people long out of office; local office holders (FCA excludes UK local government, Phase 2 note 7.1) [T72].

**Misleading alerts.** OpenSanctions says "We include RCAs documented in our data sources." and does not "independently research family or business networks." [T69]. Wikidata family links are not RCA findings. Missing occupancy end dates make former PEPs look current.

## 14. cash_commingling

**Definition.**
- FFIEC examples: "Convenience stores." "Restaurants." "Retail stores." "Liquor stores." "Cigarette distributors." "Privately owned automated teller machines (ATM)." "Vending machine operators." "Parking garages." [T7]
- FFIEC: "For example, a criminal may own a cash-intensive business, such as a restaurant, and use it to launder currency from illicit criminal activities." "However, the volume of currency in a restaurant used to launder money will most likely be higher in comparison with similar restaurants in the area." [T7]
- Risk factors include "Purpose of the account.", "Volume, frequency, and nature of currency transactions.", "Primary business activity, products, and services offered." and "Geographic locations and jurisdictions of operations." [T7]
- Europol: "Cash-intensive businesses are also often targeted, as they provide opportunities to mix licit and illicit proceeds." (p. 9); examples "Bars, restaurants, pizzerias, grocery shops, construction companies, motor vehicle retailers, car washes," (p. 16) [T25]

**Red flags a graph can see.** Company cash deposits far above peers of the same `sector` and area; deposits on days the business would be closed (no opening hours in C2; weekend use is a weak proxy); outflows to owners or related parties rather than suppliers and payroll; "The currency transaction patterns of a business show a sudden change inconsistent with normal activities." [T6]; ownership links to other cash businesses with the same anomaly.

**Starting parameters.**

| Parameter | Default | Basis |
|---|---|---|
| `peer_group` | same sector and same area (postcode district or city) | "similar restaurants in the area" [T7] |
| `min_peers` | 5 | modelling choice |
| `cash_ratio_vs_peer_median` | 3.0 | modelling choice |
| `change_window` | last 90 days against the previous 365 | modelling choice; [T6] |
| `related_party_outflow_share` | 0.5 | modelling choice |

**Look-alikes.** "Most of these businesses are conducting legitimate business;" [T7]. Busy or growing businesses, seasonal peaks, a new branch, communities that prefer cash. FFIEC notes "the difficulty in identifying unusual activity" in this segment [T7].

**Misleading alerts.** No real sector benchmarks exist in the data, so the generator's own calibration becomes the benchmark (circular); sector codes are coarse; synthetic artefacts on real entities.

## 15. trade_based_ml (explainer only)

**Definition.** TBML is "the process of disguising the proceeds of crime and moving value through the use of trade transactions" (p. 12) [T19]. Techniques: over- and under-invoicing ("the misrepresentation of the price of the good or service"), over- and under-shipment ("the misrepresentation of the quantity of goods or services, including 'phantom shipments'"), multiple invoicing ("the reuse of existing documentation to justify multiple payments for the same shipment of goods") and falsely described goods ("the misrepresentation of the quality or type of a good or service") (pp. 27 to 28) [T19].

**Why payment data alone cannot detect it.**
- Most trade is open account: "approximately 80% of international trade processed by FIs is open account trading" (p. 14) [T19].
- Open account trade creates "a disconnect between the movement of the underlying trade and the money used to finance it" (p. 14) [T19].
- In documentary collections banks "do not necessarily verify the documents" and "documents are not always standardised" (p. 15) [T19].
- "Relevant trade data is held across multiple stakeholders" (p. 5) and "no single stakeholder has ownership of or access to information that would assist in identifying TBML" (p. 27) [T19].
- So a price claim needs a reference price, a shipment record and customs data. C2 has no Invoice or Shipment nodes.
- Payment-side signals are weak proxies already covered elsewhere: payment by "an entity other than the consignee" [T20], circular routing (section 4), large round amounts [T20], split and forward (section 6), mass registration (section 9). "The existence of a single indicator in relation to a customer or transaction may not alone warrant suspicion of TBML," (p. 3) [T20].

## 16. Wording findings about real, named entities, and legal risk (analysis, not legal advice)

### 16.1 How public tools word it

- ICIJ: "No, there are legitimate uses for offshore companies and trusts. We do not intend to suggest or imply that any individuals, companies or other entities included in the ICIJ Offshore Leaks Database have broken the law or otherwise acted improperly." [T67]
- ICIJ: "We recommend caution before drawing any conclusions, as many people and entities have the same or similar names." "We suggest you confirm the identities of any individuals or entities found in the database using addresses or other identifiable information." "The inclusion of a person or entity in the ICIJ Offshore Leaks Database is not intended to suggest or imply that they have engaged in illegal or improper conduct." "Keep in mind that some information, like the status of a company and its shareholders, might have changed over time." [T67]
- OpenSanctions on "entity of interest": "It does not carry a specific legal meaning, and does not imply wrongdoing." [T68]. On PEP retention windows: "These windows are therefore our judgment, not a regulatory requirement." [T69]
- OCCRP legal notice: "references to allegations do not imply findings of guilt, liability, or wrongdoing", qualified by "Unless expressly stated otherwise" [T70].
- OpenCorporates: "In some cases the source data have errors which we have not yet detected" and "Your use of the company data is entirely at your own risk." [T71]
- Authorities word red flags the same way: "The mere presence of a red flag is not by itself evidence of criminal activity." [T6]; "No one activity by itself is a clear indication of trade-based money laundering." [T8]; a single indicator "may not alone warrant suspicion of TBML" [T20]; a PEP status "does not prejudge a link to criminal activities" [T24].

Common elements: legitimate uses exist; inclusion is not wrongdoing; names collide, so confirm with addresses or identifiers; data may be dated; the reason for inclusion traces to a source; errors can be reported.

Consequences for NeonRadar (recommendations).
- Headlines describe the shape and the numbers, not the typology. Give each typology a neutral `shape_name` for entity-facing text. "Structuring", "smurfing" and "layering" name conduct with a purpose [T1][T9][T16].
- Say what the pattern does not show, and name the look-alikes beside the alert.
- Name the source and its date for every fact about a real entity.
- Keep the Phase 2 rules: flags only on the node that carries them, "not confirmed" for possible matches, effective shares as NeonRadar calculations [T75].

### 16.2 Defamation (England and Wales)

- "A statement is not defamatory unless its publication has caused or is likely to cause serious harm to the reputation of the claimant." (Defamation Act 2013, s 1(1)) For a body trading for profit, harm is not serious unless "it has caused or is likely to cause the body serious financial loss." (s 1(2)) The section extends to England and Wales [T53].
- Courts read three levels of meaning: "(1) the claimant is guilty of the act;" "(2) reasonable grounds to suspect that the claimant is guilty of the act; and" "(3) grounds to investigate whether the claimant has committed the act." "In the lexicon of defamation, these have come to be known as the Chase levels." ([2019] EWHC 1337 (QB), para 16) [T54]
- Public interest defence: the defendant must show the statement was on "a matter of public interest" and that they "reasonably believed that publishing the statement complained of was in the public interest." (s 4(1)); the court makes "such allowance for editorial judgement as it considers appropriate." (s 4(4)) [T53]
- Analysis: an automated "matches the graph pattern of <typology>" line about a named company or person can carry a level 2 or level 3 meaning even when every graph fact is true. Proving the facts is not the same as proving the meaning (the truth defence, s 2, was not re-read today: UNVERIFIED). Automated output has no editorial judgement to allow for. Scotland and Northern Ireland were not checked (UNVERIFIED).

### 16.3 UK GDPR: profiling and automated decisions

- Profiling "means any form of automated processing of personal data consisting of the use of personal data to evaluate certain personal aspects relating to a natural person" including "reliability, behaviour, location or movements" (Article 4(4)) [T55].
- Article 22A (substituted by the Data (Use and Access) Act 2025, s 80; in force for the remainder on 5 February 2026): a decision is based solely on automated processing "if there is no meaningful human involvement in the taking of the decision"; a "significant decision" has "a legal effect for the data subject" or "a similarly significant effect for the data subject"; assessing human involvement must consider the extent the decision is reached "by means of profiling" [T55].
- Article 22B restricts such decisions based on special category data [T55]. Article 22C requires safeguards that "provide the data subject with information about decisions", "enable the data subject to make representations about such decisions", "enable the data subject to obtain human intervention on the part of the controller" and "enable the data subject to contest such decisions" [T55].
- Analysis: NeonRadar decides nothing. A user who closes an account or refuses a customer on an alert, with no meaningful human review, takes a decision under Article 22A. Pattern detection over a person's payments and ties is plausibly profiling.
- EU comparison: the CJEU held that a probability value is itself automated decision-making where a third party "draws strongly on that probability value to establish, implement or terminate a contractual relationship with that person." (C-634/21, 7 December 2023) [T65]. So `pattern_strength` about a natural person should not be handed to third parties as a score. Whether UK courts follow this 2023 ruling is UNVERIFIED.

### 16.4 Criminal offence data

- Data Protection Act 2018 s 11(2): personal data relating to criminal convictions and offences includes "(a) the alleged commission of offences by the data subject, or (b) proceedings for an offence committed or alleged to have been committed by the data subject" [T56].
- Analysis: an inference that a named person may be laundering money is plausibly data about an alleged offence, needing a Schedule 1 condition (Phase 2 note section 8) [T72]. Structural wording lowers the risk but does not remove it.

### 16.5 Data protection by design and by default

- Article 25(1): the controller must "implement appropriate technical and organisational measures, such as pseudonymisation, which are designed to implement data-protection principles, such as data minimisation" [T55].
- Article 25(2): "In particular, such measures shall ensure that by default personal data are not made accessible without the individual's intervention to an indefinite number of natural persons." [T55]
- Design consequences: real-entity alerts stay on the local real instance (Phase 2 L17) and are never published; alerts about natural persons on real data are off by default; evidence is minimised; a human reviews before any action; the deploying organisation writes its own data protection impact assessment (Article 35 not re-read today: UNVERIFIED wording).
- The journalism and academic exemption (DPA 2018 Sch 2 para 26) applies only where processing is "carried out with a view to the publication by a person of journalistic" (or academic, artistic or literary) material and "the controller reasonably believes that the publication of the material would be in the public interest." [T57]. NeonRadar cannot claim it on behalf of its users.

### 16.6 EU deployments

- GDPR Article 22(1): "The data subject shall have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her." [T64]
- AI Act Article 5(1)(d), applicable from 2 February 2025, prohibits AI systems for "risk assessments of natural persons in order to assess or predict the risk" of offending, "based solely on the profiling of a natural person", but not systems that "support the human assessment" of involvement "which is already based on objective and verifiable facts directly linked to a criminal activity." [T66]
- An "AI system" is "a machine-based system that is designed to operate with varying levels of autonomy" that "infers, from the input it receives, how to generate outputs" (Article 3(1)); the definition "should not cover systems that are based on the rules defined solely by natural persons" "to automatically execute operations." (recital 12) [T66]
- Analysis: Cypher detectors written by people are probably outside the AI Act definition. The Phase 4 copilot is probably inside it. Never output a likelihood that a natural person will offend.

## 17. Where PHASE-1.md 7.2 disagrees with the sources

### 17.1 Catalog entries

1. **structuring.**
   - The threshold source: 7.2 takes the default "after the US reporting threshold described in FIN-2014-A005". The threshold is set by 31 CFR 1010.311, "more than $10,000" [T2]; the advisory only says "below the cash reporting threshold" [T8]. Add `cfr_31_1010_311_2026`.
   - The daily total: 7.2 requires "a daily total above the threshold". The definition covers "any amount", "on one or more days", and says amounts "need not exceed" the threshold "on any single day" [T1]. A daily-total filter misses multi-day splitting, which is how per-day aggregation is avoided [T3].
   - The band edge: for the US, 10,000 exactly is below the threshold [T2]; for UK and EU thresholds it is not [T29][T58]. 7.2 does not say which.
   - The name: smurfing means teams [T9]; a one-depositor burst is not smurfing.
2. **rapid_pass_through.** Consistent in shape. The funnel account in its first citation is defined by cash and by geography [T8], which the 7.2 pattern does not use; say so in the explainer. "Outbound to few beneficiaries" comes from FFIEC [T6], which 7.2 already cites.
3. **layering_chain.** Consistent. The "amounts shrinking slightly" can cite Europol's fee range [T25].
4. **circular_flow.** Its citations describe wider circles than the detector finds: the TBML indicator is about countries [T20] and the FFIEC flag about banks [T6]. The same-holder variant is better supported by PML step 5 [T17] and the Annex E ordering-and-beneficiary indicator [T22]; add `fatf_pml_2018` evidence for it.
5. **fan_in_collection.** 7.2 applies "recently opened accounts" to the senders. The sources apply recency and short use to the mule's own accounts [T6][T18][T25]. Senders are often victims [T27].
6. **fan_out_distribution.** Consistent.
7. **dormant_reactivation.** 7.2 requires "no PAID edges for a long gap". FFIEC says "an account with little activity" [T6]. The 180-day default has no source; label it a modelling choice. Add the TBML "recently re-activated" indicator [T20] and Annex E [T22] as citations.
8. **shell_chain.** Consistent, with a data caveat: `DIRECTOR_OF.is_nominee` will be rare in real registers because nominee status is usually undisclosed [T21].
9. **mass_registration_address.** Consistent. It lacks two UK facts: the default addresses [T43] and the appropriate-address rule [T40][T42].
10. **sanctions_exposure.**
   - Source: entity-by-entity propagation comes from FAQ 401 [T13]; the 2014 guidance says only "directly or indirectly" [T12]. Cite `ofac_50_percent_faqs`.
   - Control: 7.2 says "`CONTROLS` and `DIRECTOR_OF` links create exposure without ownership". Under OFAC, control never makes an entity blocked (FAQ 398) [T13]. Under UK and EU rules some control rights count [T37][T61], but a directorship is not itself a criterion, and EU control is "a factual assessment" for national authorities [T63].
   - Scope: 7.2 describes only the US rule. The UK test (more than 50, per person, majority-stake chains, no adding up) and the EU test (50 or more, added up) give different answers on the same data (10.3).
11. **formation_agent_cluster.** Consistent. It can add ACSP data [T51].
12. **recycled_directors.** Consistent. PML Box 10 shows that small counts can matter [T17].
13. **pep_exposure.**
   - Hops: "paths of at most 4 hops ... through FAMILY_OF, ASSOCIATE_OF, ..." reach relatives of relatives and associates of associates. Every definition is one step from the PEP [T24][T32].
   - Starting from `:RCA` and walking more `FAMILY_OF` hops goes beyond the source.
   - Time: family and associate measures end when the PEP leaves office (reg 35(11)) [T32]; 7.2 does not say so.
14. **cash_commingling.** 7.2 compares "peers with the same `sector`"; FFIEC compares "similar restaurants in the area" [T7], so sector and area.
15. **trade_based_ml.** Consistent.

### 17.2 Corrections to the Phase 1 research note (aml-domain.md)

1. Section 2(g) cites a FinCEN "Purpose of the shell company is unknown or unclear" family of indicators. That wording was not found in FIN-2006-G014 as read today; the guidance's own list is quoted in sections 3 and 8 [T11]. Re-check before reuse.
2. Section 2(e) joins separate FIN-2025-A003 indicators into one quote. The p. 9 indicators are separate items. Today's extraction did not find the words "receives numerous transfers or deposits, and has a significant number of withdrawals or transfers"; the p. 9 text found reads "or receives multiple wire, ACH, or P2P transfers for no business or apparent lawful purpose." [T9] They may sit elsewhere in the advisory (UNVERIFIED either way).
3. Section 4 quotes the ICIJ disclaimer as "any persons, companies or other entities" and "located in the database based on addresses". The FAQ today reads "any individuals, companies or other entities" and "found in the database using addresses" [T67]. The header disclaimer was not re-read (UNVERIFIED).
4. The brief for this note said the EU test is "more than 50 percent". The 2024 Best Practices say "50% or more" [T61].

## Sources

All opened on 18 October 2026 unless marked local. "New" keys are proposed for `docs/sources/bibliography.yaml`; "P1" keys are in PHASE-1.md 7.3; "P2" keys are in PHASE-2.md 7.5.

**United States**
- [T1] 31 CFR 1010.100(xx), definition of structure (LII copy). https://www.law.cornell.edu/cfr/text/31/1010.100 . Key `cfr_31_1010_100_2026` (new; living text).
- [T2] 31 CFR 1010.311, filing obligations for reports of transactions in currency (LII copy). https://www.law.cornell.edu/cfr/text/31/1010.311 . Key `cfr_31_1010_311_2026` (new; living text).
- [T3] 31 CFR 1010.313, aggregation (LII copy). https://www.law.cornell.edu/cfr/text/31/1010.313 . Key `cfr_31_1010_313_2026` (new; living text).
- [T4] 31 CFR 1010.314, structured transactions (LII copy). https://www.law.cornell.edu/cfr/text/31/1010.314 . Key `cfr_31_1010_314` (P1).
- [T5] FFIEC BSA/AML Manual, Appendix G: Structuring. https://bsaaml.ffiec.gov/manual/Appendices/08 . Key `ffiec_appendix_g` (P1). No date shown.
- [T6] FFIEC BSA/AML Manual, Appendix F: Money Laundering and Terrorist Financing Red Flags. https://bsaaml.ffiec.gov/manual/Appendices/07 . Key `ffiec_appendix_f` (P1).
- [T7] FFIEC BSA/AML Manual, Cash-Intensive Businesses. https://bsaaml.ffiec.gov/manual/RisksAssociatedWithMoneyLaunderingAndTerroristFinancing/26 . Key `ffiec_cash_intensive` (P1).
- [T8] FinCEN Advisory FIN-2014-A005, Update on U.S. Currency Restrictions in Mexico: Funnel Accounts and TBML, 28 May 2014. https://www.fincen.gov/resources/advisories/fincen-advisory-fin-2014-a005 . Key `fincen_fin_2014_a005` (P1).
- [T9] FinCEN Advisory FIN-2025-A003, Chinese Money Laundering Networks, August 2025. https://www.fincen.gov/system/files/2025-08/FinCEN-Advisory-CMLN-508.pdf . Key `fincen_fin_2025_a003` (P1).
- [T10] FinCEN Advisory FIN-2020-A003, Imposter Scams and Money Mule Schemes Related to COVID-19, 7 July 2020. https://www.fincen.gov/sites/default/files/advisory/2020-07-07/Advisory_%20Imposter_and_Money_Mule_COVID_19_508_FINAL.pdf . Key `fincen_mule_advisory_2020` (new). Its full red flag list could not be extracted (UNVERIFIED).
- [T11] FinCEN Guidance FIN-2006-G014, Potential Money Laundering Risks Related to Shell Companies, 9 November 2006. https://www.fincen.gov/resources/statutes-regulations/guidance/potential-money-laundering-risks-related-shell-companies . Key `fincen_fin_2006_g014` (P1).
- [T12] OFAC, Revised Guidance on Entities Owned by Persons Whose Property and Interests in Property Are Blocked, 13 August 2014. https://ofac.treasury.gov/media/6186/download . Key `ofac_50_percent_2014` (P1).
- [T13] OFAC FAQs 398 to 402 (topic 1521). https://ofac.treasury.gov/faqs/topic/1521 . Key `ofac_50_percent_faqs` (P2).
- [T14] OFAC, Guidance on Sham Transactions and Sanctions Evasion, 31 March 2026. https://ofac.treasury.gov/media/935441/download?inline . Key `ofac_sham_transactions_2026` (P2).

**FATF, Egmont, Europol, Wolfsberg**
- [T15] FATF Recommendations, updated June 2026 (PDF). https://www.fatf-gafi.org/content/dam/fatf-gafi/recommendations/fatf-recommendations-2012.pdf . Key `fatf_recommendations_2026` (P1). The PDF text the tool reads stops before INR.10 and INR.24, so the 25 percent example and the INR.24 nominee wording were not re-checked (UNVERIFIED).
- [T16] FATF, Frequently asked questions: How is money laundered? https://www.fatf-gafi.org/en/pages/frequently-asked-questions.html . Key `fatf_faq` (P1).
- [T17] FATF, Professional Money Laundering, July 2018. https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf.coredownload.pdf . Key `fatf_pml_2018` (P1). Page numbers from running headers.
- [T18] FATF, INTERPOL and Egmont, Illicit Financial Flows from Cyber-Enabled Fraud, November 2023 (read via mirror https://www.cbr.ru/Content/Document/File/156253/IFF.PDF). https://www.fatf-gafi.org/en/publications/Methodsandtrends/illicit-financial-flows-cyber-enabled-fraud.html . Key `fatf_cyber_fraud_2023` (P1).
- [T19] FATF and Egmont, Trade-Based Money Laundering: Trends and Developments, December 2020 (read via mirror https://www.cbr.ru/Content/Document/File/117629/TBML.pdf). https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-trends-and-developments.html . Key `fatf_egmont_tbml_2020` (P1).
- [T20] FATF and Egmont, Trade-Based Money Laundering: Risk Indicators, March 2021 (read via mirror https://www.cbr.ru/Content/Document/File/119937/TBLMRI.PDF). https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-indicators.html . Key `fatf_egmont_tbml_indicators_2021` (P1).
- [T21] FATF and Egmont, Concealment of Beneficial Ownership, July 2018, main report (read via mirror https://www.aml.gov.sa/en-us/GuidanceReports/Concealment%20of%20Beneficial%20Ownership.pdf). https://www.fatf-gafi.org/en/publications/Methodsandtrends/Concealment-beneficial-ownership.html . Key `fatf_egmont_concealment_2018` (P1).
- [T22] Same report, Annex E: Indicators of Concealed Beneficial Ownership. https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-annex-E.pdf . Key `fatf_egmont_concealment_2018` (P1, extra URL).
- [T23] FATF, Money Laundering Using Trust and Company Service Providers, October 2010 (landing page and PDF). https://www.fatf-gafi.org/en/publications/Methodsandtrends/Moneylaunderingusingtrustandcompanyserviceproviders.html ; https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Money%20Laundering%20Using%20Trust%20and%20Company%20Service%20Providers..pdf.coredownload.pdf . Key `fatf_tcsp_2010` (P1). The tool read part of the PDF only.
- [T24] FATF Guidance: Politically Exposed Persons (Recommendations 12 and 22), June 2013 (PDF). https://www.fatf-gafi.org/content/dam/fatf-gafi/guidance/Guidance-PEP-Rec12-22.pdf . Key `fatf_peps_2013` (P1; add the PDF as extra URL). Paragraph and page numbers as extracted.
- [T25] Europol, European Financial and Economic Crime Threat Assessment 2023: The Other Side of the Coin. https://www.europol.europa.eu/cms/sites/default/files/documents/The%20Other%20Side%20of%20the%20Coin%20-%20Analysis%20of%20Financial%20and%20Economic%20Crime%20(EN).pdf . Key `europol_efecta_2023` (P1).
- [T26] Europol, Shadow Money: The International Networks of Illicit Finance, December 2021. https://www.europol.europa.eu/cms/sites/default/files/documents/Shadow%20money%20%E2%80%93%20the%20international%20networks%20of%20illicit%20finance_PUBLIC_0.pdf . Key `europol_shadow_money_2021` (P1).
- [T27] Europol, Money Muling (prevention guide; body needs JavaScript, text from page metadata). https://europol.europa.eu/operations-services-and-innovation/public-awareness-and-prevention-guides/money-muling . Key `europol_money_muling` (P1).
- [T28] Wolfsberg Group, Publication of the updated Wolfsberg Group Payment Transparency Standards, 19 October 2023. https://wolfsberg-group.org/news/50 . Key `wolfsberg_payment_transparency_2023` (P1).

**United Kingdom: legislation and guidance**
- [T29] MLR 2017, regulation 27 (up to date to 18 October 2026). https://www.legislation.gov.uk/uksi/2017/692/regulation/27 . Key `mlr_reg_27_2017` (new).
- [T30] MLR 2017, regulation 14. https://www.legislation.gov.uk/uksi/2017/692/regulation/14 . Key `mlr_reg_14_2017` (new).
- [T31] The Money Laundering and Terrorist Financing (Amendment) Regulations 2026, S.I. 2026/621 (sums substituted 30 June 2026, as annotated on reg 27; reg 20 inserts reg 34A on cryptoasset correspondents, not yet applied). https://www.legislation.gov.uk/uksi/2026/621/regulation/20 . Key `mlr_amendment_regs_2026` (new). Regulation 1 (commencement) failed to load (UNVERIFIED).
- [T32] MLR 2017, regulation 35 (up to date to 16 October 2026). https://www.legislation.gov.uk/uksi/2017/692/regulation/35 . Key `mlr_2017_reg_35` (P2).
- [T33] FCA FG25/3, The treatment of politically exposed persons for anti-money laundering purposes, 7 July 2025, revised 15 July 2025. https://www.fca.org.uk/publication/finalised-guidance/fg25-3.pdf . Key `fca_fg25_3` (P2).
- [T34] HMRC, Risks common to all high value dealers, updated 14 November 2025. https://www.gov.uk/government/publications/anti-money-laundering-guidance-for-high-value-dealers/risks-common-to-all-high-value-dealers . Key `hmrc_hvd_risks_2025` (new).
- [T35] HMRC, ECSH51525: Introduction to high value dealers, updated 10 December 2025. https://www.gov.uk/hmrc-internal-manuals/economic-crime-supervision-handbook/ecsh51525 . Key `hmrc_ecsh51525_2025` (new).
- [T36] OFSI, UK financial sanctions general guidance, section 4, updated 12 May 2026. https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance . Key `ofsi_general_guidance_2026` (P2).
- [T37] The Russia (Sanctions) (EU Exit) Regulations 2019, S.I. 2019/855, regulation 7 and Schedule 1. https://www.legislation.gov.uk/uksi/2019/855/regulation/7 ; https://www.legislation.gov.uk/uksi/2019/855/schedule/1 . Key `russia_sanctions_regs_2019` (new).
- [T38] Dormant Bank and Building Society Accounts Act 2008, section 10. https://www.legislation.gov.uk/ukpga/2008/31/section/10 . Key `dormant_accounts_act_2008` (new).
- [T39] Companies Act 2006, section 1169 (dormant companies; up to date to 17 October 2026). https://www.legislation.gov.uk/ukpga/2006/46/section/1169 . Key `ca_dormant_company_s1169_2006` (new).
- [T40] Companies Act 2006, section 86 (registered office at an appropriate address; up to date to 18 October 2026). https://www.legislation.gov.uk/ukpga/2006/46/section/86 . Key `ca_registered_office_s86_2006` (new).
- [T41] Economic Crime and Corporate Transparency Act 2023, section 28. https://www.legislation.gov.uk/ukpga/2023/56/section/28 . Key `eccta_registered_office_s28_2023` (new).
- [T42] Companies House, Improving the quality of data on our registers (campaign page; modified 14 May 2025). https://changestoukcompanylaw.campaign.gov.uk/improving-the-quality-of-data-on-our-registers/ . Key `ch_register_data_quality_2025` (new).
- [T43] Companies House, Registrar's Rules Volume 6: Nomination of Default Address (made 28 February 2024, in force 4 March 2024). https://assets.publishing.service.gov.uk/media/6925c5422945773cf12dd069/Registrar_s_Rules___Volume_6-_Nomination_of_Default_Address.pdf . Key `ch_default_address_rules_2024` (new).
- [T44] Companies Act 2006, section 1098A (meaning of authorised corporate service provider). https://www.legislation.gov.uk/ukpga/2006/46/section/1098A . Key `ca_acsp_s1098a_2006` (new).
- [T45] Companies Act 2006, section 1067A (delivery of documents: identity verification requirements). https://www.legislation.gov.uk/ukpga/2006/46/section/1067A . Key `ca_delivery_idv_s1067a_2006` (new).
- [T46] Companies House, Authorised Corporate Service Providers (campaign page; modified 5 August 2026). https://changestoukcompanylaw.campaign.gov.uk/authorised-corporate-service-providers . Key `ch_acsp_campaign_2026` (new).
- [T47] GOV.UK, Being an Authorised Corporate Service Provider (ACSP), published 19 February 2025, updated 19 June 2026. https://www.gov.uk/guidance/being-an-authorised-corporate-service-provider . Key `ch_acsp_guidance_2026` (new).
- [T48] Companies Act 2006, section 167M (prohibition on director acting unless ID verified). https://www.legislation.gov.uk/ukpga/2006/46/section/167M . Key `ca_director_idv_s167m_2006` (new).
- [T49] The Economic Crime and Corporate Transparency Act 2023 (Commencement No. 6 and Transitional Provisions) Regulations 2025, S.I. 2025/1118, made 22 October 2025. https://www.legislation.gov.uk/uksi/2025/1118 . Key `eccta_commencement_no6_2025` (new).
- [T50] Companies House, Companies House confirms identity verification rollout from 18 November 2025 (press release, 5 August 2025). https://www.gov.uk/government/news/companies-house-confirms-identity-verification-rollout-from-18-november-2025 . Key `ch_idv_rollout_2025` (new).
- [T51] Companies House Public Data API, officerSummary resource (identity_verification_details). https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/officersummary?v=latest . Key `ch_officer_api_2026` (new; living).
- [T52] Companies House, `psc_descriptions.yml` (api-enumerations, commit 05067ab of 11 September 2026, cloned today). https://github.com/companieshouse/api-enumerations/blob/master/psc_descriptions.yml . Key `ch_psc_descriptions` (P2). Its long descriptions still say "more than 50% but not more than 75%" and "more than 75%"; the short descriptions match the statute.
- [T53] Defamation Act 2013, sections 1 and 4. https://www.legislation.gov.uk/ukpga/2013/26/section/1 ; https://www.legislation.gov.uk/ukpga/2013/26/section/4 . Key `defamation_act_2013` (new).
- [T54] Travel Insurance Facilities Plc v Times Newspapers Plc [2019] EWHC 1337 (QB), para 16 (The National Archives, Find Case Law). https://caselaw.nationalarchives.gov.uk/ewhc/qb/2019/1337 . Key `ewhc_qb_1337_2019` (new). The 2002 Court of Appeal judgment it quotes was blocked on BAILII.
- [T55] UK GDPR (retained Regulation (EU) 2016/679 as amended), Articles 4(4), 22A, 22B, 22C and 25. https://www.legislation.gov.uk/eur/2016/679/article/4 ; https://www.legislation.gov.uk/eur/2016/679/article/22A ; https://www.legislation.gov.uk/eur/2016/679/article/22B ; https://www.legislation.gov.uk/eur/2016/679/article/22C ; https://www.legislation.gov.uk/eur/2016/679/article/25 . Key `uk_gdpr_adm_2026` (new).
- [T56] Data Protection Act 2018, section 11 (up to date to 16 October 2026). https://www.legislation.gov.uk/ukpga/2018/12/section/11 . Key `dpa_criminal_data_s11_2018` (new).
- [T57] Data Protection Act 2018, Schedule 2, paragraph 26 (up to date to 10 October 2026). https://www.legislation.gov.uk/ukpga/2018/12/schedule/2/paragraph/26 . Key `dpa_special_purposes_2018` (new).

**European Union**
- [T58] Regulation (EU) 2024/1624 (AMLR), Articles 2, 19, 80 and 90 (read via mirror https://www.springlex.eu/en/packages/aml/amlr-regulation/article-80/ and the article-2, article-19 and article-90 pages, which show "Source: OJ L, 2024/1624, 19.6.2024"; the EUR-Lex text is too long for the tool). https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng . Key `eu_amlr_2024` (new). Paragraph and point numbers on the mirror were inferred from order (UNVERIFIED).
- [T59] AMLA, Final Report: draft RTS under Article 19(9) AMLR (30 September 2026), factsheet, and press release "AMLA finalises key standards for the private sector" (1 October 2026). https://www.amla.europa.eu/document/download/32e5aea0-52dc-4b0c-b93a-b0dd373fcd0f_en?filename=Final%20Report%20-%20draft%20RTS%20under%20Article%2019%289%29%20AMLR.pdf ; https://www.amla.europa.eu/document/download/43ec825d-5671-4ffd-b94c-33fc2aa2719d_en?filename=Factsheet%20on%20RTS%20under%20Article%2019%289%29%20AMLR.pdf ; https://www.amla.europa.eu/press-release-amla-finalises-key-standards-private-sector_en . Key `amla_rts_linked_transactions_2026` (new). A final draft, not yet adopted by the Commission.
- [T60] EBA, Guidelines on ML/TF risk factors, EBA/GL/2021/02 (text read from the CSSF-hosted copy https://www.cssf.lu/wp-content/uploads/cssf21_782eng.pdf; EBA page https://eba.europa.eu/regulation-and-policy/anti-money-laundering-and-e-money/revised-guidelines-on-ml-tf-risk-factors). Key `eba_risk_factors_guidelines_2021` (new).
- [T61] Council of the EU, EU Best Practices for the effective implementation of restrictive measures, 11623/24, 3 July 2024, paras 63 to 68. https://data.consilium.europa.eu/doc/document/ST-11623-2024-INIT/en/pdf . Key `eu_best_practices_2024` (P2).
- [T62] Council Regulation (EC) No 2580/2001, Article 1(5) and (6). https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32001R2580 . Key `eu_reg_2580_2001` (new).
- [T63] European Commission, Frequently asked questions: asset freeze and prohibition to make funds and economic resources available (Council Regulation 269/2014), as of 6 May 2026; FAQs 8, 9, 17 and 43. https://finance.ec.europa.eu/system/files/2023-07/faqs-sanctions-russia-assets-freezes_en.pdf . Key `ec_asset_freeze_faq_2026` (new).
- [T64] Regulation (EU) 2016/679 (GDPR), Article 22 (read via mirror https://gdpr-info.eu/art-22-gdpr/). https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679 . Key `eu_gdpr_art22_2016` (new).
- [T65] Court of Justice of the EU, Case C-634/21, SCHUFA Holding (Scoring), judgment of 7 December 2023, operative part. https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62021CJ0634 . Key `cjeu_schufa_2023` (new).
- [T66] Regulation (EU) 2024/1689 (AI Act), Article 3(1), Article 5(1)(d) and recital 12 (read via mirror https://artificialintelligenceact.eu/article/5/ , /article/3/ and /recital/12/). https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng . Key `eu_ai_act_2024` (new).

**Public tools**
- [T67] ICIJ, Offshore Leaks Database FAQ. https://offshoreleaks.icij.org/pages/faq . Key `icij_faq` (P1).
- [T68] OpenSanctions, Glossary. https://www.opensanctions.org/docs/glossary . Key `opensanctions_glossary` (P1).
- [T69] OpenSanctions, PEP methodology. https://www.opensanctions.org/docs/coverage/pep/methodology/ . Key `opensanctions_pep_methodology_2026` (new; living).
- [T70] OCCRP, Legal Notice. https://www.occrp.org/en/legal-notice . Key `occrp_legal_notice_2026` (new; living).
- [T71] OpenCorporates, Terms of use. https://opencorporates.com/terms-of-use-2/ . Key `opencorporates_terms` (P1).

**Local project files (read, not edited)**
- [T72] Phase 2 research note, sanctions and PEPs: /home/claude/neonradar-phase2/research/sanctions-peps.md (sections 1.4, 2.8, 7.1, 8, 9). No key (local).
- [T73] PHASE-1 build spec: /home/claude/neonradar-phase1/doc/PHASE-1.md (5.2, 5.4, M1.8e, M1.9b, 7.1 to 7.3). No key (local).
- [T74] Phase 1 research note: /home/claude/neonradar-phase1/research/aml-domain.md (sections 1, 2 and 4). No key (local).
- [T75] PHASE-2 wording rules: /home/claude/neonradar-phase2/doc/parts/07b-wording-labels-data.md (7.2 rules 1 to 7). No key (local).
- [T76] PHASE-2 contracts: /home/claude/neonradar-phase2/doc/parts/05-contracts.md (C2 1.1.0 properties). No key (local).
