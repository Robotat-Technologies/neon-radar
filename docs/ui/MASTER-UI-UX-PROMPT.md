# MASTER PROMPT — NeonRadar Spatial Graph & Investigation UI/UX Upgrade (Anti-AI Design · Taste · Light Mode Only)

> **How to use this file:** Send this single `.md` file alone as a standalone prompt to any coding or design agent (`Claude Code`, `Antigravity`, `Cursor`, `Codex`, `Windsurf`). It requires **zero extra attachments**. Everything is self-contained inside this document: **which global skills and open-source packages to fetch (and exact URLs/commands)**, **the `Taste` and `Anti-AI Design` art-direction protocol (Strictly Light Mode Only)**, **NeonRadar's domain logic and `C2` visual grammar**, and **the usability, readability, and motion/interaction architecture**.

---

## ROLE & NON-NEGOTIABLE DESIGN MANDATE

You are a **Principal Product Designer & Staff Frontend Engineer** crafting investigative tools on the level of **Linear (Light), Stripe Dashboard, Financial Times Visual Journalism, and Linkurious**.

Your mission is to upgrade `ui/` (`Vue 3.5` + `TypeScript ~6.0.3` + `Pinia` + `Vue Router`) of **NeonRadar** — an open-source (`Apache-2.0`), local-first anti-corruption and financial-flow graph workbench — into a **human-crafted, studio-grade, strictly Light-Mode spatial investigation desk** while keeping every existing contract, lint, unit, and E2E check green.

> **CRITICAL TOP-LEVEL MANDATES (READ FIRST):**
> 1. **STRICT LIGHT MODE ONLY (`NO DARK MODE`):** Do **NOT** build a dark mode, dark theme CSS block, `@media (prefers-color-scheme: dark)` override, dark slate/obsidian canvas, or Light/Dark toggle button. Force `color-scheme: light;` on `:root`. Even though the repository is named **NeonRadar**, **NEVER** interpret "Neon" or "Radar" literally — zero dark radar screens, zero neon accents, zero cyber/hacker aesthetics.
> 2. **STRICT `ANTI-AI DESIGN` VIA `TASTE` METHODOLOGY:** Every layout, surface, border, icon, label, and transition must obey the **`Taste` (`design-taste-frontend`)** and **`Hallmark`** anti-AI-slop rules below so the UI looks 100% authored by a senior human product studio — never like an LLM-generated template.

---

## STEP 0 — FETCH & ACTIVATE GLOBAL SKILLS & OPEN-SOURCE PACKAGES

Before writing any UI code, fetch/load the following open-source agent skills and frontend libraries if available in your environment:

### A. Global Agent UI/UX & Anti-AI-Design Skills (Exact Sources & Install Commands)
If your environment supports agent skills (`npx skills`, `~/.claude/skills/`, `~/.gemini/config/plugins/`, or `.agents/skills/`), install and activate:

1. **`Taste-Skill` (`design-taste-frontend` — Primary Art Direction & Anti-AI Design Engine)**
   - **Where to get it:** `https://github.com/Leonxlnx/taste-skill`
   - **Install command:** `npx skills add Leonxlnx/taste-skill -g` *(or `git clone https://github.com/Leonxlnx/taste-skill` into your skills directory and load `SKILL.md`)*.
   - **Required `Taste` Tuning Dials for NeonRadar:**
     - `DESIGN_VARIANCE = 6 / 10` *(Intentional Asymmetric Spatial Workbench: breaks generic symmetric SaaS card grids into a `~70%` daylight graph canvas + `380–420px` docked architectural inspector rail, while staying disciplined and predictable for investigators).*
     - `MOTION_INTENSITY = 5 / 10` *(Tactile, Physics-Grounded & Purposeful: smooth camera focus, collision-free layout transitions, chronological transfer scrubbing, and single-arc directional flow — zero decorative bounce or scroll-jacking).*
     - `VISUAL_DENSITY = 7 / 10` *(Calibrated Analytical Daylight Desk: airy, uncluttered graph canvas via semantic zoom LOD paired with crisp, tabular-aligned provenance and evidence inside the docked inspector).*
