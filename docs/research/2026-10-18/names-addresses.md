# NeonRadar Phase 2 research: names, addresses and nationalities across scripts

Checked on Sunday 18 October 2026 for the Phase 2 build spec (ownership graph and entity resolution). Scope: normalising and comparing person names, organisation names, addresses and nationalities across Latin, Arabic and Cyrillic for entity resolution between Companies House (CH), GLEIF, the UK, US OFAC, UN and EU sanctions lists, and the ICIJ Offshore Leaks data.

Method: package metadata from the PyPI JSON API; a CPython 3.14.6 virtual environment (uv 0.11.32) with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 (built from sdist against system ICU 74.2), followthemoney 4.11.0, nomenklatura 4.17.2, jellyfish 1.3.0, rapidfuzz 3.14.6, anyascii 0.3.3 and splink 5.0.0; the installed source and the rigour repository at tag v2.5.0 were read; every output quoted below was produced by running code [N3]. Official sources were read with a web fetch tool. All person names in tests are invented or common given names; the requested محمد بن سلمان pattern was replaced by the invented سامر بن خليل العطار. Builds on `neonradar-phase1/kit/research/stack.md` 4.2 to 4.3 and `sources-opensanctions-ftm-icij.md` B.2 and B.5 [N46].

Prototype code used for the key recipes (research only, not production): `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p2-names/scripts/nr_keys.py` and `nr_addr.py`.

## 0. Answers for the spec writer

1. **Versions (Q1).** rigour 2.5.0 (2026-09-10), normality 3.1.0 (2026-03-08), followthemoney 4.11.0 (2026-09-03), nomenklatura 4.17.2 (2026-10-12), jellyfish 1.3.0 (2026-10-16, new since Phase 1) and rapidfuzz 3.14.6 (2026-08-30) are all MIT and all ran on CPython 3.14.6; anyascii 0.3.3 is ISC [N1][N3]. PyICU 2.16.2 (2026-03-20, MIT) is still sdist only and builds in about a minute with `libicu-dev`; `pyicu-wheels` 2.15.2 (Apache-2.0, cp314 wheels, bundles ICU 77.1) works through a uv override; icu4py and icupy are not drop-ins [N2][N9]. **Licence flag:** rigour requires python-stdnum 2.2 (LGPL-2.1-or-later): the spec must state that LGPL is acceptable, or rigour and FtM cannot be used [N1].
2. **APIs (Q2).** Use `analyze_names(type_tag, names, part_tags=None, *, infer_initials=False, symbols=True, phonetics=True, numerics=True, consolidate=True, rewrite=True) -> set[Name]`; `Name.comparable` is transliterated only for Latin, Cyrillic, Greek, Armenian, Georgian and Hangul, so Arabic stays Arabic [N4][N3]. `normalize_name` only casefolds and tokenises (diacritics kept); org-type functions expect casefolded input. `rigour.ids` validates LEI, IMO, IBAN, BIC, ISIN, INN, OGRN and eight more formats but nothing for UK company numbers; for addresses use `address_fingerprint` and `compare_address` (the keyword helpers are deprecated) [N4][N3].
3. **Tests (Q3).** rigour removes tashkeel and tatweel but does not unify alef forms, ta marbuta, alef maqsura or hamza carriers, and never transliterates Arabic; ICU gives vowel-less skeletons with `?` for ʿayn ("?bd alrhmn al?ly") and its BGN transform garbles unvocalised text [N3]. rigour's Cyrillic ASCII loses digraphs (Щербаков -> "Serbakov"), anyascii gives "Shcherbakov" [N3]. Mr, Mrs, Dr, Sir, Prof. and Hon. are stripped; Sheikh and Haji are kept on purpose (tagged as symbols); الشيخ, الدكتور and ذ.م.م are not handled; Ltd, PLC, LLP, LP, ООО, ЗАО, АО, S.A., GmbH and Inc are [N3][N5].
4. **Name symbols (Q4).** Yes: rigour 2.5.0 compiles a Wikidata-derived corpus (157,298 groups, 569,089 forms, `rust/data/names/person_names.txt`; repository MIT, Wikidata CC0) into its tagger [N5][N10]. Call `analyze_names(NameTypeTag.PER, [x])` and keep `Name.symbols` of category NAME. محمد, Mohammed, Muhammad and Мухаммед share `Q5837762` (Mohamad does not); Александр and Alexander share `Q923`, `Q1511218`, `Q17501806` [N3]. Lookups are spelling-exact (إحمد, مصطفي get none), so add an index keyed by NeonRadar's Arabic normaliser (17,799 keys, 0.6 MB) built from the pinned file [N3].
5. **Arabic names (Q5).** Names combine ism (including ʿAbd plus a divine name), kunya (Abu/Umm), nasab (ibn/bint; "ben" in the Maghreb), laqab and nisba [N27]; ALA-LC, BGN/PCGN 1956, the UN system, ISO 233, DIN 31635, French conventions and ICAO 9303 romanise differently and short vowels are unwritten, hence the many Latin spellings [N22][N23][N24][N26][N21]. Normalise: NFKC, drop marks and tatweel, أ إ آ ٱ -> ا, ى -> ي, ة -> ه, ؤ -> و, ئ -> ي, drop ء; detect "ال" before that; join عبد and ابو with the next word; drop بن/ابن/بنت after the first token (5.3). OFAC FAQ 249 (Jaro-Winkler plus Soundex), OFSI's Bank of Scotland penalty, the EU and the UN describe expectations, not algorithms [N11][N16][N20][N19].
6. **Arabic libraries (Q6).** CAMeL Tools 1.6.0 is MIT but requires torch and transformers; pyarabic 0.6.15 and Tashaphyne 0.3.6 are GPL-3.0 (forbidden); arabic-reshaper 3.0.1 (MIT) only reshapes for display; no permissive, maintained Arabic-to-English name transliterator was found [N28][N29]. **Recommendation:** implement the small rule set in 5.3 to 5.5 (tested here) and credit CAMeL Tools for the character rules.
7. **UK postcodes (Q7).** Six shapes AN, ANN, AAN, AANN, ANA, AANA, then a space and NAA, plus GIR 0AA; upper case, 5 to 7 characters without the space [N30][N31]; inward letters never C, I, K, M, O, V [N31]; outward code 2 to 4 characters, hierarchy area, district, sector, unit [N33]. The GOV.UK regex has a typo; a corrected regex and normaliser are in section 7 [N32]. Splink's `PostcodeComparison` derives sector, district and area itself, so **no lookup file is needed**; ONSPD's Northern Ireland data is internal-use only and Code-Point Open covers GB only [N43][N34][N35].
8. **Addresses (Q8).** `address_fingerprint` unifies "Flat 3, 12 High St., London, n1 7gu" and "Flat 3 12 High Street London N1 7GU" but is order-sensitive, maps "House" to "d" and may change between rigour versions; `compare_address` is a good fuzzy feature (St vs Street 0.985, Flat 3 vs Flat 4 0.258) [N3][N4]. libpostal is MIT but needs the C library and a 1.8 to 2.2 GB model and has no cp314 wheels [N37]. **Recommendation:** NeonRadar's own UK `address_key` (recipe below) plus `compare_address` as a Splink comparison through a DuckDB UDF (verified) [N3].
9. **Nationalities (Q9).** CH validates nationality against a 225-value list since 15 December 2017; older data is free text [N38][N39][N45]. FtM `registry.country.clean` maps 189 of the 225, returns `None` for 36 (for example Bhutanese, Chadian, Citizen of Seychelles, Stateless, Cymraes, Prydeinig), maps Mauritian to `mr` (Mauritania) and Congolese (Congo) to `cd`, and splits the UK (English -> gb, Scottish -> gb-sct); `fuzzy=True` is unsafe ("Chadian" -> ca) [N3]. **Recommendation:** a NeonRadar CSV seeded from the CH list and FCDO citizen names (OGL v3.0), UK constituents to `gb`, raw string kept, FtM `clean()` without fuzzy as fallback [N40].
10. **CH "same as" (Q10).** SI 2015/17 Schedule 3 disregards trailing Schedule 2 legal forms, trailing "& CO", "COMPANY", "UK", "GREAT BRITAIN", "WALES" and similar (Welsh and bracketed forms too), punctuation and `* = #`, a final "S", leading "THE ", "WWW" and "@", and spaces; treats AND/&, PLUS/+, number words (TO and TOO as 2, FOR as 4), currency words, PER CENT/% and AT/@ as equal; compares the first 60 characters [N41][N42]. The para 2 character table is UNVERIFIED. `ch_same_as_key` is in section 10.
11. **logic_v2 (Q11).** Score = maximum of weighted main features (name 1.0, ISIN and address entity 0.98, LEI, OGRN, IMO, INN, BIC, UEI, NPI 0.95, generic identifier 0.85, weak alias 0.8) plus qualifiers (address +0.2, country -0.2, DOB year -0.15, DOB day -0.25, gender -0.2), clipped to 0..1; the name feature pairs rigour symbols first (NAME 0.9) and fuzzy-compares the residue with `compare_parts`, weighting unmatched query parts 0.8, unmatched result parts 0.2 and family names 1.3 [N8]. nomenklatura's `ofac` matcher emulates OFAC's search tool [N8][N15].

**Recommended keys (pseudo-code).** Computed at matching time from original-script values; never written into records. Pin rigour exactly and store `keys_version` (rigour version plus NeonRadar rules version) with every persisted key.

```text
person_features(raw, given=None, family=None):
    if raw matches "^([^,]+),\s*([^,]+)$" and group1 is upper case:      # CH "SURNAME, Forenames"
        given, family = group2, group1 ; raw = given + " " + family
    raw  = rigour.remove_person_prefixes(NFKC(raw))
    toks = rigour.tokenize_name(casefold(raw))
    if "Arabic" in rigour.text_scripts(raw):
        toks = drop_leading(toks, {الشيخ, الحاج, الدكتور, المهندس, الاستاذ, ...}, keep_at_least=2)
        toks = arabic_rules(toks)   # strip "ال" only if raw token starts with bare alef+lam and >=3 letters remain
                                    # (except الله الهام الياس اليسع); join عبد/ابو + next; drop بن ابن بنت (not first);
                                    # then ar_normalize (section 5.3)
    else:
        toks = [ascii_text(t) if Latin else anyascii(t).lower() for t in toks]   # Cyrillic via anyascii
        toks = drop_leading(toks, {sheikh, shaikh, shaykh, haji, hajji, hajj, alhaji}, keep_at_least=2)
        toks = latin_rules(toks)    # abd(ul|el|al|ur|ar|...)? [al|el|ar|..] X -> "abd"+X ("abdallah" for allah forms);
                                    # abu [al] X -> "abu"+X; drop al el ul ar as ash at ad az an; drop bin ibn bint ben ould (not first)
    return name_key      = join(" ", sorted(set(toks)))
           name_tokens   = toks
           name_latn     = join(" ", parts' rigour comparable form, else ascii_text)
           name_symbols  = rigour NAME QIDs of raw  UNION  ar_symbol_index[ar_normalize(t)] for Arabic tokens and bigrams
           name_skeletons= sorted(set(skeleton(t) for t in toks)) minus length < 2   # plus "al"-stripped variant of "alX" tokens
           name_phonetic = [rigour.metaphone(t) for t in toks if t is ASCII]
           family_key    = tokens of family part when known (CH split, PSC name_elements, FtM lastName)

org_features(raw):
    t = casefold(NFKC(raw)) ; t = AR_LEGAL_FORMS.sub(" ", t)      # ذ.م.م ش.ذ.م.م ش.م.م ش.م.ع ش.م.ل ...
    legal = rigour.extract_org_types(t, generic=True) (+ "llc_ar" if Arabic form found)
    t = rigour.remove_org_prefixes(t) ; t = rigour.remove_org_types(t, replacement=" ")
    return org_key = join(" ", translit(tokenize(t.replace("&", " and ")))), org_legal_form = legal,
           ch_same_as_key = ch_same_as_key(raw) for UK-registered names only

address_features(raw):
    s  = anyascii(NFKC(raw)).upper()
    pc = last match of UK_POSTCODE_RE in s, normalised to "OUTWARD INWARD" ; remove it from s
    segments = split(s, ",;\n") minus segments starting "C/O" or "CARE OF"
    toks = [A-Z0-9-]+ tokens ; "&" -> "AND"
    drop trailing country words: UNITED KINGDOM, GREAT BRITAIN, NORTHERN IRELAND, ENGLAND, SCOTLAND, WALES, BRITAIN, UK, GB
    expand: RD ROAD, AVE AVENUE, LN LANE, SQ SQUARE, CT COURT, PL PLACE, GDNS GARDENS, HSE/HO HOUSE, APT/APARTMENT FLAT,
            STE SUITE, FIRST 1ST, ...; "ST" -> STREET when it ends a segment (or precedes only the post town), else SAINT
    address_key = (pc or "NOPC") + "|" + join(" ", toks) ; premise_key = pc + "|" + first numeric token
    if not a UK address: address_key = rigour.address_fingerprint(raw)        # version-stamped
```

