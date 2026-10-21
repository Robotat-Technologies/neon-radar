# NeonRadar phase 2 research: official sanctions lists and PEP sources

- Date checked: Sunday 18 October 2026. Every source in "Sources" was read on this date unless noted.
- Scope: what the Phase 2 build spec (ownership graph and entity resolution) needs to write production loaders for the four official sanctions lists (UK FCDO, US OFAC, UN Security Council, EU FSF) into FollowTheMoney 4.11 entities, and to choose a PEP source that does not depend on OpenSanctions data.
- Citation style: `[S12]` points to the numbered Sources list. `[P1]` is the Phase 1 note `neonradar-phase1/kit/research/sources-opensanctions-ftm-icij.md`. "UNVERIFIED" means I could not confirm the fact from an official source today. "Evidence: crawler" means the fact was read from OpenSanctions crawler code (MIT), not from an official schema.
- Not legal advice. Licence and data protection readings quote the publisher's words; anything marked "analysis" is my interpretation.
- No real designated person, PEP or list record is reproduced. Example values are invented placeholders written as patterns (AAA9999, XXi.NNN, EU.NNNN.NN, NNNNN).

## 0. Answers for the spec writer

1. **UK Sanctions List (FCDO) is the single UK source; load its XML.** GOV.UK: "The OFSI Consolidated List has closed." and "From 28 January 2026 the UK Sanctions List is the only source for all UK sanctions designations." (from 9am that day) [S2][S7]. Seven static URLs `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.{xml,csv,ods,odt,html,txt,pdf}`, no key; schema `SanctionsListSchema-4.33.3.xsd` [S1][S2]. Key `UniqueID` (regime prefix plus four digits, one per regime, so "there may be different Unique IDs for one 'designated person'") [S3]; `OFSIGroupID` historic only, not assigned from 28 Jan 2026 [S2]; `UNReferenceNumber` links to the UN [S4]. 2025 to 2026 changes: CSV, TXT, PDF formats and static URLs; fields unchanged [S1][S2]. Licence OGL v3.0; "personal data in the Information" is outside it [S1][S11].
2. **OFAC: use the Sanctions List Service and the advanced XML.** Pattern `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/{FILE_NAME.EXTENSION}`; no User-Agent header means HTTP 403 [S15]. Prefer `SDN_ADVANCED.XML` plus `CONS_ADVANCED.XML` (name parts, `LowQuality` aliases, ID documents, relationships) [S17][S24]; `SDN.XML` and `sdn.csv`/`add.csv`/`alt.csv`/`sdn_comments.csv` bury DOB, IDs and weak aliases in free-text Remarks [S20]. Licence: CC0 1.0; "This data is in the public domain and may be used without restriction." [S17][S18]. 50 Percent Rule: "applies to entities owned 50 percent or more in the aggregate by one or more blocked persons." (2014 guidance `https://ofac.treasury.gov/media/6186/download`; FAQs unchanged since 2020; supplemented by the 31 March 2026 sham-transactions guidance) [S29][S30][S31].
3. **UN: XML by permanent reference number, through a redirect; licence unclear.** `https://scsanctions.un.org/resources/xml/en/consolidated.xml` answers 302 to a signed Azure blob URL valid one hour [S34]; also by name, HTML, PDF [S33]. `CONSOLIDATED_LIST@dateGenerated`, `INDIVIDUALS/INDIVIDUAL`, `ENTITIES/ENTITY`, IDs `DATAID` and `REFERENCE_NUMBER`, alias `QUALITY` Good or Low, DOB `TYPE_OF_DATE` EXACT, APPROXIMATELY or BETWEEN [S34]. 736 individuals, 274 entities [S33]. UN terms allow download "for the User's personal, non-commercial use" [S35] and no list licence was found, so commercial reuse is **unclear**; the UK and EU lists implement UN listings and carry the UN reference (UK field observed; EU fill rate UNVERIFIED).
4. **EU FSF: the public token URLs still work; load XML 1.1.** `https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw`; XML 1.0, CSV 1.0 and 1.1, PDF too; the RSS feed lists all five (last pubDate 15 Oct 2026) [S37][S38]. `export@generationDate@globalFileId`; `sanctionEntity@euReferenceNumber@unitedNationId@logicalId` with `regulation`, `nameAlias@wholeName@nameLanguage@strong`, `birthdate`, `citizenship`, `identification`, `address` [S37]. CSV 1.1 (118 columns) lacks alias strength [S39]. Licence: Commission reuse policy, Decision 2011/833/EU ("for commercial or non-commercial purposes"), CC BY 4.0 default since 2019; no FSF-specific statement [S41][S42][S43]. The EU Sanctions Map is not the data source [S46].
5. **OpenSanctions crawler code is MIT and reusable with attribution.** Paths: `datasets/gb/fcdo_sanctions/`, `datasets/us/ofac/` (`ofac_advanced.py`, `us_ofac_sdn.yml`, `us_ofac_cons.yml`), `datasets/_global/un_sc_sanctions/` plus `zavod/zavod/shed/un_sc.py`, `datasets/eu/fsf/` plus `zavod/zavod/shed/fsf.py` (commit fc8e631, 2026-10-17) [S47]. COPYRIGHT.md: "Crawler code and configuration are MIT-licensed."; data files are CC BY-NC 4.0 and "This grant reaches only as far as our own rights do." [S47]. MIT is in Apache's Category A [S51]. Port logic, keep the MIT notice, do not copy YAML lookups (they hold real list values).
6. **Cross-list keys.** UK `UNReferenceNumber` (CSV "UN Reference Number") and EU `unitedNationId` (CSV `Entity_UnitedNationId`) carry the UN `REFERENCE_NUMBER`; store all three in FtM `Sanction:unscId` and join on it [S3][S34][S37][S47]. UK `OFSIGroupID` groups one person's several Unique IDs [S2][S3]. OFAC data has no UN reference field (evidence: crawler), so link OFAC only through strong identifiers: IMO number, passport or national ID number plus issuing country, LEI, registration number plus country, crypto address, SWIFT/BIC [S47].
7. **PEPs: UK Parliament Members API in Phase 2, Wikidata as stretch.** `https://members-api.parliament.uk/api/Members/Search` (`House=Commons`, `House=2` for Lords; current and former) plus `/api/Members/{id}/Biography` (`governmentPosts`), Open Parliament Licence v3.0: commercial use allowed, attribution "Contains Parliamentary information licensed under the Open Parliament Licence v3.0.", personal data not covered [S53][S54]. Wikidata is CC0 [S59] but needs curated position lists, and query.wikidata.org is online only (60 s per query) [S60][S61]. Scope: MLR 2017 reg 35(12) and (14)(a) to (h), 12 months minimum after office, domestic PEPs lower risk by default since 10 Jan 2024 [S55]; FATF [S57]; FCA FG25/3 [S58]. Effort: Members API 1 to 1.5 days; Wikidata 1.5 to 2 days.
8. **Data protection.** No ICO guidance specific to sanctions screening found. ICO says criminal offence data covers allegations and probably "personal data about penalties, conditions or restrictions placed on an individual" [S66]; DPA 2018 Schedule 1 offers conditions 10, 12, 14 and 15 [S67][S68]; OFSI publishes designated persons' data "to assist screening and implementation of financial sanctions" [S12]. Analysis, not legal advice: treat list data as possibly Article 10 data, minimise free-text reasons, and document a lawful basis per deployment.
9. **Matching guidance.** OFAC Sanctions List Search uses Jaro-Winkler and Soundex, a "Minimum Name Score" slider, and OFAC "cannot make such a recommendation" on a threshold; FAQ 5 says to compare DOB, ID numbers, nationality and address [S27][S28]. OFSI separates a "name match" from a "target match" [S10]. UN: Good quality a.k.a. is "sufficient for a positive identification", Low quality "probably insufficient alone" [S33]. EU best practices: as many identifiers as possible, ICAO transliteration, refute homonyms [S45].
10. **Overlap and quality.** No official or OpenSanctions overlap figure found (UNVERIFIED); compute it in the spec with the `unscId` join. Main quality issues: free-text registration numbers, partial dates written as literal "dd/mm/1970", malformed e-mails, misclassified subject types, several Unique IDs per UK person, aliases split across fields (section 10).

| List | Dataset slug | Best format and URL | Licence | Commercial reuse allowed | Cadence | Record counts (source) |
|---|---|---|---|---|---|---|
| UK Sanctions List (FCDO) | `gb_fcdo_sanctions` | XML `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml` (CSV for gap-filling) | OGL v3.0 (GOV.UK footer); personal data outside the licence | yes (data protection still applies) | irregular, several updates a week; no stated schedule | about 4,020 persons, 1,930 organisations plus 410 companies, 680 ships, 6,411 targets (OpenSanctions FtM counts, includes some non-designated owners) [S48] |
| US OFAC SDN | `us_ofac_sdn` | `.../exports/SDN_ADVANCED.XML` (121.7 MB) | CC0 1.0, public domain | yes | irregular ("frequent"); all OFAC files updated together | 7,492 persons, 9,934 organisations (plus 22 companies, 2 legal entities), 1,556 vessels, 342 aircraft, 1,065 crypto wallets [S48] |
| US OFAC Consolidated (non-SDN) | `us_ofac_cons` | `.../exports/CONS_ADVANCED.XML` (4.3 MB) | CC0 1.0 | yes | irregular | 118 persons, 356 organisations (plus 5 companies), 232 securities [S48] |
| UN SC Consolidated List | `un_sc_sanctions` | XML `https://scsanctions.un.org/resources/xml/en/consolidated.xml` (2.1 MB, 302 redirect) | UN Terms of Use (personal, non-commercial); no list licence | unclear | irregular; press release after each change | 736 individuals, 274 entities [S33]; ships are in the separate 1718 list |
| EU FSF | `eu_fsf` | XML 1.1 `https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw` (24.6 MB) | Commission reuse policy, CC BY 4.0 default | yes, with attribution (no FSF-specific statement) | irregular; RSS | 4,398 persons, 1,728 organisations, 2 vessels, 6,128 entries [S48] |

Slugs: keep the OpenSanctions-style slugs, but decide entity IDs deliberately. OpenSanctions builds IDs such as `gb-fcdo-` plus the slugified Unique ID [S47]; if NeonRadar uses the same scheme and a licensed user also loads OpenSanctions data, the two would merge silently. Recommend a NeonRadar ID prefix (for example `nr-gb-fcdo-...`) and an explicit cross-reference property instead.

## 0.1 Method and limitations

- The shell reached only PyPI, npm and GitHub. Government sites were read with WebFetch, which returns model-written extracts with quotes capped at about 125 characters, and reads only the first 90,000 to 120,000 characters of a page. Large files (the UK XML, the UN XML, the EU XML and CSV) were therefore inspected only in their first records. Structure seen there is marked "observed"; elements not reached are marked UNVERIFIED or taken from crawler code.
- HTTP headers (Last-Modified, ETag, Content-Length) could not be inspected for any list: UNVERIFIED everywhere.
- Unreadable today: the UK XSD (served as binary), the OFAC SLS host and its file listing pages (JavaScript, fetch errors), the UN XSD at `https://www.un.org/sc/resources/sc-sanctions.xsd`, the UK CSV, the official OGL page (server error; text read from the SPDX copy instead).
- GitHub: `opensanctions/opensanctions` (blobless clone, history back to October 2024, HEAD fc8e631 of 2026-10-17), `moov-io/watchman` (Apache-2.0) and `vi-malysh/ofac-vessels` (third-party evidence for the enhanced XML). The `gh` API was not enabled for this session.

## 1. UK Sanctions List (FCDO)

### 1.1 Status of the OFSI Consolidated List