2. **`Hallmark` (Anti-AI-Slop & Structural Browser Audit Skill)**
   - **Where to get it:** `https://github.com/nutlope/hallmark`
   - **Install command:** `npx skills add nutlope/hallmark -g` *(or clone and apply its `SKILL.md` / `sloplint` checks)*.
   - **Purpose:** Eliminates recognizable AI dashboard tells and requires real-browser layout/overflow verification.
3. **Anthropic Official `frontend-design` Skill**
   - **Where to get it:** `https://github.com/anthropics/claude-plugins-official/tree/main/plugins/frontend-design/skills/frontend-design`
   - **Purpose:** Editorial typography, tonal restraint, and plain factual UX copy.
4. **Optional Contrast-Only Lookup (`ui-ux-pro-max`) — Strict Filter Required**
   - **Where to get it:** `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill`
   - **Strict Rule if present:** Use **only** its offline WCAG contrast checks; **override and reject** any dark-mode, glassmorphism, claymorphism, gradient, Tailwind-indigo, or Google-Fonts suggestions.

*(Fallback: If your execution sandbox blocks network installation of agent skills, the complete `Taste` + `Anti-AI Design` rulebook is embedded inline in Step 2 below — apply it directly.)*

### B. Open-Source Vue 3 Packages for `ui/` (`MIT` / `ISC` / `EPL-2.0` — `Apache-2.0` Compatible)
Install inside `ui/` (`npm --prefix ui install ...`):