## 1. Package versions and licences (Q1)

| Package | Latest (upload date) | Licence | Python 3.14 | Notes |
|---|---|---|---|---|
| rigour | 2.5.0 (2026-09-10) | MIT | 35 wheels cp310 to cp314; classifier 3.14 | requires `normality>=3.0.1,<4`, `python-stdnum>=2.0,<3`, `pyyaml`, `orjson`, `prefixdate`, `jinja2` [N1] |
| normality | 3.1.0 (2026-03-08) | MIT | `py3-none-any`; classifiers 3.10 to 3.13; ran on 3.14.6 | requires `pyicu>=2.10.0`, `banal`, `chardet`, `charset-normalizer` [N1][N3] |
| pyicu | 2.16.2 (2026-03-20) | MIT | sdist only; built on 3.14.6 with ICU 74.2 (whole install took about 65 s) | `apt-get install pkg-config libicu-dev build-essential` still required [N1][N3] |
| pyicu-wheels | 2.15.2 (2026-03-11) | Apache-2.0 (packaging) | wheels cp310 to cp314: manylinux x86_64/aarch64/ppc64le/i686, musllinux, macOS 15, Windows | third-party wheels of PyICU 2.15.2, bundles ICU 77.1, imports as `icu` [N2][N3] |
| followthemoney | 4.11.0 (2026-09-03) | MIT | `py3`; classifiers 3.11 to 3.14 | requires `rigour>=2.4.0,<3`, `normality>=3.1.0,<4` [N1] |
| nomenklatura | 4.17.2 (2026-10-12) | MIT | `py3`; classifiers 3.11, 3.12; ran on 3.14.6 | `scikit-learn==1.9.1`, `duckdb`, `fingerprints` (unmaintained), `textual`, `lxml` [N1][N3] |
| jellyfish | 1.3.0 (2026-10-16) | MIT | wheels cp311 to cp315, PyPy 3.11 | changelog 1.3.0: metaphone fix for word-final GH, drops 3.9 and 3.10 [N1][N44] |
| rapidfuzz | 3.14.6 (2026-08-30) | MIT | wheels cp311 to cp315 incl. free-threaded cp314t | [N1] |
| anyascii | 0.3.3 (2025-06-29) | ISC (LICENSE "Copyright (c) 2020-2025, Hunter WB") | `py3` wheel | [N1][N29] |
| python-stdnum | 2.2 (2026-01-04) | LGPL-2.1-or-later | `py3` | transitive via rigour [N1] |
| chardet | 7.7.0 (2026-10-18) | 0BSD | `py3` | transitive via normality; released today [N1] |

Binary ICU alternatives [N2][N3][N9]:
- `pyicu-wheels` works as a replacement: in a uv project, `[tool.uv] override-dependencies = ["pyicu; sys_platform == 'never'"]` plus `pyicu-wheels==2.15.2` resolved, installed in 2 s and ran rigour's analyzer (verified). Risks: third-party repackager, one minor version behind PyICU. Keep the sdist build as the default (devcontainer, CI) and document the override as the Windows/macOS fallback.
- `icu4py` 1.1.0 (MIT, cp310 to cp314 wheels) exposes only breakers, `Locale` and `MessageFormat`, no `Transliterator`; `icupy` 0.24.0 (MIT) is sdist only with a different API; `PyICU-binary` 2.7.4 (2021) stops at cp39. None can back normality.

## 2. rigour 2.5.0 and normality 3.1.0: what an ER feature pipeline would call (Q2)

All signatures read from the installed package [N4][N6]; behaviour notes verified by running [N3].

### 2.1 `rigour.names`
- `analyze_names(type_tag, names, part_tags=None, *, infer_initials=False, symbols=True, phonetics=True, numerics=True, consolidate=True, rewrite=True) -> set[Name]`. Pipeline: prefix strip, prenormalise, org-type replacement (ORG/ENT), `Name`/`NamePart` construction, `part_tags` applied via `Name.tag_text`, Aho-Corasick tagger, NUMERIC/STOP/LEGAL inference, optional `consolidate_names`. `PER` strips person prefixes; `ORG`/`ENT` replace org types and strip "The"; indexers should pass `consolidate=False` [N4].
- `Name(original, form=None, tag=NameTypeTag.UNK, phonetics=True)`: attributes `original`, `form` (casefolded), `tag`, `parts`, `spans`, `comparable`, `norm_form`, property `symbols`; methods `tag_text(text, tag, max_matches=1)`, `apply_phrase`, `apply_part`, `contains(other)`, classmethod `consolidate_names(names)` [N4].
- `NamePart(form, index, tag=NamePartTag.UNSET, phonetics=True)`: `form`, `index`, `tag`, `latinize`, `numeric`, `ascii` (None outside the six admitted scripts), `integer`, `comparable`, `metaphone`; `NamePart.tag_sort(parts)` [N4].
- Tags: `NameTypeTag` UNK, ENT, PER, ORG, OBJ; `NamePartTag` UNSET, AMBIGUOUS, TITLE, GIVEN, MIDDLE, FAMILY, TRIBAL, PATRONYMIC, MATRONYMIC, HONORIFIC, SUFFIX, NICK, STOP, NUM, LEGAL, with `tag.can_match(other)`. `SymbolCategory` ORG_CLASS, SYMBOL, DOMAIN, INITIAL, NAME, NICK, NUMERIC, LOCATION, PHONETIC [N4].
- `tokenize_name(text, token_min_length=1) -> list[str]` (splits on separators and punctuation, deletes marks Mn, modifier letters Lm and format characters; so tashkeel, tatweel and apostrophes vanish, "O'BRIEN" becomes "OBRIEN"); `normalize_name(name) -> str | None` = `normalize(name, Normalize.CASEFOLD | Normalize.NAME)` [N4][N3].
- Prefixes: `remove_person_prefixes(name)`, `remove_org_prefixes(name)` (The, Le, La), `remove_obj_prefixes(name)` (The, MV, M/V); lists in `resources/names/stopwords.yml`, each prefix also matched with a trailing dot. Sheikh, Shaikh, Sultan, Emir, Prince, King, Major, Baron, Duke and Earl are left out, each with the comment that it "is also a male given name and so not currently included here" [N5].
- Org types: `replace_org_types_compare(name, normalize_flags=Normalize.CASEFOLD, cleanup=Cleanup.Noop, generic=False)`, `replace_org_types_display(name, normalize_flags=CASEFOLD|SQUASH_SPACES, cleanup=Noop)`, `remove_org_types(name, replacement="", normalize_flags=CASEFOLD, cleanup=Noop)`, `extract_org_types(name, normalize_flags=CASEFOLD, cleanup=Noop, generic=False) -> list[tuple[str, str]]`. Data: `org_types.yml`, built from an OCCRP sheet, ISO 20275 ELF codes and Wikipedia. Passing upper-case input still matches but returns mixed case ("ACME TRADING ltd"), so casefold first [N4][N3].
- Ordering and comparison: `align_person_name_order(left, right) -> (list[NamePart], list[NamePart])`; `pair_symbols(query, result) -> list[tuple[Alignment, ...]]`; `compare_parts(qry, res, config=None) -> list[Alignment]` with `CompareConfig(cost_sep_drop=0.2, cost_confusable=0.7, cost_digit=1.5, budget_log_base=2.35, budget_short_floor=2.0, budget_tolerance=1.0, cluster_overlap_min=0.51)`; `Alignment(qps, rps, symbol=None, score=0.0, weight=1.0)` [N4]. Verified scores: samer/samir 0.78, haddad/hadad 0.83, mohammed/mohamed 0.88, aleksandr/alexander 0.60, sevcuk/shevchuk 0.75, ahmed/mohammed 0.0 [N3].
- Picking and checks: `pick_name(names) -> str | None` (picked "Mohammed Al Ali" from upper, lower, hyphenated and Arabic variants), `pick_case`, `reduce_names`, `representative_names(names, limit, cluster_threshold=0.3)`, `is_name`, `contains_split_phrase` ("a.k.a.", "f/k/a", "trading as") [N4][N3].

### 2.2 `rigour.text`
- Scripts: `text_scripts(text) -> set[str]` (ICU4X script property; letters and numbers only), `common_scripts(a, b)`, `codepoint_script(cp)`; helpers `can_latinize`, `is_modern_alphabet`, `is_latin`, `is_dense_script` in `rigour.text.scripts` [N4].
- Transliteration: `maybe_ascii(text, drop=False) -> str` and `should_ascii(text) -> bool` cover only Latin, Cyrillic, Greek, Armenian, Georgian and Hangul; a string with any other script is returned unchanged ("Иванов محمد" stays as is), so transliterate token by token [N4][N3].
- Distances: `levenshtein(left, right, max_length=..., max_edits=None)`, `levenshtein_similarity(left, right, max_edits=..., max_percent=..., max_length=...)`, `is_levenshtein_plausible(...)`, `jaro_winkler(left, right, max_length=...)` which **returns 0.0 for scores at or below 0.6** [N4][N3].
- Phonetics: `metaphone(token)`, `soundex(token)` (Rust, LRU-cached). Both return "" for Cyrillic or Arabic input, so transliterate first; "mohammed" and "muhammad" both give MHMT and M530; rigour and jellyfish 1.3.0 metaphone agreed on all tested words [N3].
- Normalisation flags: `normalize(text, flags=Normalize(0), cleanup=Cleanup.Noop)` with `Normalize` STRIP, SQUASH_SPACES, CASEFOLD, NFC, NFKC, NFKD, NAME, ADDRESS and `Cleanup` Noop, Strong, Slug [N4].

