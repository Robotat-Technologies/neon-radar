# Matching keys (`neonradar_keys`)

`keys/` is the one place where NeonRadar turns a name, an address, a country, a nationality or an identifier into the form that matching compares. The loaders use it for address record ids, the resolver for its features and deterministic rules, and the graph loader for `Address.address_key` and the Latin search names (`names_latin`). Because every package calls the same functions, a key means the same thing everywhere (`docs/build/PHASE-2.md` 4.1 and M2.8).

Every function is pure: no network, no database, no files except the two data files packaged with the library (`data/ar_symbols.json.gz` and `data/nationalities.csv`). Matching keys and Latin renderings are computed from a record's original values at matching or loading time and are never written into records (C1 rule R10).

The code and its oracle tests were given verbatim in the build spec; two cases use other example strings, because the spec's were a person name on the synthetic-name denylist and company words retired under operator decision OD-12. The expected values were produced by running the code on 18 October 2026 with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 and anyascii 0.3.3; the research behind each rule is in [names-addresses.md](../research/2026-10-18/names-addresses.md). Every example below is a case in `keys/tests/test_keys.py` or, for the changes of rules version 2, in `keys/tests/test_keys_fixes.py`.

## Versioning

`neonradar_keys.RULES_VERSION` (now `"2"`) changes whenever any function's output changes, and persisted keys record it. A change to a key needs a new or changed test first.

| Version | What changed |
|---|---|
| `1` | The build spec's code (`docs/build/PHASE-2.md` M2.8) |
| `2` | Fixes after the M2.8 review, where the spec's code was wrong (`docs/build/phase-2-reconciliation.md` 2.6): an address without a postcode needs a real street line; ST that starts a segment is SAINT; company numbers need ASCII digits that are not all zeros; `find_uk_postcode` cuts the original text in the right place; name symbols are read from the NFKC form. Every assertion of the spec's own tests still passes |

