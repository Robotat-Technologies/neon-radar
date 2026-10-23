# Labelling guide

How to judge whether two records describe the same person or organisation, for everyone who labels pairs for NeonRadar's published precision figure ([PHASE-2.md](../build/PHASE-2.md) 7.3, [Assignment 3](../team/assignment-3.md)). Read the [entity resolution overview](README.md) first: it explains where the pairs come from and why the figure matters.

Your labels are the measurement. Nobody can check them against a right answer afterwards, so the figure is only as honest as the labels: label what the two cards show, take your time, and say `unsure` when the cards do not decide. Every example on this page is synthetic, from the benchmark in `data/fixtures/er-bench/`: the people and companies in it were invented by NeonRadar's generator, and any likeness to a real person or company is unintended.

## What you will see

You label with `neonradar er label` (milestone M2.10c), at a terminal on an approved machine, in a session of your own:

```bash
uv run neonradar er label --profile uk-sample --run <run id> --labeller @your-handle
```

The run id and the session times come from the graph mentor. The command shows the next pair assigned to you as two record cards side by side ([PHASE-2.md](../build/PHASE-2.md) 7.3 rule 2):

| On each card | Not shown anywhere |
|---|---|
| the source dataset and the kind of record; the names in their original scripts; birth dates; nationalities and countries; postcodes and towns; linked companies (names and numbers); identifiers; a link to the source record (leave it closed, privacy rule 7) | the match probability; the rule or method that joined the records, if any; which sample the pair comes from; anyone else's label |