- The OFSI page is withdrawn: "The OFSI Consolidated List has closed." and "From 28 January 2026 the UK Sanctions List is the only source for all UK sanctions designations." (both dated 28 January 2026; page last updated 28 January 2026) [S7].
- Guidance "Moving to a single list for UK sanctions designations: 28 January 2026" (published 13 October 2025): "From 9am (UK time) on Wednesday 28 January 2026, the" UK Sanctions List became the only list [S2].
- OFSI Group ID: newly designated persons "will not be assigned an" OFSI Group ID; "These historic Group IDs will remain valid for use, for example in licence applications," and systems keyed on Group ID should move to the Unique ID [S2].
- Formats: "There will be no change to formatting of existing UKSL (UK Sanctions List) file types."; the list "will otherwise not be modified, retaining the same data fields in the same order."; "URLs for each format will stay the same no matter how many times the list is updated/refreshed." [S2].
- OFSI's old format guide (28/02/2022) used `Group ID` ("The unique Consolidated List identifying code given to all entries relating to a specific individual or entity"), `Group Type`, `Alias Type` ("Primary Name, Primary Name Variation, AKA (also known as) or FKA (formerly known as)"), `Alias Quality`, `Listed On`, `UK Sanctions List Date Designated` [S8]. On the UK Sanctions List the same identifier is `OFSIGroupID` (XML) or "OFSI Group ID" (CSV) [S3][S4].
- OpenSanctions changelog 38 ("UK Sanctions Lists Consolidation", Breaking): "Replace all use of `gb_hmt_sanctions` with `gb_fcdo_sanctions`"; the old dataset was deleted from the repository by a commit of 2026-03-13 titled for 2026-03-16 [S49][S47].

### 1.2 Downloads, access, cadence, version detection

- Files (all on `https://sanctionslist.fcdo.gov.uk/docs/`): `UK-Sanctions-List.odt`, `.ods`, `.xml`, `.html`, `.txt`, `.csv`, `.pdf` [S1]. Schema: `https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/SanctionsListSchema-4.33.3.xsd` (16 KB) [S1]. Format guide: `https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list` (published 22 December 2025) [S3]. No JSON format. No key or registration.
- Format guide: "The data provided in each format is identical but is displayed in different ways, depending on the format." [S3]. Most complete in practice: XML (repeating elements, explicit `AliasStrength`, `SanctionsImposedIndicators`); the CSV flattens multi-valued fields (section 1.6).
- History of URL changes: CSV and TXT added 3 Dec 2025 (HTML link changed), PDF added 16 Dec 2025 (ODT and ODS links changed), XSD added 14 Nov 2025 [S1]. OpenSanctions finds the links by scraping the GOV.UK page section `#documents` [S47]; since January 2026 the URLs are static [S2], so hard-code them and keep the scrape as a fallback.
- Cadence: no stated frequency; the GOV.UK change history (482 entries) shows updates on 8, 12, 15 and 16 October 2026 [S1]. Notifications: "sign up to get UK sanctions email alerts" [S1]. OpenSanctions polls every 2 hours (`schedule: "0 */2 * * *"`) [S47].
- Version detection: XML root child `DateGenerated` [S4]; HTML header "Date generated" in DD/MM/YYYY [S5]; per record `LastUpdated` [S4]. The XML `DateGenerated` value format is UNVERIFIED. Last-Modified and ETag: UNVERIFIED. Recommendation: conditional GET when headers exist, otherwise SHA-256 of the body plus `DateGenerated`.

### 1.3 Size and counts

- OpenSanctions `gb_fcdo_sanctions` (processed 2026-10-18): Person 4,023; Organization 1,929; Company 412; Vessel 683; CryptoWallet 59; 18,790 entities, 6,411 targets; `source.csv` 47.83 MB [S48]. Organizations and Companies include parent companies, subsidiaries and ship owners that the crawler creates from free text, so designated entries are about targets minus wallets. The XML file size is UNVERIFIED.
- Designation types: `IndividualEntityShip` is Individual, Entity or Ship [S4][S47]; the UK list has no aircraft type.
- OpenSanctions assertion bounds (sanity checks for a loader): Person 3,060 to 7,200, Organization 890 to 3,000, Vessel 125 to 800 [S47].

### 1.4 XML structure (observed in the live file [S4], plus crawler evidence [S47])

```
Designations                                  (attributes xmlns:xsi, xmlns:xsd)
  DateGenerated
  Designation                                 (repeated)
    LastUpdated, DateDesignated               (DD/MM/YYYY)
    UniqueID                                  (pattern AAA9999)
    OFSIGroupID                               (number; historic)
    UNReferenceNumber                         (UN permanent reference, pattern XXi.NNN)
    Names/Name                                (repeated)
      Name1 .. Name6, NameType, AliasStrength
    NonLatinNames/NonLatinName
      NameNonLatinScript, NonLatinScriptType, NonLatinScriptLanguage
    Titles/Title
    RegimeName                                (one per designation; crawler asserts exactly one)
    IndividualEntityShip                      (Individual | Entity | Ship)
    DesignationSource                         (observed "UN"; UK-only and both: exact strings UNVERIFIED)
    SanctionsImposed                          (text, "|"-separated)
    SanctionsImposedIndicators                (15 booleans, below)
    OtherInformation, UKStatementofReasons
    Addresses/Address
      AddressLine1 .. AddressLine6, AddressPostalCode, AddressCountry
    PhoneNumbers/PhoneNumber, EmailAddresses/EmailAddress
    IndividualDetails/Individual
      DOBs/DOB
      PassportDetails/Passport/PassportNumber, PassportAdditionalInformation
      NationalIdentifierDetails/NationalIdentifier/NationalIdentifierNumber, NationalIdentifierAdditionalInformation
      Nationalities/Nationality, Genders/Gender, Positions/Position
      BirthDetails/Location/TownOfBirth, CountryOfBirth
    ShipDetails/Ship                          (evidence: crawler)
      IMONumbers/IMONumber, CurrentOwnerOperators/CurrentOwnerOperator,
      TypeOfShipDetails/TypeOfShip, CurrentBelievedFlagOfShips/CurrentBelievedFlagOfShip
```

- `SanctionsImposedIndicators` children observed: AssetFreeze, ArmsEmbargo, TargetedArmsEmbargo, CharteringOfShips, ClosureOfRepresentativeOffices, CrewServicingOfShipsAndAircraft, Deflag, PreventionOfBusinessArrangements, ProhibitionOfPortEntry, TravelBan, PreventionOfCharteringOfShips, PreventionOfCharteringOfShipsAndAircraft, TechnicalAssistanceRelatedToAircraft, TrustServicesSanctions, DirectorDisqualificationSanction (values true or false) [S4]. Verify the full list against XSD 4.33.3.
- UNVERIFIED in XML: element names for entity details (type of entity, parent company, subsidiaries, business registration numbers), previous owners, previous flags, tonnage, length, year built and HIN of ships. Their CSV columns are known (1.5). The spec should have the loader validate against the XSD and log unknown elements rather than drop them.
- The HTML version also shows an "INTERPOL-UN Security Council Special Notice web link" field [S5].

### 1.5 CSV structure

- The first line is a metadata row, then the header; OpenSanctions skips one line before `csv.DictReader` (exact metadata text UNVERIFIED) [S47]. One row per name: a designation with five names spans five rows, joined by `Unique ID` [S47].
- Header strings exactly as the crawler reads them (evidence: crawler; order UNVERIFIED): `Last Updated`, `Unique ID`, `OFSI Group ID`, `UN Reference Number`, `Name 1` to `Name 6`, `Name type`, `Alias strength`, `Title`, `Name non-latin script`, `Non-latin script type`, `Non-latin script language`, `Regime Name`, `Designation Type`, `Designation source`, `Sanctions Imposed`, `Other Information`, `UK Statement of Reasons`, `Address Line 1` to `Address Line 6`, `Address Postal Code`, `Address Country`, `Phone number`, `Website`, `Email address`, `Date Designated`, `D.O.B`, `Nationality(/ies)`, `National Identifier number`, `National Identifier additional information`, `Passport number`, `Passport additional information`, `Position`, `Gender`, `Town of birth`, `Country of birth`, `Type of entity`, `Subsidiaries`, `Parent company`, `Business registration number (s)`, `IMO number`, `Current owner/operator (s)`, `Previous owner/operator (s)`, `Current believed flag of ship`, `Previous flags`, `Type of ship`, `Tonnage of ship`, `Length of ship`, `Year Built`, `Hull identification number (HIN)` [S47].
- The format guide's headings differ slightly in spelling ("Individual/Entity/Ship", "Parent Company", "Business registration number(s)", "Current owner/operator(s)") [S3]; trust the file header, not the guide, and fail loudly on an unknown header.

### 1.6 How the UK list represents the hard fields

- Names: "Name 6" is the surname or the full entity or ship name; Name 1 is a given name; Names 2 to 5 may be given names or patronymics, so OpenSanctions only maps Name 1 to `firstName` and Name 6 to `lastName` [S3][S47].
- Name types: "Primary Name, Primary Name Variation, Alias"; "Primary name variations are spelling variations of the primary name." [S3].
- Alias quality: "The strength of an alias [dash replaced by a colon]: good quality; low quality or if empty, ‘blank’." [S3]; observed XML values `Good quality a.k.a` and `Low quality a.k.a` [S4]. Strength is given only for UN listings and is blank otherwise [S3]; OpenSanctions then guesses (single-token person alias becomes `weakAlias`, short upper-case organisation token becomes `abbreviation`) [S47].
- Non-Latin names: `NameNonLatinScript` with `NonLatinScriptType` and `NonLatinScriptLanguage` (language names such as "Romanian; Moldavian; Moldovan" need a lookup to ISO codes) [S3][S47].
- Dates of birth: "Date of birth (in dd/mm/yyyy format). The date of birth can be partially known, such as dd/mm/1970" [S3]. The letters are literal: patterns `dd/mm/YYYY`, `dd/MM/YYYY` (month known) and `00/00/YYYY` occur (OpenSanctions date formats `%d/%m/%Y`, `dd/mm/%Y`, `dd/%m/%Y`, plus patches for a zeroed day and month and for a two-letter year placeholder) [S47]. Multiple DOBs are repeated `DOB` elements in XML [S4].
- Place of birth: `TownOfBirth` and `CountryOfBirth`, repeatable `Location` [S4]. Nationality: "The citizenship and/or nationality of the target" [S3].
- Addresses: six free lines, postcode and country; P.O. boxes appear inside postcode or line text [S4][S47].
- Identity documents: passport number plus free-text additional information; national identifier "e.g. ID card numbers, Social Security Numbers, Tax Numbers etc." [S3]. No document type field beyond these two groups.
- Company registration numbers: "Known business registration number(s)" [S3], free text mixing INN, OGRN, KPP, BIK, SWIFT/BIC, TIN, LEI-like codes and third-party database identifiers in one string; OpenSanctions applies regexes and a large lookup table [S47].

### 1.7 Identifiers and cross-references

- `UniqueID`: "If an entry is designated under multiple regimes, there may be different Unique IDs for one 'designated person'." [S3]. So Unique ID is a designation key, not a person key.
- `OFSIGroupID`: groups the entries of one person or entity designated before 28 Jan 2026 [S2][S3]; absent for later designations.
- `UNReferenceNumber`: "Reference number created by the UN for those subject to UN sanctions" [S3]. `DesignationSource` says whether the designation is UK-only, UN-only or both [S3].
- FtM mapping used by OpenSanctions: `Sanction:authorityId` = Unique ID and OFSI Group ID, `unscId` = UN reference, `startDate` = DateDesignated, `modifiedAt` = LastUpdated, `reason` = UK Statement of Reasons, `provisions` = Sanctions Imposed, `authority` = Designation source, `program` = Regime Name [S47].

### 1.8 Licence

