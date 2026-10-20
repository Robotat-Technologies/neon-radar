# AML Domain Research: Primary Sources, Typologies, Terminology, Framing and Cases

Prepared for the NeonRadar Phase 1 project (open-source educational detection of laundering typologies in a graph database).

Verification window: 15 to 16 October 2026. Every document below was checked by fetching the publisher's page or PDF (or, where the publisher blocks automated fetching, a mirror plus the publisher's own index entry). Where a document could not be verified it is marked UNVERIFIED. Quotes are short and verbatim; page or paragraph references are given where the source showed them.

Project rule reminder: every AML claim in project documentation must cite one of the sources in Section 1 or Section 6. Items labelled "secondary" are useful for context but should not be the sole citation for a claim.

---

## 0. Corrections to the brief, up front

1. The FATF Recommendations were last updated in June 2026 (cover: "Updated June 2026"; page: "Last updated in June 2026"). Several third-party mirrors still say "Updated October 2025" or "February 2025"; cite the FATF page, not the mirrors. The June 2026 change amended Recommendation 6 (humanitarian exemptions per UNSCR 2664 and 2761). Recommendation 16 (payment transparency) was revised in June 2025, with implementation guidance put to consultation in June 2026.
2. Europol "Shadow Money" is dated December 2021, not 2020. Its full title is "Shadow Money - The International Networks of Illicit Finance" (Europol Spotlight, published in the wake of the Pandora Papers). A 2020 Europol financial crime report ("Enterprising criminals", June 2020) exists in search indexes via a Statewatch mirror only; it is UNVERIFIED here.
3. A FATF report titled "Money Laundering and Terrorist Financing through the Misuse of Legal Persons" could not be found on fatf-gafi.org or in any index. UNVERIFIED. Use instead: FATF "Guidance on Transparency and Beneficial Ownership" (October 2014), FATF "Best Practices on Beneficial Ownership for Legal Persons" (October 2019), and the 2006 and 2018 reports already on the list.
4. The Egmont "100 cases" publication is "FIUs in Action: 100 Cases from the Egmont Group" (circa 2000, issued on CD-ROM; the text itself gives no publication date). Egmont's more recent case compilations are the "Best Egmont Cases" books (2014-2020 edition published 2021; 2021-2023 edition published 2024).
5. The Wolfsberg "Anti-Money Laundering Principles for Correspondent Banking" (2014) has been retired; the current document is "Financial Crime Principles for Correspondent Banking" (2022). The payment transparency document is "Wolfsberg Group Payment Transparency Standards 2023".
6. The "2 to 5 percent of GDP" figure is not UNODC's own estimate. UNODC (2011) attributes it to the IMF (Michel Camdessus, February 1998 speech) and produces its own estimate of about 2.7 percent of global GDP (USD 1.6 trillion) laundered in 2009, within a range of 2.1 to 4 percent. Cite accordingly.
7. No standalone FATF report on money mules was published in 2024 to 2026 as far as could be found. The closest FATF material is the FATF/INTERPOL/Egmont report "Illicit Financial Flows from Cyber-Enabled Fraud" (November 2023), the FATF paper "Cyber-Enabled Fraud - Digitalisation and ML/TF/PF Risks" (February 2026), and "Professional Money Laundering" (2018). The June 2026 plenary approved a report on hawala and similar providers, "including by professional money launderers", for September 2026; its publication was not verified in this check. FATF did publish "Complex Proliferation Financing and Sanctions Evasion Schemes" (June 2025) and the "Seventh Targeted Update on Implementation of the FATF Standards on Virtual Assets/VASPs" (July 2026).
8. The FATF/Egmont "Concealment of Beneficial Ownership" report analysed 106 case studies (the executive summary says "Analysis of 106 case studies"; the landing page says "over 100 case studies" from 34 jurisdictions).

---

## 1. Curated reading list (25 primary documents, plus supporting sources)

Format: title; publisher; year; URL; verification; two-sentence summary; typologies covered.

