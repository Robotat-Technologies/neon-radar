# NeonRadar UI: the brief for every interface change

Status: **draft**, from the UI meeting of 23 November 2026 (no written minutes). The tech lead
approves it before anyone uses it; until then, the build specs and CLAUDE.md win wherever this
page disagrees with them.

Use this page in two ways: a person reads it before designing or reviewing a screen, and an AI
assistant gets the **prompt** at the end, with the task added under it.

## 1. Who uses NeonRadar, and what they need

The users are investigators and analysts (anti-money-laundering, anti-corruption, journalism),
plus students and reviewers who try the demo. They are careful readers, not designers or
programmers. On every screen they want to:

1. **Read** names, account numbers, amounts and dates without effort.
2. **Follow** a path: who paid whom, who owns what, step by step.
3. **Know what is real:** what is synthetic and what comes from a public source, and where each
   fact comes from.
4. **Keep evidence:** a screenshot, an export or a link that shows the same thing tomorrow.

When a design choice helps one of these four, it wins over a choice that only looks better.

## 2. Decisions already taken

| Decision | Why |
|---|---|
| The network graph stays **2D** (Cytoscape.js), no 3D | Labels must be readable, nothing may hide behind other nodes, screenshots must not depend on a camera angle, and the UI must run on ordinary laptops. Depth is shown inside 2D: hop rings, fading far hops, the alert path on top. |
| **Network design 2** (pale outlined nodes, coloured relationship families) | Chosen in the design comparison; built in #167 to #171. |
| Text keeps **one size on screen** and appears only where it fits | Built in #168. |
| Visual direction for the pages: **[to confirm: proposal 1, the minimalist light one?]** | The meeting compared four proposals; write the chosen one here once the lead confirms it. |
| Deadline: **[to confirm]** | The internship ends soon, so small, finished steps beat a large unfinished redesign. |

## 3. Rules that are never traded for looks

These come from the project's rules (CLAUDE.md, [wording.md](../wording.md), ADR-0005, ADR-0009,
PHASE-4.md 7.6) and are not design choices.

1. **Synthetic is always visible.** A synthetic node or relationship looks different from a
   public one, the key says so, and the synthetic data notice stays on every page that shows data
   (also full screen and on a phone).
2. **The standing notices are never hidden,** collapsed by default or moved below the fold so
   far that nobody reads them. They may be made shorter on small screens only if the lead agrees.
3. **Patterns, never accusations.** The UI shows the alert's own wording. It never adds words
   such as "suspect", "criminal", "guilty" or "fraud", no red "danger" styling on a person, and
   no score that reads as a verdict. Priority is a reading order, not a judgement.
4. **Flags come only from the source records** (sanctioned, PEP and so on) and say their source.
   A possible match is always shown as "not confirmed".
5. **Every fact can be traced:** a click or a link leads to its source record or dataset.
6. **Nothing phones home:** no web fonts, icon sets, maps, analytics or images from another
   host. System fonts and bundled SVG only.
7. **Copilot (when the UI shows it):** the notice and the badge appear before the first question;
   the question never goes into a URL, the page title, browser storage or the history; the
   question box has `autocomplete="off"`.
8. **No proprietary or GPL packages** (never `@neo4j-nvl`). Vue 3.5 with `<script setup
   lang="ts">`, TypeScript ~6.0, Pinia, Vue Router, Cytoscape.js.

## 4. Design principles

1. **Calm by default, loud only for the alert path.** Most of the screen is neutral. One accent
   colour (orange) marks the alert path inside a graph and the step selected on it, and nothing
   else. If everything is coloured, nothing stands out.
2. **Never colour alone.** Every meaning has a second sign: a shape, a line style, an icon or a
   word (WCAG 1.4.1). Check every screen in greyscale.
3. **Text first.** Body text at least 16 px, graph text 12 px on screen, contrast at least 4.5:1
   for text and 3:1 for lines and controls (WCAG 1.4.3, 1.4.11). Long ids wrap
   (`overflow-wrap: anywhere`) instead of pushing the page sideways.
4. **Show little, let people ask for more** (progressive disclosure): the summary first, the
   details one click away. The default view of the graph is readable; the full graph is a choice.