- GOV.UK footer on the publication page: "All content is available under the Open Government Licence v3.0, except where otherwise stated" [S1]. The files live on `sanctionslist.fcdo.gov.uk`; no separate licence statement for them was found (UNVERIFIED, analysis: OGL applies as the publication page carries it).
- OGL v3.0: you may "exploit the Information commercially and non-commercially"; attribution "Contains public sector information licensed under the Open Government Licence v3.0."; "This licence does not cover: personal data in the Information;"; no right to suggest "official status"; licensed "'as is'" [S11].
- Decision: commercial loading is allowed under the licence; the personal-data exclusion sends the personal data question to UK GDPR (section 8).

### 1.9 Parser pitfalls

- One person, several Unique IDs (one per regime); merge on OFSI Group ID where present, else by entity resolution.
- CSV: metadata first line; one row per name; addresses glued together because line breaks are stripped (OpenSanctions comment: "The CSV strips the line breaks between addresses, gluing some into one unmatchable string; the XML pass picks those up.") [S47].
- Literal `dd/mm` in dates; DD/MM order everywhere (never parse with a US-first parser).
- Multi-value separators: `|` in Sanctions Imposed, Designation source, Position, Subsidiaries, owners; Position also split on "; and " and "; " by OpenSanctions [S47].
- HTML entities in UK Statement of Reasons (OpenSanctions applies `html.unescape`) [S47].
- Crypto wallet addresses appear only inside Other Information [S47].
- Messy e-mails and websites (two addresses in one field, spaces inside addresses, websites in e-mail fields) and non-standard country names ("Congo (Democratic Republic)", "St Vincent") [S47].
- Do not copy the OpenSanctions XML pass verbatim: in `crawl_xml` the `elif entity.schema.label == "Person"` branch is unreachable after `if ... in ["Person", "Organization"]`, so person details come only from its CSV pass (observation from code) [S47].

## 2. US OFAC SDN List and Consolidated (non-SDN) List

### 2.1 Downloads and which file to use

- Sanctions List Service (SLS), launched 6 May 2024: "SLS is now the primary application OFAC will use to deliver sanctions list files and data to the public."; "existing links to OFAC list files remain functional through URL redirects." [S14]. The SLS page links the SDN and non-SDN list pages (file tables load by JavaScript), a "Customized Dataset" option and a delta file archive, and says "all non-SDN sanctions lists are consolidated in a set of separate data files." [S13].
- Official pattern: old `https://www.treasury.gov/ofac/downloads/{FILE_NAME.EXTENSION}` redirects to `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/{FILE_NAME.EXTENSION}`; the new host "requires all requests to have a "User-Agent" entry in the request's header." [S15].
- Files confirmed by OFAC's own catalogue (data.json, Project Open Data v1.1): `SDN_ADVANCED.XML`, `SDN_ENHANCED.XML`, `CONS_ADVANCED.XML`, `CONS_ENHANCED.XML` under the exports path [S17]. `SDN.XML` and `CONSOLIDATED.XML` exist (namespace notice of 7 May 2024, new XSD `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML.xsd`) [S16]. CSV `sdn.csv`, `add.csv`, `alt.csv`, `sdn_comments.csv` are fetched from the exports path by watchman (Apache-2.0) [S52]; the tutorial names "the four SDN CSV flat files" [S21]. Fixed-width `.FF` files exist (FAQ 81) [S26]; PIP, DEL and SDALL.ZIP were retired "on or about, the week of September 18, 2023" [S25]. ZIP bundles `SDN_ADVANCED.ZIP` and `SDN_ENHANCED.ZIP` are named by a third-party project (UNVERIFIED) [S32]. Non-SDN CSV names (`CONS_PRIM.CSV`, `CONS_ADD.CSV`, `CONS_ALT.CSV`, `CONS_COMMENTS.CSV`) are UNVERIFIED. No JSON export found.
- Prefer the advanced XML. OFAC: "The advanced XML files have the capacity to provide a great deal of additional meta data on sanctioned parties."; "non-western names can now be broken down into multiple name parts"; "government-issued identification information can be labeled as legitimate or fraudulent." [S22]. OpenSanctions runs both lists from the advanced files [S47].
- Enhanced XML: catalogued with XSD `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED_XML.xsd` [S18]. Its structure is UNVERIFIED; a third-party parser reads namespace `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED_XML` and elements `entity@id`, `entityType`, `names/name/translations/translation/formattedFullName`, `sanctionsPrograms/sanctionsProgram@refId`, `sanctionsTypes/sanctionsType`, `features/feature/type` and `value`, `identityDocuments/identityDocument/type` and `documentNumber` [S32]. Worth a later spike: it may be simpler than the advanced format.
- No key, token or registration.

### 2.2 Cadence and version detection

- data.json `accrualPeriodicity` "http://purl.org/cld/freq/frequent" [S17]; data.gov "irregular" [S18]; advanced files "will be updated at the same time as all of OFAC's other list products" [S22]. FAQ 88: OFAC updates lists "at an ever increasing pace" and cannot advise on download design [S26].
- Advanced XML header `DateOfIssue` with `Year`, `Month`, `Day` (date only, so same-day reissues need a content hash) [S24]. Legacy SDN.XML header: OFAC's 2005 notice adds "Publish_date" and "record_count" under "publishInformation" [S25]; the exact element spelling in today's file is UNVERIFIED.
- Delta files: "Yes, OFAC offers a delta file as part of its Sanctions List Service (SLS)."; archive `https://sanctionslist.ofac.treas.gov/Home/DeltaFileArchive` [S26]. The advanced XSD carries `DeltaAction` attributes and `SanctionsEntry@EntryDeltaFlag` (`NewEntry`, `DeletedEntry`, `ModifiedEntry`) [S24]. Delta file names: UNVERIFIED.
- FAQ 1031: OFAC sometimes publishes only UIDs in Recent Actions for clerical updates, signalling the action is "solely administrative" [S26].

### 2.3 Size and counts

- OpenSanctions `us_ofac_sdn` (processed 2026-10-18, last change 2026-10-15): People 7,492; Organizations 9,934; Companies 22; Legal entities 2; Vessels 1,556; Airplanes 342; Cryptocurrency wallets 1,065; Securities 7; Addresses 17,826; 20,420 targets; `source.xml` (`sdn_advanced.xml`) 121.69 MB [S48].
- OpenSanctions `us_ofac_cons`: People 118; Organizations 356; Companies 5; Securities 232; 711 targets; source 4.33 MB [S48].
- OpenSanctions gives its SDN crawler 2,500 MiB of memory with a 3,000 MiB limit (full DOM parse) [S47].

### 2.4 Advanced XML structure (official XSD [S24], usage as in the crawler [S47])

```
Sanctions                       (XSD targetNamespace http://www.un.org/sanctions/1.0)
  DateOfIssue (Year, Month, Day; @CalendarTypeID)
  ReferenceValueSets            (39 lookup tables: AliasTypeValues, AreaCodeValues, CountryValues,
                                 DetailReferenceValues, FeatureTypeValues, IDRegDocDateTypeValues,
                                 IDRegDocTypeValues, LegalBasisValues, ListValues, LocPartTypeValues,
                                 NamePartTypeValues, PartySubTypeValues, PartyTypeValues,
                                 RelationQualityValues, RelationTypeValues, ReliabilityValues,
                                 SanctionsProgramValues, SanctionsTypeValues, ScriptValues,
                                 ValidityValues, ...)
  Locations/Location@ID
    LocationAreaCode@AreaCodeID, LocationCountry@CountryID, LocationPart@LocPartTypeID/LocationPartValue/Value
  IDRegDocuments/IDRegDocument  @ID @IDRegDocTypeID @IdentityID @IssuedBy-CountryID @IssuedIn-LocationID @ValidityID
    Comment, IDRegistrationNo, IssuingAuthority, DocumentDate@IDRegDocDateTypeID/DatePeriod
  DistinctParties/DistinctParty@FixedRef
    Comment
    Profile@ID@PartySubTypeID
      Identity@ID
        Alias @FixedRef @AliasTypeID @Primary @LowQuality
          DocumentedName/DocumentedNamePart/NamePartValue @NamePartGroupID @ScriptID
        NamePartGroups/MasterNamePartGroup/NamePartGroup @ID @NamePartTypeID
      Feature@ID@FeatureTypeID
        FeatureVersion@ID@ReliabilityID: DatePeriod, VersionDetail@DetailTypeID@DetailReferenceID, VersionLocation@LocationID
  ProfileRelationships/ProfileRelationship @From-ProfileID @To-ProfileID @RelationTypeID @RelationQualityID @SanctionsEntryID @Former
  SanctionsEntries/SanctionsEntry @ID @ProfileID @ListID @EntryDeltaFlag
    EntryEvent@EntryEventTypeID@LegalBasisID (Date, Comment), SanctionsMeasure@SanctionsTypeID (Comment, DatePeriod)
  SanctionsEntryLinks
```

- `DatePeriod`: `@CalendarTypeID @YearFixed @MonthFixed @DayFixed`, children `Start` and `End`, each with `From` and `To` (`Year`, `Month`, `Day`) and `@Approximate` [S24]. OFAC: "any of the start, end or duration details may be marked as approximate" [S23].
- Identifiers: "The DISTINCT PARY FIXED REF number and the PROFILE ID number both make use of the SDN UID number." (sic) [S23]. The same UID is `ent_num` in the CSV [S20][S21] (analysis: consistent with FAQ 1031 [S26]).
- Section order matters: `SanctionsEntries` and `ProfileRelationships` follow `DistinctParties`, so a streaming parser needs two passes or must buffer parties.
- Namespace: the legacy XSD declares `http://www.un.org/sanctions/1.0`, while third-party code reads the SLS file with `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML` [S24][S32]. Parse namespace-agnostically (OpenSanctions calls `h.remove_namespace`) [S47].

### 2.5 Legacy CSV (dat_spec.txt [S20])

- `SDN.CSV`: `ent_num, SDN_Name, SDN_Type, Program, Title, Call_Sign, Vess_type, Tonnage, GRT, Vess_flag, Vess_owner, Remarks` (Remarks 1,000 characters).
- `ADD.CSV`: `Ent_num, Add_num, Address, City/State/Province/Postal Code, Country, Add_remarks`.
- `ALT.CSV`: `ent_num, alt_num, alt_type, alt_name, alt_remarks`; `alt_type` is aka, fka or nka.
- `SDN_COMMENTS.CSV`: remarks overflow beyond 1,000 characters [S20][S21].
- No header row ("the column names are not stored in the actual sanctions list data files") [S21]; null is `-0-`; comma delimiter, double-quote text qualifier, carriage-return record separator; weak aliases appear in Remarks "bracketed by quotation marks" [S20]. DOB, POB, nationality, passports and "Linked To" relations are also inside Remarks (watchman parses them with regexes) [S52].

### 2.6 Names, aliases, dates, places, nationality, addresses, documents

