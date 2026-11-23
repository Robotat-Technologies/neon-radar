# One pattern a week

A short social post series: each week, one money-laundering pattern explained in plain words, with its source and without accusations. This page holds the rules and the first month of drafts. **The posts are drafts. A person reviews each one and decides when to publish it.**

## Rules for every post

- **One pattern, one post, about 100 words.** What the pattern is, why it is not proof on its own, and a link to the full explainer.
- **Only what the explainer says, with its source.** Every statement about money laundering in a post is one that the pattern's explainer in [docs/typologies/](../typologies/README.md) makes with a bibliography key, and the post names that source. Look-alikes come from the explainer's own list. Add nothing the explainer does not say ([CLAUDE.md](../../CLAUDE.md) rule 4; [sources](../sources/README.md)).
- **Say it is a draft explainer** until a typology researcher has approved the pattern. All 15 are drafts today.
- **Patterns, never accusations.** Never name a real person, company or address, and never use the words that [wording.md](../wording.md) forbids next to an entity.
- **Ordinary look-alikes in every post.** Each explainer lists them under "Typical false positives". Every post carries the line: *A pattern is a reason to look closer, not evidence of wrongdoing.*
- **Images from the synthetic demo only**, checked against the [screenshot and video policy](../screenshot-policy.md).

## Order

The first five patterns have explainers that teammates have already checked against their sources, in pull requests #117 (circular flow), #151 (structuring), #153 (fan-out), #125 and #144 (mass registration address) and #132 (rapid pass-through). The rest follow once their checks merge. Week 5 is not drafted yet.

| Week | Pattern | Explainer |
|---|---|---|
| 1 | Circular flows | [circular-flow.md](../typologies/circular-flow.md) |
| 2 | Structuring | [structuring.md](../typologies/structuring.md) |
| 3 | Fan-out | [fan-out-distribution.md](../typologies/fan-out-distribution.md) |
| 4 | Mass registration addresses | [mass-registration-address.md](../typologies/mass-registration-address.md) |
| 5 | Rapid pass-through | [rapid-pass-through.md](../typologies/rapid-pass-through.md) |

## Week 1: money that comes back

Round-tripping means payments routed in a circle, so that funds return to where they started. The FATF and the Egmont Group list it among their trade-based money-laundering indicators. Their beneficial-ownership report adds cycles in which "outgoing funds are being returned with little loss".

NeonRadar's draft explainer lists ordinary look-alikes: refunds, a loan paid out and paid back, intra-group cash pooling. It also shows how the circle looks in a graph.

A pattern is a reason to look closer, not evidence of wrongdoing.

Sources: FATF and Egmont Group, *Trade-Based Money Laundering: Risk Indicators* (2021) [fatf_egmont_tbml_indicators_2021]; *Concealment of Beneficial Ownership* (2018) [fatf_egmont_concealment_2018]. Explainer: [circular-flow.md](../typologies/circular-flow.md).

## Week 2: many small deposits

Under US rules, structuring means conducting or attempting currency transactions for the purpose of evading reporting requirements. Breaking a sum above USD 10,000 into smaller transactions is one example, but the transactions do not have to exceed USD 10,000 at one bank on one day.

The draft explainer lists ordinary look-alikes: a shop banking its takings every evening, a cash-in-transit cap, fixed weekly savings. The FFIEC cautions that even two USD 9,900 deposits days apart do not necessarily establish structuring; prior account history and customer context need review.

A pattern is a reason to look closer, not evidence of wrongdoing.

Sources: FFIEC, *BSA/AML Examination Manual, Appendix G: Structuring* [ffiec_appendix_g]. Explainer: [structuring.md](../typologies/structuring.md).

## Week 3: one account, many recipients

In NeonRadar's draft definition, fan-out is one account sending money to many recipient accounts, potentially within a short period. FinCEN lists "An unusually large number and variety of beneficiaries receive wire transfers from one company" among its indicators for shell companies, and the FFIEC red flags include it too.

The draft explainer lists ordinary look-alikes with the same shape: payroll, supplier batches, dividends, benefit payments and marketplace payouts.

A pattern is a reason to look closer, not evidence of wrongdoing.

Sources: FinCEN, *FIN-2006-G014: Potential Money Laundering Risks Related to Shell Companies* (2006) [fincen_fin_2006_g014]; FFIEC, *BSA/AML Examination Manual, Appendix F: Money Laundering and Terrorist Financing "Red Flags"* [ffiec_appendix_f]. Explainer: [fan-out-distribution.md](../typologies/fan-out-distribution.md).

## Week 4: one address, many companies

**[DO NOT PUBLISH UNTIL the mass-registration-address explainer has been cleaned up: some of its paragraphs and red flags appear twice, with different page numbers.]**

When many companies list the same registered address, the FATF and the Egmont Group count it among the indicators of concealed beneficial ownership: an "Address of mass registration (usually the address of a TCSP that manages a number of shell companies on behalf of its customers)". A trust and company service provider (TCSP) offers company services to others, and providing a registered office is one of them. FATF found that "the majority of TCSPs appear to be established for legitimate purposes".

The draft explainer lists other look-alikes: serviced offices, law firms acting as registered office, and errors in the source register.

A pattern is a reason to look closer, not evidence of wrongdoing.

Sources: FATF and Egmont Group, *Concealment of Beneficial Ownership* (2018), Annex E [fatf_egmont_concealment_2018]; FATF, *FATF Glossary* [fatf_glossary]; FATF, *Money Laundering Using Trust and Company Service Providers* (2010) [fatf_tcsp_2010]. Explainer: [mass-registration-address.md](../typologies/mass-registration-address.md).