The Arabic name index is built from rigour's name data at the tag that matches the installed rigour. The pin `rigour==2.5.*` allows patch releases, so when a lock update moves rigour, `test_symbol_index_matches_installed_rigour` fails until the index is rebuilt with `keys/scripts/build_ar_symbol_index.py` (the new tag and the SHA-256 of its `person_names.txt`) and `RULES_VERSION` is bumped. `data/ar_symbols.LICENSE.txt` names the tag and carries rigour's licence; update the tag there too (`test_licence_texts_are_package_data` compares the licence text with the installed rigour's). The build is reproducible: the same source gives a byte-identical file (`THIRD_PARTY_NOTICES.md` has the checksums and the licence).

## Person names: `names.person_key(name, given=None, family=None)`

Returns a `PersonKey`:

| Field | What it holds | Used for |
|---|---|---|
| `tokens` | normalised tokens in name order | the resolver's `name_tokens` |
| `key` | the unique tokens, sorted, joined by spaces | `name_key`: equality, the strict name check of rules D1 to D4 and the term-frequency level |
| `given`, `family` | tokens of the given and family names, when the source says which is which | `forename`, `surname`, `initial` |
| `skeletons` | consonant skeletons of the tokens | the resolver's "two skeletons shared" comparison level, which compares spellings across scripts (`mhmd` for both Mohammed and محمد) |
| `phonetic` | Metaphone codes of the ASCII tokens | a phonetic aid |
| `symbols` | Wikidata ids of the name groups the name's parts belong to | the "two name symbols shared" level and a blocking rule |

The steps: Unicode NFKC, rigour's person prefixes (Mr, Mrs, Dr and others) removed, casefolding and tokenising; then one rule set for Arabic script and one for everything else.

- **Companies House order.** A name written `SURNAME, Forenames` with the surname in capitals is split, so `SMITH, John Michael` gives family `smith` and given `john michael`; `Smith, John` is not split.
- **Latin script.** Tokens are folded to ASCII (`Jürgen Müller` gives `jurgen muller`, `Łukasz Wiśniewski` gives `lukasz wisniewski`). For names of Arabic origin, Abd and Abu compounds are joined, articles (al, el, ar, as and the like) are dropped, and nasab particles (bin, ibn, bint, ben, ould) are dropped unless they come first: `Abdul Rahman Al Ali`, `Abdulrahman Al-Ali`, `Abd al-Rahman al-Ali`, `Abdel Rahman El Ali` and `AL-ALI, Abdul Rahman` all give `abdrahman ali`; `Abdullah Haddad` and `Abd Allah Haddad` give `abdallah haddad`; `Abu Bakr Haddad` gives `abubakr haddad`; `Khalil bin Samer` gives `khalil samer`. Leading honorifics such as Sheikh and Haji are dropped while at least two tokens remain (`Sheikh Hamad Saleh` gives `hamad saleh`).
- **Cyrillic script.** Tokens are folded with anyascii, which keeps digraphs: `Александр Сергеевич Иванов` gives `aleksandr ivanov sergeevich`, `Пётр Щербаков` gives `petr shcherbakov`.
- **Arabic script.** `arabic.ar_normalize` removes tashkeel, Quranic marks and tatweel and unifies the letter forms that spellings of one name vary in: alef forms to ا, alef maqsura and yeh forms to ي, ta marbuta to ه, waw with hamza to و, hamza dropped, Arabic-Indic digits to ASCII (`أحمد` and `إحمد` give `احمد`, `فاطمة` gives `فاطمه`, `مصطفى` gives `مصطفي`, `عائشة` gives `عايشه`, `٢٠٢٦` gives `2026`). The token rules then strip the article ال when at least three letters remain (never from الله, الهام, الياس, اليسع, so `إلهام حداد` keeps `الهام`), join عبد and ابو with the next word (`عبد الرحمن العلي` and `عبدالرحمن العلي` both give `عبدالرحمن علي`), drop بن, ابن and بنت after the first token (`سامر بن خليل العطار` gives `خليل سامر عطار`), and drop leading honorifics such as الشيخ and الدكتور.
- **Name symbols.** rigour's tagger supplies Wikidata name groups for the spellings it knows exactly (`Mohammed`, `Мухаммед` and `محمد` all carry `Q5837762`; `Alexander` and `Александр` share `Q17501806`). Its lookups need the exact spelling, so Arabic tokens and adjacent pairs of tokens are also looked up, after `ar_normalize`, in NeonRadar's own index of rigour's Arabic forms (`symbols.arabic_symbols`, 17,798 keys): the tagger gives `إحمد` no group, while the index finds the groups of `احمد`. The tagger reads the NFKC form of the name, so decomposed (NFD) and fullwidth spellings get the same groups as the plain one.

`names.name_similarity(left, right)` is the Jaro-Winkler similarity of two keys, from rigour, which returns 0.0 for scores at or below 0.6 (`rana` and `nora` give 0.0). The name check of rules D1 to D4 uses it with the threshold 0.85 (`docs/build/PHASE-2.md` 7.1.2).

`names.latin_forms(names)` gives anyascii renderings of the names that contain a script other than Latin, for the graph's full-text search aid (`names_latin`): `["Haddad", "Хаддад"]` gives `["Khaddad"]`. A Latin form is a search aid only and is never shown as a name.

## Organisation names: `names.org_key(name)` and `companies_house.ch_same_as_key(name)`

`org_key` returns an `OrgKey` with the folded name without its legal form or a leading "The" (`key`), and the generic legal form codes it found (`legal_forms`):

| Name | `key` | `legal_forms` |
|---|---|---|
| ACME TRADING LTD, Acme Trading Limited | `acme trading` | `llc` |
| ACME HOLDINGS PLC | `acme holdings` | `jsc` |
| Acme Partners LLP | `acme partners` | `llp` |
| ООО «Ромашка» | `romashka` | `llc` |
| The Acme Company Limited | `acme company` | `llc` |
| ACME & SONS (UK) LIMITED | `acme and sons uk` | `llc` |

Arabic legal forms that rigour does not know (ذ.م.م, ش.م.م, ش.م.ع and others) are removed by NeonRadar's own pattern and reported as `llc_ar`.

`ch_same_as_key` approximates the "same as" rules for UK company names in Schedule 3 of the Company, Limited Liability Partnership and Business (Names and Trading Disclosures) Regulations 2015 (research note section 10): trailing legal forms and words such as UK, CO and COMPANY are disregarded, AND and &, number words and digits and similar pairs count as equal, punctuation, a final S, a leading THE or WWW and the spaces are dropped. `ACME LIMITED`, `Acme Ltd.`, `ACME (UK) LIMITED`, `THE ACME COMPANY LIMITED`, `ACME & CO LTD`, `A.C.M.E. LIMITED`, `WWW.ACME.CO.UK LIMITED` and `ACMÉ LIMITED` all give `ACME`; `ACME HOLDINGS LIMITED` and `ACME HOLDING LTD` give `ACMEHOLDING`; `BACK TO BASICS LIMITED` and `BACK 2 BASICS LTD` give `BACK2BASIC`. The key deliberately merges names the register treats as the same, so it is a blocking key and strong evidence, never proof on its own.

Two gaps of the approximation:

- **A word of paragraph 4 at the very end stays a word.** The equivalences apply only to an item followed by a space, so once the legal form is removed a final number word or currency word is left as it is: `ACME ONE LTD` gives `ACMEONE` but `ACME 1 LTD` gives `ACME1`, and `ACME DOLLAR LTD` gives `ACMEDOLLAR`. The same holds for `%`, which must stand alone between spaces (`ACME 100% LTD` gives `ACME100%`, `ACME 100 PERCENT LTD` gives `ACME100PERCENT`).
- **£, € and ¥ never meet their words.** anyascii folds them to `GBP`, `EUR` and `Y` before the equivalences run, so `ACME £ HOLDINGS LTD` gives `ACMEGBPHOLDING` while `ACME POUND HOLDINGS LTD` gives `ACME£HOLDING`. Only `$`, `&`, `+` and `@` meet their words (`ACME $ HOLDINGS LTD` and `ACME DOLLAR HOLDINGS LTD` both give `ACME$HOLDING`).

## UK postcodes: `postcodes.py`

- `normalise_uk_postcode(text)` returns the postcode in capitals with one space before the inward code, or None: `n1 7gu` and `N17GU` give `N1 7GU`, `ec1a1bb` gives `EC1A 1BB`; `N1 7GC` is rejected (C is never used in the inward code), as is `hello`. `QQ1 2AB` has a valid shape and is accepted (synthetic data uses `QQ` postcodes, `docs/build/PHASE-2.md` 2.9); `ZZ1 2AB` is rejected, because Z is not used as the second letter.
- `find_uk_postcode(text)` finds the last postcode in a text and returns it with the rest of the text, cut from the original text (letters such as ß, whose upper case is longer, do not shift the cut).
- `postcode_parts(postcode)` gives area, district and sector: `N1 7GU` has area `N`, district `N1`, sector `N1 7`. Splink's postcode comparison derives the same levels itself, so no lookup file is needed.

## Addresses: `addresses.address_key(text)` and `address_key_from_parts(parts)`

The key is `POSTCODE|TOKENS`, or `NOPC|TOKENS` for an address with a street line but no UK postcode, or None when the text has neither. A street line is a token that starts with a digit (a house number such as `12`, `1-3` or `1ST`), a thoroughfare or building word after a name in its segment (STREET, ROAD, AVENUE, LANE, DRIVE, COURT, CRESCENT, PLACE, SQUARE, GARDENS, CLOSE, TERRACE, PARADE, WAY, HIGHWAY, MEWS, BOULEVARD, HOUSE, BUILDING, BUILDINGS, CENTRE, ESTATE, TOWER, CHAMBERS), or a unit word before its number or letter (FLAT, SUITE, UNIT, FLOOR, OFFICE, ROOM). Place names alone are not one: `Dubai, United Arab Emirates`, `Road Town, Tortola, British Virgin Islands` (ROAD starts its segment), `Panama City, Panama`, `New York, NY, USA` and `Isle of Man` give None, while `Example House, Leeds` gives `NOPC|EXAMPLE HOUSE LEEDS`. Text is folded to ASCII capitals; the postcode is taken out; segments that start with c/o or "care of" are dropped; trailing country words (UNITED KINGDOM, ENGLAND, UK, GB and others) are removed; common abbreviations are expanded (RD to ROAD, SQ to SQUARE, HSE to HOUSE, STE to SUITE, APT to FLAT, FIRST to 1ST and so on); ST becomes STREET when it ends a segment or comes just before the last word (the post town), unless it starts a segment or follows a number, and SAINT otherwise (`12 Main St, St Albans, AL1 1AA` gives `AL1 1AA|12 MAIN STREET SAINT ALBANS`).

| Address | `address_key` |
|---|---|
| Flat 3, 12 High St., London, n1 7gu | `N1 7GU\|FLAT 3 12 HIGH STREET LONDON` |
| FLAT 3, 12 HIGH STREET, LONDON, N1 7GU, UNITED KINGDOM | `N1 7GU\|FLAT 3 12 HIGH STREET LONDON` |
| Ste 4, Example Hse, 1-3 Example Rd., London N1 7GU | `N1 7GU\|SUITE 4 EXAMPLE HOUSE 1-3 EXAMPLE ROAD LONDON` |
| 12 St Johns Road, London, N1 7GU | `N1 7GU\|12 SAINT JOHNS ROAD LONDON` |
| c/o Example Accountants LLP, 2 Market Sq, Reading, RG1 2AA | `RG1 2AA\|2 MARKET SQUARE READING` |
| 1st Floor 5 Church Ln Leeds LS12AB | `LS1 2AB\|1ST FLOOR 5 CHURCH LANE LEEDS` |
| Moscow, Russia | None |

Loaders build the text from structured fields with `address_key_from_parts` (premises, address lines, locality, region, postcode, country), never from a free-text concatenation that may change order. Address record ids are `<prefix>-addr-<first 20 hex of sha1(address_key)>` (`docs/build/PHASE-2.md` 4.4), and rule D6 merges addresses with the same key that contains a full postcode or a street line.

## Countries and nationalities: `countries.country_code(value)`

Returns a lower-case FollowTheMoney country code for a country name, a demonym or a code, or None. For current countries that is the ISO 3166-1 alpha-2 code; FtM also has its own codes, such as `xk` (Kosovo, also in `nationalities.csv`) and `suhh`, `yucs` and `cshh` for the Soviet Union, Yugoslavia and Czechoslovakia, which rigour returns for those names. Compare codes as FtM codes, not as ISO codes. Exact, case-insensitive lookups in `nationalities.csv` (Companies House nationality values and FCDO citizen names) come first, then rigour's territory lookup without fuzzy matching, because fuzzy matching gives confident wrong answers. The four UK nations map to `gb`.

| Value | Code |
|---|---|
| British, Welsh, Scottish, United Kingdom, England, GBR | `gb` |
| Irish | `ie` |
| Emirati | `ae` |
| Saudi Arabian | `sa` |
| Mauritian | `mu` (rigour alone gives Mauritania) |
| Congolese (Congo) | `cg` (rigour alone gives the Democratic Republic of the Congo) |
| Chadian | `td` |
| VGB | `vg` |
| Stateless, an empty string, Atlantis | None |

## Identifiers: `ids.py`

- `uk_company_number(value, *, synthetic=False)` (rule D1): upper case; spaces, dots and hyphens removed; an all-digit number is left-padded to 8 digits (`1800000` gives `01800000`); one of the 36 Companies House prefixes (`CH_PREFIXES`) followed by digits is padded to 8 characters (`SC 12345` and `sc-012345` give `SC012345`; `OC300001`, `R0000123`). Anything else is not a UK company number: `HE123456` (a Cypriot form), `GB123456`, `N1234567`, `ABC` and `123456789` give None, and so do numbers written with other digits (Arabic-Indic `١٨٠٠٠٠٠`, fullwidth `０１８０００００`) and numbers with only zeros (`0`, `00000000`, `SC000000`), which are placeholders: under D1 they would link unrelated records, and under X3 they would keep records apart. The synthetic benchmark prefix `SY` (`SYNTHETIC_PREFIX`) counts only with `synthetic=True` (`sy 101` then gives `SY000101`).
- `has_ch_prefix(number)`: true for an all-digit (ASCII) number or one that starts with a Companies House prefix.
- `is_valid_lei(value)` (rule D2): the ISO 17442 check digits, through rigour (`549300OWFMSO9NYV4H90` is valid, `549300OWFMSO9NYV4H91` is not).
- `un_reference(value)` (rule D4): a UN Security Council reference in capitals, without spaces or a final dot.

## Known limits

- **Arabic is matched through normalisation, consonant skeletons and Wikidata name groups, not by transliteration.** No permissive, maintained Arabic-to-Latin name transliterator was found, and generic transliteration garbles unvocalised Arabic. An Arabic spelling and a Latin spelling of one name meet only through a shared name group (which also feeds a blocking rule) or a shared skeleton (a comparison level), and the name groups cover the names Wikidata records, not every name.
- **Scripts other than Latin, Arabic and Cyrillic get only anyascii folding.** Greek, Hebrew, Chinese and other scripts are folded character by character, with no name-specific rules.
- **A company number with a prefix outside the list of 36 is not a UK company number.** The list (`CH_PREFIXES`) is the official Companies House list of May 2012 plus the newer prefixes named by the community (`bulk-sources-loading.md` 2.6). If Companies House introduces a new prefix, those numbers give None until the list and `RULES_VERSION` change.
- **Address keys are for UK addresses.** A foreign address without a UK postcode still gets a `NOPC|` key when it has a street line, but its abbreviations and country words are not handled.
- **The "same as" key is approximate.** The character table of paragraph 2 of the Schedule could not be verified, and the key is folded with anyascii instead (research note section 10).
- **Honorifics and particles are lists.** A title the lists do not contain stays in the key; a given name that equals a dropped particle in another language can be lost. Add a failing test with a synthetic name before changing a list.
- **Empty keys exist.** `org_key("Ltd").key`, `person_key(".").key` and `ch_same_as_key("")` are empty strings, and an address that is only a postcode gives `N1 7GU|` (a postcode and no tokens). **Note for M2.10a:** empty keys must be dropped, or written as NULL in the feature tables, before they reach Splink, as empty lists are (`docs/build/PHASE-2.md` 3.2, 7.1.5): Splink tests only `IS NULL` for its null level, so two empty strings would agree as if they were the same name. A postcode-only address key identifies a postcode, not an address, and is treated the same way wherever a key is compared.

## Failing tests for the graph mentor

Each case below is a proposed test that fails today. No code was changed for them: the graph mentor decides whether each is wanted, adds the test, and then changes the code and `RULES_VERSION`.

| Proposed assertion | Today | Why it matters |
|---|---|---|
| `ar_normalize("فاطمہ") == ar_normalize("فاطمة")`, and the same for `ھ` (U+06BE) and `ۃ` (U+06C3) | `فاطمہ`, `فاطمھ`, `فاطمۃ`: the Urdu and Persian heh goal (U+06C1), heh doachashmee and teh marbuta goal are not unified with ه and ة, and `arabic_skeleton` drops them | Names written in Urdu or Persian orthography do not meet their Arabic spelling |
| `person_key("ЅMITH, John").key == person_key("SMITH, John").key` (Ѕ is the Cyrillic letter DZE, U+0405, which looks like a Latin S) | `dzmith john` against `john smith` | A look-alike letter, by mistake or on purpose, splits one name into two keys; a homoglyph fold for mixed-script tokens would join them |
| `split_ch_name("حداد, خليل") is None` | `("خليل", "حداد")`: Arabic has no capital letters, so the "surname in capitals" test always passes and any Arabic `A, B` is read as Companies House order (while the Arabic comma ، is not recognised at all) | Companies House writes Latin names; an Arabic list entry with a comma may not be surname first |