### 2.3 `rigour.addresses`
`normalize_address(address, latinize=False, min_length=4)`, `shorten_address_keywords(address, latinize=False)` and `remove_address_keywords(address, latinize=False, replacement=" ")` (both emit `DeprecationWarning` in 2.5.0), `address_fingerprint(text) -> str | None`, `compare_address(query, result) -> float`, `compare_address_many(queries, results)`, `match_addresses(queries, results) -> AddressMatch | None` (`score`, `query`, `result`, `detail`), `format_address(address, country=None)`, `format_address_line(address, country=None)` (OpenCage templates), `clean_address(full)`. The docstring gives ~0.3 as the accuracy-optimal threshold on rigour's address benchmark [N4].

### 2.4 `rigour.ids`
`get_identifier_format(name)`, `get_identifier_format_names()`, `get_identifier_formats()`, `get_strong_format_names()`; classes with `is_valid`, `normalize`, `format`: WikidataQID, OGRN, IMO, ISIN, IBAN, FIGI, BIC, INN, NPI, LEI, UEI, SSN, CPF, CNPJ, USCC, plus `generic` and `strict` [N4]. Verified: LEI check digits, IMO checksum ("IMO 9074729" normalises to "IMO9074729"), IBAN with spaces, ISIN, INN and OGRN check digits accept and reject correctly; BIC "DEUTDEFF500" normalises to "DEUTDEFF" (branch dropped) [N3]. No UK company number format; use the Phase 1 rule (8 characters, zero-pad all-digit numbers, keep prefixes such as SC, NI, OC) [N46].

### 2.5 `rigour.territories`
`get_territory(code)`, `get_territories()`, `get_territory_by_qid(qid)`, `get_ftm_countries()`, `lookup_by_identifier(identifier)` (alpha-2, alpha-3, other codes, QIDs), `lookup_territory(text, fuzzy=False)` (strong names, then weak names and demonyms, then places), `territories_intersect(left, right)` (parent and claim aware). `Territory` has `code`, `alpha3`, `name`, `full_name`, `qid`, `parent`, `is_country`, `is_jurisdiction`, `ftm_country`, `region`, `subregion` and more [N4]. Verified: "GBR" -> gb, "Q145" -> gb, "Россия" -> ru, "المملكة المتحدة" -> gb, "الامارات" -> ae, "Emirati" -> ae, "Dubai" -> `ae-du` (FtM country `ae`), "Moscow" -> `ru-mow`; `territories_intersect(['gb-sct'], ['gb'])` -> {'gb-sct'} [N3].

### 2.6 `normality`
`normalize(value, lowercase=True, collapse=True, latinize=False, ascii=False, encoding_default=..., encoding=None, replace_categories=UNICODE_CATEGORIES)` (uses `str.lower`, not casefold), `latinize_text(text, ascii=False)` (ICU `Any-Latin`), `ascii_text(text)` (ICU chain `Any-Latin; NFKD; [:Nonspacing Mark:] Remove; Accents-Any; [:Symbol:] Remove; [:Nonspacing Mark:] Remove; Latin-ASCII`, then `encode("ascii", "replace")`, which is why ʿ becomes `?`), `squash_spaces(text)`, `category_replace(text, replacements=UNICODE_CATEGORIES)`, `slugify(value, sep="-")`, `slugify_text(text, sep="-")`, `stringify`, `safe_filename` [N6]. normality 3 imports `icu.Transliterator` at module load; there is no fallback [N6]. Examples: with default arguments `normalize("  Müller-Lüdenscheidt   GmbH ")` returned 'muller ludenscheidt gmbh' (the default category replacement applies NFKD and deletes combining marks, so accents go even without `ascii=True`); `normalize("Иванов", latinize=True)` -> 'ivanov'; `squash_spaces` on " a", no-break space, zero-width space, "b", tab, "c " returned 'a b c' (zero-width characters deleted, other whitespace collapsed); `category_replace("O’Brien-Smith (UK)")` -> 'O Brien Smith  UK ' (punctuation to spaces, no squashing); `slugify("ООО «Ромашка»")` -> 'ooo-romaska'; `ascii_text("ʿAbd al-Raḥmān")` -> '?Abd al-Rahman' [N3].

## 3. Test results (Q3)

Verified by running each function in Python 3.14.6 with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 (ICU 74.2) and anyascii 0.3.3 [N3]. Columns are functions; `NR ar_normalize` is the rule set in 5.3. `maybe_ascii` returned every Arabic input unchanged and `text_scripts` returned {'Arabic'} for all, so those columns are omitted.

### 3.1 Arabic script