5. **One action, one place.** The same control looks and works the same on every page (hops,
   zoom, fit, table view, back to the entity).
6. **Every state is designed:** loading, empty, error, not found, cut at the size limit, slow
   network, offline. Each says what happened and what the person can do next, in plain words,
   never an API message such as `path.alert_id: String should...`.
7. **Keyboard and screen reader are first-class:** every control is reachable with Tab, has a
   visible focus ring and a name; the graph always has a table view with the same nodes and
   relationships (WCAG 2.1.1, 2.4.7, 4.1.2). Target: WCAG 2.2 level AA.
8. **Right to left ready.** The UI has an Arabic switch: use CSS logical properties
   (`margin-inline-start`, never `margin-left`), mirror arrows that mean "next" and "back", never
   mirror the graph or numbers, and test every screen in Arabic.
9. **Works from 375 px wide.** On a phone the panels stack under the graph; nothing scrolls
   sideways.
10. **Stable evidence.** The same data gives the same picture: a fixed layout seed where
    possible, the zoom level and the hops in the URL, exports that keep the key and the notices.

## 5. Visual language (tokens)

Use the CSS variables in `ui/src/assets/main.css` (`--color-*`, `--space-*`, `--radius`,
`--font-body`) and the graph constants in `ui/src/lib/graph-style.ts` (`FAMILY_COLOURS`,
`ALERT`, `INK`). Never write a new hex value in a component; add a token instead, with its
contrast checked.

- Spacing: steps of `--space-1` to `--space-6` (4 px grid).
- Type scale: page title 1.6rem, section 1.2rem, body 1rem, small 0.85rem; numbers and ids in
  `--font-mono`.
- Graph: node shape = kind of entity, dashed outline = synthetic, relationship colour + line +
  marker = family, orange on top = alert path.

## 6. Definition of done for a UI pull request

- [ ] Screenshots before and after, at 1440 px and 375 px, in English and in Arabic.
- [ ] Every state of section 4.6 checked (loading, empty, error, not found, truncated).
- [ ] Keyboard only: every control reachable and visible when focused.
- [ ] Greyscale check: nothing depends on colour alone.
- [ ] Contrast checked for every new colour.
- [ ] Synthetic marking and notices still visible on the changed screens.
- [ ] No new package from another host or with a GPL or proprietary licence.
- [ ] `make check` green; the PR stays within 400 changed lines (split otherwise).

## 7. The prompt

Copy everything in the box, then write the task under "Task".

```text
You are a senior product designer and front-end engineer working on NeonRadar, an open-source,
local-first graph investigation tool for anti-money-laundering and anti-corruption work. Its
users are investigators and analysts who must read names, amounts and dates, follow money and
ownership paths, tell synthetic data from public data, and keep stable evidence.

Stack: Vue 3.5 (<script setup lang="ts">), TypeScript ~6.0, Pinia, Vue Router, Cytoscape.js for
the 2D graph, plain CSS with the variables in ui/src/assets/main.css and CSS logical
properties. No other UI library unless the task says so.

Hard rules (never trade them for looks):
1. The graph is 2D. Show depth with hop rings, fading and layering, never 3D.
2. Synthetic nodes and relationships always look different from public ones, and the key says
   so. The standing notices and the synthetic data notice stay visible on every page with data.
3. Describe patterns, never accusations: no words like suspect, criminal, guilty or fraud, no
   red danger styling on a person, no score that reads as a verdict. Show the alert's own words.
4. Flags come only from source records; a possible match is always "not confirmed".
5. Nothing loads from another host: system fonts, bundled SVG, no analytics.
6. Never use colour alone: every meaning also has a shape, line style, icon or word.
7. WCAG 2.2 AA: text contrast 4.5:1, lines and controls 3:1, full keyboard use with a visible
   focus ring, names for every control, a table view for every graph.
8. RTL-ready: logical properties only; test in Arabic; never mirror the graph or numbers.
9. Works from 375 px wide with no sideways scroll.
10. Every state is designed: loading, empty, error, not found, truncated, offline, in plain
    words.

Style: calm and neutral, one accent colour (orange) only for the alert path inside a graph and
the step selected on it, never in lists, notices, tabs or links; text first, little shown by default and more one click away. Use the existing tokens; add a
token (with its contrast) instead of a new hex value.

How to answer:
1. Restate the task in one sentence and name the user goal it serves (read, follow, know what
   is real, keep evidence).
2. Propose the design: layout, components, states, and what changes for phone and for Arabic.
3. List which hard rules the design touches and how it keeps them.
4. Then the code, as small pull requests of at most 400 changed lines each, with unit tests
   (Vitest) and, for a new page, an end-to-end check (Playwright).
5. End with the review checklist: screenshots at 1440 and 375 px in English and Arabic,
   keyboard check, greyscale check, contrast, synthetic marking still visible.
If the task conflicts with a hard rule, say so and stop; do not work around it.

Task:
<write the task here: the page, what is wrong today, what done looks like>
```