- Names: aliases typed by `AliasTypeID` (values `Name`, `A.K.A.`, `F.K.A.`, `N.K.A.`); `LowQuality` true marks weak aliases; name parts typed by NamePartType (`Last Name`, `First Name`, `Middle Name`, `Maiden Name`, `Patronymic`, `Matronymic`, `Nickname`, `Entity Name`, `Vessel Name`, `Aircraft Name`) [S24][S47]. Legacy SDN.XML: "Aliases are specifically labeled as "weak" or "strong" in this file." [S22].
- Non-Latin: each `NamePartValue@ScriptID`; ScriptID 215 is Latin, other scripts have codes such as Arab, Cyrl, Hans, Hant, Hang, Geor, Grek, Armn (evidence: crawler) [S47]. "Any information presented in non-Latin character sets will also have a basic Latin version." [S22].
- Dates of birth: features `Birthdate` with a `DatePeriod`; a whole-year range (01-01 to 12-31) signals "year only"; multiple DOBs are multiple features (evidence: crawler) [S47].
- Place of birth `Place of Birth`; nationality `Nationality Country`; citizenship `Citizenship Country`; gender `Gender`; addresses `Location` features pointing to `Locations` with typed parts `ADDRESS1`, `ADDRESS2`, `ADDRESS3`, `CITY`, `POSTAL CODE`, `REGION`, `STATE/PROVINCE`, `Unknown` (evidence: crawler) [S47].
- Identity documents: `IDRegDocument` with type, number, issuing country, authority, issue and expiration dates (`IDRegDocDateType` values "Issue Date" and "Expiration Date"), validity [S24][S47].
- ID types seen (IDRegDocType values mapped by the crawler) [S47]: `Passport`, `Diplomatic Passport`, `National ID No.`, `Identification Number`, `Cedula No.`, `Tax ID No.`, `SSN`, `Driver's License No.`, `Birth Certificate Number`, `Registration Number`, `Registration ID`, `Company Number`, `UK Company Number`, `Business Registration Number`, `Commercial Registry Number`, `Certificate of Incorporation Number`, `Chamber of Commerce Number`, `Legal Entity Number` and `LE Number` (LEI), `Unified Social Credit Code (USCC)`, `Russian State Individual Business Registration Number Pattern (OGRNIP)`, `Global Intermediary Identification Number`, `V.A.T. Number`, `MMSI`, `Vessel Registration Identification` (IMO), `Aircraft Serial Identification`. Features add `SWIFT/BIC`, `D-U-N-S Number`, `BIK (RU)`, `ISIN`, `Equity Ticker`, `Digital Currency Address - XBT` and other currencies.
- Relationships: RelationType values `Associate Of`, `Providing support to`, `Acting for or on behalf of`, `Owned or Controlled By`, `Family member of`, `Leader or official of`, `playing a significant role in`, `Principal Executive Officer`, `Owns, controls, or operates`, `Property in the interest of` [S47]. These are direct inputs to the ownership graph.

### 2.7 Licence

- OFAC data.json: `"license": "http://creativecommons.org/publicdomain/zero/1.0/"`, `"rights": "No restrictions on public access"`, `"accessLevel": "public"` for the advanced and enhanced SDN and non-SDN files [S17].
- data.gov harvest record for the SDN Enhanced XML: license `https://creativecommons.org/publicdomain/zero/1.0/`, rights "This data is in the public domain and may be used without restriction." [S18]. The older SDN record also lists CC0 [S19].
- Background (not checked today): US federal government works are not subject to US copyright (17 U.S.C. 105). Decision: commercial loading and redistribution allowed.

### 2.8 The 50 Percent Rule and its UK and EU counterparts

- OFAC "Revised Guidance on Entities Owned by Persons Whose Property and Interests in Property Are Blocked", 13 August 2014, `https://ofac.treasury.gov/media/6186/download`: an entity owned in the aggregate, directly or indirectly, 50 percent or more by one or more blocked persons "is itself considered to be a blocked person" (fragment of the core sentence); blocked persons are treated as having an interest in an entity they own "whether individually or in the aggregate, directly or indirectly, a 50 percent or greater interest."; "The property and interests in property of such an entity are blocked regardless of whether the entity itself is listed"; US persons should be cautious with entities blocked persons "may control by means other than a majority ownership interest." [S29].
- FAQs (topic 1521): FAQ 399 "OFAC's 50 Percent Rule applies to entities owned 50 percent or more in the aggregate by one or more blocked persons."; FAQ 401 "'Indirectly,' ... refers to one or more blocked persons' ownership of shares of an entity through another entity or entities" (X owns 50% of A, A owns 50% of B: "Entity B is considered to be blocked."); FAQ 398 (11 Aug 2020) "OFAC's 50 Percent Rule speaks only to ownership and not to control." No FAQ updated in 2024 to 2026 [S30].
- 2026 change: "Guidance on Sham Transactions and Sanctions Evasion", 31 March 2026: "sham transactions do not terminate a blocked interest in property."; "This advisory supplements the 50 Percent Rule by providing factors to consider in conducting due diligence"; "Transfers by a blocked person to a family member or close associate can be evidence of a sham transaction."; "unnecessarily complex legal structures without a discernible legitimate purpose" "may indicate an effort to conceal an ownership interest" [S31].
- UK (OFSI general guidance, last updated 12 May 2026): owned or controlled where "the person holds (directly or indirectly) more than 50% of the shares or voting rights in an entity"; "OFSI would not simply aggregate different designated persons’ holdings in a company," unless there is a joint arrangement; owned entities "may not be designated in their own right" [S10].
- EU (Council "EU Best Practices for the effective implementation of restrictive measures", 11623/24, 3 July 2024, marked LIMITE but public): ownership is "the possession of 50% or more of the proprietary rights of an entity or having majority interest in it"; "the aggregated ownership of the entity should , also be taken into account" (example: 30% plus 25% held by two designated persons) [S45].
- Spec consequence: one exposure rule per jurisdiction: US `>= 50%` aggregated over all blocked owners; EU `>= 50%` aggregated; UK `> 50%` per person, no aggregation without a joint arrangement; control edges flagged separately in all three. For US chains, blocked status propagates entity by entity (FAQ 401: X holds 50% of A, so A is blocked; A holds 50% of B, so B is blocked), so do not multiply percentages along the path (that would give 25% and miss B) [S30]. UK and EU chain examples were not found in the texts read (the UK guidance relies on "directly or indirectly") [S10][S45]: apply the same propagation with their thresholds and mark it as an interpretation.

### 2.9 Pitfalls

- User-Agent header mandatory; follow redirects from legacy URLs [S15].
- Two-level indirection: every type, country, list and feature is an ID into `ReferenceValueSets`; PartySubType "Unknown" must fall back to PartyType (evidence: crawler) [S47].
- Sanction details hidden in features ("Additional Sanctions Information -", "Secondary sanctions risk:", "Executive Order 14024 Directive Information -", "Listing Date (EO 14024 Directive 1a):") [S47].
- IMO numbers sometimes arrive as an ID document whose number starts with "IMO " [S47].
- Some relationships point in a semantically reversed direction and OpenSanctions flips them ("HACK: Looks like OFAC just has some link in a direction that makes no semantic sense") [S47].
- `Consolidated List` is a meta list ID that always co-occurs with a specific list (for example "Non-SDN CMIC List"); an entry can carry several program tags [S47].
- OpenSanctions does not read the designation date from `EntryEvent/Date`; NeonRadar should (it feeds `Sanction:startDate`).

## 3. UN Security Council Consolidated List

### 3.1 Downloads, access, cadence

- Page (last updated 15 October 2026): XML alphabetical `https://scsanctions.un.org/resources/xml/en/name/consolidated.xml`, XML by permanent reference number `https://scsanctions.un.org/resources/xml/en/consolidated.xml`, HTML and PDF `https://scsanctions.un.org/consolidated` and `https://scsanctions.un.org/r`; search tool `https://search.sanctions.un.org`; English files only [S33]. No CSV, ODS or JSON. No key.
- Both XML URLs answer 302 to `https://unsolprodfiles.blob.core.windows.net/publiclegacyxmlfiles/EN/consolidatedLegacyByPRN.xml` (or `...ByNAME.xml`) with an Azure SAS query valid one hour (`st` to `se`) [S34]. The blob also answered without the query string today (UNVERIFIED whether that is intended). Always start from the `scsanctions.un.org` URL. The container name "publiclegacyxmlfiles" hints at a newer UN format: UNVERIFIED.
- Cadence: no fixed frequency; "A press release is issued after all changes to the respective sanctions list"; mailing list on the page [S33]. Version: root attribute `dateGenerated` (ISO 8601 UTC with milliseconds) [S34]; page text "was last updated on ... and supersedes all previous versions." [S33].
- XSD referenced by the file: `xsi:noNamespaceSchemaLocation="https://www.un.org/sc/resources/sc-sanctions.xsd"` (could not be fetched today) [S34].

### 3.2 Size and counts

- "Individuals (736 individuals)" and "Entities and other groups (274 entities)" on 15 October 2026 [S33]. OpenSanctions: Person 735, LegalEntity 269, Address 402; `source.xml` 2.08 MB [S48].
- Regimes and prefixes: QD (1267/1989), IQ (1518), CD (1533), SD (1591), KP (1718), IR (1737), LY (1970), TA (1988), GB (2048), YE (2140), SS (2206), HT (2653), SO (2713), CF (2745) [S33]. The page lists IR (1737) among current regimes [S33] and OpenSanctions added the `Iran` to UN-SC1737 mapping on 2025-09-29 [S47] (background, not checked today: the 2025 snapback of UN Iran measures).
- Ships designated by the 1718 Committee are a separate HTML list, not in this XML (OpenSanctions `un_1718_vessels`) [S47].

### 3.3 Structure (observed [S34], entity part from crawler [S47] and watchman [S52])

```
CONSOLIDATED_LIST @dateGenerated
  INDIVIDUALS/INDIVIDUAL
    DATAID, VERSIONNUM, FIRST_NAME, SECOND_NAME, THIRD_NAME, FOURTH_NAME,
    UN_LIST_TYPE, REFERENCE_NUMBER, LISTED_ON (YYYY-MM-DD), GENDER, NAME_ORIGINAL_SCRIPT,
    COMMENTS1, HAS_INTERPOL_LINK, INTERPOL_LINK,
    TITLE/VALUE, DESIGNATION/VALUE, NATIONALITY/VALUE, LIST_TYPE/VALUE ("UN List"),
    LAST_DAY_UPDATED/VALUE,
    INDIVIDUAL_ALIAS (QUALITY, ALIAS_NAME, NOTE),
    INDIVIDUAL_ADDRESS (STREET, CITY, STATE_PROVINCE, ZIP_CODE, COUNTRY, NOTE),
    INDIVIDUAL_DATE_OF_BIRTH (TYPE_OF_DATE, DATE, YEAR, FROM_YEAR, TO_YEAR, NOTE),
    INDIVIDUAL_PLACE_OF_BIRTH (CITY, STATE_PROVINCE, COUNTRY, NOTE),
    INDIVIDUAL_DOCUMENT (TYPE_OF_DOCUMENT, TYPE_OF_DOCUMENT2, NUMBER, ISSUING_COUNTRY,
                         DATE_OF_ISSUE, COUNTRY_OF_ISSUE, NOTE),
    SORT_KEY, SORT_KEY_LAST_MOD
  ENTITIES/ENTITY                                   (evidence: crawler and watchman)
    DATAID, VERSIONNUM, FIRST_NAME (the entity name), UN_LIST_TYPE, REFERENCE_NUMBER,
    LISTED_ON, NAME_ORIGINAL_SCRIPT, COMMENTS1, LAST_DAY_UPDATED/VALUE,
    ENTITY_ALIAS (QUALITY, ALIAS_NAME), ENTITY_ADDRESS (STREET, CITY, STATE_PROVINCE, ZIP_CODE, COUNTRY, NOTE)
```

- `DATE_OF_ISSUE`, `COUNTRY_OF_ISSUE`, `ZIP_CODE` and `NAME_ORIGINAL_SCRIPT` were not reached in the observed excerpt; they come from the crawler [S47].
- Reference numbers: prefix plus "The following letter "i" refers to individuals and "e" to entities" [S33] (pattern XXi.NNN, XXe.NNN). Missing data: "the letters "na" (not available) denote that the Committee has not yet been able to obtain it." [S33].

### 3.4 Hard fields