### 1.1 International Standards on Combating Money Laundering and the Financing of Terrorism and Proliferation: The FATF Recommendations
- Publisher: FATF. Adopted 16 February 2012; "Updated June 2026".
- URL: https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html (PDF: https://www.fatf-gafi.org/content/dam/fatf-gafi/recommendations/fatf-recommendations-2012.pdf)
- Verification: VERIFIED 16 October 2026 (landing page and PDF cover both show June 2026).
- Summary: The 40 Recommendations, their Interpretive Notes and the General Glossary are the global AML/CFT/CPF standard against which countries are assessed. They define beneficial owner, PEP, DNFBP, TCSP, shell bank and correspondent banking, and set customer due diligence (R.10), PEP (R.12), correspondent banking (R.13), wire transfer (R.16), suspicious transaction reporting (R.20), beneficial ownership (R.24 and R.25) and FIU (R.29) obligations.
- Typologies: all, as the normative baseline. Interpretive Note to R.10 footnote: "A controlling ownership interest depends on the ownership structure of the company. It may be based on a threshold, e.g. any person owning more than a certain percentage of the company (e.g. 25%)." (2012 text, footnote 30, p. 60; reproduced in Tax Justice Network 2016, see Section 6.)

### 1.2 Guidance on Beneficial Ownership of Legal Persons
- Publisher: FATF. 10 March 2023.
- URL: https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Legal-Persons.html
- Verification: VERIFIED 15 October 2026.
- Summary: Explains how to implement revised Recommendation 24 (agreed March 2022), which requires authorities to have access to "adequate, accurate and up-to-date information on the true owners of companies". It describes the "multi-pronged approach" (company-held information, a registry or alternative mechanism, and other sources) and addresses risks from foreign companies.
- Typologies: shell company chains, nominees, bearer shares, indirect ownership and control.

### 1.3 Guidance on Beneficial Ownership and Transparency of Legal Arrangements
- Publisher: FATF. 11 March 2024.
- URL: https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Transparency-Legal-Arrangements.html
- Verification: VERIFIED 15 October 2026.
- Summary: Risk-based guidance on Recommendation 25 after its February 2023 revision, covering express trusts and similar arrangements. It explains how to assess the ML/TF risk of legal arrangements, what beneficial ownership information trustees must hold, verification, and international cooperation.
- Typologies: concealment through trusts, nominee and trustee structures, indirect control.

### 1.4 Concealment of Beneficial Ownership
- Publisher: FATF and Egmont Group of FIUs. July 2018 (Paris, 18 July 2018).
- URL: https://www.fatf-gafi.org/en/publications/Methodsandtrends/Concealment-beneficial-ownership.html ; Annex E (indicators): https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-annex-E.pdf ; Executive summary: https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-Executive-summary.pdf
- Verification: VERIFIED 15 to 16 October 2026 (landing page, Saudi AML mirror of full PDF, Egmont copies of annex and summary).
- Summary: Based on 106 case studies from 34 jurisdictions, the report finds that legal persons, "principally shell companies, are a key feature in schemes designed to disguise beneficial ownership", that nominee arrangements "were identified in a large majority of case studies", and that "The majority of the case studies involved professional intermediaries", roughly half of them assessed as complicit. Annex E, "Indicators of Concealed Beneficial Ownership", is the single most useful red-flag list for a graph project.
- Typologies: shell and shelf companies, nominees, shared addresses, round-robin transfers, transit accounts, family-member fronts, professional intermediaries.

### 1.5 Professional Money Laundering
- Publisher: FATF. July 2018.
- URL: https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf.coredownload.pdf
- Verification: VERIFIED 15 October 2026 (PDF fetched).
- Summary: Defines professional money launderers (individuals, organisations and networks) who launder for a fee and describes their services: account settlement mechanisms, money mule networks, shell companies with nominees, trade-based schemes, cash controller networks and "proxy networks" of layered shell company accounts across jurisdictions. It notes that mule bank accounts "serve as the initial layering stage" and that funds from different clients "are mixed within the same accounts".
- Typologies: structuring, mule networks (fan-in, fan-out), layering chains, shell company chains, cash controllers, TBML.

### 1.6 Money Laundering Using Trust and Company Service Providers
- Publisher: FATF. October 2010 (adopted at the 20-22 October 2010 plenary).
- URL: https://www.fatf-gafi.org/en/publications/Methodsandtrends/Moneylaunderingusingtrustandcompanyserviceproviders.html
- Verification: VERIFIED 15 October 2026 (landing page and October 2010 plenary outcomes page; the FATF PDF blocks automated fetching, CFATF hosts a mirror dated October 2010).
- Summary: Evaluates how the FATF standards work in practice for TCSPs and finds that "TCSPs have often been used, wittingly or unwittingly, in the conduct of money laundering activities". It builds on the 2006 corporate vehicles study and proposes issues for consideration to reduce TCSP misuse.
- Typologies: formation agents, nominee director and shareholder services, registered office addresses, shell company creation.

### 1.7 The Misuse of Corporate Vehicles, Including Trust and Company Service Providers
- Publisher: FATF. October 2006 (released 13 October 2006).
- URL: https://fatf-gafi.org/content/dam/fatf-gafi/reports/Misuse%20of%20Corporate%20Vehicles%20including%20Trusts%20and%20Company%20Services%20Providers.pdf.coredownload.inline.pdf
- Verification: VERIFIED as to existence, title and date 16 October 2026 (FATF file indexed; release date per International Enforcement Law Reporter abstract, https://www.ielr.com/node/225). Full text could not be fetched (robots block), so quote from it only after a manual download.
- Summary: The first FATF typology study on corporate vehicles, built on a 2005 typologies exercise and a jurisdictional survey. It documents recurring patterns of abuse, the role of TCSPs, and areas warranting stricter regulation, and later reports (2010, 2018) treat it as the baseline.
- Typologies: shell companies, nominees, bearer shares, TCSP misuse.

### 1.8 Trade-Based Money Laundering: Trends and Developments
- Publisher: FATF and Egmont Group. December 2020 (9 December 2020).
- URL: https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-trends-and-developments.html (mirror PDF: https://www.cbr.ru/Content/Document/File/117629/TBML.pdf)
- Verification: VERIFIED 15 October 2026.
- Summary: Restates the 2006 definition of TBML as "the process of disguising the proceeds of crime and moving value through the use of trade transactions" and the basic techniques (over- and under-invoicing, over- and under-shipment including phantom shipments, multiple invoicing, falsely described goods). It explains why detection is hard: open account trade creates "a disconnect between the movement of the underlying trade and the money used to finance it", financial institutions "do not necessarily verify the documents", and trade data is fragmented across stakeholders.
- Typologies: TBML, third-party payments, circular routing.

### 1.9 Trade-Based Money Laundering: Risk Indicators
- Publisher: FATF and Egmont Group. March 2021.
- URL: https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-indicators.html (mirror PDF: https://www.cbr.ru/Content/Document/File/119937/TBLMRI.PDF)
- Verification: VERIFIED 15 October 2026.
- Summary: Groups indicators into structure of the business, trade activity, trade documents and commodities, and account and transaction activity. Several are directly graph-shaped: "A trade entity is registered at an address that is likely to be a mass registration address", "An account of a trade entity appears to be a 'pay-through' or 'transit' account", "Payments are routed in a circle", "Payment for imported commodities is made by an entity other than the consignee".
- Typologies: TBML, shared addresses, nominees, pass-through, round-tripping, fan-in from third parties.

### 1.10 Guidance on Transparency and Beneficial Ownership
- Publisher: FATF. October 2014.
- URL: http://www.fatf-gafi.org/media/fatf/documents/reports/Guidance-transparency-beneficial-ownership.pdf (FSB index entry: https://www.fsb.org/2014/10/guidance-on-transparency-and-beneficial-ownership/)
- Verification: VERIFIED via FSB index 16 October 2026; FATF PDF not fetched.
- Summary: Explains how corporate vehicles are misused and how countries should implement the (then) R.24 and R.25 requirements. Open Ownership notes that this guidance "does not recommend a specific threshold level, but mentions a 25% figure in the context of examples".
- Typologies: shell companies, indirect ownership, the 25 percent threshold.

### 1.11 Best Practices on Beneficial Ownership for Legal Persons
- Publisher: FATF. 24 October 2019.
- URL: http://www.fatf-gafi.org/publications/methodsandtrends/documents/best-practices-beneficial-ownership-legal-persons.html (FSB index: https://www.fsb.org/2019/10/best-practices-on-beneficial-ownership-for-legal-persons/)
- Verification: VERIFIED via FSB index 16 October 2026.
- Summary: Draws on mutual evaluation findings to identify common obstacles to identifying beneficial owners and the features of effective systems. It argues that combining several information sources is more effective than any single mechanism.
- Typologies: shell company chains, nominees, foreign legal persons.

### 1.12 FIUs in Action: 100 Cases from the Egmont Group
- Publisher: Egmont Group (Training and Communication Working Group). Circa 2000 (no date printed; refers to the Group's fifth anniversary in 2000).
- URL: https://fincen.gov/sites/default/files/shared/fiuinaction.pdf (FinCEN-hosted copy)
- Verification: VERIFIED 15 October 2026.
- Summary: One hundred sanitised FIU cases, each tagged with a primary typology and indicators, grouped into "Concealment within Business Structures", "Misuse of Legitimate Businesses", "Use of False Identities, Documents, or Straw Men", "Exploitation of International Jurisdictional Issues", "Use of Anonymous Asset Types" and "Effective use of Intelligence exchanges". An appendix lists the most frequently observed indicators.
- Typologies: commingling through businesses, straw men and nominees, cross-border layering, structuring.

### 1.13 Best Egmont Cases: Financial Analysis Cases 2014-2020 (2021) and 2021-2023 (2024)
- Publisher: Egmont Group. 2021 and 2024.
- URLs: https://egmontgroup.org/?p=2470 (2014-2020 announcement) ; https://egmontgroup.org/wp-content/uploads/2024/09/EGMONT_2021-2023-BECA-III_FINAL.pdf (2021-2023 PDF)
- Verification: VERIFIED 15 to 16 October 2026.
- Summary: Compilations of Best Egmont Case Award entries (26 cases in the second book, 24 cases from 78 submissions in the third). Each case describes the scheme, FIU actions, outcome and red-flag indicators, across corruption, cybercrime and virtual assets, fraud, TBML and third-party laundering, and organised crime; the 2021-2023 book includes a Hong Kong money mule syndicate case (Case 7) and shell company cases (Cases 3 and 6).
- Typologies: mule networks, shell companies, TBML, virtual assets.

### 1.14 European Financial and Economic Crime Threat Assessment 2023: The Other Side of the Coin
- Publisher: Europol. 2023.
- URL: https://www.europol.europa.eu/cms/sites/default/files/documents/The%20Other%20Side%20of%20the%20Coin%20-%20Analysis%20of%20Financial%20and%20Economic%20Crime%20(EN).pdf
- Verification: VERIFIED 15 October 2026.
- Summary: Europol's first dedicated financial and economic crime threat assessment. Key statistics: "Almost 70 % of criminal networks operating in the EU make use of basic money laundering techniques", "More than 80 % of the criminal networks active in the EU misuse legal business structures", and professional launderers' "commission-based fee is 5-20 % of the laundered sum"; it defines smurfing as splitting proceeds "into smaller sums", notes "Mules are recruited intensively through social media, particularly in fraud schemes", and that "Cash-intensive businesses are also often targeted, as they provide opportunities to mix licit and illicit proceeds".
- Typologies: smurfing, mule networks, shell company layering, cash-intensive commingling, underground banking, crypto.

### 1.15 Shadow Money - The International Networks of Illicit Finance (Europol Spotlight)
- Publisher: Europol (Publications Office of the EU). December 2021.
- URL: https://www.europol.europa.eu/cms/sites/default/files/documents/Shadow%20money%20%E2%80%93%20the%20international%20networks%20of%20illicit%20finance_PUBLIC_0.pdf
- Verification: VERIFIED 15 October 2026 (copyright notice December 2021; the brief's "2020" is incorrect).
- Summary: The law enforcement perspective after the Pandora Papers: offshore jurisdictions, shell and front companies, and professional enablers. It states that "offshore companies play a key role in money laundering schemes", that "Strawmen are too often the legal window of shell and offshore companies", and estimates EUR 7.5 trillion held offshore globally ("This represents over 10% of global GDP").
- Typologies: nominees and strawmen, offshore shell chains, professional enablers.

### 1.16 Wolfsberg Group Payment Transparency Standards 2023
- Publisher: The Wolfsberg Group. 19 October 2023.
- URL: https://wolfsberg-group.org/news/50 (PDF: https://db.wolfsberg-group.org/assets/373dbb28-b518-4080-82cc-4be7a54aa16e/Wolfsberg%20Group%20Payment%20Transparency%20Standards%202023.pdf)
- Verification: VERIFIED 15 October 2026 (announcement page; the PDF host blocks automated fetching).
- Summary: Updated industry standards extending payment transparency expectations to all payment service providers, adopting ISO 20022 terminology, and stating that the "entity initiating the payment flow should have the primary obligation to ensure transparency" while intermediaries with limited visibility should not be held to the initiator's obligations. It includes worked examples of real payment chains and their transparency gaps.
- Typologies: layering through payment chains, correspondent and intermediary hops, missing originator or beneficiary data.

### 1.17 Wolfsberg Group Financial Crime Principles for Correspondent Banking (2022) and CBDDQ v1.4
- Publisher: The Wolfsberg Group. October 2022 (Principles); CBDDQ v1.4 undated on the resources page.
- URLs: https://wolfsberg-group.org/resources/203/91 (Principles page, PDF linked) ; https://db.wolfsberg-group.org/assets/3964cedf-a462-4e55-a1e7-ca7c70dfa7ec/CBDDQ%20v1.4.pdf
- Verification: VERIFIED 15 October 2026 (resources pages; the 2014 "Anti-Money Laundering Principles for Correspondent Banking" is listed as retired).
- Summary: Sets risk-based due diligence expectations for correspondent relationships: geographic risk, ownership and management, products, customer base, regulatory history, controls, downstream (nested) financial institutions and shell banks. The CBDDQ is the standard questionnaire respondents complete.
- Typologies: nested correspondent relationships, shell banks, pass-through via respondent banks.

### 1.18 Estimating illicit financial flows resulting from drug trafficking and other transnational organized crimes
- Publisher: UNODC (Research Report, Vienna). October 2011.
- URL: https://unodc.org/lpomex/es/publicaciones/documentos/crimen/Illicit_financial_flows_2011_web.html (HTML text of the report) ; launch note: https://unodc.org/lpo-brazil/en/frontpage/2011/10/26-ilicit-money-how-much-is-there.html
- Verification: VERIFIED 15 October 2026.
- Summary: Estimates criminal proceeds at "close to US$2.1 trillion in 2009 or 3.6% of global GDP" and laundered funds at "close to US$1.6 trillion or 2.7% of GDP in 2009", and states that less than 1 percent of global illicit flows is seized. The 2 to 5 percent range is attributed to the IMF: "2%-5% of GDP, originally proposed by the head of the International Monetary Fund in 1998" (Executive Summary, p. 9; Camdessus 1998 speech cited at pp. 18-19, footnote 27).
- Typologies: none specifically; the scale citation.

### 1.19 FinCEN Advisory FIN-2014-A005: Update on U.S. Currency Restrictions in Mexico: Funnel Accounts and TBML
- Publisher: FinCEN (US Treasury). 28 May 2014.
- URL: https://www.fincen.gov/resources/advisories/fincen-advisory-fin-2014-a005
- Verification: VERIFIED 15 October 2026.
- Summary: Defines a funnel account as "An individual or business account in one geographic area that receives multiple cash deposits", "often in amounts below the cash reporting threshold", from which funds are withdrawn in a different geographic area with "little time elapsing between the deposits and withdrawals" (the three quoted fragments were verified; the connecting words are paraphrase). It lists red flags (out-of-region deposits under USD 10,000 by unidentified persons, debits unrelated to stated business, pre-signed cheques with blank payees) and warns that no single flag is conclusive.
- Typologies: funnel accounts, fan-in, structuring, TBML.

### 1.20 FinCEN Guidance FIN-2006-G014: Potential Money Laundering Risks Related to Shell Companies
- Publisher: FinCEN. 9 November 2006.
- URL: https://www.fincen.gov/resources/statutes-regulations/guidance/potential-money-laundering-risks-related-shell-companies
- Verification: VERIFIED 15 October 2026.
- Summary: Describes shell companies as "non-publicly traded corporations, limited liability companies (LLCs), and trusts that typically have no physical presence" and explains nominee incorporation services. Indicators include "Transacting businesses share the same address, provide only a registered agent's address", "An unusually large number and variety of beneficiaries receive wire transfers from one company", and "Multiple high-value payments or transfers between shell companies with no apparent legitimate business purpose".
- Typologies: shell company chains, shared addresses, fan-out, layering.

### 1.21 FinCEN Advisory FIN-2025-A003: Use of Chinese Money Laundering Networks by Mexico-Based Transnational Criminal Organizations
- Publisher: FinCEN. 28 August 2025 (with a companion Financial Trend Analysis).
- URL: https://www.fincen.gov/system/files/2025-08/FinCEN-Advisory-CMLN-508.pdf ; FTA: https://www.fincen.gov/system/files/2025-08/4000-10-INV-144549-S3F6L-FTA-CMLN-508.pdf
- Verification: VERIFIED 16 October 2026 (advisory PDF fetched; FTA URL from secondary summary, not fetched).
- Summary: Describes mirror transactions in which networks "'purchase' the value of the Cartels' illicit USD proceeds in pesos", money mules ("people who are used, wittingly or unwittingly, to transfer value"), smurfing teams, and trading companies "with shell-like characteristics". Mule indicators include a customer who "reports their occupation during customer onboarding as a student, retiree, housewife" yet "regularly deposits large volumes of cash or cashier's checks" or "receives numerous transfers or deposits, and has a significant number of withdrawals or transfers".
- Typologies: mule fan-in and fan-out, structuring, mirror settlement, TBML.

### 1.22 The Puppet Masters: How the Corrupt Use Legal Structures to Hide Stolen Assets and What to Do About It
- Publisher: Stolen Asset Recovery Initiative (World Bank and UNODC); authors van der Does de Willebois, Halter, Harrison, Park and Sharman. 2011 (launched 24 October 2011).
- URL: https://star.worldbank.org/sites/star/files/puppetmastersv1.pdf ; press release: https://www.worldbank.org/en/news/press-release/2011/10/24/corrupt-money-concealed-in-shell-companies-and-other-opaque-legal-entities-finds-new-star-study
- Verification: VERIFIED 15 October 2026.
- Summary: Reviews about 150 grand corruption cases and finds that in most of them "a corporate vehicle was misused to hide the money trail", usually "a company or corporation", with professional intermediaries setting up or managing the vehicle. It argues that beneficial ownership should be understood through control and benefit rather than formal thresholds alone, recommends immobilising bearer shares, and observes that "Any due diligence system can be beaten."
- Typologies: shell company chains, nominees, bearer shares, TCSP misuse, PEP concealment.

### 1.23 Complex Proliferation Financing and Sanctions Evasion Schemes
- Publisher: FATF. 20 June 2025.
- URL: https://www.fatf-gafi.org/en/publications/Financingofproliferation/complex-proliferation-financing-sanction-evasion-schemes.html
- Verification: VERIFIED 15 October 2026.
- Summary: Finds that only 16 percent of assessed countries show high or substantial effectiveness on proliferation-related targeted financial sanctions, and sets out four evasion typologies: use of intermediaries, obscuring beneficial ownership to access the financial system, use of virtual assets and other technologies, and exploitation of the maritime and shipping sectors. It identifies the DPRK as the most significant actor, including revenue from cyber theft and overseas IT workers, and gives risk indicators such as shell company use and IP addresses inconsistent with a customer's stated location.
- Typologies: sanctions exposure through indirect ownership, front companies, procurement networks.

### 1.24 Seventh Targeted Update on Implementation of the FATF Standards on Virtual Assets/VASPs
- Publisher: FATF. 16 July 2026.
- URL: https://www.fatf-gafi.org/en/publications/Fatfrecommendations/targeted-updated-virtualassets-vasps-2026.html
- Verification: VERIFIED 15 October 2026.
- Summary: Tracks implementation of Recommendation 15: more jurisdictions have risk assessments and licensing regimes, but turning assessments into mitigation, identifying unlicensed and offshore VASPs, and supervising the Travel Rule remain weak. It flags stablecoin misuse, peer-to-peer transfers through unhosted wallets, DeFi control questions, and organised crime groups industrialising VA-enabled fraud.
- Typologies: virtual asset layering, scam-centre proceeds, cross-chain hopping.

### 1.25 Illicit Financial Flows from Cyber-Enabled Fraud (2023) and Cyber-Enabled Fraud - Digitalisation and ML/TF/PF Risks (2026)
- Publisher: FATF with INTERPOL and the Egmont Group (9 November 2023); FATF (24 February 2026).
- URLs: https://www.fatf-gafi.org/en/publications/Methodsandtrends/illicit-financial-flows-cyber-enabled-fraud.html (mirror PDF: https://www.cbr.ru/Content/Document/File/156253/IFF.PDF) ; https://www.fatf-gafi.org/content/fatf-gafi/en/publications/Methodsandtrends/cyber-enabled-fraud-digitalisation-ml-tf-pf-risks.html
- Verification: VERIFIED 15 October 2026.
- Summary: The 2023 report describes how fraud proceeds are "rapidly layered through a series of 'pass-through' transactions" between mule accounts, with "hopping through accounts across different financial, remittance or payment service providers", and that "CEF money mules are more likely to be recruited online"; a Spanish FIU profile flagged accounts "opened by a single individual at three or more financial institutions within 20 days" (Box 23). The 2026 paper reports that 90 percent of 156 assessed jurisdictions identify fraud as a major ML risk and emphasises payment transparency, confirmation of payee and beneficial ownership transparency.
- Typologies: mule fan-in and fan-out, rapid pass-through, account hopping, virtual asset cash-out.

### Supporting sources (cite alongside, not instead of, the above)
- FFIEC BSA/AML Examination Manual, Appendix F "Money Laundering and Terrorist Financing Red Flags" (https://bsaaml.ffiec.gov/manual/Appendices/07), Appendix G "Structuring" (https://bsaaml.ffiec.gov/manual/Appendices/08), and "Cash-Intensive Businesses" (https://bsaaml.ffiec.gov/manual/RisksAssociatedWithMoneyLaunderingAndTerroristFinancing/26). US federal banking regulators; living document. VERIFIED 16 October 2026. Appendix F states that red flags "are not all-inclusive" and that a red flag alone is not evidence of crime.
- 31 CFR 1010.314 (structured transactions), Legal Information Institute copy: https://www.law.cornell.edu/cfr/text/31/1010.314 . VERIFIED 16 October 2026.
- OFAC, "Revised Guidance on Entities Owned by Persons Whose Property and Interests in Property Are Blocked", 13 August 2014: https://ofac.treasury.gov/media/6186/download . VERIFIED 16 October 2026.
- FATF Guidance: Politically Exposed Persons (Recommendations 12 and 22), 2013 (month not shown on the landing page): https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Peps-r12-r22.html . VERIFIED 16 October 2026.
- FATF Glossary (web version of the General Glossary): https://www.fatf-gafi.org/glossary/ (sections A-C, D-I, N-R etc.). VERIFIED 16 October 2026.
- FATF FAQ "How is money laundered?": https://www.fatf-gafi.org/en/pages/frequently-asked-questions.html . VERIFIED 16 October 2026.
- FATF and MENAFATF, "Money Laundering Through the Physical Transportation of Cash" (2015; date not displayed on the landing page): https://www.fatf-gafi.org/en/publications/Methodsandtrends/Ml-through-physical-transportation-of-cash.html . Landing page VERIFIED 16 October 2026; year per FATF catalogue, not re-confirmed from the PDF.
- Europol, "The changing DNA of serious and organised crime - EU-SOCTA 2025": https://europol.europa.eu/publication-events/main-reports/changing-dna-of-serious-and-organised-crime . Landing page VERIFIED 16 October 2026 (body requires JavaScript; content not quoted here).
- Europol, "Money Muling" prevention page: https://europol.europa.eu/operations-services-and-innovation/public-awareness-and-prevention-guides/money-muling . VERIFIED 16 October 2026: "A money mule is a person who receives money from a third party in their bank account and transfers it to another one"; "More than 90% of money mule transactions identified through the European Money Mule Actions are linked to cybercrime."
- Europol/EBF, EMMA 9 results (2023): 10,759 mules and 474 recruiters identified, 1,013 arrests, 2,822 banks participating. Secondary host (EBF): https://www.ebf.eu/ebf-media-centre/paper-trail-ends-in-jail-time-for-1-013-money-mules-2-822-banks-and-financial-institutions-join-forces-with-law-enforcement-agencies-in-global-effort-against-money-laundering/ . The Europol press release itself was not located in this check.
- Open Ownership, "Beneficial ownership in law: Definitions and thresholds" (thresholds page): https://www.openownership.org/en/publications/beneficial-ownership-in-law-definitions-and-thresholds/thresholds/ . VERIFIED 16 October 2026.
- Basel Institute on Governance, Basel AML Index 2025 (14th edition, 177 jurisdictions, December 2025): https://baselgovernance.org/publications/basel-aml-index-2025 . VERIFIED 16 October 2026.
- Academic and tooling (for the synthetic-data question): Altman et al., "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models" (2023), https://arxiv.org/abs/2306.16424 (NeurIPS 2023 Datasets and Benchmarks entry: https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f38404edff6f3f642d6fa5892479c42-Abstract.html); Weber et al., "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics" (2019), https://arxiv.org/abs/1908.02591 ; Östman et al., "AMLGENTEX: Mobilizing Data-Driven Research to Combat Money Laundering" (2025), https://arxiv.org/pdf/2506.13989 ; IBM AMLSim (Apache-2.0), https://github.com/IBM/AMLSim . All VERIFIED 16 October 2026.

---

## 2. Candidate typologies

Each entry: plain-language definition; the structural pattern in a graph of accounts, companies, people and addresses; primary-source citations; red flags the sources list; what a false positive looks like; and whether a synthetic transaction generator can realistically produce labelled examples.

Graph conventions used below: nodes are Account, Company, Person, Address (and optionally Device, Invoice, Shipment); edges are TRANSFER (account to account, with amount, timestamp, channel), OWNS or CONTROLS (person or company to company, with percentage), DIRECTOR_OF, REGISTERED_AT, DEPOSITED_CASH (branch or person to account), SIGNATORY_OF.

### (a) Structuring or smurfing below reporting thresholds
- Definition: Deliberately breaking cash transactions into amounts under a currency reporting threshold (USD 10,000 in the United States) so that no currency transaction report is filed, or so that the activity stays below a bank's monitoring thresholds. In US law "No person shall for the purpose of evading the transactions in currency reporting requirements ... Structure or assist in structuring, or attempt to structure or assist in structuring, any transaction with one or more domestic financial institutions" (31 CFR 1010.314). "Smurfing" is the same conduct carried out by teams: "'Smurfs' are teams of persons who, acting in conjunction with or on behalf of other persons, structure financial transactions" (FinCEN FIN-2025-A003, footnote 35). Europol describes smurfing as splitting proceeds "into smaller sums" to avoid reporting (EFECTA 2023, p. 12).
- Graph pattern: A burst of many DEPOSITED_CASH edges into one account (or a small set of accounts sharing an owner), each just below the threshold, within hours or days, often from several branches or several depositors who are otherwise unconnected to the account holder. Aggregated per account per day the total crosses the threshold that any single deposit avoided. Temporal clustering and amount clustering (for example 9,000 to 9,900) are the signatures, not any single edge.
- Primary sources: 31 CFR 1010.314; FFIEC Manual Appendix G ("a person structures a transaction if that person, acting alone, or in conjunction with, or on behalf of, other persons..."; "structuring may occur before a customer brings the funds to a bank"); FATF Professional Money Laundering 2018 ("The launderer deposits the money in amounts under the reporting threshold to avoid detection"; cash controllers who deposit "in amounts below reporting thresholds"); FinCEN FIN-2014-A005; FinCEN FIN-2025-A003; Europol EFECTA 2023.
- Red flags listed: "Currency is deposited or withdrawn in amounts just below identification or reporting thresholds"; "Deposits are structured through multiple branches of the same bank"; "Customer makes multiple and frequent currency deposits to various accounts that are purportedly unrelated" (FFIEC Appendix F); deposits "of less than $10,000 by unidentified persons" at "branches outside of the geographic region where the account is domiciled" (FIN-2014-A005).
- Typical false positive: A legitimate cash business whose daily takings naturally fall between 5,000 and 9,999 and are banked each evening (restaurants, convenience stores), a customer whose insurer or cash-in-transit contract caps a single deposit, or a person saving a fixed round sum weekly. Appendix F itself warns that a red flag alone is not evidence of criminal activity.
- Synthetic feasibility: High. Threshold evasion is a rule with explicit parameters, so a generator can emit labelled smurfing bursts (AMLSim and AMLGENTEX both model cash-based placement). The realism risk is the opposite: if the generator makes every sub-threshold deposit illicit, the model learns a trivial rule; benign sub-threshold deposit behaviour must be generated at realistic base rates.

### (b) Rapid pass-through or funnel accounts
- Definition: An account that receives funds and sends them on almost immediately, retaining little balance, so that it functions as a conduit rather than a store of value. FinCEN's funnel account is the cash variant: "An individual or business account in one geographic area that receives multiple cash deposits", "often in amounts below the cash reporting threshold", from which the funds are withdrawn in a different geographic area with "little time elapsing between the deposits and withdrawals" (FIN-2014-A005; quoted fragments verified, connecting words paraphrased). The FATF/Egmont TBML indicators describe the same shape as a "pay-through" or "transit" account with rapid movement and a small end-of-day balance.
- Graph pattern: One Account node with high in-degree (many depositors or many originating accounts, geographically dispersed), very short dwell time between inbound and outbound edges (minutes to a few days), and low out-degree to a small number of beneficiaries, frequently cross-border or to a company whose business is unrelated to the depositors. Balance-over-time is a sawtooth that returns to near zero.
- Primary sources: FinCEN FIN-2014-A005; FATF/Egmont TBML Risk Indicators 2021 ("An account of a trade entity appears to be a 'pay-through' or 'transit' account"); FATF/INTERPOL/Egmont 2023 ("rapidly layered through a series of 'pass-through' transactions"); FFIEC Appendix F ("Almost immediately, all or most of the transfers or deposits are wired to another city or country"; "Multiple accounts are used to collect and funnel funds to a small number of foreign beneficiaries"); FATF Concealment 2018 Annex E ("Exclusively facilitates transit transactions and does not appear to generate wealth or income").
- Red flags listed: deposits "in a different geographic region from where the business operates"; debits that "do not appear to be related to the stated business activity of the account holder"; cheques "pre-signed but the payee and amount lines have been left blank"; depositors who "may have no detailed knowledge" of the account (FIN-2014-A005).
- Typical false positive: Payment service providers, payroll bureaus, escrow or client accounts of law firms and estate agents, remittance aggregators, marketplace settlement accounts, and treasury sweep accounts all show low retention and high throughput by design. Distinguishing them requires the customer-type attribute and the expected-activity profile, not the flow shape alone.
- Synthetic feasibility: High for the flow shape (AMLSim and the IBM IT-AML generator produce fan-in followed by fan-out at one vertex, called gather-scatter). Medium for labels, because the benign look-alikes above must be present in the synthetic population with their own customer-type attributes or the detector will flag every intermediary.

### (c) Layering through chains of transfers across entities
- Definition: Moving funds through a sequence of accounts and legal entities, often in several jurisdictions, to put distance between the money and its origin. FATF describes layering as the stage in which the launderer "engages in a series of conversions or movements of the funds to distance them from their source" (FATF FAQ). Professional launderers run "proxy networks" that "consist of multiple layers of shell companies in different jurisdictions" through which client funds are moved and mixed before being returned (FATF PML 2018).
- Graph pattern: A directed path (or a narrow directed acyclic graph) of three or more TRANSFER hops through Accounts held by different Companies, each hop with short dwell time, amounts that shrink slightly at each hop (fees or commissions) or that are split and re-merged, and intermediate nodes that have few other edges and no payroll, tax or supplier activity. Intermediate Companies often share a formation agent, an address or a nominee director (see g and h), which is what makes the chain detectable as a chain rather than as ordinary commerce.
- Primary sources: FATF FAQ; FATF PML 2018 ("The funds from different clients are mixed within the same accounts"; "Bank accounts are chosen to make the activity appear legitimate, and to avoid suspicious transactions reporting"); FATF Concealment 2018 (More than half of the case studies "made use of complicated ownership structures"; the more companies and countries, the harder timely identification); FinCEN FIN-2006-G014 ("Multiple high-value payments or transfers between shell companies with no apparent legitimate business purpose"); Europol EFECTA 2023 ("Multiple layers of shell companies set up in various jurisdictions, sometimes offshore" are "regularly used for money laundering", p. 16); Wolfsberg Payment Transparency Standards 2023 for the obligation that originator and beneficiary data travel the chain.
- Red flags listed: "Payments have no stated purpose, do not reference goods or services" and "Frequent involvement of beneficiaries located in high-risk, offshore financial centers" (FIN-2006-G014); "Suspicious movements of funds occur from one bank to another, and then funds are moved back to the first bank" (FFIEC Appendix F); companies that "receive large sums of capital funding quickly following incorporation/formation" that are "spent or transferred elsewhere in a short period of time without commercial justification" (Concealment Annex E).
- Typical false positive: Intra-group treasury and cash-pooling flows, multi-tier supply chains where each tier adds a margin, correspondent banking hops (an intermediary bank is a legitimate node in almost every cross-border payment), and fund-of-funds or securitisation structures. Many legitimate chains cross jurisdictions for tax or regulatory reasons that are lawful.
- Synthetic feasibility: High for the shape (AMLSim "random" and "stack" patterns; IT-AML "stack" adds bipartite layers). Medium for realism: generators produce chains among accounts the launderer controls but rarely generate the corporate ownership, address and director context that an investigator uses to call a chain suspicious, so a project should generate the entity layer (companies, agents, addresses) together with the transaction layer.

### (d) Round-tripping or circular flows
- Definition: Funds leave an entity or jurisdiction, pass through one or more other entities, and come back to the originator (or to a party under the same control), often dressed as investment, loan, or trade payments, so that the returning money appears to be legitimate revenue or foreign investment. The FATF/Egmont TBML indicators put it plainly: "Payments are routed in a circle", meaning funds leave a country and return to it after passing through other jurisdictions.
- Graph pattern: A directed cycle in the TRANSFER graph that starts and ends at the same Account, or at two Accounts with the same beneficial owner, with near-equal amounts and a short total traversal time, typically through foreign Companies with no operating footprint. Concealment Annex E describes cyclical "round-robin" transactions in which "outgoing funds are being returned with little loss".
- Primary sources: FATF/Egmont TBML Risk Indicators 2021; FATF Concealment 2018 Annex E; FFIEC Appendix F ("funds are moved back to the first bank"); FATF PML 2018 (proxy networks return mixed funds to clients).
- Red flags listed: as above, plus "A trade entity consistently displays unreasonably low profit margins" and prices "that do not seem to be in line with commercial considerations" when the circle is dressed as trade (TBML indicators).
- Typical false positive: Refunds and payment reversals, loan drawdown followed by repayment, FX hedging legs, intra-group cash pooling, dividend upstreaming followed by capital injection, and genuine trade in which a distributor buys from and sells to the same group. Short cycles between related parties are routine in corporate finance; the suspicious version has no commercial rationale and uses entities that exist only for the loop.
- Synthetic feasibility: High. Cycle detection is a standard graph query and both AMLSim and IT-AML emit a "simple cycle" pattern. Labelled benign cycles (refunds, loans) should be generated too, with reference attributes (loan ID, invoice ID) so the detector cannot rely on cycle shape alone.

### (e) Fan-in to a collection account (mule network collection)
- Definition: Many unrelated individuals, often money mules who were recruited online or who are fraud victims themselves, send funds to one collection account that aggregates proceeds before they are moved on or cashed out. Europol: "A money mule is a person who receives money from a third party in their bank account and transfers it to another one". FATF: "Money mules may be knowingly complicit in the laundering of funds or work unwittingly, or negligently" and mule accounts "serve as the initial layering stage in the laundering process" (PML 2018).
- Graph pattern: One Account with high in-degree over a short window from many Person-held Accounts that have no prior relationship to it or to each other, frequently newly opened, low-balance accounts with student or retiree occupation attributes, with the collector then showing a fan-out or cash-out (so fan-in and fan-out often co-occur, see b). Cross-institution variants show the same person opening accounts at several banks within days.
- Primary sources: FATF/INTERPOL/Egmont 2023 (accounts "opened by a single individual at three or more financial institutions within 20 days", Box 23; recruitment "via social media and messaging platforms ... at scale"); FinCEN FIN-2025-A003 (mule indicators); FinCEN FIN-2014-A005 (funnel account definition); FFIEC Appendix F ("Multiple accounts are used to collect and funnel funds to a small number of foreign beneficiaries"); Europol money muling page and EFECTA 2023; Egmont Best Cases 2021-2023, Case 7 (Hong Kong mule syndicate).
- Red flags listed: customer "reports their occupation as a student during the onboarding process" yet "regularly deposits large volumes of cash or cashier's checks" or "receives numerous transfers or deposits, and has a significant number of withdrawals or transfers" (FIN-2025-A003); mules who "only allow their accounts to be used for a specific and limited period of time" (FATF 2023, para. 29); common device IDs and foreign contact details across accounts (FATF 2023, Box 15).
- Typical false positive: Charities and donation drives, crowdfunding, membership clubs, landlords collecting rent, small e-commerce sellers, tutors, and utility or school fee accounts all have high fan-in from unrelated individuals. The discriminators are account age and profile of the senders, dwell time, and what happens next, not the fan-in alone.
- Synthetic feasibility: High for the shape (AMLSim "fan_in"; IT-AML "fan-in"). Medium-high for labels if the generator also emits mule-specific node attributes (account age, occupation, device sharing) and benign fan-in populations (charities, landlords). AMLGENTEX explicitly supports missing and noisy labels, which matches the reality that many mules are never identified.

### (f) Fan-out distribution from a single account
- Definition: One account disperses funds to many recipients in a short period, often newly created or low-activity accounts, so that each recipient holds a small, unremarkable amount that can be withdrawn or forwarded. FinCEN lists as a shell company indicator that "An unusually large number and variety of beneficiaries receive wire transfers from one company" (FIN-2006-G014), and the FFIEC red flags repeat it.
- Graph pattern: One Account with high out-degree over a short window, recipients with no commercial relationship to the sender, amounts similar or round, recipients that subsequently cash out (ATM, cash withdrawal, crypto on-ramp) or forward to a second layer. In fraud "cash-out" networks the fan-out follows a fan-in, giving the scatter-gather or gather-scatter motifs used by synthetic generators.
- Primary sources: FinCEN FIN-2006-G014; FFIEC Appendix F ("Unusually large number and variety of beneficiaries are receiving funds transfers from one company"); FATF PML 2018 (mule herders directing mule accounts); FATF/INTERPOL/Egmont 2023 ("hopping through accounts across different financial, remittance or payment service providers").
- Red flags listed: as above, plus payments that "do not reference goods or services" (FIN-2006-G014) and recipients concentrated in high-risk jurisdictions.
- Typical false positive: Payroll runs, supplier payment batches, dividend and interest distributions, government benefit disbursements, insurance claim payouts, marketplace and gig-platform payouts, and refunds after a cancelled event. These are periodic, reference an invoice or employee ID, and go to accounts with history.
- Synthetic feasibility: High (AMLSim "fan_out"; IT-AML "fan-out", "scatter-gather", "bipartite"). As with (e), benign fan-out populations with reference attributes must be generated at realistic volume.

### (g) Shell company chains with nominee directors or shared formation agents
- Definition: Layers of companies with no real operations, owned through one another and fronted by nominee directors or shareholders supplied by a formation agent or TCSP, so that the person who actually controls the money does not appear in any public record. FATF/Egmont define a shell company as an "incorporated company with no independent operations, significant assets, ongoing business activities" and a shelf company as "an incorporated company that has inactive shareholders, directors, and secretary and is left dormant" (Concealment 2018). Nominees are "formal nominee shareholders and directors where the identity of the nominator is undisclosed" (Concealment 2018, para. 52); Europol calls them strawmen: "nominee directors are strawmen that appear on the paperwork, but do not operate independently" (Shadow Money 2021).
- Graph pattern: An OWNS/CONTROLS chain of two or more Company layers, frequently across jurisdictions; Person nodes with DIRECTOR_OF or SHAREHOLDER_OF edges to dozens or hundreds of unrelated Companies (professional nominees) or Person nodes who are employees of the same TCSP; a shared FORMED_BY edge to one formation agent; clustered incorporation dates; and Companies with high TRANSFER volume but no payroll, tax, rent or supplier edges. FinCEN notes that incorporators may "provide the shell company with nominees for all offices that appear in public records" (FIN-2006-G014).
- Primary sources: FATF Concealment 2018 and Annex E; FATF Guidance on Beneficial Ownership of Legal Persons 2023; FATF TCSP 2010; FATF Corporate Vehicles 2006; StAR Puppet Masters 2011 (in most of ~150 cases "a corporate vehicle was misused to hide the money trail"); FinCEN FIN-2006-G014; Europol Shadow Money 2021 and EFECTA 2023 ("Front or shell companies are largely used by money laundering syndicates").
- Red flags listed (Annex E): "agreements for nominee directors and shareholders"; "employees of professional intermediary firms acting as nominee directors and shareholders"; "informal nominees, such as children, spouses, relatives or associates"; "No real business activities undertaken"; directors or owners who "are listed against the accounts of other legal persons or arrangements" "indicating the use of professional nominees"; transfer of "(bearer) shares in an off-market sale". FIN-2006-G014 adds the "Purpose of the shell company is unknown or unclear" family of indicators.
- Typical false positive: Lawful holding companies and group structures, special purpose vehicles in securitisation, aircraft and ship leasing, investment funds with corporate directors, joint ventures, and start-ups that have not begun trading. Professional directors are normal in fund jurisdictions. Shelf companies are a legal product. Structure alone cannot distinguish; purpose, flow and consistency with declared activity can.
- Synthetic feasibility: Medium. Ownership and directorship graphs are easy to synthesise structurally, but ground-truth labels depend on intent, which a generator must assert by construction. The practical approach is to generate a benign corporate population calibrated to public registry statistics (OpenCorporates, national registers) and inject labelled shell chains whose transaction behaviour matches the Annex E indicators; note that public registries provide realistic base rates but no wrongdoing labels, and real names must never be attached to synthetic allegations.

### (h) Shared registered address clusters and recycled directors
- Definition: Many companies registered at one address (often a TCSP office, a post box or a residential flat) and a small set of individuals who serve as directors or signatories across those companies, which is how formation agents mass-produce entities and how nominees get recycled. Annex E calls this an "Address of mass registration" ("usually the address of a TCSP that manages a number of shell companies").
- Graph pattern: An Address node with very high REGISTERED_AT in-degree relative to the type of premises; Person nodes with abnormally many DIRECTOR_OF edges, often with directorships starting and ending in bursts; and, decisively, TRANSFER edges between Companies that share the address or the director. FinCEN's indicator is the transaction-linked version: "Transacting businesses share the same address, provide only a registered agent's address".
- Primary sources: FATF Concealment 2018 Annex E ("is registered at an address that is also listed against numerous other companies or legal arrangements"; "Only a post-box address"); FATF/Egmont TBML Risk Indicators 2021 ("A trade entity is registered at an address that is likely to be a mass registration address"); FinCEN FIN-2006-G014; FATF TCSP 2010 (registered office provision is a defined TCSP service, FATF Glossary).
- Red flags listed: as above; TBML indicators give the examples of a high-density residential building or a post-box address; Annex E adds "family members with no role or involvement in the running of the business" as directors.
- Typical false positive: Registered agent addresses host tens of thousands of legitimate companies (every state-registered agent in the United States, every corporate services firm in Dublin, Luxembourg or the Cayman Islands); serviced offices and law or accounting firms likewise. Professional directors and corporate secretaries legitimately hold many appointments. Address normalisation errors (unit numbers, transliteration) create spurious clusters.
- Synthetic feasibility: High structurally, but with a strong caveat: the generator must include legitimate mass-registration addresses and professional directors at realistic frequency, otherwise the detector learns that "registered agent equals suspicious", which is false and would also be unfair to named real firms if the project ever overlays public registry data.

### (i) Sanctioned or politically exposed person exposure through indirect ownership or control
- Definition: A customer or counterparty that is not itself listed but is owned or controlled, directly or through a chain of entities, by a sanctioned person or a PEP (or a PEP's family member or close associate). Under the OFAC 50 percent rule, "The property and interests in property of such an entity are blocked" when blocked persons own 50 percent or more in the aggregate, "regardless of whether the entity itself is listed", and US persons should "act with caution when considering a transaction with a non-blocked entity" that blocked persons "may control by means other than a majority ownership interest". FATF's beneficial owner definition reaches "the natural person(s) who ultimately owns or controls a customer" and "those natural persons who exercise ultimate effective control over a legal person" (FATF Glossary).
- Graph pattern: OWNS edges carrying percentages, traversed from the customer upward; the aggregate indirect stake of a flagged Person is the sum over all paths of the product of percentages along each path. Control edges (DIRECTOR_OF, SIGNATORY_OF, nominee agreements, family relations) create exposure even when ownership is below any threshold. PEP exposure adds Person-to-Person FAMILY_OF and ASSOCIATE_OF edges and the "use of corporate vehicles to obscure ownership by PEPs" that the FATF PEP guidance names as a red flag.
- Primary sources: OFAC Revised Guidance, 13 August 2014; FATF Glossary (beneficial owner; PEP definitions); FATF Guidance on PEPs (R.12 and R.22), 2013; FATF Guidance on Beneficial Ownership of Legal Persons 2023; FATF Complex PF and Sanctions Evasion 2025 (typology: "Obscuring beneficial ownership information to access the financial system"); FATF Concealment 2018 Annex E ("informal nominees, such as children, spouses, relatives or associates").
- Red flags listed: information from the PEP "inconsistent with public information, such as asset declarations and published official salaries" and business with PEPs connected to higher-risk countries or sectors (PEP guidance); shell company use and IP addresses inconsistent with stated location (PF report 2025); family members as nominal directors (Annex E).
- Typical false positive: Name-matching errors are the dominant source: common names, transliteration variants, and homonyms. ICIJ's own disclaimer warns that "Many people and entities have the same or similar names"; OpenSanctions notes that its "entity of interest" label "does not imply wrongdoing". Other false positives: minority holdings far below any threshold that happen to aggregate in a model but not in law, former PEPs long out of office, listed companies with diffuse shareholding, and sovereign wealth or state-owned enterprises that are lawful counterparties.
- Synthetic feasibility: High for the ownership mathematics (synthetic percentage edges and a flagged attribute on synthetic persons), and the project can simulate identity-matching noise (name variants, missing dates of birth). Do not attach real sanctions-list or PEP names to synthetic transactions; if real list structure is wanted for testing matching logic, keep it in a separate screening component that touches no synthetic flows.

### (j) Dormant account reactivation followed by high velocity
- Definition: An account or company that has been inactive for a long period suddenly starts receiving and sending large volumes, often shortly after a change of signatory, director or owner. The FFIEC red flag is direct: "an account with little activity may suddenly experience large deposit and withdrawal activity". Shelf companies are the corporate version: a company "left dormant" (Concealment 2018, footnote 20) that is later sold with an established incorporation date.
- Graph pattern: An Account or Company node with a long gap in TRANSFER edges followed by a burst with high in-degree, high out-degree or both within days; often preceded by a change event on DIRECTOR_OF, SIGNATORY_OF or OWNS edges; frequently the burst follows the fan-in or pass-through shapes above. Annex E describes companies that "receive large sums of capital funding quickly following incorporation/formation" that are "spent or transferred elsewhere in a short period of time without commercial justification", which is the same signature at the start of a company's life.
- Primary sources: FFIEC Appendix F; FATF Concealment 2018 (shelf company definition; Annex E); FATF/INTERPOL/Egmont 2023 (mule accounts used only "for a specific and limited period of time"; accounts opened at several institutions within 20 days); FATF TCSP 2010 (shelf company sales as a TCSP service).
- Red flags listed: as above, plus "The currency transaction patterns of a business show a sudden change inconsistent with normal activities" (FFIEC Appendix F).
- Typical false positive: Seasonal businesses, an account revived after the holder returns from abroad or recovers from illness, receipt of an inheritance or property sale proceeds, a dormant company genuinely restarted by new owners, and student accounts reactivated at term start. Change-of-control plus burst is more specific than burst alone, but legitimate acquisitions produce exactly that.
- Synthetic feasibility: High. This is a temporal pattern a generator controls directly (activity gap, then burst), and the generator can also emit the preceding ownership or signatory change. Benign reactivations should be generated with plausible explanations attached as attributes so that evaluation can measure precision honestly.

### (k) Trade-based money laundering with over- or under-invoicing
- Definition: Using trade transactions to move value by misrepresenting price, quantity or quality of goods: "over- and under-invoicing" is "the misrepresentation of the price of the good or service, in order to transfer value"; over- and under-shipment misrepresents quantity, including "'phantom shipments' where no product is moved at all"; multiple invoicing reuses documents to justify several payments for one shipment; falsely described goods misrepresent "the quality or type of a good or service" (FATF/Egmont 2020, restating FATF 2006). TBML is "the process of disguising the proceeds of crime and moving value through the use of trade transactions".
- Why it is hard to detect from payments alone: In open account trade the bank sees a payment and, at most, an invoice reference; the report states that open account trading creates "a disconnect between the movement of the underlying trade and the money used to finance it" and that financial institutions "do not necessarily verify the documents", which are "not always standardised". Price manipulation is invisible without the shipment, customs declaration and a market price benchmark, and that data sits with customs, shippers and insurers, not the bank: no single stakeholder has the full picture. A payment of USD 1,000,000 for "metal goods" looks identical whether the metal was worth 1,000,000 or 100,000.
- Graph pattern: Payment edges between an importer and an exporter whose amounts are inconsistent with the Shipment or Invoice nodes attached to them (unit price far from market, quantities mismatched, the same invoice ID financing several payments); payments made by a third party unrelated to the consignee; shipments or payments routed through jurisdictions without commercial reason; and circular payment routes. Without Invoice, Shipment and price nodes the only payment-side signals are third-party payment, routing anomalies, round amounts and counterparty inconsistency with declared business.
- Primary sources: FATF/Egmont TBML Trends and Developments 2020; FATF/Egmont TBML Risk Indicators 2021; FinCEN FIN-2014-A005 (funnel accounts used to pay for goods exported to Mexico); FinCEN FIN-2025-A003 ("Hong Kong registered trading companies with shell-like characteristics"; a customer who "makes payments for multiple credit cards associated with various individuals"); FATF PML 2018 (fake or inflated invoices, phantom shipments).
- Red flags listed: "Trade activity is inconsistent with the stated line of business of the entities involved"; "A trade entity consistently displays unreasonably low profit margins"; "Inconsistencies across contracts, invoices or other trade documents"; "Payment for imported commodities is made by an entity other than the consignee"; "Shipments of commodities are routed through a number of jurisdictions without economic or commercial justification"; "Payments are sent or received in large round amounts for trade in sectors where this is deemed as unusual" (all TBML Risk Indicators 2021).
- Typical false positive: Legitimate price dispersion (quality grades, incoterms, volume discounts, FX movements, commodity volatility), lawful transfer pricing within groups, third-party payments arranged by trade finance intermediaries or factoring companies, and goods legitimately transhipped through hubs. Over- or under-invoicing claims require a defensible reference price; without one, any mismatch is an allegation about commercial judgement.
- Synthetic feasibility: Low to medium. A payment-only generator cannot label TBML credibly; at most it can label "third-party payment", "circular routing" and "counterparty inconsistent with declared business", which are weak proxies. A credible TBML generator must simulate invoices, shipments, declared customs values and a market price series, and then inject mispriced trades. Existing public generators (AMLSim, IT-AML, AMLGENTEX) do not model trade documents, so this typology should be marked as out of scope for transaction-only synthetic data, or built as a separate module.

### (l) Cash-intensive business commingling
- Definition: Mixing criminal cash with the genuine takings of a business that naturally handles a lot of cash, so that the combined deposits look like revenue. The FFIEC manual lists convenience stores, restaurants, retail and liquor stores, cigarette distributors, privately owned ATMs, vending operators and parking garages, and explains that "a criminal may own a cash-intensive business, such as a restaurant", so that the "volume of currency in a restaurant used to launder money will most likely be higher". Europol: "Cash-intensive businesses are also often targeted, as they provide opportunities to mix licit and illicit proceeds" and are "easily misused for money laundering" (car washes are among the "common examples").
- Graph pattern: A Company Account with cash deposit volume far above what its sector, location, size and card-payment ratio would predict; deposits spread across branches or days in ways unrelated to opening hours; outflows to the owner, related Persons or related Companies rather than to suppliers and payroll in proportion to the declared revenue; and ownership links to other cash businesses with the same anomaly. Egmont's largest case chapter, "Concealment within Business Structures", is this typology.
- Primary sources: FFIEC Manual "Cash-Intensive Businesses"; Europol EFECTA 2023 (pp. 9 and 16); Egmont 100 Cases (chapter 1); FATF PML 2018 (cash controller networks); FATF/MENAFATF Physical Transportation of Cash 2015 for the cash supply side.
- Red flags listed: "The currency transaction patterns of a business show a sudden change inconsistent with normal activities" (FFIEC Appendix F); risk factors "Purpose of the account", "Volume, frequency, and nature of currency transactions", "Primary business activity, products, and services offered", "Geographic locations and jurisdictions of operations" (FFIEC Cash-Intensive Businesses).
- Typical false positive: A genuinely busy or growing cash business, seasonal peaks, a new branch opening, communities that prefer cash, price changes, and businesses that bank for a neighbour or franchise group. The FFIEC manual itself notes "the difficulty in identifying unusual activity" in this segment. Sector benchmarks (deposits per square metre, cash-to-card ratio) are needed and are rarely available in transaction data.
- Synthetic feasibility: Medium. A generator can embed a ground-truth "true revenue" for each synthetic business and add illicit cash on top, which gives clean labels, but realism depends on calibrating benign cash-deposit distributions by sector, which public generators do not do (AMLGENTEX grounds benign behaviour in public payment statistics, which is a start). Treat as feasible with explicit, documented calibration assumptions.

---

## 3. Standard terminology (use consistently, with citations)

- Placement, layering, integration. FATF's FAQ describes the three stages: in placement the launderer "introduces his illegal profits into the financial system"; in layering the launderer "engages in a series of conversions or movements of the funds to distance them from their source"; in integration the funds "re-enter the legitimate economy". Source: FATF FAQ "How is money laundered?" (https://www.fatf-gafi.org/en/pages/frequently-asked-questions.html). Europol EFECTA 2023 (p. 10) uses the same three-stage framing. Note that FATF treats the stages as descriptive, not as elements of an offence; many schemes skip or repeat stages.

- Beneficial owner. "the natural person(s) who ultimately owns or controls a customer and/or the natural person on whose behalf a transaction is being conducted. It also includes those natural persons who exercise ultimate effective control over a legal person or arrangement." Source: FATF General Glossary (https://www.fatf-gafi.org/glossary/a-c/; the web entry breaks the definition into legal persons and legal arrangements, the latter ending with "any other natural person(s) exercising ultimate effective control over the arrangement"). The project should use "beneficial owner" only for natural persons; a company that owns another company is a "legal owner" or "intermediate owner", never a beneficial owner.

- Politically exposed person (PEP) and relatives and close associates (RCA). FATF Glossary: "Foreign PEPs are individuals who are or have been entrusted with prominent public functions by a foreign country"; "Domestic PEPs are individuals who are or have been entrusted domestically with prominent public functions"; international organisation PEPs are "Persons who are or have been entrusted with a prominent function by an international organisation"; the definition "is not intended to cover middle ranking or more junior individuals" (https://www.fatf-gafi.org/glossary/n-r/ and the FATF PEP guidance page). Recommendation 12 extends the PEP requirements to family members and close associates of PEPs; FATF uses the words "family members or close associates", and "RCA" (relatives and close associates) is industry shorthand for the same group. The R.12 sentence was not re-fetched in this check; confirm wording against the June 2026 PDF before quoting it. The FATF PEP guidance stresses that PEP measures are preventive and "don't mean all PEPs are involved in wrongdoing" (paraphrase of the landing page), which the project should repeat in its own framing.

- Nominee (nominee director, nominee shareholder, nominator). FATF does not define "nominee" in the General Glossary; the 2018 FATF/Egmont report describes "formal nominee shareholders and directors where the identity of the nominator is undisclosed" and "informal nominees, such as children, spouses, relatives or associates" (Concealment 2018, para. 52 and Annex E). Revised Recommendation 24 (2022) and the 2023 guidance require countries to address nominee arrangements. Europol's "strawman" is a synonym (Shadow Money 2021). Use "nominee" in documentation and treat "strawman" and "proxy" as synonyms when quoting sources.

- Shell, shelf and front companies. Shell company: "incorporated company with no independent operations, significant assets, ongoing business activities, or employees" (FATF/Egmont Concealment 2018, executive summary sidebar; the verified fragment ends at "ongoing business activities"); FinCEN: "non-publicly traded corporations, limited liability companies (LLCs), and trusts that typically have no physical presence" (FIN-2006-G014). Shelf company: "an incorporated company that has inactive shareholders, directors, and secretary and is left dormant" for later sale (Concealment 2018, footnote 20). Front company: "fully functioning company with the characteristics of a legitimate business" that is used to launder (Concealment 2018). Documentation should never call a company a shell merely because it has few employees; the term describes a structure, and the project's standing disclaimer (Section 4) must apply.

- Trust and company service provider (TCSP). FATF Glossary: "all persons or businesses" not covered elsewhere in the Recommendations that provide to third parties any of: acting as a formation agent of legal persons; acting as (or arranging for another person to act as) a director or secretary of a company; providing a registered office, business address or administrative address; acting as (or arranging) a trustee of an express trust or equivalent; acting as (or arranging) a nominee shareholder (https://www.fatf-gafi.org/glossary/d-i/, within the DNFBP entry).

- Suspicious activity report (SAR) and suspicious transaction report (STR). FATF Recommendation 20 requires financial institutions to report to the FIU when they suspect funds are proceeds of crime or related to terrorist financing; FATF's term is "suspicious transaction report" (the Interpretive Note to R.29 refers to "suspicious transaction reports, as required by Recommendation 20 and 23"). "Suspicious activity report" is the US Bank Secrecy Act term used by FinCEN and the FFIEC manual. Use "STR" when discussing FATF or non-US FIUs and "SAR" for US material; treat them as equivalent for the project's purposes and say so once. Source: FATF Recommendations (R.20, R.29 and its Interpretive Note; CFATF mirror https://www.cfatf-gafic.org/index.php/documents/fatf-40r/395-fatf-recommendation-29-); FFIEC Manual.

- Financial intelligence unit (FIU). FATF Recommendation 29: countries should establish an FIU that "serves as a national centre for the receipt and analysis of" suspicious transaction reports and "other information relevant to money laundering, associated predicate offences and terrorist financing", and "for the dissemination of the results of that analysis". The Egmont Group describes FIUs as bodies that "serve as national centres for the receipt and analysis of suspicious transaction reports" and that "are also responsible for disseminating analysis results" (https://egmontgroup.org/about/financial-intelligence-unit).

- Designated non-financial businesses and professions (DNFBP). FATF Glossary: casinos (including internet- and ship-based casinos); real estate agents; dealers in precious metals; dealers in precious stones; lawyers, notaries, other independent legal professionals and accountants (sole practitioners, partners or employed professionals within professional firms, not in-house professionals); and trust and company service providers (https://www.fatf-gafi.org/glossary/d-i/).

- The 25 percent beneficial ownership threshold and where it comes from. The FATF standard does not mandate 25 percent. The Interpretive Note to Recommendation 10 (2012 text, footnote 30, p. 60) says a controlling ownership interest "depends on the ownership structure of the company. It may be based on a threshold, e.g. any person owning more than a certain percentage of the company (e.g. 25%)". The EU made it law in Directive (EU) 2015/849 (4th AMLD), Article 3(6)(a)(i): "A shareholding of 25 % plus one share or an ownership interest of more than 25 % in the customer held by a natural person" is an indication of direct ownership (text as reproduced in EBA Single Rulebook Q&A 2022_6622, https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2022_6622). Open Ownership records that "FATF does not recommend a specific threshold level, but mentions a 25% figure in the context of examples", that early register implementers (UK, Ukraine, 2015) adopted 25 percent, that AMLD4 incorporated it "in the same year", and that the trend is toward lower thresholds (Nigeria 5 percent, Kenya and Cayman 10 percent, Senegal 2 percent, Argentina one share). The US CDD Rule (31 CFR 1010.230) also uses 25 percent; it was not re-fetched in this check. Project documentation should state: "25 percent is an illustrative FATF example that became a legal threshold in the EU and elsewhere; it is not a FATF requirement, and control can exist at any percentage."

---

## 4. Honest-framing language: how public graph tools word their disclaimers

Verbatim quotes, checked 16 October 2026. The project should model its own standing disclaimer on these three elements: (1) legitimate uses exist, (2) inclusion or a pattern match does not imply wrongdoing, (3) identity and data errors are possible and corrections are welcome.

1. ICIJ Offshore Leaks Database, FAQ (https://offshoreleaks.icij.org/pages/faq), with the same text printed above database results (https://offshoreleaks.icij.org/):
   "There are legitimate uses for offshore companies and trusts. We do not intend to suggest or imply that any persons, companies or other entities included in the ICIJ Offshore Leaks Database have broken the law or otherwise acted improperly. Many people and entities have the same or similar names. We suggest you confirm the identities of any individuals or entities located in the database based on addresses or other identifiable information. If you find an error in the database please get in touch with us."
   The FAQ adds: "The inclusion of a person or entity in the ICIJ Offshore Leaks Database is not intended to suggest or imply that they have engaged in illegal or improper conduct." (The database home page renders the disclaimer client-side, so an automated fetch shows only the "Disclaimer" heading; the FAQ text is static.)

2. OpenSanctions, Glossary entry "Entity of interest" (https://www.opensanctions.org/docs/glossary):
   "The term "entity of interest" is used to describe companies or people that are not directly subject to sanctions but are included in OpenSanctions for other reasons. It does not carry a specific legal meaning, and does not imply wrongdoing." The entry goes on: "Having grown from our core focus of aggregating sanctions data, OpenSanctions also includes politically exposed persons, companies and people included in debarment databases, criminal watchlists, and other domain datasets related to corruption, money laundering and other forms of financial crime." and advises users uncertain why an entity is included to check the "Relationships" section and the data-source metadata.

3. OpenCorporates, Terms of use, "Disclaimers and Limitation of Liability" (https://opencorporates.com/terms-of-use-2/):
   "The data on companies that is available through OpenCorporates ("company data") is drawn from many different sources. In some cases the source data have errors which we have not yet detected. Therefore we cannot make any promises as to the accuracy or quality of company data. Your use of the company data is entirely at your own risk." Elsewhere: "OpenCorporates and any data is provided "as is" and on an "as available" basis without any representations or warranties of any kind".

4. Open Ownership Register, licence terms, "Warning - essential reading" (https://register.openownership.org/terms-and-conditions):
   "The information in the Register comes from national beneficial ownership registers. This means that we cannot guarantee the accuracy of the information in the Register, ... Therefore you use the information at your own risk and should conduct your own investigations." and "we make no promises that the information available through the Register is accurate." ... "The original source, over which we have no control, may contain errors." ... "We welcome reports of any errors in the Register."

Suggested project disclaimer (drafted from the above, not a quote): "This is an educational tool that detects structural patterns in synthetic or public data. A pattern match is not evidence of money laundering or of any other wrongdoing. There are legitimate reasons for almost every structure shown here, including holding companies, shared registered agents, professional directors, payment intermediaries and cash businesses. Where public data is used, many people and entities share the same or similar names, and source registers contain errors. Nothing here suggests or implies that any identifiable person or entity has broken the law. If you find an error, tell us and we will correct it."

---

## 5. Real cases that fit on one slide as a graph

Each case: summary; graph structure (entities, accounts, flows); primary sources; adjudicated versus alleged. Only convicted persons or institutions that admitted facts are named as wrongdoers; everyone else is described by role.

### 5.1 Danske Bank Estonia non-resident portfolio (2007-2015)
- Summary: Danske Bank's Estonian branch ran a "Non-Resident Portfolio" of roughly 10,000 customers (about 15,000 when every customer with a cross-border characteristic is included) through which approximately EUR 200 billion flowed in 2007-2015 in about 9.5 million payments. Of about 6,200 customers examined first because they hit the most risk indicators, "the vast majority have been found to be suspicious", and those 6,200 "represent the majority of the flow". In December 2022 the bank pleaded guilty in the United States to one count of conspiracy to commit bank fraud, admitting that the branch "processed $160 billion through U.S. banks on behalf of the NRP" while misrepresenting its AML controls to US correspondent banks, and agreed to forfeit USD 2.059 billion.
- Graph structure for one slide: Centre node, Danske Bank Estonia branch (one institution node holding thousands of Account nodes). Left side, customer Companies, predominantly UK limited partnerships and LLPs and entities from the British Virgin Islands, with declared residence concentrated in "Russia, the UK and the British Virgin Islands" and the wider CIS; many introduced by commission-earning agents and some by "non-regulated entities acting as intermediaries providing cross-border payment solutions to unknown end-clients". Right side, US correspondent banks through which the dollar legs cleared (the bank admitted lying to them). Two labelled sub-clusters: 177 customers potentially linked to the Russian Laundromat ("The majority of the 177 customers are limited partnerships") and 75 customers linked by media reporting to the Azerbaijani Laundromat ("Two thirds of the 75 customers were LPs or LLPs incorporated in the U.K."). Edges: incoming transfers from CIS banks into NRP accounts, pass-through to Western beneficiaries via US dollar correspondents.
- Primary sources: Bruun & Hjejle, "Report on the Non-Resident Portfolio at Danske Bank's Estonian branch", 19 September 2018, commissioned and published by Danske Bank (https://danskebank.com/-/media/danske-bank-com/file-cloud/2018/9/report-on-the-non-resident-portfolio-at-danske-banks-estonian-branch.pdf ; press release https://danskebank.com/news-and-insights/news-archive/press-releases/2018/pr19092018 ; copy at https://kkc.com/wp-content/uploads/2022/12/Danske-Report.pdf); US DOJ press release, 13 December 2022 (https://www.justice.gov/opa/pr/danske-bank-pleads-guilty-fraud-us-banks-multi-billion-dollar-scheme-access-us-financial); Estonian FSA precept of February 2019 ordering closure within eight months (reported by ERR, https://news.err.ee/912124/financial-authority-danske-has-eight-months-to-shut-up-shop-in-estonia); Danish prosecutors' January 2021 decision not to charge six former employees (ERR, https://news.err.ee/1232371/denmark-drops-money-laundering-charges-against-six-danske-bank-suspects).
- Adjudicated versus alleged: Adjudicated: the bank's guilty plea and admissions in the United States (conspiracy to commit bank fraud, USD 160 billion through US banks, misleading correspondents); the Estonian supervisory closure order. The bank's own report is an admission of control failure but explicitly states that its findings do not allow a conclusion that money laundering or other crime actually occurred (Section 7.3), and it does not name customers. Alleged or unresolved: criminality of any specific customer; individual liability of former executives (Danish prosecutors dropped money laundering charges against six individuals in January 2021 because gross negligence was not demonstrated; the Estonian criminal proceeding opened in 2018 reported "over 10 predicate offenses, amounting to over US$ 2 billion" in January 2020, with outcomes not verified here). The slide should name Danske Bank as an institution that admitted fraud on US banks and should not name any customer, agent or former employee.

### 5.2 The Azerbaijani Laundromat (2012-2014)
- Summary: OCCRP and Berlingske reported in September 2017 that about EUR 2.5 billion (USD 2.9 billion) moved in more than 16,000 transactions over two years through four UK-registered shell companies, all with accounts at Danske Bank Estonia. The beneficial owners and directors recorded for the companies "are not real"; one supposed controller of two of them was "a working class driver living in a modest home in the outskirts of Baku". Almost half of the inflows came from an account at the International Bank of Azerbaijan held by a shell company linked by OCCRP to Azerbaijan's ruling family, with other inflows from government ministries and from Rosoboronexport. Outflows went to "at least three European politicians, a journalist who wrote stories friendly to the regime", businessmen, luxury car dealers, football clubs and others.
- Graph structure for one slide: Four Company nodes, two Scottish limited partnerships (Hilux Services LP, Polux Management LP) and two English LLPs (Metastar Invest LLP, LCM Alliance LLP), each REGISTERED_AT a UK formation address with operating addresses in Baku, each with an Account at Danske Bank Estonia. Nominee Person nodes as recorded directors and signatories. Inbound edges from a small number of Azerbaijani state-linked accounts; dense internal transfers among the four; outbound fan-out to several hundred recipients across Europe. This is a textbook combination of typologies (g), (h), (b) and (f).
- Primary sources: OCCRP, "The Azerbaijani Laundromat" project (https://www.occrp.org/en/project/the-azerbaijani-laundromat) and "The Core Companies" (https://occrp.org/en/project/the-azerbaijani-laundromat/the-core-companies), both 4 September 2017; Bruun & Hjejle 2018 report, Section 7.2.5 (75 customers linked by media to the scheme); OCCRP, "Italian Court Sentences Former Council of Europe MP for Bribery", 14 January 2021 (https://www.occrp.org/en/news/italian-court-sentences-former-council-of-europe-mp-for-bribery).
- Adjudicated versus alleged: Adjudicated at first instance: a Milan court sentenced former Italian deputy and PACE member Luca Volontè to four years for taking bribes from Azerbaijani politicians, paid "through British and offshore companies" including Hilux Services, which OCCRP reports was funded by Baktelekom MMC (the appellate history was not verified in this check, so describe him as "convicted at first instance in January 2021"); a UK couple agreed to forfeit over GBP 4 million received from the scheme (OCCRP 2021 listing). Danske Bank's own report confirms the 75 customer accounts existed and were suspicious but not that crimes occurred. Alleged: everything else, including the source and purpose of the funds, the involvement of any named Azerbaijani official or family, and the knowledge of any recipient; one recipient's libel claim against OCCRP was settled on agreed terms with a statement that he "categorically denies involvement in money laundering or any unlawful activity". On a slide, show the four companies, the bank, and anonymised sender and recipient clusters; do not name recipients other than persons already convicted.

### 5.3 The Troika Laundromat (2006-2013)
- Summary: OCCRP, with 15min.lt and 21 partners, reported in March 2019 on a network of at least 75 offshore companies, designed and operated according to OCCRP by the Russian investment bank Troika Dialog, that brought USD 4.6 billion into the system and sent USD 4.8 billion out, with USD 8.8 billion of internal transfers among the companies; at least 35 companies banked at Ukio Bankas in Lithuania. Shell companies issued "bogus invoices for nonexistent goods" (labelled "goods", "food goods", "metal goods", "bills", "auto parts") to justify transfers; some recorded owners were Armenian seasonal workers whose signatures were, by their account, forged. Funds were used for property, yachts, art, tuition and donations, and some flows were linked to the Sheremetyevo fuel fraud and the Magnitsky case. At least USD 69 million went to companies linked to a cellist described as a close associate of the Russian president.
- Graph structure for one slide: Three BVI Company nodes (Brightwell, Gotland, Quantus) paying one formation agent (IOS Group) to create a layer of about 75 Companies with proxy directors and shareholders (Latvian proxies linked to Cascado AG; Armenian proxies); Account nodes at Ukio Bankas; dense internal TRANSFER edges justified by fake Invoice nodes; outbound edges through Western correspondent accounts (Austrian and German banks) to real estate, assets and individuals. Typologies (c), (d), (g), (h) and the invoice-dressing of (k).
- Primary sources: OCCRP, "Vast Offshore Network Moved Billions With Help From Major Russian Bank", Paul Radu, 4 March 2019 (https://www.occrp.org/en/project/the-troika-laundromat/vast-offshore-network-moved-billions-with-help-from-major-russian-bank); OCCRP project page (https://www.occrp.org/en/troikalaundromat/about-the-project); ICIJ summary, 4 March 2019 (https://www.icij.org/investigations/russia-archive/troika-laundromat-reveals-russian-banks-8-8bn-offshore-scheme/); RFE/RL report (https://www.rferl.org/a/money-laundering-scheme-set-up-run-by-russia-s-largest-investment-bank-occrp-says/29802833.html).
- Adjudicated versus alleged: Nothing in this case has been adjudicated against the bank or its leadership as far as could be verified. OCCRP itself states that reporters "found no evidence that he was ever investigated or accused of any wrongdoing by authorities" regarding the bank's then CEO, who said the bank "always acted according to the rules of the world financial market of that time"; ICIJ writes "It is not alleged that the financier did anything illegal." Ukio Bankas was closed by Lithuanian authorities in 2013 for unrelated reasons stated at the time; a Lithuanian investigation into related flows was reported as open in 2019. Treat the entire case as journalistic allegation, describe it as "reported by OCCRP", keep individuals unnamed, and use it only to illustrate structure (formation agent, proxies, fake invoices, correspondent hops). It is the weakest of the three for a public slide and the strongest as a graph.

### 5.4 1MDB (2009-2015)
- Summary: US civil forfeiture complaints allege that more than USD 4.5 billion was misappropriated from Malaysia's 1Malaysia Development Berhad between 2009 and 2015 and laundered through accounts in Singapore, Switzerland, Luxembourg and the United States into real estate, art, a jet, EMI music rights and the film "The Wolf of Wall Street". DOJ's complaints describe four phases: the "Good Star" phase (2009-2011, more than USD 1 billion to a Swiss account of Good Star Limited "beneficially owned not by PetroSaudi or the joint venture, but by LOW Taek Jho"); the "Aabar-BVI" phase (2012, about USD 1.367 billion from the Project Magnolia and Project Maximus bonds to Aabar Investments PJS Limited, an entity that "has no genuine affiliation with Aabar or IPIC"); the "Tanore" phase (2013, more than USD 1.26 billion of the USD 3 billion Project Catalyze bond "diverted to a bank account in Singapore held by Tanore Finance Corporation"); and the "Options Buyback" phase (2014, about USD 850 million). Goldman Sachs underwrote the three 2012-2013 bonds (about USD 6.5 billion) and in October 2020 its Malaysian subsidiary pleaded guilty and the parent entered a deferred prosecution agreement for conspiracy to violate the FCPA, paying over USD 2.9 billion; the scheme involved more than USD 1.6 billion in bribes.
- Graph structure for one slide: Source node 1MDB (state fund). Three bond issuances as money-in edges. Three look-alike Company nodes (Good Star Limited; Aabar Investments PJS Limited (BVI), a name chosen to resemble the genuine Abu Dhabi entity; Tanore Finance Corporation) each with an Account in Switzerland or Singapore. Onward fan-out to US assets and to accounts of officials. One Person node (the financier charged and still a fugitive) with CONTROLS edges to the look-alike companies. Two convicted banker nodes attached to the bond issuance edges. Typologies (c), (f), (g) and (i) (PEP exposure).
- Primary sources: US DOJ press release, 20 July 2016, "United States Seeks to Recover More Than $1 Billion Obtained from Corruption Involving Malaysian Sovereign Wealth Fund" (https://www.justice.gov/opa/pr/united-states-seeks-recover-more-1-billion-obtained-corruption-involving-malaysian-sovereign); DOJ verified complaint for forfeiture in rem, C.D. Cal. 2:25-cv-00474, 17 January 2025 (https://www.justice.gov/opa/media/1385611/dl), which restates the four phases; DOJ press release, 22 October 2020, "Goldman Sachs Charged in Foreign Bribery Case and Agrees to Pay Over $2.9 Billion" (https://www.justice.gov/archives/opa/pr/goldman-sachs-charged-foreign-bribery-case-and-agrees-pay-over-29-billion); DOJ press release on the sentencing of former Goldman managing director Roger Ng to 10 years (https://www.justice.gov/opa/pr/former-goldman-sachs-investment-banker-sentenced-27b-bribery-and-money-laundering-scheme); DOJ press release, 30 October 2019, on the USD 700 million settlement with the financier and his family (https://www.justice.gov/usao-cdca/pr/us-reaches-settlement-recover-more-700-million-assets-allegedly-traceable-corruption).
- Adjudicated versus alleged: Adjudicated: Goldman Sachs (Malaysia) guilty plea and the parent's DPA admissions (2020); Roger Ng convicted by a jury in April 2022 and sentenced to 10 years; Tim Leissner pleaded guilty in August 2018 (sentenced in May 2025 to two years according to Malaysian and international press, secondary sources only in this check); in Malaysia, former prime minister Najib Razak was convicted in the SRC International case (2020, upheld 2022) and, as reported by The Edge Malaysia, found guilty on 26 December 2025 of four abuse of power and 21 money laundering charges in the 1MDB-Tanore trial and sentenced to 15 years with fines totalling about RM 11.38 billion (first instance; stay and appeal rights reserved; verify current status before publication). Alleged: the DOJ civil forfeiture complaints are allegations ("These allegations are not proven until a court awards judgment in favor of the United States"), although many assets were forfeited by settlement; Low Taek Jho was indicted in November 2018, remains a fugitive and "is presumed innocent" per DOJ; the 2019 settlement "does not release any entity or individual from filed or potential criminal charges". On the slide, name the institutions that admitted facts and the individuals convicted; refer to the financier as "charged, fugitive, presumed innocent" and to other officials by role only.

---

## 6. Sources (every URL used in this research, grouped)

FATF
- https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html
- https://www.fatf-gafi.org/content/dam/fatf-gafi/recommendations/fatf-recommendations-2012.pdf
- https://www.fatf-gafi.org/en/publications/Fatfgeneral/outcomes-fatf-plenary-june-2026.html
- https://www.fatf-gafi.org/en/publications/Fatfgeneral/outcomes-FATF-plenary-february-2026.html
- https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Legal-Persons.html
- https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Transparency-Legal-Arrangements.html
- https://www.fatf-gafi.org/en/publications/Methodsandtrends/Concealment-beneficial-ownership.html
- https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf.coredownload.pdf
- https://www.fatf-gafi.org/en/publications/Methodsandtrends/Moneylaunderingusingtrustandcompanyserviceproviders.html
- https://www.fatf-gafi.org/en/publications/Fatfgeneral/Outcomesofthefatfplenarymeetingparis20-22october2010.html
- https://fatf-gafi.org/content/dam/fatf-gafi/reports/Misuse%20of%20Corporate%20Vehicles%20including%20Trusts%20and%20Company%20Services%20Providers.pdf.coredownload.inline.pdf (robots-blocked; existence confirmed via index)
- https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-trends-and-developments.html
- https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-indicators.html
- http://www.fatf-gafi.org/media/fatf/documents/reports/Guidance-transparency-beneficial-ownership.pdf (via FSB index)
- http://www.fatf-gafi.org/publications/methodsandtrends/documents/best-practices-beneficial-ownership-legal-persons.html (via FSB index)
- https://www.fatf-gafi.org/en/publications/Financingofproliferation/complex-proliferation-financing-sanction-evasion-schemes.html
- https://www.fatf-gafi.org/en/publications/Fatfrecommendations/targeted-updated-virtualassets-vasps-2026.html
- https://www.fatf-gafi.org/en/publications/Methodsandtrends/illicit-financial-flows-cyber-enabled-fraud.html
- https://www.fatf-gafi.org/content/fatf-gafi/en/publications/Methodsandtrends/cyber-enabled-fraud-digitalisation-ml-tf-pf-risks.html
- https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Peps-r12-r22.html
- https://www.fatf-gafi.org/en/publications/Methodsandtrends/Ml-through-physical-transportation-of-cash.html
- https://www.fatf-gafi.org/glossary/ ; https://www.fatf-gafi.org/glossary/a-c/ ; https://www.fatf-gafi.org/glossary/d-i/ ; https://www.fatf-gafi.org/glossary/n-r/ (n-r fetch failed on the day; PEP text taken from the glossary index page)
- https://www.fatf-gafi.org/en/pages/frequently-asked-questions.html

Mirrors used where FATF blocked fetching (content only, cite the FATF URL)
- https://www.cbr.ru/Content/Document/File/119937/TBLMRI.PDF (TBML Risk Indicators 2021)
- https://www.cbr.ru/Content/Document/File/117629/TBML.pdf (TBML Trends 2020)
- https://www.cbr.ru/Content/Document/File/156253/IFF.PDF (Cyber-enabled fraud 2023)
- https://www.aml.gov.sa/en-us/GuidanceReports/Concealment%20of%20Beneficial%20Ownership.pdf (Concealment 2018 full text)
- https://cfatf-gafic.org/home-test/english-documents/typologies/2185-money-laundering-using-trusts-and-company-service-providers (TCSP 2010)
- https://www.cfatf-gafic.org/index.php/documents/fatf-40r/395-fatf-recommendation-29- (R.29 text)
- https://www.fsb.org/2014/10/guidance-on-transparency-and-beneficial-ownership/ ; https://www.fsb.org/2019/10/best-practices-on-beneficial-ownership-for-legal-persons/
- https://taxjustice.net/wp-content/uploads/2020/11/TJN2016_BO-EUAMLD-FATF-Part1.pdf (reproduces INR.10 footnote 30 and AMLD4 Art. 3(6))
- https://www.ielr.com/node/225 (release date of the 2006 corporate vehicles report)
- https://www.bvifsc.vg/sites/default/files/documents/Presentations/misuse_of_corporate_vehicles_typologies_exercise_kbaker.pdf (2005-2006 typologies exercise)

Egmont Group
- https://fincen.gov/sites/default/files/shared/fiuinaction.pdf (100 Cases, FinCEN-hosted)
- https://egmontgroup.org/?p=2470 (Best Egmont Cases 2014-2020)
- https://egmontgroup.org/wp-content/uploads/2024/09/EGMONT_2021-2023-BECA-III_FINAL.pdf
- https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-annex-E.pdf
- https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-Executive-summary.pdf
- https://egmontgroup.org/about/financial-intelligence-unit

Europol
- https://www.europol.europa.eu/cms/sites/default/files/documents/The%20Other%20Side%20of%20the%20Coin%20-%20Analysis%20of%20Financial%20and%20Economic%20Crime%20(EN).pdf
- https://www.europol.europa.eu/cms/sites/default/files/documents/Shadow%20money%20%E2%80%93%20the%20international%20networks%20of%20illicit%20finance_PUBLIC_0.pdf
- https://europol.europa.eu/publication-events/main-reports/changing-dna-of-serious-and-organised-crime
- https://europol.europa.eu/operations-services-and-innovation/public-awareness-and-prevention-guides/money-muling
- https://www.ebf.eu/ebf-media-centre/paper-trail-ends-in-jail-time-for-1-013-money-mules-2-822-banks-and-financial-institutions-join-forces-with-law-enforcement-agencies-in-global-effort-against-money-laundering/ (EMMA 9, secondary host)
- https://www.icij.org/investigations/pandora-papers/europol-pandora-papers-report-warns-of-parallel-underground-system-exploited-by-criminal-networks/ (date context for Shadow Money)

Wolfsberg Group
- https://wolfsberg-group.org/news/50
- https://db.wolfsberg-group.org/assets/373dbb28-b518-4080-82cc-4be7a54aa16e/Wolfsberg%20Group%20Payment%20Transparency%20Standards%202023.pdf
- https://wolfsberg-group.org/resources/203/91
- https://wolfsberg-group.org/resources/204/
- https://db.wolfsberg-group.org/assets/3964cedf-a462-4e55-a1e7-ca7c70dfa7ec/CBDDQ%20v1.4.pdf
- https://ripjar.com/blog/wolfsberg-group-financial-crime-principles-for-correspondent-banking (secondary summary)

UNODC and StAR
- https://unodc.org/lpomex/es/publicaciones/documentos/crimen/Illicit_financial_flows_2011_web.html
- https://unodc.org/lpo-brazil/en/frontpage/2011/10/26-ilicit-money-how-much-is-there.html
- https://star.worldbank.org/sites/star/files/puppetmastersv1.pdf
- https://www.worldbank.org/en/news/press-release/2011/10/24/corrupt-money-concealed-in-shell-companies-and-other-opaque-legal-entities-finds-new-star-study

FinCEN, FFIEC, OFAC, US law
- https://www.fincen.gov/resources/advisories/fincen-advisory-fin-2014-a005
- https://www.fincen.gov/resources/statutes-regulations/guidance/potential-money-laundering-risks-related-shell-companies
- https://www.fincen.gov/system/files/2025-08/FinCEN-Advisory-CMLN-508.pdf
- https://www.fincen.gov/system/files/2025-08/4000-10-INV-144549-S3F6L-FTA-CMLN-508.pdf (not fetched)
- https://www.thompsonhine.com/insights/fincen-issues-advisory-and-financial-trend-analysis-on-chinese-money-laundering-networks/ (secondary, for FTA URL)
- https://bsaaml.ffiec.gov/manual/Appendices/07
- https://bsaaml.ffiec.gov/manual/Appendices/08
- https://bsaaml.ffiec.gov/manual/RisksAssociatedWithMoneyLaunderingAndTerroristFinancing/26
- https://www.law.cornell.edu/cfr/text/31/1010.314
- https://ofac.treasury.gov/media/6186/download

EU and beneficial ownership thresholds
- https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2022_6622
- https://www.openownership.org/en/publications/beneficial-ownership-in-law-definitions-and-thresholds/thresholds/

Disclaimers
- https://offshoreleaks.icij.org/
- https://offshoreleaks.icij.org/pages/about
- https://offshoreleaks.icij.org/pages/faq
- https://www.transcend.org/tms/?p=73439 (reproduces the ICIJ database header disclaimer)
- https://en.wikipedia.org/wiki/Offshore_Leaks (reproduces the same text; tertiary)
- https://www.opensanctions.org/docs/glossary
- https://www.opensanctions.org/docs/criteria/
- https://www.opensanctions.org/docs/about/
- https://www.opensanctions.org/faq/concepts/poi/
- https://www.opensanctions.org/docs/coverage/pep/methodology/
- https://opencorporates.com/terms-of-use-2/
- https://opencorporates.com/legal-information/
- https://register.openownership.org/terms-and-conditions

Cases
- https://danskebank.com/news-and-insights/news-archive/press-releases/2018/pr19092018
- https://danskebank.com/-/media/danske-bank-com/file-cloud/2018/9/report-on-the-non-resident-portfolio-at-danske-banks-estonian-branch.pdf?rev=56b16dfddae94480bb8cdcaebeaddc9b&hash=B7D825F2639326A3BBBC7D524C5E341E
- https://kkc.com/wp-content/uploads/2022/12/Danske-Report.pdf (copy of the Bruun & Hjejle report)
- https://www.justice.gov/opa/pr/danske-bank-pleads-guilty-fraud-us-banks-multi-billion-dollar-scheme-access-us-financial
- https://mondovisione.com/media-and-resources/news/us-department-of-justice-danske-bank-pleads-guilty-to-fraud-on-us-banks-in-mu-20221213/ (mirror of the DOJ release)
- https://news.err.ee/912124/financial-authority-danske-has-eight-months-to-shut-up-shop-in-estonia
- https://news.err.ee/1232371/denmark-drops-money-laundering-charges-against-six-danske-bank-suspects
- https://www.occrp.org/en/project/the-azerbaijani-laundromat
- https://occrp.org/en/project/the-azerbaijani-laundromat/the-core-companies
- https://www.occrp.org/en/news/italian-court-sentences-former-council-of-europe-mp-for-bribery
- https://www.occrp.org/en/project/the-troika-laundromat/vast-offshore-network-moved-billions-with-help-from-major-russian-bank
- https://www.occrp.org/en/troikalaundromat/about-the-project
- https://www.icij.org/investigations/russia-archive/troika-laundromat-reveals-russian-banks-8-8bn-offshore-scheme/
- https://www.rferl.org/a/money-laundering-scheme-set-up-run-by-russia-s-largest-investment-bank-occrp-says/29802833.html
- https://www.justice.gov/opa/pr/united-states-seeks-recover-more-1-billion-obtained-corruption-involving-malaysian-sovereign
- https://www.justice.gov/opa/media/1385611/dl
- https://www.justice.gov/archives/opa/pr/goldman-sachs-charged-foreign-bribery-case-and-agrees-pay-over-29-billion
- https://www.justice.gov/opa/pr/former-goldman-sachs-investment-banker-sentenced-27b-bribery-and-money-laundering-scheme
- https://www.justice.gov/usao-cdca/pr/us-reaches-settlement-recover-more-700-million-assets-allegedly-traceable-corruption
- https://theedgemalaysia.com/node/787231 (Najib 1MDB-Tanore verdict, secondary)
- https://www.malaymail.com/amp/news/malaysia/2025/05/30/brazen-and-audacious-ex-goldman-sachs-exec-tim-leissner-sentenced-to-two-years-in-prison-in-us-court-for-1mdb-crimes/178626 (Leissner sentence, secondary, not fetched)

Academic, tooling and indices
- https://arxiv.org/abs/2306.16424 ; https://arxiv.org/html/2306.16424v1 ; https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f38404edff6f3f642d6fa5892479c42-Abstract.html
- https://arxiv.org/abs/1908.02591
- https://arxiv.org/pdf/2506.13989
- https://github.com/IBM/AMLSim
- https://baselgovernance.org/publications/basel-aml-index-2025

Plenary and amendment context (secondary)
- https://www.plenitudeconsulting.com/news-insights/fatf-publishes-outcomes-from-june-2026-plenary
- https://www.cgc.org.cy/en/fatf-issues-amended-aml-ctf-recommendations/ (June 2025 R.16 revision)
- https://www.regulationtomorrow.com/2026/07/fatf-publishes-targeted-update-on-implementation-of-the-fatf-standards-on-virtual-assets-and-virtual-asset-service-providers/

UNVERIFIED items (do not cite until checked)
- FATF, "Money Laundering and Terrorist Financing through the Misuse of Legal Persons" (title not found).
- Europol, "Enterprising criminals: Europe's fight against the global networks of financial and economic crime" (June 2020), seen only as https://www.statewatch.org/news/2020/jun/eu-europol-financial-economic-crime-report-5-6-20.pdf in search results, not fetched.
- FATF report on hawala and similar providers approved June 2026 for September 2026 publication (publication not confirmed).
- Appellate status of the Volontè conviction; appellate status of the Najib 1MDB-Tanore conviction; the Europol press release for EMMA 9 (statistics taken from the EBF co-release).