## 8. Page cards

Write one card under "Task" in the prompt of section 7, one page per pull request. Fill the
blanks marked `[...]` from the chosen proposal in the UI proposals the team shared (the
13-page "neon radar" file; it is not in the repository).

### Card 1 · Search (`/`)
- Now: `ui/src/views/SearchView.vue`. Full-text search over names and addresses, exact account
  numbers, kind filters.
- Reference: proposal [...], page [...].
- Change: [...]
- Must keep: the 2-character minimum; long terms wrap (issue #164); an empty, a no-match and an
  error state; the kind filters as real checkboxes.
- Done: a search box above the fold at 375 px, with the notices still visible; screenshots in
  English and Arabic.

### Card 2 · Alerts (`/alerts`)
- Now: `ui/src/views/AlertsView.vue`, rows from `AlertList.vue`. The queue in the API's order
  (priority, then pattern strength), filters by priority, typology or entity, paged.
- Reference: proposal [...], page [...].
- Change: [...]
- Must keep: the API's order (never re-sorted in the browser); priority shown as a word, not
  only a colour; the synthetic label on each row; the headline as the API writes it.
- Done: a 20-row page readable at 1440 and 375 px; filters reachable by keyboard.

### Card 3 · Alert (`/alerts/:id`)
- Now: `ui/src/views/AlertView.vue`. Headline, evidence graph, explanation steps, subjects,
  other explanations, metrics, typology with citations (C4).
- Reference: proposal [...], page [...].
- Change: [...]
- Must keep: "Other explanations for this structure" as visible as the steps; selecting a step
  highlights its relationships; the alert path on top of the graph; citations linked; no word
  beyond the alert's own wording.
- Done: the steps and the graph side by side from 1024 px, stacked below; a malformed id shows
  "Nothing with this id was found." (issue #165).

### Card 4 · Entity (`/entities/:id`)
- Now: `ui/src/views/EntityView.vue`. Name, flags, network with hops, details, relationships,
  sources, alerts that name the entity.
- Reference: proposal [...], page [...].
- Change: [...]
- Must keep: flags with their source; "possible match, not confirmed"; every fact linked to its
  source record; the link to the full-screen network.
- Done: name, kind, flags and synthetic or public status visible without scrolling.

### Card 5 · Network, full screen (`/entities/:id/network`)
- Now: `ui/src/views/NetworkView.vue` (#170, #171 by Mustafa, in review). Agree with Mustafa
  before changing it.
- Reference: network design 2 (the "design 1 vs design 2" file the team shared).
- Change: [...]
- Must keep: 2D; the key includes nodes (shapes, dashed = synthetic, flags) as well as
  relationships; the notices; the table view; hops and zoom in the URL.
- Done: 1, 2 and 3 hops readable; the alert path stays visible when a family is hidden.

### Card 6 · Data sources (`/sources`)
- Now: `ui/src/views/DataSourcesView.vue`. The datasets from `GET /meta` with licence,
  attribution and what is loaded.
- Reference: proposal [...], page 13.
- Change: [...]
- Must keep: every licence and attribution word for word; the loaded date of each dataset.
- Done: a table on desktop, cards on a phone; the smallest page, so test the prompt here first.

### Card 7 · Copilot (new page, Phase 5)
- Now: no page yet; the API is `GET /api/v1/copilot` and the ask route (C3 1.2.0).
- Reference: proposal [...] or none yet.
- Must keep (PHASE-4.md M4.10): the notice and the badge before the first question, as text;
  the question box with `autocomplete="off"`; no question in a URL, title, history or browser
  storage; the reading of the question beside every answer; clarifying choices as buttons; a
  confirm control for a reading the model proposed; evidence, queries and the data date beside
  every answer; people by name, role and source only.
- Done: the whole flow works by keyboard and screen reader. Ask the lead before starting: it
  has legal points (ADR-0028).

## 9. A version for design tools (Stitch and similar)

A design tool draws screens; it does not write our Vue code. Use this shorter prompt there,
with one card's page and change under it. Use only synthetic names from the demo (for example
"Calvane Holdings Ltd", "Plover Brae Textiles"); never a real person or company.

```text
Design a desktop (1440 px) and a phone (375 px) screen for NeonRadar, an investigation tool
that shows companies, people, bank accounts and payments as a network. Users are careful
investigators who must read names, amounts and dates and follow money paths.

Style: calm, light, minimal, plenty of white space, system font, one accent colour (orange)
used only for the alert path inside a graph and the step selected on it; never in lists. Text
contrast at least 4.5:1. Never use colour alone: every meaning also has a shape, line style,
icon or word.

Always on screen: a top bar (Search, Alerts, Data sources, a language switch "العربية"), a
short notice that the tool shows patterns, not conclusions, and a notice that the data is
synthetic. Synthetic items carry a "Synthetic" label or a dashed outline.

Graphs are 2D: nodes as pale shapes with a dark outline (circle = person, rounded rectangle =
company, small rounded bar = account), relationships coloured by kind (money, ownership,
roles, account, address), the alert path in orange on top.

Never use the words suspect, criminal, guilty or fraud, and no red danger styling on a person.
Show loading, empty and error states too.

The product is called "NeonRadar"; use no other name. It runs on one computer, offline:
- Navigation has exactly: Search, Alerts, Data sources, and the language switch. No other
  pages, no sidebar sections such as Overview, Settings, Pipelines or Schema.
- No login, user name, avatar, profile, team or account menu.
- Do not invent features: no dashboards, summary number cards, export or sync buttons,
  "connected", "live" or "real-time" badges, or API words such as "GET /meta".
- Never claim compliance: no "compliant", "verified", "audited" or "certified" anywhere.
- No status badges about the system ("offline", "local", "connected", "synced").
- The UI only reads. It never loads, downloads, imports, refreshes or deletes data: no "Load",
  "Import", "Refresh" or "Delete" buttons (an operator loads data with a command).
- Draw only the page as a user sees it: no design-spec header, colour notes, state samples,
  legends or status panels around it. A graph key belongs only on pages that show a graph.
- Every field shows a value; never leave a label without its value.
- Show only the numbers given here; never compute or add totals, percentages or other figures.
- No taglines, versions or extra words: never "forensic", "evidence workspace", "v1.0".
Fonts: the system sans-serif font for all text, including Arabic. Monospace only for ids,
account numbers, licence ids, dates and amounts.
Orange means the alert path and nothing else: notices, tabs, links, licences and status words
use the colours below, never orange.
Do not translate the notices: on an Arabic screen keep them in English (the project approves
its own translation).
Colours: text #1f2933, muted text #52606d, page #f7f8fa, cards #ffffff, borders #d3d8de, links
and buttons #1d4ed8, synthetic label background #e8f1fd with border #2f6fbf, notice background
#fff7e0 with border #b7791f. Orange #ea580c only for the alert path.
Notice text (keep it, shorten only with "Read more"): "NeonRadar is an educational, open-source
tool that finds structural patterns in synthetic or public data. A pattern match is not
evidence of wrongdoing." Synthetic notice: "This demo shows synthetic data only."
Show the desktop and the phone screen side by side.

Sample data for the Data sources page (use exactly these, with their licences):
NeonRadar synthetic data (Apache-2.0, loaded, marked Synthetic); UK Companies House public
register (OGL-UK-3.0); GLEIF Global LEI Index (CC0-1.0); OpenSanctions, default collection
(CC-BY-NC-4.0); OFAC SDN list (CC0-1.0); UK Sanctions List (OGL-UK-3.0). Only the synthetic one
is loaded in the demo; the others show "Not loaded". For the attribution write the publisher
only: NeonRadar, Companies House, GLEIF, OpenSanctions, US Treasury (OFAC), UK FCDO.

Sample data for the Alerts page (use exactly these; never invent others):
- An alert has only: priority (High, Medium or Low; there is no "Critical"), a headline, a
  typology, a pattern strength from 0 to 1 (shown as "0.82", never as a percentage, "match"
  or "confidence"), the date it was found, its subjects and the Synthetic label.
- No case management: no assign, export, checkboxes, SLA, timers, "new" counters or audit log.
- Rows:
  1. High · 0.91 · "Synthetic scenario: funds returned to the originating account through 4
     transfers within 6 days" · Round-tripping or circular flows · Tansy Strand Supplies Ltd
  2. High · 0.84 · "Synthetic scenario: money passed through an account within 2 days" ·
     Rapid pass-through · Bracken Dale Freight Ltd
  3. Medium · 0.66 · "Synthetic scenario: one account paid 9 accounts within 3 days" ·
     Fan-out distribution from one account · Copper Acre Interiors Ltd
  4. Medium · 0.58 · "Synthetic scenario: funds moved through a chain of 5 transfers" ·
     Layering through chains of transfers · Basalt Holm Foods Ltd
  5. Low · 0.41 · "Synthetic scenario: funds returned to the originating account through 3
     transfers within 20 days" · Round-tripping or circular flows · Sorrel Sike Trading Ltd
- Explain "Pattern strength" once, next to its column title: "How closely the structure
  matches the pattern; not a likelihood of wrongdoing."
- The synthetic data notice is blue (#e8f1fd, border #2f6fbf); only the standing notice is
  yellow.
- Show the filters (Priority, Typology) above the list and the page links (20 per page) below.
- Subjects are companies only, from the synthetic demo above; never show a person's name on
  this page.
- Never write "laundering", "fraud", "crime", "suspicious" or "risk" in a row, a filter or a
  title. The page title is "Alerts", with the line "Patterns to review, in the order the
  detection found them."

Sample data for the Alert page and any graph (use exactly these; never invent others):
- Use only the company names in this prompt. Never show the name of a real company, bank,
  person, government body or sanctions list entry, anywhere, for any reason.
- No risk score, risk index, "hazard", "threat", "severity", "critical", confidence or match
  percentage. No buttons that act on a case: no "assign", "issue SAR", "add to case",
  "run sweep", "export". No classification banners ("top secret", "noforn"). Light theme only.
- Alert: High · pattern strength 0.91 · found 2026-10-23 · Synthetic.
  Headline: "Synthetic scenario: funds returned to the originating account through 4
  transfers within 6 days". Typology: Round-tripping or circular flows.
- Graph (2D): 4 companies, each holding one account (account numbers NRSYN0000000011 to
  NRSYN0000000014), all with a dashed outline (synthetic). The alert path, in orange, numbered:
  Step 1: Tansy Strand Supplies Ltd paid Bracken Dale Freight Ltd EUR 48,000.00 (2026-10-01)
  Step 2: Bracken Dale Freight Ltd paid Copper Acre Interiors Ltd EUR 46,500.00 (2026-10-02)
  Step 3: Copper Acre Interiors Ltd paid Basalt Holm Foods Ltd EUR 45,200.00 (2026-10-04)
  Step 4: Basalt Holm Foods Ltd paid Tansy Strand Supplies Ltd EUR 44,000.00 (2026-10-06)
  Around them, 6 grey relationships to other synthetic companies (owns, director, holds).
- "Other explanations for this structure", as visible as the steps: "Refunds and payment
  reversals" and "Loan drawdown followed by repayment".
- Metrics: cycle length 4, duration 6 days, amount kept 92%.
- Subjects: Tansy Strand Supplies Ltd. Typology section: its name, a one-line description and
  "Sources" with 2 citation links.
- A key under the graph: node shapes, dashed outline = synthetic, the relationship colours,
  orange = alert path.

Screen: <page name and what it shows, from the card>
Change: <what should be different from today>
```