- Names: "Four separate name fields have been provided in order to accommodate the full range of naming conventions" [S33]; OpenSanctions maps first to `firstName`, last non-empty to `lastName` and joins all for `name` [S47]. Original script in `NAME_ORIGINAL_SCRIPT` (one string, no language tag).
- Aliases: "Good quality a.k.a.": "Alias(es) (also known as) sufficient for a positive identification."; "Low quality a.k.a.": "Alias(es) (also known as) probably insufficient alone for a positive identification." [S33]. `QUALITY` values seen: `Good`, `Low`, empty [S34]; the crawler also handles `a.k.a.` and `f.k.a.` and splits `ALIAS_NAME` on "; " [S47].
- DOB: "Date of birth, including alternative date(s) of birth." [S33]; `TYPE_OF_DATE` EXACT (DATE), APPROXIMATELY (YEAR), BETWEEN (FROM_YEAR, TO_YEAR) [S34]. Some dates carry a timezone suffix such as `YYYY-MM-DD-04:00` [S47].
- POB, nationality (`NATIONALITY/VALUE`, free text such as "Possibly ..." or "... (until 1991)") and documents (`TYPE_OF_DOCUMENT` in English, French or Spanish: "Passport", "Numéro de passeport", "Número de pasaporte", "National Identification Number") need lookups [S47].
- No company registration numbers as fields; they appear in `COMMENTS1` text.
- FtM: `Sanction:unscId` = REFERENCE_NUMBER, `program` = UN_LIST_TYPE, `listingDate` and `startDate` = LISTED_ON, `modifiedAt` = LAST_DAY_UPDATED [S47].

### 3.5 Terms of use

- UN Terms of Use: "The use of this web site constitutes agreement with the following terms and conditions:"; the UN "grants permission to Users to visit the Site and to download and copy the information, documents and materials" "for the User’s personal, non-commercial use, without any right to resell or redistribute them" "or to compile or create derivative works therefrom"; materials "“as is”, without warranty of any kind"; privileges and immunities "specifically reserved" [S35].
- UN Copyright: "None of the materials provided on this web site may be used, reproduced or transmitted, in whole or in part," "without permission in writing from the publisher." [S36].
- No terms specific to the Consolidated List were found; the list page says "Member States are obliged to implement the measures" and gives `sc-sanctionslists@un.org` for questions [S33].
- Decision: commercial reuse **unclear** (literal reading of the general terms: no). Options: (a) rely on the UK and EU copies of UN listings, which carry the UN reference and come under OGL and CC BY 4.0; (b) ask `sc-sanctionslists@un.org` for written permission; (c) ship the UN loader as user-run with a notice. NeonRadar ships code only, never UN data.

### 3.6 Pitfalls

- Signed redirect URL expires after one hour; never store it.
- `LAST_DAY_UPDATED` may be empty or hold several values [S34].
- `TITLE`, `DESIGNATION` and `NATIONALITY` are lists of `VALUE`; ADDRESS `ZIP_CODE` sometimes holds a province name (OpenSanctions moves non-numeric postcodes into region) [S47].
- Countries in free text (two countries joined by a slash, a country followed by an "as at" date, "Possibly" prefixes, former states such as the USSR) [S47].

## 4. EU Financial Sanctions Files (FSF, European Commission)

### 4.1 Downloads, access, cadence

- RSS `https://webgate.ec.europa.eu/fsd/fsf/public/rss` ("European Commission - External relations / Sanctions List") lists five files, all published 15 Oct 2026 about 10:20 GMT [S38]:
  - `XML (Based on XSD) - v1.1`: `https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw`
  - `XML (Based on XSD) - v1.0`: `.../files/xmlFullSanctionsList/content?token=dG9rZW4tMjAxNw`
  - `CSV - v1.1`: `.../files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw`
  - `CSV - v1.0`: `.../files/csvFullSanctionsList/content?token=dG9rZW4tMjAxNw`
  - `PDF - v1.0`: `.../files/pdfFullSanctionsList/content?token=dG9rZW4tMjAxNw`
- The public token works: XML 1.1 and CSV 1.1 were fetched today [S37][S39]. OpenSanctions: "The data is published in a password-protected area but the generated download links can be used to programmatically update the material." [S47]. The FSF manual says crawler URLs include a token that is the logged-in user's ID, offered after EU Login [S40]; the public token is unpadded base64 for the fixed string `token-2017`, so the Commission could revoke it: keep the token configurable (watchman does: `EU_CSL_TOKEN`) [S52].
- OpenSanctions: "The webgate endpoint generates the ~25MB XML on the fly and takes over a minute to serve it. It intermittently answers with bursts of HTTP 500" (5 retries, backoff factor 3) [S47].
- Version: root `generationDate` (ISO 8601 with offset) and numeric `globalFileId` [S37]; CSV column `fileGenerationDate` (DD/MM/YYYY) [S39]; RSS `pubDate` [S38]; "Each file comes with its checksum" [S40]. The values read through WebFetch did not match the RSS date (UNVERIFIED observation): compare `globalFileId` and a content hash too.
- Most complete: XML 1.1 (OpenSanctions uses it); differences between 1.0 and 1.1 are UNVERIFIED.

### 4.2 Size and counts

- OpenSanctions `eu_fsf`: Person 4,398; Organization 1,728; Vessel 2; Address 2,128; 6,128 targets; `source.xml` 24.57 MB [S48]. Assertion bounds: Person 3,400 to 8,000, Organization 970 to 2,300 [S47].

### 4.3 XML 1.1 structure (observed [S37], plus crawler [S47])

```
export @generationDate @globalFileId                    (xmlns http://eu.europa.ec/fpi/fsd/export)
  sanctionEntity @designationDetails @unitedNationId @euReferenceNumber @logicalId @designationDate
    remark
    regulation @regulationType @organisationType @publicationDate @entryIntoForceDate
               @numberTitle @programme @logicalId
      publicationUrl
    subjectType @code (person | enterprise) @classificationCode (P observed)
    nameAlias @firstName @middleName @lastName @wholeName @function @gender @title
              @nameLanguage @strong @regulationLanguage @logicalId
      regulationSummary @regulationType @publicationDate @numberTitle @publicationUrl
      remark
    citizenship @region @countryIso2Code @countryDescription @regulationLanguage @logicalId
    birthdate @circa @calendarType @city @zipCode @birthdate @dayOfMonth @monthOfYear @year
              @yearRangeFrom @yearRangeTo @region @place @countryIso2Code @countryDescription
    identification @diplomatic @knownExpired @knownFalse @reportedLost @revokedByIssuer
                   @issuedBy @issueDate @latinNumber @nameOnDocument @number @region
                   @identificationTypeCode @identificationTypeDescription
                   @countryIso2Code @countryDescription @logicalId
      remark, regulationSummary
    address @street @poBox @city @place @zipCode @region @countryIso2Code @countryDescription
      contactInfo @key (PHONE | FAX | EMAIL | WEB) @value, remark          (evidence: crawler)
```

- `euReferenceNumber` pattern `EU.N+.N+`; `nameLanguage` two-letter codes (FR, ES, FI observed) [S37][S39]. `designationDate`, `issueDate`, the address attributes and `contactInfo` come from the crawler (not reached in the excerpt) [S47].
- `identificationTypeCode` values handled by OpenSanctions: `passport`, `id`, `other`, `tradelic`, `ssn`, `birthcert`, `nationcert`, `travelcardid`, `electionid`, `residentperm`, `drivinglicence`, `NRN`, `unssn`, `swiftbic`, `imo`, `regnumber`, `fiscalcode`, `taxid`, `euvat` [S47]. No dedicated LEI type.

### 4.4 CSV 1.1

- 118 columns, `;` delimiter, no quoting, UTF-8 with BOM, header on line 1; one entity spans several rows (one per alias, birth date, document, citizenship or address) [S39].
- First columns exactly: `fileGenerationDate`, `Entity_LogicalId`, `Entity_EU_ReferenceNumber`, `Entity_UnitedNationId`, `Entity_DesignationDate`, `Entity_DesignationDetails`, `Entity_Remark`, `Entity_SubjectType`, `Entity_SubjectType_ClassificationCode`, `Entity_Regulation_Type`, `Entity_Regulation_OrganisationType`, `Entity_Regulation_PublicationDate`, `Entity_Regulation_EntryIntoForceDate`, `Entity_Regulation_NumberTitle`, `Entity_Regulation_Programme`, `Entity_Regulation_PublicationUrl`, `NameAlias_LastName`, `NameAlias_FirstName`, `NameAlias_MiddleName`, `NameAlias_WholeName`, `NameAlias_NameLanguage`, `NameAlias_Gender`, `NameAlias_Title`, `NameAlias_Function`, `NameAlias_LogicalId`, `NameAlias_RegulationLanguage`, `NameAlias_Remark`, then seven `NameAlias_Regulation_*` columns, then the `Address_*`, `BirthDate_*`, `Identification_*` and `Citizenship_*` groups [S39]. Group members read today (full column names inferred from the prefix pattern, UNVERIFIED): BirthDate group BirthDate, Day, Month, Year, YearRangeFrom, YearRangeTo, Circa, CalendarType, ZipCode, Region, Place, City, CountryIso2Code, CountryDescription; Identification group Number, Diplomatic, KnownExpired, KnownFalse, ReportedLost, RevokedByIssuer, IssuedBy, IssuedDate, ValidFrom, ValidTo, LatinNumber, NameOnDocument, TypeCode, TypeDescription, Region, CountryIso2Code, CountryDescription [S39].
- No `NameAlias_Strong` column was seen: the CSV loses alias strength. Use XML.

### 4.5 Hard fields

- Names: `wholeName` always; first, middle and last when known; translations of organisation names into many EU languages. OpenSanctions keeps names with no language or in eng, zho, rus, fas, ara as `name` and moves other languages to `alias` when such a name exists [S47].
- Alias quality: `strong="false"` means weak; remarks also carry "low quality" and "good quality" (with typos such as "lo quality" and "god quality") [S47].
- DOB: full `birthdate` and/or partial `year`, `monthOfYear`, `dayOfMonth`, `circa` true or false, `yearRangeFrom` and `yearRangeTo`, `calendarType` (GREGORIAN observed); place of birth on the same element [S37][S47].
- Nationality: `citizenship` with ISO2 code and description; "UNKNOWN" description; code `CS` (Serbia and Montenegro) mapped to RS by OpenSanctions [S47].
- Documents: `number` and `latinNumber`, status flags `knownFalse`, `knownExpired`, `reportedLost`, `revokedByIssuer`, `diplomatic` [S37].
- FtM: `Sanction:authorityId` = euReferenceNumber, `unscId` = unitedNationId, `program` = regulation `programme`, `sourceUrl` = `publicationUrl`, `reason` = `numberTitle`, `startDate` = earliest of `designationDate` and `entryIntoForceDate`, `listingDate` = `publicationDate`; one Sanction per `regulation` [S47].

### 4.6 Licence