| Input | `normalize_name` | `normality.ascii_text` | ICU `Arabic-Latin/BGN` | `anyascii` | NR `ar_normalize` | rigour NAME symbols |
|---|---|---|---|---|---|---|
| سامر بن خليل العطار | سامر بن خليل العطار | samr bn khlyl al?tar | sاmr bn khlيl l‘ţاr | smr bn khlyl l\`tr | unchanged | n/a |
| عبد الرحمن العلي | عبد الرحمن العلي | ?bd alrhmn al?ly | ‘bd lrḩmn l‘lي | \`bd lrhmn l\`ly | unchanged | عبد الرحمن: 4 |
| أحمد | أحمد | ahmd | (combining hamza)ḩmd | 'hmd | احمد | 6 |
| احمد | احمد | ahmd | ḩmd | hmd | احمد | 2 |
| إحمد | إحمد | ahmd | (combining hamza)ḩmd | 'hmd | احمد | 0 |
| آمنة | آمنة | amnt | (combining madda)mnh | amnh | امنه | 1 |
| مُحَمَّد (tashkeel) | محمد | muhamad | muḩamaّd | muhamad | محمد | 15 |
| عَبْدُ الرَّحْمٰنِ | عبد الرحمن | ?abdu alrahmni | ‘abdu lraّḩmٰni | \`abdu lrahmani | عبد الرحمن | 4 |
| فاطمة (ta marbuta) | فاطمة | fatmt | fاţmh | ftmh | فاطمه | 6 |
| فاطمه | فاطمه | fatmh | fاţmh | ftmh | فاطمه | 3 |
| مصطفى (alef maqsura) | مصطفى | mstfy | mşţfy | mstfa | مصطفي | 7 |
| مصطفي | مصطفي | mstfy | mşţfي | mstfy | مصطفي | 0 |
| محـــمد (tatweel) | محمد | mhmd | mḩـــmd | mhmd | محمد | 15 |
| عائشة (hamza on ya) | عائشة | ?aysht | ‘ئshh | \`i'shh | عايشه | 4 |
| عايشة | عايشة | ?aysht | ‘يshh | \`yshh | عايشه | 0 |

Findings: `normalize_name` removes tashkeel and tatweel only; every ICU route loses vowels, and the BGN transform assumes vocalised input; NR `ar_normalize` makes all orthographic variants of one name equal; symbol coverage depends on the exact spelling (section 4 describes an index that fixes this).

### 3.2 Latin spellings

| Input | `normalize_name` | metaphone per token | soundex per token | rigour NAME symbols | NR `person_name_key` |
|---|---|---|---|---|---|
| Mohammed | mohammed | MHMT | M530 | Q19794110, Q5837762 | mohammed |
| Muhammad | muhammad | MHMT | M530 | Q131190381, Q26905901, Q5837762 | muhammad |
| Mohamed | mohamed | MHMT | M530 | Q19729888, Q19794110, Q5837762 | mohamed |
| Mohamad | mohamad | MHMT | M530 | Q20000198 | mohamad |
| Abdul Rahman | abdul rahman | ABTL RMN | A134 R550 | Q307378 (+ SYMBOL:ABDUL) | abdrahman |
| Abdulrahman | abdulrahman | ABTLRMN | A134 | Q307378 | abdrahman |
| Abd al-Rahman | abd al rahman | ABT AL RMN | A130 A400 R550 | Q307378 (+ SYMBOL:ABDUL) | abdrahman |
| Abdel Rahman | abdel rahman | ABTL RMN | A134 R550 | Q307378 | abdrahman |

Metaphone and Soundex already collapse the four Muhammad spellings; the Abd compounds need the joining rule (or the shared symbol `Q307378`).

### 3.3 Cyrillic and Latin diacritics

| Input | `maybe_ascii` (= `normality.ascii_text`) | ICU `Russian-Latin/BGN` | ICU `Ukrainian-Latin/BGN` | `anyascii` |
|---|---|---|---|---|
| Александр Сергеевич Иванов | Aleksandr Sergeevic Ivanov | Aleksandr Sergeyevich Ivanov | Aleksandr Serheevych Yvanov | Aleksandr Sergeevich Ivanov |
| Олександр | Oleksandr | Oleksandr | Oleksandr | Oleksandr |
| Пётр Щербаков | Petr Serbakov | Pëtr Shcherbakov | Pёtr Shcherbakov (ё left in Cyrillic) | Petr Shcherbakov |
| Алёна Щукина | Alena Sukina | Alëna Shchukina | Alёna Shchukyna | Alena Shchukina |
| Юлия Шевчук | Ulia Sevcuk | Yuliya Shevchuk | Yulyya Shevchuk | Yuliya Shevchuk |

ICAO Doc 9303 (passports, preferred by the EU for lists) uses Ж ZH, Х KH, Ц TS, Ч CH, Ш SH, Щ SHCH, Ю IU, Я IA, Й I (Ukrainian initial Ю, Я, Й as YU, YA, Y) [N21]. Use anyascii (ISC, no ICU) for Cyrillic tokens in keys; rigour's `comparable` keeps the lossy form but its NAME symbols still bridge common names (Шевчук and Shevchuk share `Q21452250`) [N3].

| Input | `normalize_name` | `maybe_ascii` / `anyascii` | `normalize(..., ascii=True)` | `slugify` |
|---|---|---|---|---|
| Jürgen Müller | jürgen müller | Jurgen Muller | jurgen muller | jurgen-muller |
| Łukasz Wiśniewski | łukasz wiśniewski | Lukasz Wisniewski | lukasz wisniewski | lukasz-wisniewski |
| Ayşe Çelik | ayşe çelik | Ayse Celik | ayse celik | ayse-celik |
| Straße | strasse (casefold) | Strasse | strasse | strasse |

ICAO allows Ü as UE, UXX or U in the machine-readable zone [N21], so "MUELLER" also occurs; logic_v2 scored "Jürgen Müller" vs "Juergen Mueller" 0.87 and vs "Jurgen Muller" 1.00 [N3].

### 3.4 Companies House style and honorifics

| Input | Function | Output |
|---|---|---|
| SMITH, John Michael | `tokenize_name` | ['SMITH', 'John', 'Michael'] (comma ignored, no family tag) |
| SMITH, John Michael | `analyze_names(PER)` comparable | 'smith john michael' |
| SMITH, John Michael | NR `split_ch_name` | ('John Michael', 'SMITH') |
| AL-SAYED, Omar | `analyze_names(PER)` parts | al (STOP), sayed (UNSET), omar (UNSET) |
| AL-SAYED, Omar | NR `person_name_key` | 'omar sayed' |
| O'BRIEN, Seán | `tokenize_name` | ['OBRIEN', 'Seán'] |
| VAN DER BERG, Pieter | `analyze_names(PER)` parts | van, der (STOP), berg, pieter |
| Mr John Smith / Mrs. Jane Doe | `remove_person_prefixes` | 'John Smith' / 'Jane Doe' |
| Dr Ahmed Khan / Sir David Jones | `remove_person_prefixes` | 'Ahmed Khan' / 'David Jones' |
| Prof. Dr. Hans Weber / The Hon. Mary Brown | `remove_person_prefixes` | 'Hans Weber' / 'Mary Brown' |
| Sheikh Hamad Saleh | `remove_person_prefixes`; symbols | unchanged; SYMBOL:SHEIKH |
| Haji Rashid Karim | `remove_person_prefixes`; symbols | unchanged; SYMBOL:HAJI |
| Sheikh Hamad Saleh | NR `person_name_key` | 'hamad saleh' |
| الشيخ سامر العطار | `remove_person_prefixes`; symbols | unchanged; no SYMBOL (only bare شيخ and حاج are in symbols.yml) |
| الشيخ سامر العطار | NR `person_name_key` | 'سامر عطار' |
| الدكتور خليل حداد | `remove_person_prefixes` / NR key | unchanged / 'حداد خليل' |

`align_person_name_order` lines up "Smith John" with "John Smith", and logic_v2 scored "SMITH, John Michael" vs "John Michael Smith" at 1.00 [N3].

### 3.5 Organisation names

All rigour calls on casefolded input; `NR org_name_key` and `ch_same_as_key` are the prototypes in sections 0 and 10 [N3].

| Input | `replace_org_types_compare` | `generic=True` | `replace_org_types_display` | `analyze_names(ORG)` comparable | NR `org_name_key` (legal form) | NR `ch_same_as_key` |
|---|---|---|---|---|---|---|
| ACME TRADING LTD | acme trading ltd | acme trading llc | ACME TRADING LTD | acme trading ltd | acme trading (llc) | ACMETRADING |
| Acme Trading Limited | acme trading ltd | acme trading llc | Acme Trading Ltd | acme trading ltd | acme trading (llc) | ACMETRADING |
| ACME HOLDINGS PLC | acme holdings plc | acme holdings jsc | ACME HOLDINGS PLC | acme holdings plc | acme holdings (jsc) | ACMEHOLDING |
| Acme Partners LLP | acme partners llp | acme partners llp | Acme Partners LLP | acme partners llp | acme partners (llp) | ACMEPARTNER |
| Acme Ventures LP | acme ventures lp | acme ventures lp | Acme Ventures LP | acme ventures lp | acme ventures (lp) | ACMEVENTURE |
| ООО «Ромашка» | ooo «ромашка» | llc «ромашка» | ООО «Ромашка» | ooo romaska | romashka (llc) | n/a |
| ЗАО Ромашка | ao ромашка | jsc ромашка | ЗАО Ромашка | ao romaska | romashka (jsc) | n/a |
| АО «Ромашка» | ao «ромашка» | jsc «ромашка» | АО «Ромашка» | ao romaska | romashka (jsc) | n/a |
| Общество с ограниченной ответственностью «Ромашка» | ooo «ромашка» | llc «ромашка» | ООО «Ромашка» | ooo romaska | romashka (llc) | n/a |
| شركة النخيل للتجارة ذ.م.م | unchanged | unchanged | unchanged | شركة النخيل للتجارة ذمم | شركه النخيل للتجاره (llc_ar) | n/a |
| Acme S.A. | acme sa | acme jsc | Acme SA | acme sa | acme (jsc) | ACMESA |
| Acme GmbH | acme gmbh | acme llc | Acme GmbH | acme gmbh | acme (llc) | ACMEGMBH |
| Acme Inc. | acme inc | acme llc | Acme Inc | acme inc | acme (llc) | ACMEINC |
| The Acme Company Limited | the acme company ltd | the acme company llc | The Acme Company Ltd | acme company ltd | acme company (llc) | ACME |
| ACME & SONS (UK) LIMITED | acme & sons (uk) ltd | acme & sons (uk) llc | ACME & SONS (UK) LTD | acme sons uk ltd | acme and sons uk (llc) | ACME&SON |
| Acme Public Limited Company | acme plc | acme jsc | Acme PLC | acme plc | acme (jsc) | ACME |
| Acme Cyf | acme ltd | acme llc | Acme Cyf | acme ltd | acme (llc) | ACME |
| Acme Corporation | acme corporation | acme corporation | Acme Corporation | acme corporation | acme corporation | ACMECORPORATION |

"Holdings" is never stripped; "Corporation" and "Company" are org symbols, not legal forms; rigour's Arabic aliases are المحدودة, المساهمة المحدودة and a few full phrases written with shadda (for example شّركة ذات مسؤوليّات محدودة ش.م.م), so ذ.م.م, ش.ذ.م.م, ش.م.م alone and ذات مسؤولية محدودة were not recognised [N5][N3]. Add the Arabic forms locally (regex in `nr_keys.py`) and offer them upstream.

### 3.6 Pairwise scores with nomenklatura logic_v2 (design reference)

`name_match` and `OFACMatcher.compare` with each algorithm's `default_config()` on single-name FtM entities; `LogicV2.compare` equalled the name score in every row [N3][N8]:

| Left | Right | logic_v2 name | OFAC emulation | Evidence (abridged) |
|---|---|---|---|---|
| محمد عبد الرحمن العلي | Mohammed Abdul Rahman Al Ali | 0.59 | 0.00 | محمد~mohammed and عبد الرحمن~abdul rahman by NAME symbols; العلي unmatched |
| Mohammed Abdul Rahman Al Ali | Muhammad Abd al-Rahman al-Ali | 0.97 | 0.94 | Q5837762, SYMBOL:ABDUL, literal rahman |
| AL-SAYED, Omar | Omar Al Sayed | 1.00 | 1.00 | all three parts by symbol |
| AL-SAYED, Omar | عمر السيد | 0.39 | 0.00 | only Omar by symbol |
| Омар Аль-Сайед | Omar Al-Sayed | 0.87 | 0.00 | sajed~sayed fuzzy 0.64 |
| Юлия Шевчук | Yuliya Shevchuk | 0.90 | 0.00 | both parts by symbol (ulia~yuliya, sevcuk~shevchuk) |
| Пётр Щербаков | Pyotr Shcherbakov | 0.90 | 0.00 | both by symbol |
| Олександр Шевчук | Alexander Shevchuk | 0.90 | 0.00 | Q17501806, Q21452250 |
| أحمد خليل | احمد خليل | 0.95 | 0.92 | symbol |
| إحمد خليل | احمد خليل | 0.50 | 0.92 | إحمد~احمد fuzzy 0.00 |
| مصطفى حداد | مصطفي حداد | 0.82 | 0.96 | fuzzy 0.64 on the first name |
| فاطمة حداد | Fatima Haddad | 0.90 | 0.00 | both by symbol |
| Mohammed Khalil | Ahmed Khalil | 0.50 | 0.90 | the OFAC emulation over-matches |
| ООО «Ромашка» | Romashka LLC | 0.84 | 0.00 | ooo~llc by ORG_CLASS, romaska~romashka 0.88 |
| شركة النخيل للتجارة ذ.م.م | Al Nakheel Trading LLC | 0.00 | 0.00 | nothing shared |
| ACME & SONS LIMITED | Acme and Sons Ltd | 0.97 | 0.88 | "and" left as extra part |

Cross-script given names work through symbols; Arabic family names, nisbas and Arabic organisation names do not, which is what the skeleton feature (5.5) addresses.

## 4. Cross-script name symbols (Q4)

- **Location.** `rust/data/names/person_names.txt` in the rigour repository (tag v2.5.0, commit b0ba4adc of 2026-09-10): one line per group, `form1, form2, ... => Qnnn`; 157,298 groups, 569,089 forms, 208 manual `X...` overrides, 8,610,609 bytes [N5][N3]. `build.rs` compresses it with zstd level 19 into the binary; `rust/src/names/person_names.rs` describes "the 2.7 MB compressed copy that already lives in .rodata"; the cp314 x86_64 `_core` extension is 10,837,464 bytes in total [N5][N3]. Script coverage: 20,694 groups contain Arabic forms (20,387 also Latin), 54,805 Cyrillic, 10,874 all three [N3].
- **Provenance and licence.** Generated by `contrib/namesdb` (crawls Wikidata items of classes such as family name Q101352, given name Q202444, patronymic Q110874) [N5]. The repository is MIT ("Copyright (c) 2023-2025: OpenSanctions Datenbanken GmbH"); no separate data licence file was found; `docs/data.md` calls the reference data "openly licensed" and says the person-name database "allows for name matching across scripts without the need to rely on machine-based transliteration" [N5]. Wikidata: "All structured data in the main, property and lexeme namespaces is made available under the Creative Commons CC0 License" [N10]. Keeping the MIT notice is sufficient for an Apache-2.0 project.
- **Standalone use.** No public "lookup token" function exists; use `analyze_names(NameTypeTag.PER, [text])` and read `Name.symbols` (or `Name.spans` for which parts carry which symbol), or `pair_symbols(q, r)` for aligned pairs. Category `NAME` carries Wikidata QIDs; `NICK` (e.g. NICK:ALEX for Alexander), `SYMBOL` (ABDUL, BIN for both "bin" and بن, UMM, HAJI, SHEIKH) and `ORG_CLASS` also occur [N4][N3].
- **Tests** [N3]: محمد has 15 NAME QIDs including Q5837762; Mohammed {Q19794110, Q5837762}; Muhammad {Q131190381, Q26905901, Q5837762}; Мухаммед {Q5837762}; Мохаммед and Магомед also carry Q5837762; Mohamad only Q20000198 (shared with محمد, not with Mohammed). Александр {Q923, Q1511218, Q17501806, ...}; Alexander {Q923, Q1511218, Q17501806, NICK:ALEX}; Олександр shares Q17501806 with both; Oleksandr shares Q19818135 with Олександр and Александр but not with Alexander; الكسندر carries Q923.
- **Spelling sensitivity.** The tagger tolerates tashkeel and tatweel (مُحَمَّد and محـــمد keep 15 QIDs) but not other variants: إحمد 0, مصطفي 0, عايشه 0, امنه 0 [N3]. Building an index from the same file keyed by `ar_normalize(form)` gives 23,569 Arabic forms under 17,799 keys (607,319 bytes of JSON) and returns احمد 6, مصطفي 7, عايشه 4, امنه 2, فاطمه 7 QIDs [N3]. Generate it at build time from the pinned tag (not at runtime) and ship it with its MIT notice.
- **Behaviour as evidence.** On 12 invented persons (Arabic script vs three Latin spellings each), all 36 true pairs shared at least one NAME QID, but so did 18 of 396 false pairs (common given names such as Omar or Khalil) [N3]. Treat symbol overlap as a comparison level (Splink `ArrayIntersectAtSizes`), never as a match on its own.

## 5. Arabic names: structure, romanisation, normalisation and official guidance (Q5)

### 5.1 Structure
- IFLA's guide (2018) lists the classical elements: kunya ("Abu" or "Umm" plus a child's name, not necessarily real kinship), ism (simple, or compound "formed by combining the prefix 'Abd (slave) with one of the 99 names of God"), nasab ("ibn" plus father and grandfather), laqab (sobriquet or title), nisba (origin or affiliation, often with al- and ending -i, e.g. al-Baghdadi), and the shuhra (best-known element) [N27].
- Modern usage: kunya and honorific compounds largely disappeared; nasab mostly disappeared except in Tunisia, Algeria and Morocco, where "the traditional nasab is now preceded by the word ben and not ibn"; "The laqab and nisba are the most consistently used name elements"; entry is usually under the last element [N27]. Libraries may disregard the article al- when filing [N27].
- ALA-LC romanises ابن and بن as "ibn" in all positions (except modern North African "Bin"), writes the article "al-" joined by a hyphen and never assimilated, and shows ʿAbd compounds as separate words ("ʿAbd al-Majīd") [N22].
- Matching consequences: the same person can appear with or without nasab markers, with the nisba or family name in different positions (CH puts the surname first), with the article attached, detached or assimilated, and with the ʿAbd compound joined or split.

### 5.2 Romanisation standards and why lists show many spellings
- **ALA-LC** (2012 table): "al-" always, lower case, hyphenated; ta marbuta "h" (absolute) or "t" (construct); alif maqsura "á" (Muṣṭafá); hamza ʼ and ʿayn ʻ [N22].
- **BGN/PCGN 1956** (revised presentation 2019, for geographical names): article assimilated before sun letters, capitalised at the start, no hyphens ("Ar Riyāḑ", "Abd ar Raḩmān"); ta marbuta "ah"/"at"; alif maqsura "á"; based on fully pointed Arabic, and "vowel points are generally omitted in ordinary Arabic writing", which makes uniform romanisation hard [N23].
- **UN system**: UNGEGN report v5.0 (June 2018): the 2017 recommendation (resolution XI/3) is based on the Unified Arabic Transliteration System (Beirut 2007, amended 2008 and 2017); the 1972 system (resolution II/8) remains widely used; BGN/PCGN 1956 is almost identical to 1972; Algeria, Morocco, Tunisia, Mauritania and Djibouti generally use French-based renderings [N24].
- **ISO 233:1984** gives each character a unique equivalent; **ISO 233-2:1993** is a simplified scheme for bibliographic use, confirmed 2017 and expected to be replaced by ISO/DIS 233-1 [N24][N25]. **DIN 31635:2011-07** is current; its Arabic tables are "nearly identical to ISO 233" [N26].
- **ICAO Doc 9303 Part 3** (8th edition 2021): Table 6.C encodes Arabic reversibly for the passport MRZ (ث XTH, ح XH, خ XKH, ص XSS, ع E, ق Q, ة XTA or XAH, ى XAY), so passports and lists derived from them can carry forms unlike any human romanisation [N21].
- Result: vowels must be guessed, articles are written four ways (al-, al, el-, assimilated), ta marbuta becomes a, ah, at, eh or nothing, emphatic consonants lose their dots, and Egyptian Arabic pronounces ج as g (Gamal for Jamal). This is why list entries carry several Latin forms: the UK list has "primary name variations" and aliases, the UN list good and low quality aliases next to the original script [N18][N19].

### 5.3 Normalisation rules for Arabic-script names (tested)
Implemented as `ar_normalize` plus `arabic_rules` in the prototype; CAMeL Tools applies the same alef, alef maqsura and ta marbuta replacements in `camel_tools.utils.normalize` [N28][N3].
1. NFKC (folds presentation forms; ﷲ becomes الله).
2. Delete marks U+0610 to U+061A, U+064B to U+065F, U+0670, U+06D6 to U+06ED (except the symbols U+06DD, U+06DE, U+06E9), U+08D3 to U+08FF (tashkeel, shadda, sukun, superscript alef, Quranic marks) and tatweel U+0640, ZWNJ, ZWJ, LRM, RLM, ALM.
3. أ إ آ ٱ ٲ ٳ -> ا; ى -> ي; ئ -> ي; ؤ -> و; ة -> ه; delete standalone ء; ی (Farsi yeh) and ے -> ي; ک -> ك; Arabic-Indic and Extended digits -> ASCII.
4. Detect the article before step 3: strip a leading "ال" only when the raw token starts with bare alef plus lam (or alef wasla plus lam), at least three letters remain, and the token is not الله, الهام, الياس or اليسع (step 3 would otherwise turn إلهام into الهام and lose the distinction).
5. Join عبد and ابو with the following word (عبد الرحمن and عبدالرحمن both become عبدالرحمن); drop بن, ابن, بنت after the first token; drop leading honorifics (الشيخ, الحاج, الدكتور, المهندس, الاستاذ and feminine forms) only when two or more tokens remain. السيد is ambiguous (Mr or the family name Al-Sayed) and is not stripped.
Results: إحمد, أحمد and احمد all give احمد; فاطمة/فاطمه, مصطفى/مصطفي, عائشة/عايشة collapse; "سامر بن خليل العطار" gives tokens [سامر, خليل, عطار] [N3]. Steps 1 to 3 as tested (steps 4 and 5 are token rules in `arabic_rules`):

```python
import re, unicodedata
AR_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۜ۟-۪ۨ-ۭ࣓-ࣿ]")
AR_MAP = str.maketrans({
    "آ": "ا", "أ": "ا", "إ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    "ى": "ي", "ی": "ي", "ے": "ي", "ئ": "ي",
    "ة": "ه", "ؤ": "و", "ک": "ك",
    "ء": None, "ـ": None, "‌": None, "‍": None, "‎": None, "‏": None, "؜": None,
    **{chr(0x0660 + i): str(i) for i in range(10)}, **{chr(0x06F0 + i): str(i) for i in range(10)},
})
def ar_normalize(text: str) -> str:
    return AR_MARKS.sub("", unicodedata.normalize("NFKC", text)).translate(AR_MAP)
```

### 5.4 Latin-side rules for Arabic-origin names (tested)
- Join ʿAbd compounds: "abd"/"abdul"/"abdel"/"abdur"/... plus optional article token plus X, and joined forms matching `^abd(ul|el|al|ur|ar|...)?([a-z]{3,})$`, become "abd"+X; Allah forms (abdullah, abdallah, abd allah, abdulla) become "abdallah". Abdul Rahman, Abdulrahman, Abd al-Rahman, Abdel Rahman, Abd ar-Rahman and Abdurrahman all gave "abdrahman" [N3].
- "abu"/"abou" plus X becomes "abu"+X; drop article tokens al, el, ul, ar, as, ash, at, ad, az, an; drop bin, ibn, bint, binti, ben, ould after the first token ("Ben" can be an English given name); drop leading Sheikh/Shaikh/Haji/Hajji/Alhaji when two or more tokens remain.

### 5.5 Consonant skeletons for Arabic and Latin (experimental cross-script blocking)
Each token maps to a consonant string: Arabic letters through a fixed table (ث ت ط -> t, ح ه -> h, خ -> k, ذ ض د -> d, ش ص س -> s, ق ك -> k, ع ا و ي ء -> nothing; final ه dropped; inner "ال" of ʿAbd compounds dropped), Latin through digraphs (kh -> k, gh -> g, sh/ch -> s, dj -> j, th -> t, dh -> d, q/c -> k), dropping vowels, y, w and a final vowel+h, then collapsing doubled letters. "محمد" and "Mohammed", "Muhammad", "Mohamed" all give "mhmd"; "عبد الرحمن" and the six Latin Abd forms give "bdrhmn"; for "alX" tokens both "lX" and "X" skeletons are emitted [N3]. On the 36 invented true pairs and 396 false pairs above: 35 true pairs shared every Arabic-side skeleton (the exception is Jamal written "Gamal"), 33 shared two or more, the remaining 3 (عبد الرحمن العلي, whose "علي" skeleton is too short) shared their single usable skeleton; 30 false pairs shared one skeleton (common given names) and none shared two [N3]. This is a tiny invented sample: use skeletons as a blocking key and a Splink comparison level, measure on labelled data, and keep the rigour symbols as the stronger signal.

### 5.6 What the sanctions bodies say about name matching
- **OFAC FAQ 249** (28 April 2021): Sanctions List Search uses "Jaro-Winkler, a string difference algorithm, and Soundex, a phonetic algorithm"; it compares the whole input string and also each name part, and the Score shows the higher of the two; candidate selection uses the first letter of the input and edit distance ("at least 50% or more similar based on edit distance") [N11]. **FAQ 246**: fuzzy logic "uses character and string matching as well as phonetic matching"; "Only the name field ... invokes fuzzy logic" [N12]. **FAQ 5** (updated 9 September 2026): confirm hits against aliases, nationality, identification numbers, place and date of birth and addresses [N13]. **FAQs 122 to 125**: weak AKAs are "relatively broad or generic" aliases; OFAC "does not expect that persons will screen for weak AKAs"; they are flagged `LowQuality="true"` in the advanced XML [N14].
- **OFSI**: the Bank of Scotland penalty notice (2026 publication, £160,000 after a 50 percent disclosure discount) records that a customer's passport spelling differed from the listing by one changed and one extra character in the forename, a missing middle name and one changed character in the surname, that "The character changes are common equivalents in Russian to English translations", and that "the screening system did not reconcile the character changes between the spelling variations" [N16]. OFSI's blog of 23 February 2026 says firms should ask whether their screening copes with spelling and transliteration variants and consider enriched lists [N17]. The UK Sanctions List format guide distinguishes "Primary name variations" (spelling variations), aliases, alias strength (UN only) and non-Latin script name, script type and language fields [N18].
- **UN**: the Consolidated List carries "Name (original script)" and distinguishes good quality a.k.a. ("sufficient for a positive identification") from low quality a.k.a. ("probably insufficient alone") [N19].
- **EU** (Council document 11623/24 of 3 July 2024, Best Practices): names should be transliterated as in travel documents or by ICAO standards, ICAO transliteration "should be present at all times and in all language versions", and the original-language name included where available [N20].
- None of these prescribe a matching algorithm; nomenklatura's `ofac` matcher reverse-engineers FAQ 249 and reports about 96 percent agreement with the live tool [N15][N8].

## 6. Arabic NLP libraries (Q6)

| Library | Version (date) | Licence (checked in repository) | Python 3.14 | Verdict |
|---|---|---|---|---|
| camel-tools | 1.6.0 (2026-06-08) | MIT, "Copyright 2018-2026 New York University Abu Dhabi" | classifiers 3.11 to 3.14 | do not depend on it: requires `torch>=2.0`, `transformers>=4.44.0`, `pandas`, `scikit-learn>=1.8.0`, `camel-kenlm` [N28] |
| pyarabic | 0.6.15 (2022-06-18) | GPL-3.0 (LICENSE) | no classifiers | forbidden (GPL) [N29] |
| Tashaphyne | 0.3.6 (2022-01-29) | GPL-3.0 (LICENSE); depends on pyarabic | no classifiers | forbidden [N29] |
| qalsadi | 0.5.1 (2025-07-27) | GPL (PyPI metadata only) | n/a | forbidden; depends on pyarabic [N1] |
| arabic-reshaper | 3.0.1 (2026-04-28) | MIT (LICENSE) | classifiers to 3.14 | display shaping only, not needed [N29] |
| anyascii | 0.3.3 | ISC | yes | consonant skeletons only ("smr bn khlyl l\`tr") [N3] |
| ICU via PyICU/normality | 2.16.2 | MIT / Unicode | yes | `Any-Latin` skeletons, BGN transform needs vocalised text [N3] |
| unidecode / text-unidecode | 1.4.0 / 1.3 | GPL-2.0+ / Artistic or GPL (PyPI classifiers) | n/a | forbidden [N1] |

Recommendation: write the rule set in 5.3 to 5.5 (about 120 lines with tests) inside the `resolve` package, cite CAMeL Tools in a comment for the character rules (copying MIT code would also be allowed with its notice), and contribute missing Arabic legal forms and demonym fixes to rigour upstream.

## 7. UK postcodes (Q7)

- **Format.** UPU's UK addressing sheet (November 2011): 5 to 7 alphanumeric characters with a space before the last three; formats AN NAA (M2 5BQ), ANN NAA (M34 4AB), AAN NAA (CR0 2YR), AANN NAA (DN16 9AA), ANA NAA (W1A 4ZZ), AANA NAA (EC1A 1HQ); "The only exception is GIR 0AA"; capitals, no punctuation, on its own line [N30]. The ESFA ILR 2015/16 Appendix C repeats the six formats, requires upper case and one space, says "The letters C, I, K, M, O and V are never used in the inward code", and uses ZZ999ZZ for unknown postcodes [N31]. The 2001 e-GIF data standards catalogue adds that I and Z are not used in the second position (except GIR 0AA) [N36]. Rules on first-position Q, V, X and on third- and fourth-position letters were not found in an official source fetched today (UNVERIFIED).
- **Hierarchy** (ONS): outward code 2 to 4 characters, inward code 3; area "PO" (124), district "PO15" (3,118), sector "PO15 5" (12,463), unit "PO15 5RR" (about 1.79 million live, August 2022; large users receive at least 500 items a day) [N33].
- **Official regex** (GOV.UK, Bulk data transfer: validation rules for CAS upload, valid from 12 November 2015, section 3.1), as printed: `([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([AZa-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z])))) [0-9][A-Za-z]{2})$` [N32]. As extracted it contains `[AZa-z]` (only A, Z and lower case; a typo for `[A-Za-z]`), has a trailing `$` that binds only to the second alternative, and requires the space.
- **Recommended expression** (same shapes, upper case, optional space, inward letters from [N31]): `(?<![A-Z0-9])(GIR ?0AA|(?:[A-Z][0-9]{1,2}|[A-Z][A-HJ-Y][0-9]{1,2}|[A-Z][0-9][A-Z]|[A-Z][A-HJ-Y][0-9][A-Z]) ?[0-9][ABD-HJLNP-UW-Z]{2})(?![A-Z0-9])`. Normalise: upper case, remove all whitespace, insert one space before the last three characters, re-validate; take the last match in an address. Derive `outward` = all but the last 3 characters, `inward` = last 3, `area` = leading 1 or 2 letters, `district` = outward, `sector` = outward + " " + first inward digit. Verified: "n1 7gu" and "N17GU" -> "N1 7GU" (area N, district N1, sector N1 7); "ec1a1bb" -> "EC1A 1BB"; "N1 7GC" rejected [N3].
- **Splink**: `cl.PostcodeComparison(col_name, *, invalid_postcodes_as_null=False, lat_col=None, long_col=None, km_thresholds=[1, 10, 100])` gives levels exact, sector, district, area (plus distance when coordinates are supplied); its valid-postcode regex `^[A-Za-z]{1,2}[0-9][A-Za-z0-9]? [0-9][A-Za-z]{2}$` needs exactly one space [N43].
- **Lookup files.** ONS postcode products are OGL v3.0 with three attribution lines (OS, Royal Mail, ONS); for BT (Northern Ireland) postcodes ONS issues only an end user licence "limited to internal business use" and commercial use needs a Land and Property Services licence [N34]. Code-Point Open: Great Britain only, CSV and GeoPackage, quarterly, OGL with OS, Royal Mail and National Statistics attribution; Northern Ireland only in the premium products [N35]. NeonRadar does not need a lookup file for keys or Splink levels; add Code-Point Open only if a distance feature is wanted, and never redistribute NI data.

## 8. Address normalisation for UK registered office addresses (Q8)

rigour 2.5.0 on invented addresses [N3]:

| Input | `normalize_address` | `address_fingerprint` |
|---|---|---|
| Flat 3, 12 High St., London, n1 7gu | flat 3 12 high st london n1 7gu | apt 3 12 high st london n1 7gu |
| Flat 3 12 High Street London N1 7GU | flat 3 12 high street london n1 7gu | apt 3 12 high st london n1 7gu |
| 12 High Street, Flat 3, London N17GU, United Kingdom | 12 high street flat 3 london n17gu united kingdom | 12 high st apt 3 london n17gu gb |
| Suite 4 Example House 1-3 Example Road London N1 7GU United Kingdom | suite 4 example house 1 3 example road london n1 7gu united kingdom | ste 4 example d 1 3 example rd london n1 7gu gb |
| Suite 4, Example House, 1-3 Example Rd, London, N1 7GU, England | (same but "rd" and "england") | ste 4 example d 1 3 example rd london n1 7gu gb-eng |
| First Floor, 5 Church Lane, Leeds LS1 2AB | first floor 5 church lane leeds ls1 2ab | first fl 5 church ln leeds ls1 2ab |
| 1st Floor 5 Church Ln Leeds LS12AB | 1st floor 5 church ln leeds ls12ab | 1 fl 5 church ln leeds ls12ab |
| c/o Example Accountants LLP, 2 Market Sq, Reading, RG1 2AA | c o example accountants llp 2 market sq reading rg1 2aa | co example accountants llp 2 market sq reading rg1 2aa |
| ул. Тверская, д. 7, кв. 12, Москва, Россия | ул тверская д 7 кв 12 москва россия | ul tverskaa d 7 kv 12 ru-mow |

`compare_address` scores: St vs Street 0.985 (detail `flat 3 12 high st~street london n1 7gu`); reordered with "N17GU" 0.624; Road vs Rd with England vs United Kingdom 0.790; "First" vs "1st" plus split postcode 0.657; Flat 3 vs Flat 4 0.258 (`-3 +4`); flat missing 0.877; "20-22 Station Rd" vs "20 22 Station Road" 0.963 [N3]. Strengths: keyword aliases, ordinal handling, number-conflict penalty. Weaknesses for UK keys: order-sensitive fingerprint, "House" -> "d" (the Russian дом alias), constituent countries become `gb-eng` rather than disappearing, postcodes without a space stay different, care-of names kept, and fingerprints "are stable within one version of rigour but may change between versions" [N4][N3].

**libpostal.** MIT (LICENSE "Copyright (c) 2015 openvenues"); the README asks for "a few GB of space", gives the Senzing model as about 2.2 GB "compared to 1.8GB for the default model", and links a REST server needing about 4 GB of memory [N37]. Python bindings: `postal` 1.1.11 (2025-10-29) is sdist only and needs the compiled C library; `pypostal-multiarch` 1.0.3 has wheels only for cp38 to cp312 [N37]. Not practical for a 3.14 laptop-first stack and unnecessary for CH addresses, which arrive as structured fields (premises, address_line_1, locality, region, postal_code, country) [N46].

**Recommended `address_key`** (prototype `nr_addr.address_key`, outputs verified [N3]):

| Input | `address_key` |
|---|---|
| Flat 3, 12 High St., London, n1 7gu | `N1 7GU\|FLAT 3 12 HIGH STREET LONDON` |
| FLAT 3, 12 HIGH STREET, LONDON, N1 7GU, UNITED KINGDOM | `N1 7GU\|FLAT 3 12 HIGH STREET LONDON` |
| 12 High Street, Flat 3, London N17GU, United Kingdom | `N1 7GU\|12 HIGH STREET FLAT 3 LONDON` |
| Suite 4 Example House 1-3 Example Road London N1 7GU United Kingdom | `N1 7GU\|SUITE 4 EXAMPLE HOUSE 1-3 EXAMPLE ROAD LONDON` |
| Ste 4, Example Hse, 1-3 Example Rd., London N1 7GU | `N1 7GU\|SUITE 4 EXAMPLE HOUSE 1-3 EXAMPLE ROAD LONDON` |
| 12 St Johns Road, London, N1 7GU | `N1 7GU\|12 SAINT JOHNS ROAD LONDON` |
| 12 Saint Johns Rd, London N1 7GU | `N1 7GU\|12 SAINT JOHNS ROAD LONDON` |
| c/o Example Accountants LLP, 2 Market Sq, Reading, RG1 2AA | `RG1 2AA\|2 MARKET SQUARE READING` |
| 1st Floor 5 Church Ln Leeds LS12AB | `LS1 2AB\|1ST FLOOR 5 CHURCH LANE LEEDS` |
| Office 5, Al Nakheel Tower, Dubai, United Arab Emirates | `NOPC\|OFFICE 5 AL NAKHEEL TOWER DUBAI UNITED ARAB EMIRATES` (use the rigour fingerprint for non-UK) |

For CH records build the key from the structured fields (premises + address_line_1 + address_line_2 + locality + postal_code), not from a concatenated string. Use the key for the `Address` node identity and the "many companies at one address" typology; for fuzzy evidence use `compare_address` inside Splink: a DuckDB Python UDF (`con.create_function("rigour_addr", ...)`) called from `cl.CustomComparison` levels worked with Splink 5.0.0 and DuckDB 1.5.6 (Flat 3 vs Flat 4 fell to the else level, St vs Street reached the 0.9 level) [N3].

## 9. Nationality strings (Q9)

- **Inputs.** Companies House announced standard nationality and country registers on 23 October 2017, enforced from 15 December 2017, values must match exactly [N38]; the lists are on GOV.UK "Nationalities and countries for company filings" (last updated 29 October 2025, OGL v3.0): 225 nationalities (including British, English, Scottish, Welsh, Northern Irish, Cymraes, Cymro, Prydeinig, Emirati, Stateless, "Citizen of ..." forms) and 254 countries (including England, Scotland, Wales, Northern Ireland, United Kingdom, "Guernsey, Alderney, Sark") [N39]. Earlier data "could be anything" [N45]. The FCDO Geographical Names Index (July 2026, OGL v3.0) gives ISO alpha-2 codes with citizen names (for example "Briton, British", "Citizen of the United Arab Emirates") [N40].
- **FtM 4.11.0 `registry.country.clean(raw, fuzzy=False, format=None, proxy=None)`** (wraps `rigour.territories.lookup_territory` and returns `ftm_country`) [N7][N3]:

| Input set | Mapped | Returned `None` | Wrong code |
|---|---|---|---|
| Requested strings: British, Irish, Indian, Pakistani, Emirati, Russian, Ukrainian, Saudi Arabian | all (gb, ie, in, pk, ae, ru, ua, sa) | none | none |
| English / Welsh / Scottish / Northern Irish | English -> gb | none | Welsh -> gb-wls, Scottish -> gb-sct, Northern Irish -> gb-nir (valid FtM codes, but not gb) |
| country_of_residence: United Kingdom, England, Scotland, Wales, Northern Ireland | gb, gb, gb-sct, gb-wls, gb-nir | none | same split |
| CH nationality list (225) | 189 | 36: Anguillan, Citizen of Antigua and Barbuda, Bermudian, Bhutanese, Citizen of Bosnia and Herzegovina, Bruneian, Cape Verdean, Cayman Islander, Chadian, Comoran, Cook Islander, Cymraes, Citizen of the Dominican Republic, Guamanian, Hong Konger, Citizen of Kiribati, Liechtenstein citizen, Martiniquais, Montserratian, Nauruan, Palauan, Papua New Guinean, Pitcairn Islander, Prydeinig, Samoan, Citizen of Seychelles, Solomon Islander, St Helenian, Stateless, Tristanian, Turks and Caicos Islander, Tuvaluan, Vatican citizen, Citizen of Vanuatu, Vincentian, Wallisian | Mauritian -> mr (Mauritania), Congolese (Congo) -> cd (DR Congo) |
| FCDO citizen names (198 names) | 168 | 29 (similar set plus "Briton") | Mauritian -> mr |
| CH country list (254) | 253 | "Guernsey, Alderney, Sark" | none |

- With `fuzzy=True`: "Chadian" -> ca (Canada), "Vincentian" -> la (Laos), "Channel Islands" -> ic (Canary Islands), "Citizen of Bosnia and Herzegovina" -> ba-bih [N3]. The Mauritian error comes from rigour's data: `resources/territories/mr.yml` lists "Mauritian" under Mauritania's `names_weak` [N5].
- **Recommendation.** Ship `nationality_map.csv` (raw string, ISO alpha-2, optional subdivision) built from the CH list and the FCDO citizen names, with UK constituent nationalities and Cymraes, Cymro, Prydeinig mapped to `gb` (subdivision `gb-sct` and so on kept separately), Stateless and "Not specified" to null, "Congolese (Congo)" to `cg`; look up exact values case-insensitively, fall back to `registry.country.clean` without fuzzy, log misses. Store the raw string, compare `nationality` codes with `territories_intersect` semantics (or map to alpha-2 first) so that gb-sct and gb agree, and treat a missing nationality as null in Splink. Report the two rigour data errors upstream.

## 10. Companies House "same as" rules (Q10)

The Company, Limited Liability Partnership and Business (Names and Trading Disclosures) Regulations 2015 (SI 2015/17), Schedule 3 "Name same as another in the Registrar's Index of Company Names", made under regulations 7 and 8; latest revised version, no outstanding effects listed [N41]. Paragraphs apply in order:
1. Para 1: apply paragraphs 2 to 10 in sequence.
2. Para 2: each permitted character in column 1 of a table is the same as the character or characters in column 2. The table is an image on the page and the XML could not be fetched (HTTP 429), so its contents are **UNVERIFIED**; the prototype approximates it with anyascii folding (é -> E).
3. Para 3: disregard at the end of the name any word, expression or abbreviation in inverted commas in Schedule 2 [N41]. Schedule 2 lists "LIMITED"/"LTD", "CYFYNGEDIG"/"CYF", "UNLIMITED", "ANGHYFYNGEDIG", "PUBLIC LIMITED COMPANY"/"PLC", "CWMNI CYFYNGEDIG CYHOEDDUS"/"CCC", "COMMUNITY INTEREST COMPANY"/"CIC", "CWMNI BUDDIANT CYMUNEDOL"/"CBC", "COMMUNITY INTEREST PUBLIC LIMITED COMPANY"/"COMMUNITY INTEREST PLC" and Welsh forms, "RIGHT TO ENFRANCHISEMENT"/"RTE", "HAWL I RYDDFREINIAD", "RIGHT TO MANAGE"/"RTM", "CWMNI RTM CYFYNGEDIG", "UK ECONOMIC INTEREST GROUPING"/"UKEIG", "INVESTMENT COMPANY WITH VARIABLE CAPITAL" and Welsh form, "LIMITED PARTNERSHIP", "LIMITED LIABILITY PARTNERSHIP", "OPEN-ENDED INVESTMENT COMPANY", "CHARITABLE INCORPORATED ORGANISATION" and Welsh forms, "INDUSTRIAL AND PROVIDENT SOCIETY", "CO-OPERATIVE SOCIETY", "PROTECTED CELL COMPANY"/"PCC LIMITED"/"PCC LTD" and Welsh "CUG" forms (inserted 8 December 2017), "COMMUNITY BENEFIT SOCIETY", and abbreviations "LP", "PC", "LLP", "PAC", "CIO", "SEC"; paragraphs 2 and 4 of Schedule 2 extend to variants of these by omission, addition or substitution [N42].
4. Para 4: treat as the same, when the item is preceded and followed by a space or starts the name followed by a space: AND and &; PLUS and +; 0, ZERO and O; 1 and ONE; 2, TWO, TO and TOO; 3 and THREE; 4, FOUR and FOR; 5 to 9 and their words; £ and POUND; € and EURO; $ and DOLLAR; ¥ and YEN; %, PER CENT, PERCENT, PER CENTUM and PERCENTUM; @ and AT [N41].
5. Para 5: disregard at the end, alone or in combination, when preceded by a space, a full stop or "@": "& CO", "& COMPANY", "AND CO", "AND COMPANY", "BIZ", "CO", "CO UK", "CO.UK", "COM", "COMPANY", "EU", "GB", "GREAT BRITAIN", "NET", "NI", "NORTHERN IRELAND", "ORG", "ORG UK", "ORG.UK", "UK", "UNITED KINGDOM", "WALES", and Welsh "& CWMNI", "A'R CWMNI", "CWMNI", "CYM", "CYMRU", "DU", "PF", "PRYDAIN FAWR", "Y DEYRNAS UNEDIG"; sub-paragraph (3) extends this to those matters inside the brackets listed in Schedule 1 table 2 [N41].
6. Para 6: disregard anywhere the punctuation in regulation 2(2)(c) or Schedule 1 table 2 column 2, and the symbols "*", "=" and "#" [N41].
7. Para 7: disregard a final letter "S". Para 8: disregard any permitted character after the first 60 (spaces between characters count). Para 9: disregard at the start "@", "THE" (only when followed by a space) and "WWW", alone or in combination. Para 10: disregard spaces between permitted characters [N41].

Prototype `ch_same_as_key` outputs [N3]: "ACME LIMITED", "Acme Ltd.", "ACME UK LIMITED", "ACME (UK) LIMITED", "THE ACME COMPANY LIMITED", "ACME & CO LTD", "ACME AND COMPANY LIMITED", "ACME GREAT BRITAIN LIMITED", "A.C.M.E. LIMITED", "ACME PLC", "ACME LLP", "ACME CYF", "WWW.ACME.CO.UK LIMITED" and "ACMÉ LIMITED" all give `ACME`; "ACME HOLDINGS LIMITED" and "ACME HOLDING LTD" give `ACMEHOLDING`; "BACK TO BASICS LIMITED" and "BACK 2 BASICS LTD" give `BACK2BASIC`; "ACME@WORK LTD" and "ACME AT WORK LIMITED" give `ACME@WORK`; "ACME ONE LTD" gives `ACMEONE` but "ACME 1 LIMITED" gives `ACME1`, because a number word at the very end is not followed by a space and para 4 does not apply as worded (check the exact wording before relying on this edge). Use the key only for UK-registered names: as a blocking key and as strong but not conclusive evidence (it intentionally merges HOLDING/HOLDINGS and ACME/ACME UK).

## 11. nomenklatura logic_v2 and name_based matchers (Q11, design reference)

- `LogicV2` ("logic-v2") features and weights: `name_match` 1.0, `address_entity_match` 0.98, `crypto_wallet_address` 0.98, `isin_security_match` 0.98, `lei_code_match`, `ogrn_code_match`, `vessel_imo_mmsi_match`, `inn_code_match`, `bic_code_match`, `uei_code_match`, `npi_code_match` 0.95 each, `identifier_match` 0.85, `weak_alias_match` 0.8; qualifiers `address_prop_match` +0.2, `country_mismatch` -0.2, `dob_year_disjoint` -0.15, `dob_day_disjoint` -0.25, `gender_mismatch` -0.2. `compute_score` takes the maximum weighted main feature, adds qualifiers only if it is above zero, and clips to [0, 1] [N8].
- Name matching (`logic_v2/names/match.py`): literal early exit on equal `comparable` forms when part tags are compatible; otherwise names are consolidated, pairs pruned by shared scripts or shared symbols (`names_product`), symbol pairings from `pair_symbols` scored per category (`SYM_SCORES`: NAME 0.9, ORG_CLASS 0.8, INITIAL 0.9, NICK 0.6, SYMBOL, DOMAIN, NUMERIC, LOCATION 0.9; `SYM_WEIGHTS`: ORG_CLASS 0.7, INITIAL 0.5, NICK 0.8, SYMBOL 0.3, DOMAIN 0.7, NUMERIC 1.3, LOCATION 0.8), residues aligned with `align_person_name_order` (persons) or `NamePart.tag_sort` and scored by `compare_parts`; unmatched parts weigh `nm_extra_query_name` 0.8 and `nm_extra_result_name` 0.2, stopwords 0.7, family-name alignments `nm_family_name_weight` 1.3; the score is the weighted mean of alignment scores [N8].
- `name_based`: `OFACMatcher` ("ofac") emulates OFAC's Sanctions List Search from FAQ 249 (whole-string Jaro-Winkler gated by the first letter, SimMetrics-style Jaro-Winkler without the 0.7 boost threshold, per-token best pairing with a 0.5 floor, query tokens of two characters or fewer dropped) and subtracts country, DOB, gender and organisation-ID mismatch qualifiers; `NameMatcher` and `NameQualifiedMatcher` are deprecated in its favour [N8][N15]. The default algorithm is `RegressionV1`; `EntityResolveRegression` ("erun") is the dedupe default [N8].
- For NeonRadar: borrow the ideas (symbol pairing first, asymmetric extra-part weights, family-name boost, identifier features as near-deterministic evidence) as Splink comparison levels and keep `LogicV2.compare` as an optional offline second opinion for clerical review; do not run nomenklatura in the pipeline.

## 12. Verified Splink wiring and pitfalls

This ran with splink 5.0.0, duckdb 1.5.6 and rigour 2.5.0 in Python 3.14.6: two renderings of the same Flat 3 address reached the top address level, Flat 3 vs Flat 4 fell to the else level, two shared NAME QIDs gave the top `ArrayIntersectAtSizes` level and equal postcodes the exact level [N3][N43].

```python
import duckdb, pyarrow as pa
import splink.comparison_library as cl
import splink.comparison_level_library as cll
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
from rigour.addresses import compare_address