1. **Interactive Graph Engine + Deterministic Layout (Pick Primary Path):**
   - **Recommended Path (Sharpest Daylight Typography, Custom Vue/SVG Shape Nodes, Native RTL & A11y within NeonRadar's 200-node API cap):**
     - `@vue-flow/core` `@vue-flow/controls` `@vue-flow/minimap` `@vue-flow/background` (`https://github.com/bcakmakoglu/vue-flow` — MIT)
     - `elkjs` (`https://github.com/kieler/elkjs` — EPL-2.0) for deterministic, zero-overlap layered and radial layouts.
   - **Alternative Path (Dense Multi-Edge Canvas / Existing Stack Upgrade):**
     - `@antv/g6` (`https://github.com/antvis/G6` — MIT, native quadratic multi-edge `PAID` arc separation and combos), **OR** retain `cytoscape` + `cytoscape-fcose` and add `cytoscape-elk`.
2. **Headless Accessible Primitives (Zero Pre-Baked AI Styling):**
   - `reka-ui` (`https://github.com/unovue/reka-ui` — MIT) for accessible, RTL-aware `Dialog` (`⌘K` Command Palette), `Tabs`, `Tooltip`, and `Collapsible` styled strictly with NeonRadar's custom CSS tokens.
3. **Local Monoline Vector Icons:**
   - `lucide-vue-next` (`https://github.com/lucide-icons/lucide` — ISC) bundled 100% locally (`1.5px` stroke width).

> **STRICT DEPENDENCY & PRIVACY BANS (`CLAUDE.md`):**
> - **NEVER** add `@neo4j-nvl` (proprietary) or any `GPL` dependency.
> - **NEVER** fetch Google Fonts, icons, scripts, or telemetry from external URLs (`G3`: 100% offline at runtime).
> - Keep `typescript` pinned to `~6.0.3` (never upgrade to TypeScript 7).

---

## STEP 1 — DOMAIN LOGIC, LEGAL GUARDRAILS & `C2` VISUAL GRAMMAR

NeonRadar serves **investigative journalists, anti-corruption researchers, small FIUs, and students**. Every screen must answer four questions without friction:
1. **Who is this entity and how is it connected?** (Is each record `:Synthetic` or public data? Is a link confirmed or an unconfirmed `POSSIBLY_SAME_AS` match?)
2. **Why did this alert pattern appear?** (A clear chronological story of transfers/ownership synchronized with the graph).
3. **What ordinary, legitimate business activity could produce this exact structure?** (Preventing confirmation bias).
4. **How do I export and verify the evidence offline?** (`Download JSON`, `Download CSV`, source dataset licences, and citations).

### Non-Negotiable Project Guardrails
1. **Patterns, Never Accusations (`G5` & `docs/wording.md`):**
   - Never output accusing terms (`suspicious`, `launderer`, `criminal`, `fraud`, `mule`, `shell company`, `guilty`, `illicit`) anywhere in UI labels, badges, or tooltips.
   - Never use "danger/crime red" banners for alerts. An alert is **a structural observation — a reason to review, never an accusation or proof**.
   - Keep the standing disclaimer and synthetic/real data provenance banner (`GET /api/v1/meta`) visible before rendering entity or alert content.
   - Always render **"Other explanations for this structure"** (`false_positive_notes`) prominently on every alert page.
2. **Data Honesty (`G1` & `G8`):**
   - Synthetic records (`flags.synthetic === true`, IDs starting with `syn-`) must **always** keep a **dashed outer ring/outline**, even when hovered or selected.
   - Unconfirmed entity-resolution edges (`edge.type === 'POSSIBLY_SAME_AS'`) must render as **undirected dotted lines** (no arrowhead) labeled *"Possible match (not confirmed)"*.
   - `:Sanction` nodes (`node.schema === 'Sanction'`) render in the graph as evidence records but **must not link** to `/entities/:id` (`opensEntityPage(node) === false`).
3. **Contract & E2E Preservation (`C3` / `C4`):**
   - Never modify `contracts/**` or `graph/schema/**`.
   - Preserve existing E2E `data-testid` hooks (`meta-error`, `alert-headline`, `explanation-steps`, `graph-canvas`, `network-depth`, etc.) so `make check` and `make e2e` pass without regression.

### The 3-Layer `C2` Daylight Visual Grammar (`ui/src/lib/entity-visuals.ts`)
Build a single strongly-typed module mapping NeonRadar's fixed `C2` schemas (`contracts/C2-graph-schema.md`) to **distinct geometric emblems + `1.5px` Lucide icons + Light-Mode studio inks** — never plain text-stuffed rectangles:

- **Layer 1 — Geometric Emblem + `1.5px` Icon = `node.schema` (Daylight Palette):**
  | `node.schema` | Geometric Emblem | `lucide-vue-next` Icon | Daylight Surface Fill | Crisp `1.5px` Stroke & Icon Ink |
  | :--- | :--- | :--- | :--- | :--- |
  | `Person` | Circle (`999px` radius) | `User` | `#EEF2FF` | `#3730A3` *(Deep Slate-Indigo)* |
  | `Company` | Squircle (`12px` radius) | `Building2` | `#F3F0FF` | `#5B21B6` *(Muted Aubergine)* |
  | `Organization` / `LegalEntity` | Squircle (`12px` radius) | `Briefcase` | `#F1F5F9` | `#334155` *(Architectural Slate)* |
  | `PublicBody` | Octagon | `Landmark` | `#E0F2FE` | `#0369A1` *(Civic Steel Blue)* |
  | `BankAccount` | Wide Pill / Capsule | `CreditCard` | `#F0FDFA` | `#0F766E` *(Deep Mineral Teal)* |
  | `Address` | Diamond | `MapPin` | `#FFFBEB` | `#92400E` *(Archival Ochre)* |
  | `Position` | Hexagon | `Award` | `#F4F4F5` | `#3F3F46` *(Graphite Ink)* |
  | `Sanction` | Shield / Tag | `ShieldAlert` | `#FFF1F2` | `#9F1239` *(Muted Crimson — record, not alarm)* |

  *Node Label Placement Rule:* Keep the geometric emblem clean (`44px–52px`) with the `1.5px` icon centered inside, and place the entity `caption` **outside and below** the emblem on a crisp daylight pill/label (`max-width: 164px`, clean ellipsis, full text in the right inspector) so text **never** overflows or collides with node borders.

- **Layer 2 — Outer Ring + Corner Micro-Badge = Provenance & `node.flags`:**
  - `flags.synthetic === true` -> **Fine dashed outer halo ring** (`1.5px dashed #0F766E`), retained during selection/hover.
  - `flags.synthetic === false` -> **Solid crisp outer border** (`1.5px solid`).
  - `flags.sanctioned`, `flags.pep`, `flags.rca` -> Compact **top-end corner micro-badge** (`16px` neutral/amber/crimson indicator) — never paint the whole node danger-red.

- **Layer 3 — Edge Stroke & Curvature = Relationship Family:**
  - `PAID` -> Smooth curved directional bezier/arc with crisp arrowhead. When multiple `PAID` transfers connect the same account pair, fan curvature offsets (`±26px, ±52px`) so parallel transfers never overlap. Display the currency/amount pill (`EUR 103,753.63`) **only on the active step or hovered edge** (or zoomed in `> 1.15`) to eliminate edge-label clutter.
  - `OWNS` / `CONTROLS` / `DIRECTOR_OF` -> Clean `1.5px` `#64748B` directional line (reveal share band `75–100%` or `nominee` badge cleanly on hover/focus).
  - `HOLDS_ACCOUNT` / `HAS_ADDRESS` / `REPRESENTS` -> Quiet `1px` `#CBD5E1` structural connector.
  - `POSSIBLY_SAME_AS` -> `1.5px` `#B45309` **dotted undirected line** (zero arrowhead).

---

## STEP 2 — `ANTI-AI DESIGN` & `TASTE` SYSTEM (STRICT LIGHT MODE)

Channel the **Swiss Archival Daylight** aesthetic: crisp paper-white and cool mineral-stone matte surfaces, razor-sharp `1px` structural hairlines, disciplined whitespace, and editorial typography.

### 10 Hard `Anti-AI Design` Bans (`Taste` + `Hallmark` Enforcement)
1. **NO Dark Mode Anywhere:** Zero dark backgrounds (`#0D0F12`, `#111827`, `#0F172A`), zero dark cards, zero dark code/inspector blocks, and zero theme switchers.
2. **NO Glows, Neon, or Colored Shadows:** Zero glowing borders, zero `drop-shadow` halos around nodes, zero blurred ambient pastel blobs behind the canvas. Elevation uses **only** `1px` hairline borders and subtle neutral shadow `0 1px 2px rgba(17, 19, 24, 0.04)` on floating canvas toolbars.
3. **NO AI Default Colors or Gradients:** Ban Tailwind indigo/violet (`#6366F1`, `#8B5CF6`), ban multi-stop gradients on buttons/headers/badges, and ban the overused AI warm-cream/terracotta (`#F4F1EA` + `#D97757`) palette.
4. **NO Decorative Glassmorphism:** Ban `backdrop-filter: blur(...)` frosted panels; use opaque matte daylight surfaces (`#FFFFFF`, `#F6F7F9`, `#EEF1F5`).
5. **NO Left-Border Accent Stripes on Cards (`border-left: 4px solid`):** That is the single most obvious AI-generated UI tell. Every callout, step row, and notice uses a uniform `1px` full-perimeter border (`border: 1px solid ...`) with a quiet tonal background.
6. **NO Symmetric 4-Card SaaS KPI Grids:** Do not render four identical metric boxes (`Sent`, `Returned`, `Ratio`, `Strength`). Replace them with a single editorial **Flow Retention Bar** + inline tabular figures.
7. **NO Floating Popovers Covering the Graph:** Clicking a node never opens a floating card on top of adjacent nodes; details dock cleanly in the right-hand inspector rail.
8. **NO Emojis Anywhere in the UI:** Use `lucide-vue-next` (`1.5px` stroke) exclusively.
9. **NO AI Typography & Copywriting Clichés:** Ban tracked-out `ALL-CAPS` small eyebrows above every section title, ban `→` suffixes on buttons, ban exclamation marks, and ban filler adjectives. Write concise, calm, factual investigator prose.
10. **NO Bouncy / Gimmicky Animations:** Never animate card hover scaling (`transform: scale(1.03)`), pulsing rings, or continuous background motion.

### Single Source of Truth — Swiss Archival Daylight CSS Tokens (Light Mode Only)
Define one clean `:root` token sheet (`color-scheme: light`):

```css
:root {
  color-scheme: light;

  /* Matte Daylight Surfaces */
  --bg-canvas: #F6F7F9;          /* Cool archival stone behind the graph */
  --bg-grid-dot: #D5DBE3;        /* Subtle 1px spatial dot matrix (20px pitch) */
  --bg-surface: #FFFFFF;         /* Crisp paper white for header & docked inspector */
  --bg-subtle: #FAFBFD;          /* Quiet secondary section background */
  --bg-inset: #EEF1F5;           /* Matte inset controls, pills, & inactive tabs */

  /* Editorial Ink Hierarchy (WCAG AA+ on Daylight Surfaces) */
  --ink-primary: #111318;        /* Deep carbon ink for headlines & entity names */
  --ink-secondary: #374151;      /* Balanced body & evidence prose */
  --ink-muted: #6B7280;          /* Metadata, timestamps, & secondary captions */

  /* Architectural Hairlines */
  --border-hairline: #E2E6EC;    /* Primary 1px structural divider */
  --border-strong: #CBD2DC;      /* Hover / interactive control border */

  /* Restrained Functional Accents (Zero Neon) */
  --accent-ink: #1D4ED8;         /* Focused cobalt ink for active transfer hop & selection */
  --accent-surface: #EFF6FF;     /* Active step & selected row tint */
  --accent-border: #BFDBFE;      /* Active selection perimeter border */

  /* Non-Accusatory Review & Provenance Tones */
  --synthetic-ink: #0F766E;      /* Mineral teal for :Synthetic dashed rings & provenance */
  --synthetic-surface: #F0FDFA;
  --synthetic-border: #99F6E4;

  --review-ink: #92400E;         /* Calm archival amber for 'Other explanations' & priority */
  --review-surface: #FEF9EC;
  --review-border: #F3D999;

  /* Precision Radii & Shadow */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 10px;
  --shadow-control: 0 1px 2px rgba(17, 19, 24, 0.05);
}
```

### Typography & Bidirectional Numeric Precision
- **UI & Editorial Copy:** Local system stack (`system-ui, -apple-system, "Segoe UI", "Noto Sans Arabic", sans-serif`), tight headline tracking (`-0.015em`), clear weight contrast (`600` titles vs `400` prose), prose width capped at `68ch`.
- **Amounts, Account IDs, Hashes & Dates:** Monospace stack (`ui-monospace, "Cascadia Mono", "SFMono-Regular", Consolas, monospace`) with `font-variant-numeric: tabular-nums` and `direction: ltr; unicode-bidi: isolate` so `EUR 103,753.63` and `NRSYN0000000013 -> NRSYN0000000004` align to the pixel and never flip in Arabic `RTL`.

---

## STEP 3 — USABILITY, READABILITY & MOTION ARCHITECTURE

### 1. Full-Viewport Spatial Workbench (Zero Wasted Margins, Zero Cut-Off Controls)
- Compact `48px` top navigation bar (`NeonRadar` wordmark + `Search`, `Alerts`, `Data sources` + `⌘K` search trigger + `3-Step Tour` + `English / العربية` switch) + slim `32px` provenance/disclaimer strip (`--synthetic-surface` or `--bg-subtle` separated by `1px solid var(--border-hairline)`).
- On `/alerts/:id` (`AlertView.vue`) and `/entities/:id` (`EntityView.vue`), fill the remaining viewport (`height: calc(100dvh - 80px)` on desktop `>= 960px`; clean vertical stack on mobile `< 960px`):
  - **Main Spatial Graph Pane (`flex: 1`, ~68%–72% width):** Full-bleed daylight dot-grid canvas (`--bg-canvas`) with generous breathing room around the network.
  - **Docked Right Inspector Rail (`width: 400px`, `border-inline-start: 1px solid var(--border-hairline)`, `--bg-surface`):**
    - **Sticky Top Header:** Compact context title + two crisp `Reka UI` tabs: `1. Pattern Story` (or `Overview` on Entity view) and `2. Selected Node`.
    - **Independently Scrollable Body:** Never pushes the page past `100dvh`.
    - **Pinned Sticky Bottom Footer:** Always visible above the fold with `Download JSON` and `Download CSV` buttons (`ui/src/lib/evidence-export.ts`) so evidence export is never cut off.

### 2. Collision-Free Layout, Semantic Zoom (LOD) & Tactile Camera Motion
- **Deterministic Non-Overlapping Layout (`elkjs`):** Compute initial node coordinates with generous spacing (`>= 140px` between nodes) so neither emblems nor labels overlap on load. Keep a `Reset layout` button on the canvas toolbar.
- **3-Tier Semantic Zoom (Level of Detail):**
  - **Overview (`zoom < 0.65`):** Render geometric emblems + `1.5px` icons + active path highlight only (hide text labels for zero clutter).
  - **Standard (`0.65 <= zoom <= 1.15`):** Render geometric emblems + 1-line external entity caption below + amount pill on the active/hovered edge only.
  - **Detail (`zoom > 1.15`):** Reveal secondary metadata line (`GB · EUR` / registration ID) and relationship type labels (`OWNS 75–100%`, `HOLDS_ACCOUNT`).
- **Restrained Studio Motion (`@media (prefers-reduced-motion: no-preference)`):**
  - Camera `fit` and node-focus transitions use `220ms cubic-bezier(0.22, 1, 0.36, 1)`.
  - Only the **currently active transfer edge (`PAID`)** displays a subtle, steady directional dash drift (`stroke-dashoffset`) indicating money flow direction; all other edges remain completely still.
  - Compact floating **Daylight Canvas Controls** (`+`, `−`, `Fit`, `Reset`, `Legend` popover) in `--bg-surface` with `1px solid var(--border-hairline)` + optional compact corner `MiniMap`.

### 3. Bottom Chronological Money-Flow Scrubber (Synchronized Alert Investigation)
- Anchor a slim horizontal **Transfer Timeline Bar** (`--bg-surface`, `1px solid var(--border-hairline)`, `border-radius: 8px`) at the bottom-center of the Alert graph canvas:
  - Controls: `Play / Pause` (`1.5s` per transfer hop; pauses immediately on manual click) + `Prev` / `Next` buttons (also bound to `←` / `→` keyboard arrows).
  - Interactive chronological step pills (`1 · 16 Feb` — `2 · 17 Feb` — `3 · 18 Feb` — `4 · 20 Feb`).
  - Selecting any step synchronously:
    1. Highlights that `PAID` arc + its sender/receiver `BankAccount` emblems in `--accent-ink`,
    2. Softly dims non-active `PAID` arcs to `0.32` opacity so the active hop stands out effortlessly, and
    3. Highlights and scrolls to the matching transfer row in the Right Inspector's `Pattern Story` tab.

### 4. Editorial Flow Retention Bar & Calm Legitimate Explanations
- Inside `Pattern Story` (`AlertView.vue`), replace boxy KPI tiles with a clean **Flow Retention Meter**:
  - Single-row tabular comparison (`Sent: EUR 103,753.63` vs `Returned: EUR 97,690.35 · 94.2% retained` · `Pattern strength: 0.84`) above a crisp `6px` flat linear bar (`--bg-inset` track, `--accent-ink` fill — zero gradients, zero glow).
- Directly beneath the transfer steps, render **"Other explanations for this structure"** (`false_positive_notes`) inside a `--review-surface` box (`1px solid var(--review-border)`, uniform 4-side border, zero left stripe) so benign explanations (`Refunds`, `Loan drawdown/repayment`, `Cash pooling`) are read as part of the core analysis.

### 5. First-Run Guided Start (`U5`), `⌘K` Quick Jump, Full Arabic `RTL` (`D4`) & A11y (`U3`)
- **First-Run Guided Empty State (`SearchView.vue`):** Below the clean daylight search bar, include a dismissible **3-Step Quick-Start Strip** (`1. Open a synthetic circular-flow alert`, `2. Inspect a synthetic company network`, `3. Review data licences`) using real IDs fetched from `/api/v1/alerts` / `/api/v1/entities` so first-time users can explore in one click.
- **`⌘K` / `Ctrl+K` Command Palette (`Reka UI Dialog`):** Clean daylight modal to search entities instantaneously, jump to `Alerts` or `Data sources`, or switch language (`English` / `العربية`) — no dark-mode toggle.
- **Full Bilingual `English / العربية (RTL)` (`D4`):** Connect `ui/src/stores/locale.ts` and `ui/src/lib/messages.ts` across `App.vue` and all views using CSS logical properties (`margin-inline`, `padding-inline`, `inset-inline`, `border-inline`, `text-align: start`) and `<html :lang="locale" :dir="dir">`.
- **Keyboard & Screen-Reader Parity (`U3`):** Include an accessible collapsible `<details>` data table of subgraph nodes and edges alongside the visual graph, enforce WCAG AA contrast (`>= 4.5:1`) across all daylight tokens, and render crisp `2px solid var(--accent-ink)` `:focus-visible` outlines on every interactive element.

---

## STEP 4 — MODULAR IMPLEMENTATION & MANDATORY VERIFICATION

Implement cleanly inside `ui/src/` without touching backend/contract files:
1. `ui/src/styles/tokens.css` (imported in `main.ts` / `App.vue`) — Strictly Light-Mode Swiss Archival Daylight CSS variables, typography rules, `tabular-nums`, and logical layout helpers.
2. `ui/src/lib/entity-visuals.ts` (+ unit tests in `ui/src/lib/__tests__/entity-visuals.spec.ts`) — Complete `C2` schema-to-shape, `lucide-vue-next` icon, daylight fill/stroke, `:Synthetic` dashed-ring, and `POSSIBLY_SAME_AS` edge-style mapping.
3. `ui/src/components/GraphCanvas.vue` (and focused subcomponents for custom C2 shape nodes & timeline scrubber) — Non-overlapping `elkjs` layout, 3-tier semantic zoom LOD, smooth `220ms` camera transitions, single-arc active flow, `MiniMap`, and `<details>` accessible table parity.
4. `ui/src/App.vue`, `AlertView.vue`, `EntityView.vue`, `AlertsView.vue`, `SearchView.vue`, `SourcesView.vue` — Full-viewport daylight spatial split, docked right inspector rail with sticky JSON/CSV export footer, Editorial Flow Retention Bar, calm `Other explanations` card, 3-Step First-Run guide, `⌘K` Command Palette, and complete `EN / العربية (RTL)` wiring via `ui/src/stores/locale.ts`.

### Mandatory Quality & Visual Gate Before Completion
Run every check below and resolve all errors or warnings:
```bash
npm --prefix ui run lint
npm --prefix ui run type-check
npm --prefix ui run test:unit -- --run
npm --prefix ui run build
```
*(When the local stack is running, also run `make e2e` and verify in a real browser at `1440x900` and `390x844` in both `English (LTR)` and `العربية (RTL)` that: (1) the interface is 100% Light Mode with zero dark surfaces or AI-slop tropes, (2) zero node labels overflow their containers, (3) clicking nodes updates the docked right inspector without covering the graph, and (4) `Download JSON` / `Download CSV` remain visible without scrolling the outer window.)*
