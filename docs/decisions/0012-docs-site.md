# 0012. Documentation site

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (technical writer, tech lead)

To be decided in Phase 6, when the documentation site is built (`docs/build/PHASE-1.md` sections 0.3 and 7.6). This draft records the research recommendation so the documentation written until then fits the likely tool; the deciders edit it until it says what they think.

## Context

Phase 6 publishes a documentation site from the Markdown in `docs/`; the [project plan](../plan/neonradar-project-plan.md) lists typology explainers, the architecture and a quickstart, and wants the project's domain pointed at the documentation site. Four things shape the choice:

- **The frontend team writes Vue 3.** A tool whose themes and components are Vue lets the same people and skills build both.
- **Arabic documentation may follow.** The frontend is written right-to-left ready, with CSS logical properties (`.claude/rules/frontend.md`), and the documentation site should be able to add an Arabic locale without a rework.
- **Search should work without a third-party service**, in the spirit of guardrail G3 (nothing phones home).
- **Hosting on GitHub Pages**, built by a GitHub Actions workflow, as the research note assumed.

What the candidates looked like on 16 October 2026 (`docs/research/2026-10-16/synthetic-docs-mcp.md` part B):

- **VitePress** (MIT). Stable 1.6.4 (August 2025, on Vite 5) and 2.0.0-alpha.20 (September 2026, on Vite 8, like the NeonRadar frontend). Themes and custom components are Vue single-file components. Built-in local search ("fuzzy full-text search using an in-browser index", minisearch) needs no external service; its tokenizer splits Arabic words, but there is no Arabic stemming unless a custom `processTerm` is supplied. The deploy guide has an official GitHub Pages workflow. Right-to-left: the stable documentation calls RTL support experimental and needs an RTLCSS plugin; native RTL with CSS logical properties was merged to `main` on 13 September 2026 but is not in any published release yet.
- **Astro Starlight** (MIT, 0.42.6, peer Astro 7). "Full right-to-left (RTL) language support", with an Arabic locale as the i18n guide's own example and built-in Arabic interface strings. Pagefind search by default, which supports Arabic stemming. A GitHub Pages action exists. Vue components can be embedded as islands, but the site framework is Astro, a second framework for the team; 0.x versions may break on minor releases.
- **Material for MkDocs** (MIT, 9.7.7). Entered maintenance mode on 11 November 2025: "no new features will be added", with critical bug and security fixes "for 12 month at least". It is incompatible with MkDocs 2.0, and MkDocs 1.x is unmaintained.
- **Zensical** (MIT), from the creators of Material for MkDocs. Arabic interface and direction support and offline search, but still an alpha (0.0.70).

## Options considered

1. **VitePress.** Vue-native, local search, a short official GitHub Pages workflow. Drawbacks: stable 1.6.4 is 14 months old and on Vite 5; native RTL is merged but unreleased; Arabic search quality needs extra work.
2. **Astro Starlight.** The best right-to-left and Arabic search support today. Drawbacks: a second framework (Astro, Node 22.22 or later) in which Vue appears only as islands; 0.x versioning.
3. **Material for MkDocs.** Mature and well known. Drawbacks: maintenance mode, a fix guarantee that runs out around November 2026, incompatible with MkDocs 2.0. Not a choice for a new project.
4. **Zensical.** Promising for a Python-first team. Drawback: alpha.

## Decision

We will use VitePress:

- Start on the 2.0 line if a release that includes native right-to-left support exists when Phase 6 starts; otherwise weigh 2.0 alpha against 1.6.4 then.
- Use the built-in local search; no hosted search service.
- Deploy to GitHub Pages with the official workflow, updating the action versions it pins.
- Write custom CSS with logical properties from the start, so an Arabic locale needs no rework, and plan an Arabic-aware `processTerm` (or a Pagefind plugin) when Arabic pages arrive.

If Arabic documentation becomes urgent before VitePress ships native right-to-left support, or Arabic search quality matters more than one framework, we will use Astro Starlight instead.

## Consequences

- The Docs and UI squads share Vue skills and components between the explorer and the documentation site.
- The documentation stays plain Markdown in `docs/`, so the choice can still change in Phase 6 with little rework; VitePress-specific syntax is not used before then.
- Right-to-left support depends on a VitePress release that did not exist on 16 October 2026. If none ships by Phase 6, the fallback is Starlight or the experimental RTLCSS route.
- Arabic search needs extra work in either VitePress option.
- Before launch, the built site should be checked for third-party requests (fonts, analytics, search), in the spirit of G3.
- The facts above date from 16 October 2026; the deciders re-check versions and the state of right-to-left support when Phase 6 starts.

## Sources

- `docs/research/2026-10-16/synthetic-docs-mcp.md` part B (B1 VitePress, B2 MkDocs, Material for MkDocs and Zensical, B3 Astro Starlight, B4 recommendation), with the primary sources it lists ([B1] to [B18]).
- `docs/build/PHASE-1.md`: sections 0.3 (Phase 6), 2.1 (G3) and 7.6 (ADR numbers).
- `docs/plan/neonradar-project-plan.md`: Docs, DX and Launch squad, and "pointing the domain at the documentation site".
- `.claude/rules/frontend.md` (CSS logical properties).
