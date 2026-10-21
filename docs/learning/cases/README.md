# Real cases

Three public cases whose structure fits on one slide as a graph. Each note shows what the money flows and the companies looked like, in roles rather than names, and keeps what courts decided apart from what is only alleged. They are learning material: NeonRadar loads no data about these cases, and its synthetic scenarios run only among synthetic entities (guardrail G1 in [PHASE-1.md](../../build/PHASE-1.md) section 2.1).

| Case | Period | What it shows in a graph | Adjudicated or admitted | Typologies |
|---|---|---|---|---|
| [Danske Bank, Estonian branch](danske-bank-estonia.md) | 2007 to 2015 | One branch holding thousands of non-resident customer accounts, with payments passing through US correspondent banks [danske_bruun_hjejle_2018] [doj_danske_2022] | The bank's guilty plea in the United States, December 2022 [doj_danske_2022] | [`rapid_pass_through`](../../typologies/rapid-pass-through.md) |
| [The Azerbaijani Laundromat](azerbaijani-laundromat.md) | 2012 to 2014 | Four UK-registered partnerships with accounts at one bank branch, transfers among them, and a fan-out to many recipients, as reported by journalists [occrp_azerbaijani_laundromat_2017] | One first-instance bribery conviction, January 2021 [occrp_pace_bribery_2021] | [`shell_chain`](../../typologies/shell-chain.md), [`mass_registration_address`](../../typologies/mass-registration-address.md), [`rapid_pass_through`](../../typologies/rapid-pass-through.md), [`fan_out_distribution`](../../typologies/fan-out-distribution.md) |
| [1MDB](1mdb.md) | 2009 to 2015 | A state fund, bond issuances, companies abroad (one with a name resembling a genuine entity) and onward payments into assets; everything after the bond issuances is alleged in US civil forfeiture complaints [doj_1mdb_complaint_2025] | One bank's guilty plea and deferred prosecution agreement, October 2020 [doj_goldman_2020]; two former bankers, one convicted at trial [doj_ng_sentencing_2023] and one who pleaded guilty [doj_goldman_2020] | [`layering_chain`](../../typologies/layering-chain.md), [`fan_out_distribution`](../../typologies/fan-out-distribution.md), [`shell_chain`](../../typologies/shell-chain.md), `pep_exposure` |

The typology slugs link to their explainers in [docs/typologies/](../../typologies/README.md); the definitions are in `detect/typologies/`. The `pep_exposure` explainer arrives with the third typology batch (M1.10b-3). A typology listed for a case names a graph pattern that the reported structure shows. It is not a finding about any company or person.

## How the notes are written

Every note follows the documentation rules in [docs/wording.md](../../wording.md):

- **Names.** A note names as wrongdoers only institutions that admitted facts and individuals who were convicted, with the court level. Victims, publishers, courts and authorities may be named in those roles. Everyone else is described by role ("a recipient of payments", "a former member of a parliamentary assembly").
- **Adjudicated and alleged.** Each note has a section for what a court decided or a party admitted, a section for what is alleged or unresolved, and, where the source is a party's own investigation, a section for what that investigation documented without a court finding.
- **Dates checked.** Each note says when each court outcome was last checked and by whom. Outcomes change on appeal: re-check them before you quote a note in a talk, a slide or the launch post.
- **Diagrams.** Each note has a Mermaid diagram of roles, never names. Dotted arrows mark relationships that are reported, alleged or documented without a court finding; each note says which.
- **Citations.** Every fact cites a key from the [bibliography](../../sources/bibliography.yaml) ([how to cite](../../sources/README.md)). A fact that no cited source supports is left out.
- **Wording.** The notes describe structures. A pattern in a case is a reason to look closer, never evidence on its own, and the [standing disclaimer](../../wording.md#disclaimers) applies to every structure shown here.

## Status of the court outcomes

The status of every court outcome in these notes was last checked by the research note [`docs/research/2026-10-16/aml-domain.md`](../../research/2026-10-16/aml-domain.md) on 15 and 16 October 2026, and some sources were re-opened on 21 October 2026 (each note's "Status checked" table says which). The US Department of Justice (DOJ) press releases answer automated clients with a bot challenge, so the build could not re-open them on 21 October 2026. A person re-checks each outcome in a browser before these notes are published, and updates the dates.

## Cases not used

The research note describes a fourth case, reported by journalists in 2019, in which nothing had been adjudicated in the sources it checked ([`aml-domain.md`](../../research/2026-10-16/aml-domain.md) section 5.3). NeonRadar does not use it as a case note. It may appear later only as an anonymised structural illustration.

## Adding a case

Open a pull request with the `learning` label. Use the shape of the existing notes (summary, diagram, typologies, adjudicated or admitted, alleged, status checked, sources), add any new source to the bibliography first, and ask a typology researcher to review it. If nothing in a case has been adjudicated or admitted, do not add it.

## Sources

- [danske_bruun_hjejle_2018] Bruun & Hjejle for Danske Bank, *Report on the Non-Resident Portfolio at Danske Bank's Estonian branch*, 2018. <https://danskebank.com/news-and-insights/news-archive/press-releases/2018/pr19092018>
- [doj_1mdb_complaint_2025] US Department of Justice, *Verified complaint for forfeiture in rem, C.D. Cal. 2:25-cv-00474*, 2025. <https://www.justice.gov/opa/media/1385611/dl>
- [doj_danske_2022] US Department of Justice, *Danske Bank Pleads Guilty to Fraud on U.S. Banks in Multi-Billion Dollar Scheme to Access the U.S. Financial System*, 2022. <https://www.justice.gov/opa/pr/danske-bank-pleads-guilty-fraud-us-banks-multi-billion-dollar-scheme-access-us-financial>
- [doj_goldman_2020] US Department of Justice, *Goldman Sachs Charged in Foreign Bribery Case and Agrees to Pay Over $2.9 Billion*, 2020. <https://www.justice.gov/archives/opa/pr/goldman-sachs-charged-foreign-bribery-case-and-agrees-pay-over-29-billion>
- [doj_ng_sentencing_2023] US Department of Justice, *Former Goldman Sachs Investment Banker Sentenced for $2.7B Bribery and Money Laundering Scheme*, 2023. <https://www.justice.gov/opa/pr/former-goldman-sachs-investment-banker-sentenced-27b-bribery-and-money-laundering-scheme>
- [occrp_azerbaijani_laundromat_2017] OCCRP, *The Azerbaijani Laundromat*, 2017. <https://www.occrp.org/en/project/the-azerbaijani-laundromat>
- [occrp_pace_bribery_2021] OCCRP, *Italian Court Sentences Former Council of Europe MP for Bribery*, 2021. <https://www.occrp.org/en/news/italian-court-sentences-former-council-of-europe-mp-for-bribery>