- Decision 2011/833/EU, Article 4: "All documents shall be available for reuse:" "(a) for commercial or non-commercial purposes under the conditions laid down in Article 6;" "(b) without charge," "(c) without the need to make an individual application"; Article 6 conditions may include "the obligation for the reuser to acknowledge the source of the documents;", "the obligation not to distort the original meaning or message of the documents;" and "the non-liability of the Commission for any consequence stemming from the reuse."; Article 2 excludes "documents for which the Commission is not in a position to allow their reuse" [S41].
- February 2019 decision (C(2019) 1655, reference read from the decision's URL): CC BY 4.0 "for all content" and CC0 1.0 for raw data, metadata or comparable documents [S43][S44].
- Commission legal notice: "content owned by the EU on this website is licensed under the" "Creative Commons Attribution 4.0 International (CC BY 4.0) licence."; "reuse is allowed, provided appropriate credit is given and changes are indicated." [S42].
- FSF disclaimer (from the FSF website, as quoted by OpenSanctions and in the data.europa.eu record): "Only the information published in the Official Journal of the EU is deemed authentic." [S47][S70].
- No licence statement attached to the FSF files themselves was found (the FSF interface sits behind EU Login, and the data.europa.eu record for the dataset, issued 2021-12-03, has no licence and no distributions): UNVERIFIED [S70]. Decision: commercial reuse allowed with attribution, for example "Source: European Commission, Financial Sanctions Files (FSF), reused under the Commission reuse policy (Decision 2011/833/EU)".

### 4.7 EU Sanctions Map is not the data source

- The map "is a visualisation of EU sanctions policy" and "includes a broader set of policies and entities than the EU consolidated sanctions list"; it "mostly includes the same data as the EU Consolidated List"; Annex IV entities "are subject to specific economic prohibitions" but "are not subject to an asset freeze", so they are not in the consolidated list [S46].
- Consequence: the FSF covers financial sanctions (asset freezes) only; sectoral lists such as Annex IV need another loader later.

### 4.8 Pitfalls

- Slow on-the-fly generation and HTTP 500 bursts: generous timeouts and retries [S47].
- Entries without `euReferenceNumber` need `logicalId` as a fallback ID [S47].
- `subjectType` misclassifications (vessels as enterprise, an organisation coded person) handled by overrides [S47].
- Titles and functions enumerate as "(a) ... (b) ..." and need splitting [S47].
- E-mail and phone values with spaces, "and", several addresses per field [S47].

## 5. OpenSanctions crawlers: paths, licences and what they handle

- Paths (commit fc8e631, 2026-10-17) [S47]: UK `datasets/gb/fcdo_sanctions/crawler.py` and `gb_fcdo_sanctions.yml`; OFAC `datasets/us/ofac/ofac_advanced.py` (entry point for both), `us_ofac_sdn.yml`, `us_ofac_cons.yml`; UN `datasets/_global/un_sc_sanctions/crawler.py`, `un_sc_sanctions.yml`, helper `zavod/zavod/shed/un_sc.py`; EU `datasets/eu/fsf/crawler.py`, `eu_fsf.yml`, helper `zavod/zavod/shed/fsf.py`. PEP references: `datasets/gb/commons/`, `datasets/gb/lords/`, `datasets/_wikidata/peps/`.
- Code licence: LICENSE is MIT ("Copyright (c) 2023-2026 OpenSanctions Datenbanken GmbH", "Copyright (c) 2015-2022 Friedrich Lindenberg", "Copyright (c) 2018-2019 Journalism Development Network, Inc.") with the condition "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software." [S47].
- COPYRIGHT.md: "All source code is licensed under the MIT License"; "Crawler code and configuration are MIT-licensed."; "Data files produced by OpenSanctions are licensed under [CC BY-NC 4.0] ... They are **not** covered by the MIT License."; "OpenSanctions asserts database rights, and copyright where applicable, in the OpenSanctions data as a collection. This grant reaches only as far as our own rights do."; "Some files under `datasets/` are copies of material published by someone else ... Rights in those remain with their publisher. We grant no license to them" [S47].
- So the CC BY-NC licence attaches to OpenSanctions' published datasets, not to the government lists. OpenSanctions' own FAQs: "Commercial customers are not paying for access to a file."; "Information published by governments and public institutions, however, is considered fair game." [S50]. Phase 1: "Any use inside a for-profit business requires a data license." applies to OpenSanctions data only [P1].
- Compatibility: Apache: "Licenses in Category A may be included in Apache Software Foundation products." and the list includes "MIT/X11" [S51]. Analysis: porting or copying crawler logic into Apache-2.0 NeonRadar is fine if the MIT notice is kept (a `THIRD_PARTY_NOTICES` file plus a header comment in each derived module). Do not copy YAML lookups: although "configuration" is MIT, they embed real e-mails, company names and registration strings of designated parties, which conflicts with the no-real-records rule and with data minimisation; build NeonRadar's own patch tables.
- What the crawlers handle (beyond the per-list pitfalls above): language lookups for non-Latin scripts; weak alias and abbreviation heuristics; date format lists and patches; country and address normalisation; regex extraction of Russian INN, OGRN, KPP, BIK, SWIFT and TIN; crypto wallet extraction; parent, subsidiary and vessel owner entities with `Ownership` edges; schema overrides; assertion ranges per schema and property fill rates (`birthDate`, `nationality`, `imoNumber`, `program`) that catch silent breakage [S47]. The fill-rate assertions are a good pattern for NeonRadar's loader tests.

## 6. Cross-list linking

| Link | Field(s) | Determinism |
|---|---|---|
| UK to UN | UK `UNReferenceNumber` (CSV "UN Reference Number") = UN `REFERENCE_NUMBER` | deterministic [S3][S4][S34] |
| EU to UN | EU `sanctionEntity@unitedNationId` (CSV `Entity_UnitedNationId`) = UN `REFERENCE_NUMBER` | deterministic; empty in all records seen today, so check fill rate [S37][S39][S47] |
| UK internal | `OFSIGroupID` shared by several `UniqueID`s of one person | deterministic for pre-2026 designations [S2][S3] |
| UK to old OFSI data | `OFSIGroupID` = OFSI `Group ID` | deterministic [S8] |
| OFAC internal | UID = `DistinctParty@FixedRef` = `Profile@ID` = `SanctionsEntry@ProfileID` = CSV `ent_num` | deterministic [S20][S23][S24] |
| OFAC to anyone | no UN or foreign list reference in the data | none (evidence: crawler) [S47] |
| Vessels | IMO number: UK `IMONumber`, OFAC ID document "Vessel Registration Identification" or feature, EU `identification@identificationTypeCode="imo"` | deterministic after normalising "IMO NNNNNNN" [S4][S47] |
| Persons | passport or national ID number plus issuing country; DOB plus name as support only | strong but not unique (numbers reused across countries, OCR errors) |
| Companies | LEI (OFAC "Legal Entity Number"), registration number plus jurisdiction, SWIFT/BIC, crypto addresses | strong |

- FtM: put every list's UN reference into `Sanction:unscId`, the list's own key into `Sanction:authorityId`, and merge only on exact `unscId` or exact IMO; feed everything else to the probabilistic matcher.
- UN `DATAID` is the UN's internal record ID; use `REFERENCE_NUMBER` for joins (analysis).

### 6.1 FtM mapping summary (as OpenSanctions does it [S47], with NeonRadar suggestions marked)

| FtM | UK (XML) | OFAC (advanced) | UN | EU (XML 1.1) |
|---|---|---|---|---|
| target schema | Individual: Person; Entity: Organization (Company when a parent is given); Ship: Vessel | PartyType Individual: Person; Entity: Organization; Vessel: Vessel; Aircraft: Airplane | INDIVIDUAL: Person; ENTITY: LegalEntity | subjectType person: Person; enterprise: Organization |
| `Sanction:authorityId` | `UniqueID`, `OFSIGroupID` | `SanctionsEntry@ProfileID` (UID) | (none; suggestion: `DATAID`) | `euReferenceNumber` |
| `Sanction:unscId` | `UNReferenceNumber` | none | `REFERENCE_NUMBER` | `unitedNationId` |
| `Sanction:program` and `programId` | `RegimeName` (lookup to GB-...) | SanctionsMeasure Comment of type Program (tag such as an executive order programme) | `UN_LIST_TYPE` | `regulation@programme` |
| `Sanction:startDate` | `DateDesignated` | not used by OpenSanctions; suggestion: `EntryEvent/Date` | `LISTED_ON` | min(`designationDate`, `entryIntoForceDate`) |
| `Sanction:listingDate` | (none) | listing-date features | `LISTED_ON` | `regulation@publicationDate` |
| `Sanction:reason` | `UKStatementofReasons` | `EntryEvent@LegalBasisID` text | (none) | `regulation@numberTitle` |
| `Sanction:sourceUrl` | (none) | (entity) `sanctionssearch.ofac.treas.gov/Details.aspx?id=` plus UID | (none) | `publicationUrl` |
| `Sanction:authority` | `DesignationSource` | (constant) | (constant) | (constant) |
| other | `provisions` from `SanctionsImposed`; `modifiedAt` from `LastUpdated` | `provisions` from SanctionsMeasure types | `modifiedAt` from `LAST_DAY_UPDATED` | `modifiedAt` from `entryIntoForceDate` |

- Topics: `sanction` on every designated entity and on derived crypto wallets [S47]; `role.pep` only from PEP sources. Do not tag stub owner organisations created from free-text names with `sanction`.
- Suggested build effort (analysis, for the eight-day phase): UN 0.5 day (small, clean); EU 0.75 day; UK 1 day (XML plus CSV fallbacks, free-text identifiers); OFAC advanced 1.5 days (reference tables, features, relationships, two-pass parse); cross-list linker and fill-rate assertions 0.5 day. Each loader ships with synthetic fixtures that copy the structure with invented values.

## 7. PEP sources without OpenSanctions

### 7.1 Legal scope

- MLR 2017 reg 35(12)(a): "politically exposed person" means an individual entrusted with prominent public functions, "other than as a middle-ranking or more junior official"; (12)(d) "domestic PEP" means one entrusted with prominent public functions by the United Kingdom [S55].
- Reg 35(14): "(a) heads of state, heads of government, ministers and deputy or assistant ministers"; "(b) members of parliament or of similar legislative bodies"; "(c) members of the governing bodies of political parties"; "(d) members of supreme courts, of constitutional courts" or similar; "(e) members of courts of auditors or of the boards of central banks"; "(f) ambassadors, charges d'affaires and high-ranking officers in the armed forces"; "(g) members of the administrative, management or supervisory bodies of State-owned enterprises"; "(h) directors, deputy directors and members of the board or equivalent function of an international organisation" [S55].
- Family members (12)(b): spouse or civil partner, children and their spouses or civil partners, parents; known close associates (12)(c): joint beneficial ownership of a legal entity or arrangement, "any other close business relations with a PEP", sole beneficial ownership of an entity set up for the PEP [S55].
- After leaving office: measures "for a period of at least 12 months after the date on which that person ceased" [S55]. Reg 35(3A) (inserted 10 Jan 2024 by S.I. 2023/1371): for a domestic PEP "the starting point for the assessment is that the customer or potential customer presents a lower level of risk" [S55]. legislation.gov.uk lists outstanding changes from S.I. 2026/621 (new reg 34A) not yet applied: re-check before the spec is final [S55].
- FATF glossary: foreign PEPs are entrusted with prominent public functions by a foreign country, for example "Heads of State or of government, senior politicians, senior government, judicial or military officials" (the list goes on to senior executives of state-owned corporations and important political party officials: paraphrase, the rest of the sentence was not quoted today); "Domestic PEPs are individuals who are or have been entrusted domestically with prominent public functions,"; international organisation PEPs; "The definition of PEPs is not intended to cover middle ranking or more junior individuals in the foregoing categories." [S57].
- FCA FG25/3 (7 July 2025, revised 15 July 2025): similar legislative bodies include "the Scottish Parliament and Scottish Government, the Northern Ireland Assembly and Northern Ireland Executive" "and the National Assembly for Wales and the Welsh Government," "where such bodies have some form of executive decision-making powers."; "It does not include local government in the UK"; UK senior judges: "only judges of the Supreme Court"; civil servants below "Permanent or Deputy Permanent Secretary" normally not PEPs; armed forces from "Vice Admiral, Lieutenant General or Air Marshal"; party governing bodies only for parties represented in a national or supranational parliament; SOEs where the state holds "greater than 50%"; a Member of the House of Lords is named as already meeting the definition [S58].

### 7.2 (a) UK Parliament Members API

- Base `https://members-api.parliament.uk/`; OpenAPI `https://members-api.parliament.uk/swagger/v1/swagger.json` ("Members API", v1, no licence field) [S53].
- Useful endpoints [S53]: `GET /api/Members/Search` (parameters `Name`, `Location`, `PostTitle`, `PartyId`, `House`, `ConstituencyId`, `NameStartsWith`, `Gender`, `MembershipStartedSince`, `MembershipEnded.MembershipEndedSince`, `MembershipEnded.MembershipEndReasonIds`, `MembershipInDateRange.WasMemberOnOrAfter`, `MembershipInDateRange.WasMemberOnOrBefore`, `MembershipInDateRange.WasMemberOfHouse`, `IsEligible`, `IsCurrentMember`, `PolicyInterestId`, `Experience`, `skip`, `take`); `GET /api/Members/SearchHistorical`; `GET /api/Members/{id}`; `GET /api/Members/{id}/Biography` (`representations`, `electionsContested`, `houseMemberships`, `governmentPosts`, `oppositionPosts`, `otherPosts`, `partyAffiliations`, `committeeMemberships`; each item `name`, `startDate`, `endDate`, `house`, `id`, `additionalInfo`, `additionalInfoLink`); `GET /api/Members/History`; `GET /api/Posts/GovernmentPosts`; `GET /api/Posts/OppositionPosts`; `GET /api/Posts/SpeakerAndDeputies/{forDate}`; `GET /api/Members/{id}/RegisteredInterests`.
- OpenSanctions usage [S47]: `/api/Members/Search?House=Commons` and `?House=2` (Lords), "The API caps `take` at 20", fields `latestHouseMembership.membershipStartDate`, `membershipEndDate`, `membershipFrom`, `nameDisplayAs`, `nameFullTitle`, `nameAddressAs`, `nameListAs`, `gender`, `latestParty.name`; biography for government posts; assertions at least 770 Commons and 750 Lords persons. Bishops appear only by their see name, so successive holders share a name.
- Licence: "Use of Parliamentary material is governed by the terms of the Open Parliament Licence." (which "applies to material made available in hard copy or electronically"; photographic images excluded) [S54]. OPL v3.0: "You are encouraged to use and re-use the information that is available under this licence freely and flexibly"; you may copy, publish, distribute, transmit and adapt the information and exploit it commercially and non-commercially (paraphrase of the grant); attribution "Contains Parliamentary information licensed under the Open Parliament Licence v3.0."; not covered: "personal data in the information;" [S54]. No rate limit or key documented (UNVERIFIED).
- Gives: current and former MPs and Lords, constituencies, parties, ministerial and shadow posts with dates. Does not give: family members or associates, devolved legislatures, judges, ambassadors, military, SOE boards.

### 7.3 (b) Wikidata

- Licence: "All structured data in the main, property and lexeme namespaces is made available under the Creative Commons CC0 License" [S59].
- Extraction difficulty: high. OpenSanctions' MIT crawler discovers positions per territory by usage (`?position wdt:P1001|wdt:P17 wd:Q...` with human holders via `wdt:P39`, or `wdt:P1308` officeholder), plus positions held by citizens with occupation politician (Q82955), diplomat (Q193391) or judge (Q16533); it needs a curated PEP categorisation of positions and comments that Wikidata has a "chaotic ontology of position classes"; occupancy dates come from the P39 claim's qualifiers P580 (start) and P582 (end), and abolished positions are dropped via P576/P582 (`zavod/zavod/shed/wikidata/position.py`) [S63]. Its assertions expect at least 170,000 persons and 10,000 positions [S63].
- Online only: query.wikidata.org has "a hard query deadline configured which is set to 60 seconds"; "One client (user agent + IP) is allowed 60 seconds of processing time each 60 seconds"; "One client is allowed 30 error queries per minute" (as quoted by the Wikimedia R client documentation) [S61]. OpenSanctions sets a 90 s client timeout because large-territory queries run "close to the query service's own 60s execution budget" [S63]. The WMF "finalized the split of Wikidata into two" graphs on 20 January 2026 (scholarly articles moved to a separate endpoint) and plans to "migrate Wikidata's SPARQL engine to another database by summer 2027" [S60].
- Offline: only via the full dumps; a mirror listing showed `latest-all.json.gz` at 127 GB in June 2024 [S62] (current size UNVERIFIED). Filtering a dump is a multi-hour job, not suitable for an eight-day phase.
- RCAs: Wikidata relatives (P22 father, P25 mother, P26 spouse, P40 child, P3373 sibling) could seed `Family` edges, but OpenSanctions removed automatic `role.rca` tagging of all relatives [P1]. Defer.

### 7.4 (c) Other official, openly licensed UK sources

- GOV.UK ministers: content API `https://www.gov.uk/api/content/government/ministers` (`document_type` `ministers_index`, `links.ordered_cabinet_ministers`, `ordered_also_attends_cabinet`, role appointments with `current`, `started_on`, `ended_on`) under the GOV.UK OGL footer; current only [S1][S69].
- Scottish Parliament open data portal `https://data.parliament.scot/`: "available under an open government license" (no version stated) [S64]; Northern Ireland Assembly web services: "under terms described in the Open Government Licence" [S65]. Senedd data: not checked (UNVERIFIED). These cover devolved legislators that FG25/3 includes [S58].
- Judges, ambassadors, senior military, Bank of England boards and SOE boards have no single open machine-readable UK list found; Wikidata is the practical source.

### 7.5 Recommendation and effort (eight-day phase)

- Phase 2: load the Members API into FtM (`Person` with topics `role.pep`; `Position` with `gov.national` plus `gov.legislative` or `gov.executive`; `Occupancy` with `startDate`, `endDate`, `status`), covering MPs and Lords who held office in the last N years (configurable; at least 12 months after leaving office per reg 35(9), longer by policy). Effort 1 to 1.5 days including pagination at 20 per page, one biography call per member (estimate: 1,500 to 2,500 calls a run, throttled), recorded synthetic fixtures (invented names), OPL attribution and a CLI notice that the data is personal data.
- Stretch (only if the ownership graph work is ahead): a Wikidata loader for a fixed, reviewed list of position QIDs (heads of state and government, ministers, legislators, supreme court judges, central bank governors, ambassadors) with cached query results; 1.5 to 2 days. NeonRadar may port OpenSanctions' `datasets/_wikidata/peps` logic under MIT.
- Later: devolved legislatures (about 0.5 day each), RCAs, SOE boards.

## 8. Data protection (analysis, not legal advice)

- Sanctions list rows are personal data of designated persons (names, DOB, passports, addresses); PEP rows are personal data of office holders. The OGL and the OPL both exclude "personal data" from the licence grant [S11][S54], so licences settle copyright and database right only; UK GDPR applies to whoever runs a loader, including Robotat during development.
- Government purpose: OFSI's privacy notice describes "the publication of personal data relating to persons subject to financial sanctions" "to assist screening and implementation of financial sanctions"; OFSI itself relies on Article 6(1)(e) and, for criminal offence data, "section 10(5) of the DPA" with "paragraphs 5 and 6 of Part 2 of Schedule 1" (last updated 28 March 2024; it still refers to the closed Consolidated List) [S12].
- No ICO guidance specific to sanctions list screening was found (searches on ico.org.uk topics and the web, 2026-10-18).
- ICO on criminal offence data (page dated 9 September 2025, under review because of the Data (Use and Access) Act): covers "the alleged commission of offences by the data subject"; "related security measures" are not defined but it "is likely to include personal data about penalties, conditions or restrictions placed on an individual"; civil orders usually fall outside the term unless breaching them can "carry a criminal sanction for non-compliance." [S66]. Analysis: an asset freeze or travel ban is an administrative restriction whose breach is a criminal offence, and UK Statements of Reasons often describe alleged criminal conduct, so treat list data as possibly Article 10 data.
- Conditions available (ICO): "Preventing or detecting unlawful acts" (10), "Regulatory requirements relating to unlawful acts and dishonesty" (12), "Preventing fraud" (14), "Suspicion of terrorist financing or money laundering" (15); an "appropriate policy document" is needed for some conditions [S67]. Paragraph 15 is narrow: it covers processing "necessary for the purposes of making a disclosure in good faith" under section 21CA TA 2000 or section 339ZB POCA 2002 [S68].
- MLR 2017 reg 41: personal data obtained under the Regulations "may only be processed for the purposes of preventing money laundering, terrorist financing or proliferation financing"; reg 41(7) makes such processing a task "carried out in the public interest" [S56].
- Design consequences for the spec: data minimisation (make free-text `reason` and `notes` optional, off by default); keep delisted records only as long as policy requires; refresh often enough for accuracy; no real list or PEP data in the repository, CI or demo fixtures; document that each deploying organisation needs its own lawful basis and, where relevant, an appropriate policy document.

## 9. Name matching guidance from the authorities

- OFAC FAQ 246: besides exact matches "(when the match threshold slider bar is set to 100%)", the tool "can also provide a broader set of results using fuzzy logic." "This logic uses character and string matching as well as phonetic matching." [S27].
- FAQ 247: "The slider bar defaults to a score of 100, which indicates an exact match." "Lower scores indicate potential matches." [S27].
- FAQ 248 ("How do I use the Minimum Name Score field and score slider bar?"): "A value of 100 will return only names that exactly match the characters entered into the name field."; "A value of 50 will return all names that are deemed to be 50% similar based upon the matching logic of the search tool." [S27].
- FAQ 249: candidates are pre-filtered "based on the first letter of input search terms" and "at least 50% or more similar based on edit distance"; "The two algorithms are Jaro-Winkler, a string difference algorithm, and Soundex, a phonetic algorithm."; the tool "returns the higher of the two scores in the Score column." [S27].
- FAQ 250: "OFAC cannot make such a recommendation because each search has its own unique set of facts surrounding it." [S27]. FAQ 892: the 2021 upgrade added an algorithm, so results changed; users should repeat baseline tests [S27].
- FAQ 5 (updated 9 September 2026): review the full entry; "Consider how much of the listed person's information matches against information for the party"; "does only the first or last name match the listed name or aliases?"; "Does the party to your transaction or activity have a different date of birth, identification number, or nationality?"; an address match alone may not suffice; OFAC does not confirm matches [S28].
- OFSI: "This is known as a name match." and it "does not necessarily mean that the individual, entity or ship you are dealing with is the same one as is on the list."; "If the individual, entity or ship you are dealing with matches all the information on the list, this is likely to be a target match."; a close match with differences should be raised: "You should contact OFSI immediately." [S10].
- UK search tool guide (16 Oct 2026): fuzzy search "is off by default"; 3 to 4 character terms match "with 1 character different", 5 or more "with up to 2 characters different"; ranking exact, partial, fuzzy, then "Relevance = TF × IDF"; quotation marks risk "a 'false negative' result"; "Always search unfiltered first." [S9].
- UN: Good quality a.k.a. "sufficient for a positive identification"; Low quality "probably insufficient alone for a positive identification." [S33].
- EU best practices (11623/24): "as many specific identifiers as possible should be available at the moment of identification"; "ICAO-standard transliteration should be present at all times and in all language versions."; cooperation "to refute a positive match that is due to the lack of sufficient identifiers"; "the limited availability of identifiers cannot justify dealings with a designated person or entity." [S45].
- Spec consequence: weak aliases (UN Low, UK "Low quality a.k.a", OFAC `LowQuality`, EU `strong="false"`) must never produce a match on their own; a confirmed match needs a name or strong alias plus at least one corroborating identifier (DOB, ID number, nationality).

## 10. Overlap between the lists and data quality

- Overlap: no published figure found from the authorities or OpenSanctions (UNVERIFIED). Expected shape (analysis): the UK and EU implement every UN regime, so nearly all 1,010 UN listings should appear in both with the UN reference (UK `DesignationSource` UN or both); OFAC implements UN listings under its own programmes without a UN key. The spec can compute overlap at load time: UK and EU rows with a non-empty `unscId` joined to UN `REFERENCE_NUMBER`, plus IMO joins for vessels.
- Quality issues seen in code and files [S3][S37][S39][S47]: literal placeholder dates (`dd/mm/YYYY`, `00/00/YYYY`); free-text registration numbers; malformed e-mails and websites; non-standard country names; vessels and organisations misclassified; empty `unitedNationId` in the EU rows seen; several Unique IDs per UK person; owners and parents given only as names (OpenSanctions creates name-keyed `Organization` stubs: never merge these on name alone); OFAC relationships in reversed direction; the UN's mixed-language document types.
- OpenSanctions' description of the old OFSI list: "The UK sanctions list suffers from very bad data quality as the result of manual data processing and inappropriate data structures used by the XML files." [S47] (opinion, about the closed list).

## Sources

All checked 2026-10-18.

- [P1] NeonRadar Phase 1 note `neonradar-phase1/kit/research/sources-opensanctions-ftm-icij.md`, sections A.2 and A.4 (local file).
- [S1] GOV.UK, The UK Sanctions List (publication page, attachments, change history, footer): https://www.gov.uk/government/publications/the-uk-sanctions-list
- [S2] GOV.UK, Moving to a single list for UK sanctions designations: 28 January 2026: https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026 (also https://www.gov.uk/government/publications/uk-sanctions-list-change-in-format)
- [S3] GOV.UK, Format guide for the UK Sanctions List: https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list and content API https://www.gov.uk/api/content/guidance/format-guide-for-the-uk-sanctions-list
- [S4] FCDO, UK Sanctions List XML (first records only): https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml ; schema (not readable): https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/SanctionsListSchema-4.33.3.xsd
- [S5] FCDO, UK Sanctions List HTML (first records only): https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.html
- [S7] GOV.UK, [Withdrawn] Financial sanctions consolidated list of targets: https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets
- [S8] OFSI, Consolidated List Format Guide (28/02/2022): https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1057611/280222_Consolidated_List_Format_Guide.pdf
- [S9] GOV.UK, UK Sanctions List search tool: user guide: https://www.gov.uk/government/publications/the-uk-sanctions-list/uk-sanctions-list-search-tool-user-guide
- [S10] OFSI, UK financial sanctions general guidance: https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance
- [S11] Open Government Licence v3.0, SPDX text copy: https://raw.githubusercontent.com/spdx/license-list-data/main/text/OGL-UK-3.0.txt (official page https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ returned a server error)
- [S12] OFSI privacy notice: https://www.gov.uk/government/publications/office-of-financial-sanctions-implementation-privacy-notice/office-of-financial-sanctions-implementation-privacy-notice
- [S13] OFAC, Sanctions List Service: https://ofac.treasury.gov/sanctions-list-service
- [S14] OFAC Recent Actions, 6 May 2024 (SLS launch): https://ofac.treasury.gov/recent-actions/20240506_33
- [S15] OFAC technical notice, 16 May 2024 (403 errors, URL pattern): https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/ofac-technical-actions-in-reverse-chronological-order/20240516_44
- [S16] OFAC Recent Actions, 7 May 2024 (namespace change): https://ofac.treasury.gov/recent-actions/20240507_44
- [S17] OFAC Project Open Data catalogue: https://ofac.treasury.gov/system/files/2026-08/data.json
- [S18] data.gov, SDN List Enhanced XML File Standard: https://catalog.data.gov/dataset/specially-designated-nationals-sdn-list-enhanced-xml-file-standard and harvest record https://catalog.data.gov/harvest_record/9eb6352a-5e4d-4456-91d7-8e77e498476f/raw
- [S19] data.gov, Specially Designated Nationals (SDN) and Blocked Persons List: https://catalog.data.gov/dataset/specially-designated-nationals-sdn-and-blocked-persons-list
- [S20] OFAC, SDN data specification (dat_spec.txt): https://ofac.treasury.gov/media/29976/download?inline
- [S21] OFAC, Tutorial on the use of list-related legacy flat files: https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/tutorial-on-the-use-of-list-related-legacy-flat-files
- [S22] OFAC, FAQ on the advanced sanctions list standard: https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/frequently-asked-questions-on-advanced-sanctions-list-standard
- [S23] OFAC, SDN Advanced Sanctions Data Model XML Explanatory Notes (last updated 1/12/2015): https://ofac.treasury.gov/media/10391/download?inline
- [S24] OFAC, advanced XML schema (legacy URL): http://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xsd
- [S25] OFAC technical actions: https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/ofac-technical-actions-in-reverse-chronological-order ; 2005 header notice https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/ofac-technical-actions-in-reverse-chronological-order/recent-ofac-actions-5252005 ; 2017 date notice https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/ofac-technical-actions-in-reverse-chronological-order/date-formatting-change-in-the-sdnxml-file
- [S26] OFAC FAQs topic 1641 (79, 80, 81, 83, 88, 89, 90, 105, 422, 1031): https://ofac.treasury.gov/faqs/topic/1641 ; https://ofac.treasury.gov/faqs/88 ; https://ofac.treasury.gov/faqs/1031
- [S27] OFAC FAQs 246, 247, 248, 249, 250, 892: https://ofac.treasury.gov/faqs/246 ; https://ofac.treasury.gov/faqs/247 ; https://ofac.treasury.gov/faqs/248 ; https://ofac.treasury.gov/faqs/249 ; https://ofac.treasury.gov/faqs/250 ; https://ofac.treasury.gov/faqs/892
- [S28] OFAC FAQ 5: https://ofac.treasury.gov/faqs/5
- [S29] OFAC, Revised Guidance on Entities Owned by Persons Whose Property and Interests in Property Are Blocked (13 August 2014): https://ofac.treasury.gov/media/6186/download
- [S30] OFAC FAQs 398 to 402 (topic 1521): https://ofac.treasury.gov/faqs/topic/1521
- [S31] OFAC, Guidance on Sham Transactions and Sanctions Evasion (31 March 2026): https://ofac.treasury.gov/media/935441/download?inline
- [S32] vi-malysh/ofac-vessels (third-party parser of SDN_ADVANCED.XML and SDN_ENHANCED.XML): https://github.com/vi-malysh/ofac-vessels
- [S33] UN Security Council, United Nations Security Council Consolidated List: https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list
- [S34] UN Consolidated List XML: https://scsanctions.un.org/resources/xml/en/consolidated.xml and https://scsanctions.un.org/resources/xml/en/name/consolidated.xml (302 redirects), content read at https://unsolprodfiles.blob.core.windows.net/publiclegacyxmlfiles/EN/consolidatedLegacyByPRN.xml
- [S35] United Nations, Terms of Use: https://www.un.org/en/about-us/terms-of-use
- [S36] United Nations, Copyright: https://www.un.org/en/about-us/copyright
- [S37] European Commission FSF, XML 1.1 (first records only): https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw
- [S38] European Commission FSF RSS: https://webgate.ec.europa.eu/fsd/fsf/public/rss
- [S39] European Commission FSF, CSV 1.1 (header and first rows): https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw
- [S40] FSF Stakeholders' User Manual: https://circabc.europa.eu/d/a/workspace/SpacesStore/9cf02a9e-7604-4178-a21d-d0b6bdcb4114/MA_FSF_EN.pdf
- [S41] Commission Decision 2011/833/EU on the reuse of Commission documents: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32011D0833
- [S42] European Commission, Legal notice: https://commission.europa.eu/legal-notice_en
- [S43] European Commission, Rules for the reuse of Commission information: https://digital-strategy.ec.europa.eu/en/news/rules-reuse-commission-information
- [S44] Creative Commons, European Commission adopts CC BY and CC0 for sharing information (2 April 2019): https://creativecommons.org/2019/04/02/european-commission-adopts-cc-by-and-cc0-for-sharing-information/
- [S45] Council of the EU, EU Best Practices for the effective implementation of restrictive measures (update), 11623/24, 3 July 2024: https://data.consilium.europa.eu/doc/document/ST-11623-2024-INIT/en/pdf
- [S46] OpenSanctions, EU Sanctions Map dataset page (quotes the Council and Commission): https://www.opensanctions.org/datasets/eu_sanctions_map/
- [S47] OpenSanctions repository, commit fc8e631 (2026-10-17): https://github.com/opensanctions/opensanctions (LICENSE, COPYRIGHT.md, the crawler paths in section 5, `datasets/gb/hmt` history, `datasets/_global/un_1718_vessels/un_1718_vessels.yml`)
- [S48] OpenSanctions dataset pages (counts, file sizes): https://www.opensanctions.org/datasets/us_ofac_sdn/ ; https://www.opensanctions.org/datasets/us_ofac_cons/ ; https://www.opensanctions.org/datasets/gb_fcdo_sanctions/ ; https://www.opensanctions.org/datasets/un_sc_sanctions/ ; https://www.opensanctions.org/datasets/eu_fsf/
- [S49] OpenSanctions changelog 38, UK Sanctions Lists Consolidation: https://www.opensanctions.org/changelog/38/
- [S50] OpenSanctions FAQs: https://www.opensanctions.org/faq/commercial/paying-for-use/ ; https://www.opensanctions.org/faq/12/data-origin
- [S51] Apache Software Foundation, ASF 3rd Party License Policy: https://www.apache.org/legal/resolved.html
- [S52] moov-io/watchman (Apache-2.0): https://github.com/moov-io/watchman (`pkg/sources/ofac/download.go`, `pkg/sources/csl_eu/download_eu.go`, `pkg/sources/csl_un/un_csl.go`, `pkg/sources/ofac/mapper.go`)
- [S53] UK Parliament Members API: https://members-api.parliament.uk/ and https://members-api.parliament.uk/swagger/v1/swagger.json
- [S54] UK Parliament, Open Parliament Licence v3.0: https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/ and Copyright Parliament: https://www.parliament.uk/site-information/copyright-parliament/
- [S55] Money Laundering, Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations 2017, regulation 35: https://www.legislation.gov.uk/uksi/2017/692/regulation/35
- [S56] Same Regulations, regulation 41: https://www.legislation.gov.uk/uksi/2017/692/regulation/41
- [S57] FATF Glossary: https://www.fatf-gafi.org/en/pages/fatf-glossary.html
- [S58] FCA, FG25/3 The treatment of politically exposed persons for anti-money laundering purposes: https://www.fca.org.uk/publication/finalised-guidance/fg25-3.pdf
- [S59] Wikidata, Licensing: https://www.wikidata.org/wiki/Wikidata:Licensing
- [S60] The Signpost, Technology report, 17 February 2026: https://signpost.news/2026-02-17/Technology_report
- [S61] WikidataQueryServiceR manual (quotes the WDQS limits): https://wikimedia.r-universe.dev/WikidataQueryServiceR/doc/manual.html
- [S62] Debian mirror of Wikidata dumps (2024 listing): https://cdimage.debian.org/mirror/wikimedia.org/other/wikibase/wikidatawiki/
- [S63] OpenSanctions Wikidata PEP crawler: https://github.com/opensanctions/opensanctions/tree/main/datasets/_wikidata/peps
- [S64] Scottish Parliament, Class 9 open data: https://www.parliament.scot/about/information-rights/guide-to-information/class-9-open-data
- [S65] Northern Ireland Assembly open data: https://data.niassembly.gov.uk
- [S66] ICO, What is criminal offence data?: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/criminal-offence-data/what-is-criminal-offence-data/
- [S67] ICO, What are the conditions for processing?: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/criminal-offence-data/what-are-the-conditions-for-processing/
- [S68] Data Protection Act 2018, Schedule 1 paragraph 15: https://www.legislation.gov.uk/ukpga/2018/12/schedule/1/paragraph/15
- [S69] GOV.UK content API, Ministers: https://www.gov.uk/api/content/government/ministers
- [S70] data.europa.eu search API record for the EU consolidated financial sanctions list: https://data.europa.eu/api/hub/search/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions
