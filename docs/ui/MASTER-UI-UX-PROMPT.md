# MASTER PROMPT — NeonRadar UI/UX Presentation & Graph Visual Upgrade (Pure Visual Layer · Zero Logic Change · Anti-AI Design · Taste · Light Mode Only)

> **How to use this file:** Send this single `.md` file alone as a standalone prompt to any coding or design agent (`Claude Code`, `Antigravity`, `Cursor`, `Codex`, `Windsurf`). It requires **zero extra attachments**. Everything is self-contained inside this document: **which global design skills to fetch (and exact URLs/commands)**, **strict code-logic & test preservation boundaries**, **the `Taste` and `Anti-AI Design` art-direction system (Strictly Light Mode Only)**, **the `C2` Cytoscape visual grammar**, and **the layout, readability, and camera-motion refinements**.

---

## ROLE & STRICT SCOPE BOUNDARY (READ FIRST)

You are a **Principal Product Designer & Staff Frontend Engineer** crafting investigative interfaces on the level of **Linear (Light), Stripe Dashboard, Financial Times Visual Journalism, and Linkurious**.

Your mission is to upgrade **only the visual presentation, spatial CSS layout, typography, Cytoscape stylesheet, and non-destructive camera ergonomics** of `ui/` (`Vue 3.5` + `TypeScript ~6.0.3` + `Cytoscape.js`) in **NeonRadar** while changing **ZERO business logic, ZERO API behavior, ZERO routing rules, and ZERO data transformations**.

> **THREE NON-NEGOTIABLE TOP-LEVEL MANDATES:**
> 1. **ZERO LOGIC OR FUNCTIONAL CODE CHANGES (`PRESENTATION LAYER ONLY`):** Do **NOT** alter any backend file, contract, API client, Pinia store logic, Vue Router table, data-formatting logic, search/filter logic, evidence-export logic, or node-click navigation behavior. You are restyling and spatially arranging the existing data and controls — never changing how NeonRadar fetches, computes, filters, exports, or navigates.
> 2. **STRICT LIGHT MODE ONLY (`NO DARK MODE`):** Do **NOT** build a dark mode, dark theme CSS block, `@media (prefers-color-scheme: dark)` override, dark slate/obsidian canvas, or Light/Dark toggle button. Force `color-scheme: light;` on `:root`. Even though the repository is named **NeonRadar**, **NEVER** interpret "Neon" or "Radar" literally — zero dark radar screens, zero neon accents, zero cyber/hacker aesthetics.
> 3. **STRICT `ANTI-AI DESIGN` VIA `TASTE` METHODOLOGY:** Every layout, surface, hairline border, icon, label, and transition must obey the **`Taste` (`design-taste-frontend`)** and **`Hallmark`** anti-AI-slop rules below so the interface reads as 100% authored by a senior human studio — never like an LLM-generated template.

---

## STEP 0 — FETCH & ACTIVATE GLOBAL DESIGN SKILLS & ALLOWED ICON PACKAGE

Before editing any style or template, load the following open-source agent design skills if supported by your environment:

### A. Global Agent UI/UX & Anti-AI-Design Skills (Exact Sources & Install Commands)
If your environment supports agent skills (`npx skills`, `~/.claude/skills/`, `~/.gemini/config/plugins/`, or `.agents/skills/`), install and activate:

1. **`Taste-Skill` (`design-taste-frontend` — Primary Art Direction & Anti-AI Design Engine)**
   - **Where to get it:** `https://github.com/Leonxlnx/taste-skill`
   - **Install command:** `npx skills add Leonxlnx/taste-skill -g` *(or `git clone https://github.com/Leonxlnx/taste-skill` into your skills folder and read `SKILL.md`)*.
   - **Required `Taste` Tuning Dials for NeonRadar:**
     - `DESIGN_VARIANCE = 6 / 10` *(Intentional Asymmetric Spatial Workbench: replaces generic stacked SaaS boxes with an asymmetric `~68%` daylight graph stage + docked `~32%` architectural evidence/details column on desktop, while keeping every existing section predictable and accessible).*
     - `MOTION_INTENSITY = 4 / 10` *(Tactile & Restrained: smooth `220ms` Cytoscape camera fit/zoom and crisp focus transitions — zero decorative bounce, zero continuous loops, and zero state-machine timers).*
     - `VISUAL_DENSITY = 7 / 10` *(Calibrated Analytical Daylight Desk: airy, collision-free graph canvas paired with high-legibility tabular numbers, provenance records, and citations).*
2. **`Hallmark` (Anti-AI-Slop & Structural Browser Audit Skill)**
   - **Where to get it:** `https://github.com/nutlope/hallmark`
   - **Install command:** `npx skills add nutlope/hallmark -g` *(or clone and apply its `SKILL.md` / `sloplint` rules)*.
   - **Purpose:** Strips recognizable AI dashboard clichés and verifies zero text overflow in a real browser.
3. **Anthropic Official `frontend-design` Skill**
   - **Where to get it:** `https://github.com/anthropics/claude-plugins-official/tree/main/plugins/frontend-design/skills/frontend-design`
   - **Purpose:** Editorial typography, tonal restraint, and clear visual hierarchy.
4. **Optional Contrast-Only Lookup (`ui-ux-pro-max`) — Strict Filter Required**
   - **Where to get it:** `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill`
   - **Strict Rule if present:** Use **only** its offline WCAG AA contrast checks; **reject** any dark-mode, glassmorphism, claymorphism, gradient, Tailwind-indigo, or Google-Fonts suggestions.

*(Fallback: If network installation of external agent skills is disabled in your sandbox, the full `Taste` + `Anti-AI Design` rulebook is embedded inline in Step 2 below — apply it directly.)*

### B. Frontend Dependencies Policy (Keep Existing Graph Engine!)
- **KEEP `cytoscape` and `cytoscape-fcose`** (already installed in `ui/package.json`). **DO NOT** replace `Cytoscape` with another graph library — Playwright E2E tests (`ui/e2e/demo-mini.spec.ts`) explicitly assert a visible `<canvas>` inside `[data-testid="graph-canvas"]`, and unit tests (`ui/src/lib/__tests__/graph-style.spec.ts`) test `graphStyle` directly in headless Cytoscape.
- **Optional Local Icon Package Only:** You may install `lucide-vue-next` (`https://github.com/lucide-icons/lucide` — `ISC` licence, `npm --prefix ui install lucide-vue-next`) for crisp local `1.5px` vector icons in Vue templates, OR use clean inline `<svg>` monoline icons with `stroke-width="1.5"` (omitting any external namespace URL).
- **STRICT BANS (`CLAUDE.md`):**
  - **NEVER** install `@neo4j-nvl` (proprietary), any `GPL` package, or Tailwind CSS.
  - **NEVER** load Google Fonts, icons, stylesheets, or scripts from any external URL (`G3`: 100% offline at runtime).
  - Keep `typescript` pinned to `~6.0.3` (never upgrade to TypeScript 7).

---

## STEP 1 — CODE-LOGIC FREEZE & AUTOMATED GUARDRAILS

### A. Frozen Files & Untouched Logic (DO NOT MODIFY)
1. **Everything outside `ui/` is strictly off-limits:** Never touch `contracts/**`, `graph/**`, `detect/**`, `ingest/**`, `copilot/**`, `api/**`, `cli/**`, `data/**`, or `scripts/**`.
2. **Frozen Logic Modules inside `ui/src/` (Keep 100% Unchanged):**
   - `ui/src/api/client.ts`, `ui/src/api/schema.d.ts`, `ui/src/api/types.ts` — zero new or altered API requests.
   - `ui/src/router/index.ts` — keep exact routes (`/`, `/entities/:id`, `/alerts`, `/alerts/:id`, `/sources`).
   - `ui/src/stores/meta.ts` and `ui/src/stores/locale.ts` — keep store state and methods unchanged.
   - `ui/src/lib/alerts.ts`, `ui/src/lib/evidence-export.ts`, `ui/src/lib/flags.ts`, `ui/src/lib/format.ts`, `ui/src/lib/graph.ts`, `ui/src/lib/notices.ts`, `ui/src/lib/search.ts` — keep all data helpers and export logic intact.
3. **Preserved Component Contracts, Landmarks & Test Hooks:**
   - **`App.vue` (`App.spec.ts`):** Never render `<RouterView />` before `metaStore.meta && metaStore.noticeKind` is ready; refresh notices on navigation; preserve `data-testid="standing-disclaimer"`, `data-testid="data-notice"`, `data-notice-kind`, and `data-testid="meta-error"`.
   - **`GraphCanvas.vue` (`demo-mini.spec.ts`):** Preserve exact props (`subgraph`, `label`, `focusIds`, `highlightEdgeIds`), exact `@select` emit behavior (`opensEntityPage` -> navigates to `/entities/:id`, while `:Sanction` nodes stay in the graph without navigating), `data-testid="graph-canvas"` with Cytoscape's `<canvas>`, `<figcaption>` starting with `{{ props.subgraph.nodes.length }} nodes, {{ props.subgraph.edges.length }} relationships`, and the accessible `<details class="graph__nodes">` list.
   - **`AlertView.vue` & `EntityView.vue` (`demo-mini.spec.ts`):** Preserve `<section aria-labelledby="evidence-heading"><h2 id="evidence-heading">Evidence</h2>` on `AlertView.vue`, `<section aria-labelledby="network-heading"><h2 id="network-heading">Network</h2>` and `data-testid="network-depth"` on `EntityView.vue`, `data-testid="alert-headline"`, `data-testid="explanation-steps"` (clicking a step toggles `selectedStep` to highlight `step.edge_ids`), `data-testid="citations"`, `Other explanations for this structure` (`false_positive_notes`), `Download JSON` / `Download CSV` (`downloadEvidence`), and `<details class="reproduce">`.
   - **`SearchView.vue` & `AlertsView.vue`:** Preserve `data-testid="search-input"`, submit button `Search`, `data-testid="search-count"`, `data-testid="search-results"`, and `data-testid="alert-list"`. Do **not** fire extra background API requests on page mount.

### B. Automated Source-Guard Traps (`ui/src/__tests__/source-guards.spec.ts` & `graph-style.spec.ts`)
1. **CSS Logical Properties ONLY (Hard Unit-Test Gate):**
   - `source-guards.spec.ts` scans **every** `.css` file and every `<style>` block or `style=""` attribute in `.vue` files and **fails immediately** if it sees physical properties:
     - **BANNED IN CSS:** `width`, `min-width`, `max-width`, `height`, `min-height`, `max-height`, `left`, `right`, `top`, `bottom`, `margin-left/right/top/bottom`, `padding-left/right/top/bottom`, `border-left/right/top/bottom`, `text-align: left/right`, `float: left/right`.
     - **USE INSTEAD:** `inline-size`, `min-inline-size`, `max-inline-size`, `block-size`, `min-block-size`, `max-block-size`, `inset-inline-start/end`, `inset-block-start/end`, `margin-inline/block`, `padding-inline/block`, `border-inline/block`, `text-align: start/end` (use `@media (width >= 64rem)` without a colon for media queries, matching `main.css`).
2. **Zero External URLs Anywhere in `ui/src/` or `ui/index.html` (Hard Unit-Test Gate):**
   - `source-guards.spec.ts` rejects any line matching `http://`, `https://`, `ws://`, `wss://`, or `//domain/` — **even inside comments or SVG `xmlns` attributes!** When embedding inline `<svg>` or Cytoscape `data:image/svg+xml;utf8,<svg viewBox='0 0 24 24'>...</svg>`, never include `http://www.w3.org/2000/svg`.
3. **Zero Forbidden Terms (`G5` — Hard Unit-Test Gate):**
   - Never write accusing words from `contracts/wording/forbidden-terms.txt` anywhere in `ui/src/` (including comments). Alerts are calm structural observations, never accusations.
4. **`graphStyle` Headless Test Invariants (`graph-style.spec.ts`):**
   - Keep **exactly two** highlight/focus selector rules matching `/\.(focus|highlighted)\b/`: `node.focus` and `edge.highlighted`.
   - Neither `node.focus` nor `edge.highlighted` may set `border-style` or `line-style` (so `node.synthetic` stays `dashed`, public nodes stay `solid`, `edge.synthetic` stays `dashed`, and `edge.type-possibly_same_as` stays `dashed` with `target-arrow-shape: 'none'`).
   - `node.focus` must apply one consistent `border-color` across focused nodes, and `edge.highlighted` must set `width: 4`.

---

## STEP 2 — `ANTI-AI DESIGN` & `TASTE` SYSTEM (STRICT LIGHT MODE)

Channel the **Swiss Archival Daylight** aesthetic: crisp paper-white and cool mineral-stone matte surfaces, razor-sharp `1px` structural hairlines, disciplined breathing room, and editorial typography.

### 10 Hard `Anti-AI Design` Bans (`Taste` + `Hallmark` Enforcement)
1. **NO Dark Mode Anywhere:** Zero dark backgrounds (`#0D0F12`, `#111827`, `#0F172A`), zero dark cards or code blocks, and zero theme toggles.
2. **NO Glows, Neon, or Colored Shadows:** Zero glowing borders, zero colored `box-shadow` halos, zero blurred ambient blobs. Use `1px` structural hairlines and at most `0 1px 2px rgba(17, 19, 24, 0.04)` on elevated controls.
3. **NO AI Default Palettes or Gradients:** Ban Tailwind indigo/violet (`#6366F1`, `#8B5CF6`), ban multi-stop gradients on buttons/headers/badges, and ban cliché AI warm-cream/terracotta (`#F4F1EA` + `#D97757`).
4. **NO Decorative Glassmorphism:** Ban `backdrop-filter: blur(...)`; use opaque matte daylight surfaces (`#FFFFFF`, `#F6F7F9`, `#EEF1F5`).
5. **NO Thick Side-Stripe Callout Borders:** Remove `border-inline-start-width: 6px` stripes on `.notice` and cards (the classic AI dashboard tell). Use uniform `1px` full-perimeter borders (`border: 1px solid ...`) with quiet tonal surface fills and a clean monoline icon or pill tag.
6. **NO Symmetric 4-Card SaaS KPI Grids:** Keep metrics in crisp typographic definition lists (`<dl>`) and clean inline summary strips — never bloated SaaS stat tiles.
7. **NO Floating Popovers Obscuring Graph Nodes:** Never cover graph neighbors with floating cards.
8. **NO Emojis Anywhere in the UI:** Use crisp `1.5px` stroke vector icons only.
9. **NO AI Typography & Copywriting Tells:** Ban tracked-out `ALL-CAPS` eyebrows above every heading, ban `→` button suffixes, and never alter NeonRadar's neutral wording tone.
10. **NO Bouncy / Gimmicky Animations:** Never use `transform: scale(...)` hover jumps or pulsing rings.

### Swiss Archival Daylight CSS Tokens (`ui/src/assets/main.css` — Light Mode Only)
Upgrade `:root` in `ui/src/assets/main.css` cleanly (`color-scheme: light`):

```css
:root {
  color-scheme: light;

  /* Matte Daylight Surfaces */
  --color-bg: #f6f7f9;               /* Cool archival stone app canvas */
  --color-grid-dot: #d5dbe3;         /* Subtle 1px spatial dot pattern inside graph frame */
  --color-surface: #ffffff;          /* Crisp paper white for panels, header & cards */
  --color-subtle: #fafbfd;           /* Quiet secondary surface */
  --color-inset: #eef1f5;            /* Matte inset controls & subtle pills */

  /* Editorial Ink Hierarchy (WCAG AA+ on Daylight) */
  --color-text: #111318;             /* Deep carbon ink for headings & primary values */
  --color-secondary: #374151;        /* Balanced body & explanation prose */
  --color-muted: #5b6472;            /* Metadata, timestamps & secondary labels */

  /* 1px Architectural Hairlines */
  --color-border: #dfe4ea;           /* Primary 1px structural divider */
  --color-border-strong: #c5cdd8;    /* Interactive hover / input border */

  /* Restrained Functional Accents (Zero Neon, Non-Accusatory) */
  --color-link: #1d4ed8;             /* Focused cobalt ink for links & active step */
  --color-accent: #b45309;           /* Calm archival amber for focus/priority highlights */
  --color-accent-soft: #eff6ff;      /* Soft selection surface for active explanation step */
  --color-accent-border: #bfdbfe;

  /* Standing & Provenance Notice Tones (Uniform 1px Perimeter Borders) */
  --color-standing-bg: #fef9ec;
  --color-standing-border: #ecd494;
  --color-synthetic-bg: #f0fdfa;
  --color-synthetic-border: #99f6e4;
  --color-synthetic-ink: #0f766e;
  --color-real-bg: #f8fafc;
  --color-real-border: #cbd5e1;
  --color-error: #9f1239;

  /* Typography & Rhythm */
  --font-body:
    system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans', 'Noto Sans Arabic', sans-serif;
  --font-mono: ui-monospace, 'SFMono-Regular', 'Cascadia Mono', Menlo, Consolas, monospace;
  --radius: 8px;
  --radius-sm: 6px;
  --page-max: 88rem;
}
```

### Typography & Bidirectional Numeric Precision
- Tight, authoritative heading tracking (`letter-spacing: -0.015em`), clear weight contrast (`600` headings vs `400` body), comfortable reading measure (`max-inline-size: 68ch` on prose paragraphs).
- Apply `font-variant-numeric: tabular-nums` and `direction: ltr; unicode-bidi: isolate` to `.mono`, IDs, timestamps, metrics, and currency amounts so figures align vertically and never scramble in Arabic `RTL`.

---

## STEP 3 — `C2` CYTOSCAPE VISUAL GRAMMAR, LAYOUT & CAMERA ERGONOMICS

### 1. Upgraded `C2` Daylight Visual Grammar (`ui/src/lib/graph-style.ts`)
Upgrade `graphStyle` and `fcoseLayout` in `ui/src/lib/graph-style.ts` (while keeping every `graph-style.spec.ts` test invariant 100% green!):

- **Distinct Geometric Shapes + Daylight Tinted Fills + Embedded `1.5px` Monoline SVG Icons (via offline `data:image/svg+xml;utf8,...` without any `http` string):**
  | Selector (`node.schema-*`) | Cytoscape `shape` | Daylight `background-color` | Stroke / Icon Ink | Concept Icon |
  | :--- | :--- | :--- | :--- | :--- |
  | `node.schema-person` | `ellipse` | `#EEF2FF` | `#3730A3` | Person silhouette |
  | `node.schema-company` | `round-rectangle` | `#F3F0FF` | `#5B21B6` | Building |
  | `node.schema-organization`, `node.schema-legalentity` | `round-rectangle` | `#F1F5F9` | `#334155` | Briefcase / Registry |
  | `node.schema-publicbody` | `octagon` | `#E0F2FE` | `#0369A1` | Civic columns |
  | `node.schema-bankaccount` | `barrel` *(or `round-rectangle`)* | `#F0FDFA` | `#0F766E` | Account card |
  | `node.schema-address` | `diamond` | `#FFFBEB` | `#92400E` | Location pin |
  | `node.schema-position` | `hexagon` | `#F4F4F5` | `#3F3F46` | Role badge |
  | `node.schema-sanction` | `tag` | `#FFF1F2` | `#9F1239` | Record tag |

- **Zero-Overflow External Node Captions:**
  - Size node emblems cleanly (`36px`–`40px`), set `border-width: 1.5`, `border-style: 'solid'` by default (`border-style: 'dashed'` on `node.synthetic`), and render `label: 'data(caption)'` **below** the node (`text-valign: 'bottom'`, `text-margin-y: 6`, `text-wrap: 'ellipsis'`, `text-max-width: '152px'`, `font-size: 11`, `color: '#111318'`, `text-background-color: '#ffffff'`, `text-background-opacity: 0.92`, `text-background-padding: '3px'`) so entity names never collide with node borders!
- **Clean Relationship Strokes & Spacious Layout:**
  - Increase `fcoseLayout` spacing (`nodeSeparation: 140`, `idealEdgeLength: 150`, `padding: 40`) so subgraphs breathe without overlapping labels.
  - Keep edge labels crisp (`font-size: 9.5`, `text-rotation: 'autorotate'`, `text-background-color: '#ffffff'`, `text-background-opacity: 0.94`, `text-background-padding: '2px'`), preserving `edge.synthetic` (`line-style: 'dashed'`), `edge.type-possibly_same_as` (`line-style: 'dashed'`, `target-arrow-shape: 'none'`), and the exact two highlight selectors (`node.focus` and `edge.highlighted`).

### 2. Spatial Daylight Workbench Layout (CSS Grid Arrangement — Zero Logic Mutation)
- **Compact Editorial Shell (`App.vue` + `main.css`):**
  - Sleek single-row top header (`background: var(--color-surface)`, `border-block-end: 1px solid var(--color-border)`), active nav indicator, language switcher (`English / العربية` bound to existing `useLocaleStore()`), and slim, calm provenance notices (`NoticeBanner.vue`) styled with uniform `1px` perimeter borders instead of thick side stripes.
- **Asymmetric Two-Pane Investigation Layout on Desktop (`AlertView.vue` & `EntityView.vue` at `@media (width >= 64rem)`):**
  - Arrange the existing `<section aria-labelledby="evidence-heading">` (or `network-heading`) on the **inline-start (`~65%–68%`)** and the existing explanation/details/metrics/sources sections in a clean **docked inline-end column (`~32%–35%`)** separated by `1px solid var(--color-border)`, stacking naturally into a single column on smaller screens.
  - Keep `Download JSON` and `Download CSV` prominently grouped in the `Evidence` header bar so they are immediately visible without scrolling.
  - Style explanation step buttons (`.step`) as numbered, tactile daylight rows: clicking a step (using the existing `toggleStep(step.order)` function) highlights the row with `background: var(--color-accent-soft)` and `border-color: var(--color-link)` while highlighting its transfer edges on the canvas.
  - Style `Other explanations for this structure` (`false_positive_notes`) as a calm `--color-standing-bg` panel (`1px solid var(--color-standing-border)`, zero side stripe) so investigators read legitimate explanations effortlessly.

### 3. Non-Destructive Graph Camera Toolbar & Smooth Motion (`GraphCanvas.vue`)
- Add purely visual camera helper buttons (`+` Zoom In, `−` Zoom Out, `Fit` to View) inside `GraphCanvas.vue` that call Cytoscape's built-in `cy.zoom(...)` and `cy.fit(undefined, 36)` (using smooth `220ms` easing when `prefers-reduced-motion` is not enabled) — **without** changing `GraphCanvas`'s props, `@select` event, `<canvas>`, `<figcaption>`, or `<details class="graph__nodes">`.
- Render the graph container (`.graph__canvas`) on `--color-bg` with a subtle CSS `radial-gradient(var(--color-grid-dot) 1px, transparent 1px)` `20px 20px` dot matrix and crisp `1px solid var(--color-border)` frame (`block-size: clamp(26rem, 62dvh, 42rem)` using logical `block-size`!).

---

## STEP 4 — EXECUTION & MANDATORY VERIFICATION

Touch **only** presentation files inside `ui/src/` (`ui/src/assets/main.css`, `ui/src/lib/graph-style.ts`, `ui/src/components/*.vue`, `ui/src/views/*.vue`, `ui/src/App.vue`, and style/visual unit tests if needed) — leaving all API, router, store, and domain-logic `.ts` files untouched.

### Mandatory Quality Gate Before Reporting Completion
Run every command below and resolve all warnings or errors:
```bash
npm --prefix ui run lint
npm --prefix ui run type-check
npm --prefix ui run test:unit -- --run
npm --prefix ui run build
```
Confirm specifically that:
1. `git diff ui/src/api ui/src/router ui/src/stores/meta.ts ui/src/lib/alerts.ts ui/src/lib/evidence-export.ts ui/src/lib/flags.ts ui/src/lib/format.ts ui/src/lib/graph.ts ui/src/lib/notices.ts ui/src/lib/search.ts` is **completely empty** (zero logic modified).
2. `ui/src/__tests__/source-guards.spec.ts` passes (100% CSS logical properties, zero external URLs, zero forbidden terms).
3. `ui/src/lib/__tests__/graph-style.spec.ts` and `ui/src/__tests__/App.spec.ts` pass.
4. When the demo stack is running, `make e2e` passes (`demo-mini.spec.ts`) and live browser inspection at `1440x900` and `390x844` in `LTR` and `RTL` confirms Light-Mode-Only Swiss Archival Daylight styling with zero text overflow.