con = duckdb.connect()
con.create_function("rigour_addr", lambda a, b: float(compare_address(a or "", b or "")),
                    ["VARCHAR", "VARCHAR"], "DOUBLE")
db_api = DuckDBAPI(connection=con)
sdf = db_api.register(pa.Table.from_pylist(rows), dataset_display_name="people")  # rows carry pc, addr, name_symbols
addr = cl.CustomComparison(output_column_name="addr", comparison_levels=[
    cll.NullLevel("addr"),
    cll.CustomLevel("rigour_addr(addr_l, addr_r) >= 0.9", label_for_charts="addr >= 0.9"),
    cll.CustomLevel("rigour_addr(addr_l, addr_r) >= 0.3", label_for_charts="addr >= 0.3"),
    cll.ElseLevel()])
settings = SettingsCreator(link_type="dedupe_only",
    comparisons=[cl.PostcodeComparison("pc"), cl.ArrayIntersectAtSizes("name_symbols", [2, 1]), addr],
    blocking_rules_to_generate_predictions=[block_on("pc")])
pairs = Linker(sdf, settings).inference.predict()
```

Pitfalls found while testing [N3][N4]:
- `jaro_winkler` in rigour returns 0.0 at or below 0.6: for "rana" and "nora" DuckDB's `jaro_winkler_similarity` (what Splink's DuckDB levels call) and rigour's raw function gave 0.5, `rigour.text.jaro_winkler` gave 0.0. Do not mix the two in one feature.
- `maybe_ascii`, `metaphone` and `soundex` do nothing useful on a string that contains Arabic; tokenise first and handle scripts per token.
- `normality.ascii_text` inserts `?` for characters it cannot map (ʿ, ʾ); strip them or pre-delete U+02BB to U+02BF, U+2018, U+2019.
- `remove_address_keywords` and `shorten_address_keywords` emit `DeprecationWarning`; fingerprints and name symbols change with rigour data releases, so persisted keys need `keys_version` and a rebuild on upgrade.
- `fuzzy=True` country lookups produce confident wrong codes; never use them for nationality.
- jellyfish 1.3.0 changed metaphone for word-final GH; pin phonetic libraries with the same discipline as rigour [N44].

## Sources

- [N1] PyPI JSON API: https://pypi.org/pypi/rigour/json, https://pypi.org/pypi/normality/json, https://pypi.org/pypi/pyicu/json, https://pypi.org/pypi/followthemoney/json, https://pypi.org/pypi/nomenklatura/json, https://pypi.org/pypi/jellyfish/json, https://pypi.org/pypi/rapidfuzz/json, https://pypi.org/pypi/anyascii/json, https://pypi.org/pypi/python-stdnum/json, https://pypi.org/pypi/chardet/json, https://pypi.org/pypi/camel-tools/json, https://pypi.org/pypi/pyarabic/json, https://pypi.org/pypi/tashaphyne/json, https://pypi.org/pypi/qalsadi/json, https://pypi.org/pypi/arabic-reshaper/json, https://pypi.org/pypi/unidecode/json, https://pypi.org/pypi/text-unidecode/json, https://pypi.org/pypi/postal/json, https://pypi.org/pypi/pypostal-multiarch/json; checked 2026-10-18.
- [N2] PyPI JSON for binary ICU options: https://pypi.org/pypi/pyicu-wheels/json, https://pypi.org/pypi/icu4py/json, https://pypi.org/pypi/icupy/json, https://pypi.org/pypi/PyICU-binary/json; icu4py 1.1.0 cp314 wheel contents inspected; https://github.com/Init7/pyicu (README); checked 2026-10-18.
- [N3] Verified by running scripts in Python 3.14.6 (uv 0.11.32) with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 (ICU 74.2), followthemoney 4.11.0, nomenklatura 4.17.2, jellyfish 1.3.0, rapidfuzz 3.14.6, anyascii 0.3.3, splink 5.0.0, duckdb 1.5.6; scripts in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p2-names/scripts/`; 2026-10-18.
- [N4] rigour 2.5.0 installed source: `rigour/_core.pyi`, `rigour/names/*.py`, `rigour/text/*.py`, `rigour/addresses/*.py`, `rigour/ids/*.py`, `rigour/territories/*.py`; verified by reading in Python 3.14.6 with rigour 2.5.0, 2026-10-18.
- [N5] rigour repository at tag v2.5.0 (commit b0ba4adce7c99a5947b45d3461c69278e808521d): https://github.com/opensanctions/rigour/tree/v2.5.0 (`LICENSE`, `README.md`, `docs/data.md`, `resources/names/stopwords.yml`, `symbols.yml`, `org_types.yml`, `resources/territories/mr.yml`, `rust/data/names/person_names.txt`, `rust/src/names/person_names.rs`, `rust/build.rs`, `contrib/namesdb/`); checked 2026-10-18.
- [N6] normality 3.1.0 installed source (`normality/__init__.py`, `transliteration.py`, `cleaning.py`, `slugify.py`, `constants.py`); verified in Python 3.14.6, 2026-10-18.
- [N7] followthemoney 4.11.0 installed source (`followthemoney/names.py`, `types/country.py`, `types/name.py`); verified in Python 3.14.6, 2026-10-18.
- [N8] nomenklatura 4.17.2 installed source (`nomenklatura/matching/__init__.py`, `types.py`, `logic_v2/model.py`, `logic_v2/names/*.py`, `name_based/*.py`); verified in Python 3.14.6, 2026-10-18.
- [N9] uv override test: project with `rigour==2.5.0`, `normality==3.1.0`, `pyicu-wheels==2.15.2` and `override-dependencies = ["pyicu; sys_platform == 'never'"]`; verified by running `uv lock` and `uv sync` (uv 0.11.32) and rigour in Python 3.14.6, 2026-10-18.
- [N10] Wikidata licensing: https://www.wikidata.org/wiki/Wikidata:Licensing; checked 2026-10-18.
- [N11] OFAC FAQ 249: https://ofac.treasury.gov/faqs/249; checked 2026-10-18.
- [N12] OFAC FAQ 246: https://ofac.treasury.gov/faqs/246; checked 2026-10-18.
- [N13] OFAC FAQ 5: https://ofac.treasury.gov/faqs/5; checked 2026-10-18.
- [N14] OFAC weak aliases FAQs 122 to 125: https://ofac.treasury.gov/faqs/topic/1646/print; checked 2026-10-18.
- [N15] OpenSanctions, "How we reverse-engineered OFAC's sanctions screening algorithm" (2026-07-01): https://www.opensanctions.org/articles/2026-07-01-ofac-matcher/; checked 2026-10-18.
- [N16] OFSI penalty notice, Bank of Scotland plc: https://assets.publishing.service.gov.uk/media/697741f167ae94b3280137ee/Penalty_Publication_Notice_LBG_2026.pdf; checked 2026-10-18.
- [N17] OFSI blog, 23 February 2026: https://ofsi.blog.gov.uk/2026/02/23/sanctions-compliance-in-practice-lessons-from-ofsis-160000-bank-of-scotland-penalty/; checked 2026-10-18.
- [N18] FCDO, Format guide for the UK Sanctions List: https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list; checked 2026-10-18.
- [N19] UN Security Council Consolidated List: https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list; checked 2026-10-18.
- [N20] Council of the EU, EU Best Practices for the effective implementation of restrictive measures, 11623/24 (3 July 2024): https://data.consilium.europa.eu/doc/document/ST-11623-2024-INIT/en/pdf; checked 2026-10-18.
- [N21] ICAO Doc 9303 Part 3, 8th edition 2021 (Section 6, Tables 6.A to 6.C): https://icao.int/publications/Documents/9303_p3_cons_en.pdf; checked 2026-10-18.
- [N22] ALA-LC Arabic romanization table, 2012: https://www.loc.gov/catdir/cpso/romanization/arabic.pdf; checked 2026-10-18.
- [N23] BGN/PCGN, Romanization of Arabic, 1956 system (revised presentation 2019): https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/858000/ROMANIZATION_OF_ARABIC.pdf; checked 2026-10-18.
- [N24] UNGEGN Working Group on Romanization Systems, report on Arabic, version 5.0 (June 2018): https://arhiiv.eki.ee/wgrs/rom1_ar.pdf; checked 2026-10-18.
- [N25] ISO 233-2:1993: https://www.iso.org/standard/4118.html; checked 2026-10-18.
- [N26] DIN 31635:2011-07: https://dinmedia.de/en/standard/din-31635/140593750; checked 2026-10-18.
- [N27] IFLA Cataloguing Section, Names of Persons: Arabic Names (2018): https://repository.ifla.org/handle/20.500.14598/3933 (PDF https://repository.ifla.org/bitstreams/e41641d3-309d-4108-ada8-86cf282ae354/download); checked 2026-10-18.
- [N28] CAMeL Tools 1.6.0: wheel source (`camel_tools/utils/normalize.py`, `dediac.py`, `charmaps/`), https://pypi.org/project/camel-tools/, https://raw.githubusercontent.com/CAMeL-Lab/camel_tools/HEAD/LICENSE; checked 2026-10-18.
- [N29] Licence files: https://raw.githubusercontent.com/linuxscout/pyarabic/HEAD/LICENSE, https://raw.githubusercontent.com/linuxscout/tashaphyne/HEAD/LICENSE, https://raw.githubusercontent.com/mpcabd/python-arabic-reshaper/HEAD/LICENSE, https://raw.githubusercontent.com/anyascii/anyascii/HEAD/LICENSE; checked 2026-10-18.
- [N30] UPU, United Kingdom addressing (11/2011): https://www.upu.int/UPU/media/upu/PostalEntitiesFiles/addressingUnit/gbrEn.pdf; checked 2026-10-18.
- [N31] ESFA, ILR Specification 2015 to 2016, Appendix C: Valid Postcode Format (February 2015): https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/404522/ILRSpecification_2015_16_Appendix_C_Feb2015_v1.pdf; checked 2026-10-18.
- [N32] UKVI, Bulk data transfer: validation rules for CAS upload (valid from 12 November 2015), section 3.1: https://www.gov.uk/government/publications/bulk-data-transfer-for-sponsors-validation-rules-for-cas-upload and https://assets.publishing.service.gov.uk/media/5a7f3ff4ed915d74e33f5438/Bulk_Data_Transfer_-_additional_validation_valid_from_12_November_2015.pdf; checked 2026-10-18.
- [N33] ONS, Postal geography: https://www.ons.gov.uk/methodology/geography/ukgeographies/postalgeography; checked 2026-10-18.
- [N34] ONS, Geography licences (terms and conditions of supply): https://www.ons.gov.uk/methodology/geography/licences; checked 2026-10-18.
- [N35] Ordnance Survey, Code-Point Open: https://www.ordnancesurvey.co.uk/business-government/products/code-point-open; checked 2026-10-18.
- [N36] e-GIF Government Data Standards Catalogue, Volume 2, issue 0.5 (consultation, 2001), archived: https://webarchive.nationalarchives.gov.uk/ukgwa/+mp_/http://www.cabinetoffice.gov.uk/media/254290/GDS%20Catalogue%20Vol%202.pdf; checked 2026-10-18.
- [N37] libpostal README and LICENSE: https://raw.githubusercontent.com/openvenues/libpostal/master/README.md, https://raw.githubusercontent.com/openvenues/libpostal/HEAD/LICENSE, https://raw.githubusercontent.com/openvenues/pypostal/HEAD/LICENSE; PyPI `postal` and `pypostal-multiarch` [N1]; checked 2026-10-18.
- [N38] Companies House XML forum, "IMPORTANT CHANGES to Country and Nationality fields" (23 October 2017): https://xmlforum.companieshouse.gov.uk/t/important-changes-to-country-and-nationality-fields/351; checked 2026-10-18.
- [N39] Companies House, Nationalities and countries for company filings: https://www.gov.uk/government/publications/nationalities, https://www.gov.uk/government/publications/nationalities/list-of-nationalities, https://www.gov.uk/government/publications/nationalities/list-of-countries; checked 2026-10-18.
- [N40] FCDO, Geographical names and information (Geographical Names Index July 2026): https://www.gov.uk/government/publications/geographical-names-and-information and https://assets.publishing.service.gov.uk/media/6a5e0ceb9e2827ee5f6d08ca/FCDO_Geographical_Names_Index_July2026.csv; checked 2026-10-18.
- [N41] SI 2015/17 Schedule 3: https://www.legislation.gov.uk/uksi/2015/17/schedule/3 (https://www.legislation.gov.uk/uksi/2015/17/schedule/3/data.xml was refused with HTTP 429); checked 2026-10-18.
- [N42] SI 2015/17 Schedule 2: https://www.legislation.gov.uk/uksi/2015/17/schedule/2; checked 2026-10-18.
- [N43] Splink 5.0.0 installed source, `splink/internals/comparison_library.py` (`PostcodeComparison`, `ArrayIntersectAtSizes`, `CustomComparison`); verified in Python 3.14.6, 2026-10-18.
- [N44] jellyfish changelog: https://raw.githubusercontent.com/jamesturk/jellyfish/main/docs/changelog.md; checked 2026-10-18.
- [N45] Companies House forum, "List of all nationality values" (April 2024): https://forum.companieshouse.gov.uk/t/list-of-all-nationality-values/7817; checked 2026-10-18.
- [N46] NeonRadar Phase 1 notes: `/home/claude/neonradar-phase1/kit/research/stack.md` (sections 3.5, 4.2, 4.3), `sources-opensanctions-ftm-icij.md` (B.2, B.5), `sources-ch-gleif.md` (company number normalisation, officer fields); read 2026-10-18.