The pairs mix merges NeonRadar made with possible matches it did not make, in one random order, so neither the order nor the screen tells you what NeonRadar thought. Do not try to guess it: judge the two cards. Answer `s` (same), `d` (different) or `u` (unsure), and add a note if you like (see [Notes](#notes)). Each answer is saved at once, nothing is pre-selected, and you can stop and resume where you left off.

## What "the same entity" means

**A person** is one human being. Two records are the same entity when they describe the same person, whatever the source, the role, the date or the spelling: an officer appointment and a shareholding of one person are the same entity. A person and a company they own or direct are two entities.

**An organisation** is one legal entity, such as one company or one limited liability partnership; in the UK register each has its own company number.

- **A subsidiary is not its parent**, even when the parent owns all of it, they share directors or an address, or their names differ only by a word such as "Holdings" or "UK". [Example 10](#example-10-a-parent-and-the-company-it-owns) shows a company and the company that owns it.
- **A trading name is the same company.** A company that trades under another name is still one legal entity.
- **A renamed company is the same company.** The register keeps a company's previous names, with the date of each change, under its one company number [ch_free_company_data]. An old record with the former name and a new one with the current name describe one entity (see [A name change](#a-name-change)).
- **Companies incorporated in different countries are different companies**, even with the same name and inside one group.

Some records do not say whether they describe a person or an organisation (a leak record of schema `LegalEntity`, for example). Judge such a record against the other card: if the other card is a person, ask whether the record describes that person.

Being linked to each other is not being the same. Two records that point at each other, an owner and the company it owns, a director and their company, are almost always two entities.

## How to judge from partial information

Records are rarely complete: an officer record gives a birth month but no day, a list entry gives a full date but no address, a leak record may give only a name. Read both cards completely, then work through the evidence in this order.

1. **Identifiers.** The same official identifier on both cards (a company number, an LEI, a UN reference number, a passport number) is strong evidence of the same entity when the names are compatible. Two different identifiers of a kind an entity has only one of (two company numbers, two LEIs) are strong evidence of two entities. Two exceptions: one person can hold several Companies House person numbers ([PHASE-2.md](../build/PHASE-2.md) 7.1.2, rule D3), and the UK Sanctions List gives a person one Unique ID per regime, so "there may be different Unique IDs for one designated person" [fcdo_format_guide]. A different number of those kinds proves nothing. A list entry can also carry the number of a related company, which is why the names must agree too.
2. **Dates.** Birth dates that differ at a precision both cards give (June 1996 against October 1996) mean two people. A month on one card and a full date on the other agree if the month agrees. A list entry may give a range of years or two possible dates; any one of them can agree.
3. **Names.** Compare the names after allowing for the variations under [Common traps](#common-traps). A difference that no variation explains (another given name, a middle name that cannot match the other card's initial) is a conflict.
4. **Ties.** Look for something a different person or company with the same name would be unlikely to share: the same identifier, the same full postcode, a role in the same company, a full birth date (day, month and year) on both cards, or the same incorporation date.
5. **Weak agreement.** A shared nationality, town, postcode district, birth year or birth month is what different people with the same name often share too. On its own it is not a tie.
6. **Missing is not different.** A field on one card and not on the other counts neither for nor against.

Then decide:

| Answer | When |
|---|---|
| `same` | The names are compatible, nothing conflicts that a known variation does not explain, and at least one tie (step 4) connects the two cards |
| `different` | Something conflicts that no variation explains: different birth dates at a precision both give, two identifiers of a kind one entity has only one of, names that cannot belong to one entity, or one card describes the owner or parent of the other |
| `unsure` | Nothing ties the cards and nothing conflicts, or a tie and a conflict stand against each other and you cannot explain the conflict |

This is how the publishers of the lists and of the leak database ask people to treat a match: OFSI separates a name match from a match on all the information on the list [ofsi_general_guidance_2026], OFAC asks whether only the first or last name matches and whether the date of birth, identification number or nationality differs [ofac_faq_5], and ICIJ, which publishes the Offshore Leaks Database, asks users to confirm identities with addresses or other identifiable information [icij_faq]. A name match is where the check starts, not where it ends.

## Common traps

Every trap except the name change has a worked example below, from the synthetic benchmark.

| Trap | What to do | Examples |
|---|---|---|
| **Transliterations.** Arabic and Cyrillic names have many Latin spellings: vowels are guessed, ق becomes Q or K, the article is written al-, el- or joined, and Russian and Ukrainian forms differ (Pyotr, Petr, Piotr, Petro) | Treat spellings of one name in one script, or across scripts, as compatible. A spelling is not a tie; look for a tie as usual | [1](#example-1-one-arabic-name-two-latin-spellings), [2](#example-2-russian-and-ukrainian-forms-of-one-name) |
| **Initials and dropped middle names.** One record gives a middle name, another its initial or nothing | An initial agrees with any name, or any spelling of a name, that starts with it; a missing middle name agrees with anything. A different full middle name, or an initial that fits no spelling of the other card's name, conflicts | [4](#example-4-a-middle-name-and-its-initial), [6](#example-6-near-twins-with-different-middle-names), [7](#example-7-same-name-same-month-nothing-else) |
| **Swapped name order.** Lists and some registers write the surname first; Companies House writes `SURNAME, Forenames` | Compare the parts, not the order | [3](#example-3-surname-first-and-a-shared-un-reference) |
| **Titles, capitals and punctuation.** Mr, Mrs, Dr; all capitals; commas | Ignore them. A title can change between records (Miss, Mrs, Ms) | [2](#example-2-russian-and-ukrainian-forms-of-one-name), [4](#example-4-a-middle-name-and-its-initial) |
| **Typos.** One or two letters wrong in one word | Compatible, when the rest of the name and a tie agree | [9](#example-9-one-company-number-a-typo-and-a-legal-form) |
| **Moved addresses.** A person's service address changes over time, and one source shows an old one | A different postcode is weak evidence against; a role in the same company or another tie can still decide `same` | [1](#example-1-one-arabic-name-two-latin-spellings), [5](#example-5-a-moved-address) |
| **Near twins.** A different person with the same name, birth year or month and sometimes the same district | Look for a conflict (a different middle name, a different birth month) or a tie; without either, answer `unsure` | [6](#example-6-near-twins-with-different-middle-names), [7](#example-7-same-name-same-month-nothing-else), [8](#example-8-two-companies-with-the-same-name-core) |
| **Legal forms.** Ltd, Limited, LTD., & and "and", a leading "The" | Spellings of one legal form are compatible. Different legal forms (an LLP and a PLC) point to two entities, unless the same company number ties the records together | [8](#example-8-two-companies-with-the-same-name-core), [9](#example-9-one-company-number-a-typo-and-a-legal-form) |
| **Parent and subsidiary.** An owner and the company it owns, often with similar names | Two legal entities: `different` | [10](#example-10-a-parent-and-the-company-it-owns) |
| **A name change.** A company's former and current names | One entity, if the company number or another tie agrees | [below](#a-name-change) |

### A name change

The benchmark has no renamed companies, so this trap has no worked example; here is its shape, with placeholders instead of names. Card A is an older record, for example a GLEIF or officer record, that gives the company's former name and its company number. Card B is the register record with the current name and the same number, and it lists the former name as a previous name [ch_free_company_data]. The right answer is `same`: one legal entity changed its name. Without the number or another tie, two different names are not evidence of one company, and the answer is `unsure` at most.

## When to answer unsure

Answer `unsure` when, after reading both cards completely:

- nothing ties the two cards together and nothing conflicts (the typical case: the same name and birth month, and nothing else; [example 7](#example-7-same-name-same-month-nothing-else)), or
- a tie and a conflict stand against each other and no known variation explains the conflict.

A record that gives only a name is the common case. The benchmark's leak-style record `syn-erb-r-5e3efc8464e109f8` gives one name string, "MAKSIM ARSENYEVICH BRAKESBER", and nothing else; the officer record `syn-erb-r-daffb111ff31d33b` gives "BRAKESBER, Maksim Arsenyevich", born June 1992, Russian, at QQ40 2BY. The names agree in full, but a name alone does not establish identity [icij_faq] [ofsi_general_guidance_2026], so the right answer for this pair is `unsure`, even though the benchmark's answer key says both records belong to one invented person. Your label describes what the cards show, not what you suspect.

Do not answer `unsure` to save time, when a case feels hard but the steps above decide it, or because a name is unfamiliar to you. Every `unsure` has a cost ([PHASE-2.md](../build/PHASE-2.md) 7.3 rule 3):

- It is left out of the headline precision, which is computed over `same` and `different` labels only.
- The report also publishes the precision as if every `unsure` pair were wrong, k / (n + u). Each `unsure` lowers that published bound.
- When more than 15 percent of the labels are `unsure`, the report says so in its first line.

## Notes

A note is optional. Write one when the decision was close, so that an adjudicator or an auditor can see your reasoning, and always when you answer `unsure`: say what was missing. Say only how the fields compare, never a value from a card: "same company, birth month agrees, Q and K spellings" or "names agree in full, nothing else on the leak record". Label files hold record ids and labels only ([real-data handling](../data/real-data-handling.md), rule 8), so a note never holds a name, a date, a nationality, a town, a postcode, a company's name or sector, an identifier or a record id.

## Privacy rules for labelling sessions

Labelling shows real records about real people. These rules hold in every session ([PHASE-2.md](../build/PHASE-2.md) 2.1 G9 and 7.4; [real-data handling](../data/real-data-handling.md)):

1. **Approved machine only.** Label only on a machine listed in [real-data-machines.md](../data/real-data-machines.md) (full-disk encryption, screen lock), never in GitHub Codespaces, CI or a cloud session. Lock the screen whenever you step away.
2. **You, at a terminal.** `er label` refuses to run without a terminal. Run it yourself; never ask an AI agent, a script or another person to run it for you.
3. **No screenshots.** No screenshots, photos, screen recordings or screen sharing of the cards.
4. **No names or other card values outside the session.** Not in chat, email, notes of your own, learning logs, issues, pull requests, slides or teach-backs. When you talk about a case, say only how the fields compare ("same surname, birth years one apart, different nationality", "same postcode district, different companies"), never a value from a card: no name, date, nationality, town, postcode, company name or sector, identifier or record id ([Assignment 3](../team/assignment-3.md)).
5. **Labels stay where they are.** Your labels live in `data/cache/real/labels/<profile>/<run id>/` on that machine. Never copy, email or commit them; they are deleted after `access.label_days` (30 days by default, [project.yaml](../build/project.yaml)).
6. **No AI tools for labelling.** AI help is fine for understanding the method, never for deciding a label, and never paste a card or any part of it into an AI tool (G10, G9). Run `er label` in a plain terminal window, not in an editor's built-in terminal or a terminal with AI features, and switch off any assistant that can read or record the screen for the whole session.
7. **Judge from the cards only.** Do not search the web or other sources for the people and companies on the cards, and do not open a card's source link while you label: a search sends the name off the machine, a source page leaves real records in the browser's history and cache, and the other labellers judge from the same cards as you.
8. **If something is wrong, stop.** If real data shows up anywhere it should not be, stop and tell the data steward and the tech lead at once; do not try to fix it yourself ([PHASE-2.md](../build/PHASE-2.md) 7.4 rule 10).

## How adjudication works

1. **Overlap.** Fifty pairs of the sample (40 from the merges, 10 from the possible matches) are labelled by two different people. You will not know which of your pairs they are.
2. **Agreement first.** Before any disagreement is settled, the report gives the percentage agreement, Cohen's kappa [cohen_1960], the share of `same`, and positive and negative agreement [cicchetti_feinstein_1990], so that the published agreement is the labellers' own.
3. **Blind adjudication.** Each overlap pair whose two labels differ goes to an adjudicator, who sees the two cards but neither label, and records a label with `neonradar er label --adjudicate`. The adjudicated label is the one that counts.
4. **Who adjudicates.** Someone who did not set the thresholds: the project lead by default, never the tech lead or the graph mentor, and never anyone who labelled that pair; the tool refuses them ([PHASE-2.md](../build/PHASE-2.md) 7.3 rule 4, M2.10c). While one person holds every role ([OD-6](../build/operator-decisions.md)), the project lead names someone else for this step.

## Worked examples

Ten pairs from the synthetic benchmark. Each card shows the kinds of field the labelling tool shows, worded in the style of the source the benchmark record imitates; the tool lays them out in its own way. The Record row is not on the tool's cards, which show no record ids: it is here so that you, and the test named below, can find each record in the benchmark. "Benchmark truth" is the generator's answer key (`data/fixtures/er-bench/labels/er_truth.csv`), which real data never has; "right answer" is the label these cards support. They differ only in example 7. A test (`resolve/tests/test_labelling_guide.py`) checks that every record id on this page exists in the benchmark, that the names and linked companies on each card are those of its record, and that each answer key matches the truth file.

Try each example yourself before you read the answer.

### Example 1: one Arabic name, two Latin spellings

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-71e612767907c2a6` | `syn-erb-r-f3884df70c08f16c` |
| Source | Companies House officer (style) | Companies House officer (style) |
| Name | BERQANYUN, Salah al-Din | BERKANYUN, Salah Eddine |
| Born | 1987-05 | 1987-05 |
| Nationality | Egyptian (`eg`) | not given |
| Postcode and town | QQ65 3AG, Bristol | QQ68 4HJ, Birmingham |
| Linked companies | director of BIRCH & SEDGE FREIGHT LTD. | director of BIRCH & SEDGE FREIGHT LTD. |
| Identifiers | Companies House person number SYN794820007 | Companies House person number SYN794820004 |

**Right answer:** `same`. **Benchmark truth:** `same`.

Why: Salah al-Din and Salah Eddine are two Latin spellings of one Arabic given name, and BERQANYUN and BERKANYUN differ only in Q and K, two common renderings of the letter qaf; their consonant skeletons are identical. The birth month agrees, a missing nationality counts for nothing, and the tie is a role in the same company. The different postcodes are a moved service address, not a conflict. The two person numbers differ, which proves nothing (step 1). NeonRadar's rule D3 reads their shared first eight characters as one person, a reading Companies House has not confirmed ([PHASE-2.md](../build/PHASE-2.md) 3.3), so this guide does not count it as a tie.

### Example 2: Russian and Ukrainian forms of one name

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-b1559489dc890a92` | `syn-erb-r-d2ecbef63e922849` |
| Source | Companies House officer (style) | Companies House PSC (style) |
| Name | BERBRAFEN, Pyotr | Dr Petro Berbrafen |
| Born | 1945-11 | 1945-11 |
| Nationality | not given | Ukrainian (`ua`) |
| Postcode and town | QQ7 1NE, London | QQ7 1NE, London |
| Linked companies | director of THE OSIER DALE LOGISTICS PLC | holds more than 25 and at most 50 percent of the shares of FLINT LEAT TRADING LIMITED |

**Right answer:** `same`. **Benchmark truth:** `same`.

Why: Pyotr is a Latin spelling of the Russian form of the name, Petro the Ukrainian form of the same name, and the title "Dr" does not matter. The birth month agrees and the tie is the same full postcode. The two records link to different companies, which is normal: one person can direct one company and own shares in another. Beware: the benchmark also holds a different man, "BERBRAFEN, Piotr", born in the same month, at QQ35 0NN in Birmingham (`syn-erb-r-1e21284a7654b359`). Against card A, he has the same name in another spelling and the same birth month, but nothing ties them together and nothing conflicts: that pair is `unsure`. Only the full postcode decides this example.

### Example 3: surname first, and a shared UN reference

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-307ab2860abcd4ca` | `syn-erb-r-5642cb3939681203` |
| Source | sanctions list entry (synthetic, Synthetic Authority C) | sanctions list entry (synthetic, Synthetic Authority B) |
| Name | Ostap Traselrim; also Остап Тразелрим, Ostap Trazelrim | Trazelrim Ostap; also Остап Тразелрим, Ostap Traselrim |
| Born | 1952-04-11 | 1952 |
| Nationality | Ukrainian, Maltese (`ua`, `mt`) | Ukrainian, Maltese (`ua`, `mt`) |
| Postcode and town | not given | not given |
| Identifiers | UN reference ZZi.999157; list entry SYC-990019 | UN reference ZZi.999157; list entry SYB-990013 |

**Right answer:** `same`. **Benchmark truth:** `same`.

Why: card B writes the surname first, and each card's other spellings include the other's (s and z for the Cyrillic з). The full date on card A falls in the year on card B, the nationalities agree, and the tie is the shared UN reference number, which national lists carry for an entry that implements a UN Security Council listing [fcdo_format_guide] [unsc_consolidated_list] (rule D4 joins such entries). The two list entry numbers differ because each list numbers its own entries; that is not a conflict.

### Example 4: a middle name and its initial

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-48a754c4a288af89` | `syn-erb-r-0beba596d07ae1d1` |
| Source | Companies House PSC (style) | Companies House officer (style) |
| Name | Ms Wafaa Husayn Tharvinzel | THARVINZEL, Wafaa H |
| Born | 1984-12 | 1984-12 |
| Nationality | Moroccan (`ma`) | not given |
| Postcode and town | QQ42 0HG, Manchester | QQ42 0HG, Manchester |
| Linked companies | holds more than 25 and at most 50 percent of the shares of LICHEN HOLM HOLDINGS LTD. | director of THE ELDER THORPE PACKAGING LTD |
| Identifiers | not given | Companies House person number SYN370370008 |

**Right answer:** `same`. **Benchmark truth:** `same`.

Why: the initial H fits the middle name Husayn, the birth month agrees, and the tie is the same full postcode. A person number on one card only counts for nothing. Keep card A in mind for example 6.

### Example 5: a moved address

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-0efd3c164bf61a31` | `syn-erb-r-d627be12c55fd3b9` |
| Source | Companies House officer (style) | Companies House PSC (style) |
| Name | MIOSKEMIO, Lisa Andrea | Mrs Lisa Andrea Mioskemio |
| Born | 1943-01 | 1943-01 |
| Nationality | British (`gb`) | British (`gb`) |
| Postcode and town | QQ42 6XE, Birmingham | QQ8 0XN, London |
| Linked companies | director of SEDGE & FLINT VENTURES PLC | holds more than 50 and less than 75 percent of the shares of SEDGE & FLINT VENTURES PLC |

**Right answer:** `same`. **Benchmark truth:** `same`.

Why: the full names agree, the birth month and the nationality agree, and the tie is the same company: a director and a major shareholder of SEDGE & FLINT VENTURES PLC with this name and birth month. The postcodes differ, in different towns, because the two records show service addresses from different times. A different postcode is weak evidence against, and here a tie outweighs it.

### Example 6: near twins with different middle names

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-48a754c4a288af89` | `syn-erb-r-119a846ec90f277c` |
| Source | Companies House PSC (style) | Companies House officer (style) |
| Name | Ms Wafaa Husayn Tharvinzel | THARVINZEL, Wafaa Khaled |
| Born | 1984-12 | 1984-12 |
| Nationality | Moroccan (`ma`) | Egyptian (`eg`) |
| Postcode and town | QQ42 0HG, Manchester | QQ42 4WA, Manchester |
| Linked companies | holds more than 25 and at most 50 percent of the shares of LICHEN HOLM HOLDINGS LTD. | director of THE BRIAR SIKE ENGINEERING LTD |

**Right answer:** `different`. **Benchmark truth:** `different`.

Why: card A is card A of example 4. The surname, the first given name, the birth month and the postcode district all agree, which is exactly what the benchmark's near twins share. But the middle names conflict: Husayn and Khaled are two different names, not two spellings of one name. Nothing ties the cards together (different full postcodes, different companies), so nothing outweighs the conflict; the different nationalities count for little on their own, because one person can hold two. Card B of example 4 would make a harder pair with this card B: its initial H is not the initial of Khaled, but it is the initial of Halid, another Latin spelling of the same Arabic name, so nothing clearly conflicts, nothing ties the two cards, and that pair would be `unsure`.

### Example 7: same name, same month, nothing else

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-1a289cf204e5ed32` | `syn-erb-r-0f3c9200b3bdabe6` |
| Source | Companies House officer (style) | Companies House officer (style) |
| Name | SOLVOSKTESH, Gavin | SOLVOSKTESH, Gavin Alexander |
| Born | 1951-06 | 1951-06 |
| Nationality | not given | British (`gb`) |
| Postcode and town | QQ3 5XS, Manchester | QQ3 2GX, Leeds |
| Linked companies | secretary of BASALT LEAT LOGISTICS LTD | director of SEDGE LEA VENTURES LIMITED |
| Identifiers | Companies House person number SYN241810003 | Companies House person number SYN797490001 |

**Right answer:** `unsure`. **Benchmark truth:** `different`.

Why: the names are compatible (card A gives no middle name), the birth month agrees and the postcodes share a district, QQ3 (the towns differ, Manchester and Leeds, only because the benchmark's generator picks a town without looking at the postcode), so nothing conflicts; the person numbers differ, which proves nothing, because one person can hold several (step 1). But nothing ties the cards either: different full postcodes, different companies, and every agreement is one that near twins share. The cards do not decide, so the honest label is `unsure`, with a note such as "names and birth month agree, nothing else connects them". The answer key shows why guessing would be wrong: these are two different people, near twins, and a `same` here would count against the published precision.

### Example 8: two companies with the same name core

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-1f10d1575ce2e6c4` | `syn-erb-r-901b592d6795e9ab` |
| Source | Companies House register (style) | Companies House register (style) |
| Name | THE FENNEL & UMBER VENTURES L.L.P. | FENNEL AND UMBER VENTURES PLC |
| Company number | SY104669 | SY828977 |
| Incorporated | 1999-08-09 | 2017-04-04 |
| Postcode and town | QQ44 5GR, London | QQ19 0GT, Leeds |

**Right answer:** `different`. **Benchmark truth:** `different`.

Why: "&" and "and" and a leading "The" are spellings of one name, so the names look alike. But the cards give two different company numbers, two different legal forms (a limited liability partnership and a public limited company) and incorporation dates eighteen years apart: two legal entities. Different company numbers alone decide it (cannot-link rule X3 refuses such a merge in any case).

### Example 9: one company number, a typo and a legal form

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-696f4b7102bf79cc` | `syn-erb-r-3b67993a796c6d4c` |
| Source | Companies House corporate officer (style) | GLEIF record (style) |
| Name | MARRAM LEAT CATEIRNG LTD | Marram Leat Catering Ltd |
| Company number | SY510485 | SY510485 |
| LEI | not given | SYN000XMX55SDGHBSG23 |
| Postcode and town | not given | QQ30 5WS, London |
| Linked companies | corporate director of THE SAFFRON & BASALT INTERIORS, LTD. | none shown |

**Right answer:** `same`. **Benchmark truth:** `same`.

Why: both cards give the same company number, which is the tie, and the names differ only by a typo (CATEIRNG) and capitals. A company acting as a corporate director of another company is still itself; the link describes its role, not a second entity.

### Example 10: a parent and the company it owns

| | Card A | Card B |
|---|---|---|
| Record | `syn-erb-r-ba457410be7ec353` | `syn-erb-r-8a57775a9ea26979` |
| Source | Companies House PSC (style): a corporate person with significant control | Companies House register (style) |
| Name | Amber Acre Catering Ltd. | AMBER HOWE HOLDINGS LTD. |
| Company number | SY321414 | SY882725 |
| Incorporated | not given | 1992-04-02 |
| Postcode and town | not given | QQ59 6XA, London |
| Linked companies | holds at least 75 percent of the shares of AMBER HOWE HOLDINGS LTD. | none shown |

**Right answer:** `different`. **Benchmark truth:** `different`.

Why: card A is a company that owns most of the shares of the company on card B. An owner and the company it owns are two legal entities, however much of it it owns and however alike their names; the different company numbers confirm it. A linked company that matches the other card's name is a sign of a relationship, never of identity.

## Sources

- [ch_free_company_data] Companies House, *Free Company Data Product*, living document. <https://download.companieshouse.gov.uk/en_output.html>
- [cicchetti_feinstein_1990] Domenic V. Cicchetti and Alvan R. Feinstein, *High agreement but low kappa: II. Resolving the paradoxes*, Journal of Clinical Epidemiology 43(6), 1990. <https://doi.org/10.1016/0895-4356(90)90159-M>
- [cohen_1960] Jacob Cohen, *A Coefficient of Agreement for Nominal Scales*, Educational and Psychological Measurement 20(1), 1960. <https://doi.org/10.1177/001316446002000104>
- [fcdo_format_guide] FCDO (GOV.UK), *Format guide for the UK Sanctions List*, 2025. <https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list>
- [icij_faq] ICIJ, *Offshore Leaks Database: frequently asked questions*, living document. <https://offshoreleaks.icij.org/pages/faq>
- [ofac_faq_5] OFAC, *FAQ 5: what to do when a party may match the SDN List*, 2026. <https://ofac.treasury.gov/faqs/5>
- [ofsi_general_guidance_2026] OFSI, *UK financial sanctions general guidance*, 2026. <https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance>
- [unsc_consolidated_list] United Nations, *United Nations Security Council Consolidated List*, living document. <https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list>
