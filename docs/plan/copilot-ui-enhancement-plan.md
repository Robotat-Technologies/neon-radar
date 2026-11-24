# Copilot UI enhancement implementation plan

**Baseline:** `dev`, commit `2cbd71c`, reviewed on 24 November 2026.

**Status:** Draft for the lead's review. No implementation has started.

This document is a plan only. Each implementation task below needs its own authorization.

## 1. Documentation placement and context

[docs/README.md](../README.md) places project plans under `docs/plan/`. The documentation index does not list this document yet; the proposed `plan/` row is:

```markdown
| [plan/](plan/) | The [project plan export](plan/neonradar-project-plan.md) and the [copilot UI enhancement plan](plan/copilot-ui-enhancement-plan.md) | present |
```

Do not edit the exported project plan.

### Current application

- Vue 3.5.44, Vue Router 5.4.0, Pinia 4.1.0, Vite 8.3.5 and TypeScript 6.0.3.
- Plain CSS with logical properties; Cytoscape/fcose for graphs.
- API requests use same-origin `/api/v1`, proxied through Vite or nginx.
- The shell gates page rendering on metadata and mandatory notices.
- There is no existing chat UI, conversation store or notification queue.

Sources: [package manifest](../../ui/package.json), [lockfile](../../ui/package-lock.json), [application shell](../../ui/src/App.vue), [API client](../../ui/src/api/client.ts).

Follow [CLAUDE.md](../../CLAUDE.md), [frontend rules](../../.claude/rules/frontend.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md):

- Use `<script setup lang="ts">`; retain TypeScript `~6.0.3`.
- Derive transport types from the generated schema.
- Preserve mandatory disclaimers and logical CSS.
- Bundle runtime resources locally; introduce no telemetry, external fonts or CDNs.
- Use synthetic fixtures only. Do not inspect protected real or held-out data.
- Preserve unrelated working-tree changes.
- Use Conventional Commits and small PRs, respecting the documented 400-line limit for code, tests and configuration.

### Current versus planned copilot contract

The existing [endpoint](../../api/src/neonradar_api/main.py) returns HTTP 501 for valid requests.

| Area | Current contract | Planned Phase 4 |
|---|---|---|
| Request | `question`, `context_entity_ids` | Adds `template_id` and `slots`. |
| Status | `answered`, `refused`, `unsupported` | Adds `needs_clarification`. |
| Clarification | No choices or grounded-slot payload | Adds choices, slots and interpretation. |
| Confirmation | Cannot express the required resubmission | Resubmits `template_id` and `slots`; no separate confirmation wire status. |
| Refusal text | `answer_text` must be null; use `refusal_reason` | Refusal text also appears in `answer_text`. |
| Supporting data | One query, parameters and subgraph | Adds query lists, facts, notices, suggestions and router/model information. |
| Metadata | No `GET /copilot` operation | Adds notice, badge and template catalog. |

Sources: [current Python models](../../contracts/src/neonradar_contracts/api.py), [generated frontend schema](../../ui/src/api/schema.d.ts), [planned contract and confirmation semantics](../build/PHASE-4.md) (sections 5.3 and 7.1).

Unknown request fields are forbidden. Sending `template_id` or `slots` to the current API would fail validation.

## 2. Goals, boundaries and approved decisions

### Goals

- Add centralized interface feedback through a typed notification facade.
- Add a dedicated `/copilot` page and navigation item.
- Retain one conversation across in-app navigation, clearing it on reload.
- Demonstrate richer workflows through explicitly enabled development scenarios.
- Isolate transport mapping so future contract adoption does not require component changes.
- Preserve accessibility, privacy, existing notices and production CSP.

### Approved decisions

- Pin **vue-sonner 2.0.9**. Its real build/CSP/RTL verification is the first implementation task.
- Keep plain CSS. Add no shadcn-vue or Tailwind.
- Sonner owns the toast queue. Add no notification queue in Pinia.
- Name interface feedback `UiNotification`; retain existing generated investigation `Alert` types.
- Store ordered typed turns with stable IDs; introduce no normalized conversation tables.
- Enable scenarios only through a serve-only compile-time gate plus `VITE_COPILOT_SCENARIOS=1`.
- Normal development, preview and production use the live adapter unless the development gate explicitly enables scenarios.
- Production output must contain no scenario modules or fixture data.
- Live requests contain only current generated request fields.
- Development scenarios use frontend models and never masquerade as generated responses.
- If Task 1 fails, stop and ask the user. Do not substitute a library, upgrade the stack or weaken CSP automatically.

### Non-goals

Backend changes, contract changes, Phase 4 implementation, streaming, authentication, a `User` model, persistent history, multiple conversations, broad entity normalization, and a whole-application visual redesign.

## 3. Design

### Notifications

Introduce a small facade under `ui/src/lib/notifications.ts`.

- `UiNotification`: severity `success | error | warning | info`, message, optional description and optional deduplication key.
- `notify(notification)` returns a string notification ID.
- `dismissNotification(id)` dismisses that notification.
- Generate IDs in the facade; reuse a deduplication key as a stable Sonner ID where supplied.
- Success/info default to five seconds. Warning/error default to persistent, manually dismissible feedback.
- Accept plain text. Do not display raw exceptions, request payloads or stack traces.

Mount one `NotificationHost.vue` in the application shell **outside the metadata gate**. Import Sonner's CSS once and theme through existing CSS variables. Sonner remains responsible for toast lifecycle and dismissal.

Keep mandatory notices and page-loading errors in their existing persistent components. Keep the API client presentation-free. Failed copilot turns display their own inline errors; they must not also produce automatic global error toasts.

Use truthful action feedback, such as "Download started," rather than claiming the browser saved a file successfully.

### Copilot organization and provider boundary

Create `ui/src/features/copilot/` containing:

- `models.ts`: frontend commands, results, turns and errors.
- `provider.ts`: provider interface.
- `live-adapter.ts` and `mapping.ts`: generated transport types and mapping.
- `session.ts`: the Pinia session store.
- Components for composer, turn, resolution controls and evidence.

Add the routed view at `ui/src/views/CopilotView.vue`.

Components consume frontend models and emit semantic events. They do not inspect raw copilot responses or construct HTTP request bodies.

The frontend provider supports:

- **Ask:** original question plus context entity IDs.
- **Resubmit:** original input plus a selected choice or explicitly confirmed interpretation.
- An `AbortSignal` for each attempt.

The frontend result supports answer, refusal, unsupported and clarification outcomes, with:

- Display text and optional interpretation.
- Notices and suggestions.
- Optional evidence subgraph.
- A query list.
- Optional clarification controls: choice, confirmation or rephrasing.

Confirmation is a frontend resubmission action. It is never introduced as a separate API status.

The current live adapter:

- Uses generated `CopilotRequest` and `CopilotAnswer` aliases.
- Serializes only `question` and `context_entity_ids`.
- Maps refusals from `refusal_reason`.
- Maps the singular query into the frontend query list.
- Preserves the real 501 unavailable outcome.
- Rejects unsupported resubmission commands locally, before fetching.
- Never silently resends a question as though that confirmed an interpretation.
- Does not invent a copilot metadata endpoint or claim a model mode.

A future Phase 4 adapter will translate the same frontend resubmission command into the approved generated request and map richer responses. Components and session actions remain unchanged.

### Session and request lifecycle

Use one Pinia store with an ordered array of turns. Each turn holds:

- Stable UUID.
- Snapshot of submitted input.
- Last semantic command, enabling exact manual retry.
- Phase: pending, complete, failed or cancelled.
- Last result and a safe, typed error.
- Attempt correlation identifier.

Allow one active request. Users may edit their next draft while it runs.

- Preserve the submitted draft until success. Clear it only if its revision still matches the submitted snapshot.
- Failure leaves the draft untouched.
- Retry repeats the saved command on the same turn without overwriting a newer draft.
- Choice and confirmation resubmissions update the existing turn.
- Preserve the previous clarification while a follow-up is pending or failed; disable its controls during that attempt.
- Enable resolution controls only on the latest applicable turn.
- Cancellation aborts locally and invalidates correlation. Do not claim server processing stopped.
- Ignore success, failure and cleanup from stale attempts.
- Route unmounting does not abort or clear the session.
- Reset aborts, invalidates pending work and clears turns and draft.
- Keep controllers and provider instances outside serializable store state.

Attach evidence to each answer. Later entity requests must not mutate earlier answer evidence. Use immutable turn replacement and stable graph references.

### Development isolation and build enforcement

Reserve `ui/src/dev/copilot-scenarios/` for scenario providers, fixtures and controls.

Derive `__COPILOT_DEV_SCENARIOS__` in Vite configuration. It is true only when:

- `command === 'serve'`;
- `isPreview === false`;
- `VITE_COPILOT_SCENARIOS === '1'`.

Use a single guarded dynamic import, also retaining the literal `import.meta.env.DEV` check. No scenario import may appear above that boundary.

Consume the opt-in from `ui/.env.development.local` or the process environment. Tests inject providers directly rather than relying on environment flags.

Add two build checks:

1. A build-only Vite hook rejects scenario module identities in emitted chunks.
2. A Node post-build scanner checks every emitted file for fixture sentinels, reserved asset names and scenario source-map identities.

Reserve `NR_COPILOT_DEV_SCENARIOS_V1` and `syn-copilot-ui-` for development fixtures. Keep these tokens out of normal application source.

Parse external, hidden and inline source maps, including indexed sections. Do not reject a normal importer's original source merely because its eliminated guarded import appears in `sourcesContent`.

Run the scanner after output writing, using the actual output directory. Preserve existing `build-only` argument forwarding. Wire a portable matrix runner into UI CI.

Vite documents [conditional configuration](https://vite.dev/config/#conditional-config), [static defines](https://vite.dev/config/shared-options#define) and [environment replacement](https://vite.dev/guide/env-and-mode). `DEV` alone cannot guarantee exclusion when `NODE_ENV` is overridden.

### UX, accessibility and privacy

- Label the composer and expose pending, unavailable, cancelled and retry states.
- Support keyboard submission, with Shift+Enter for a newline and no submission during IME composition.
- Keep focus stable when responses arrive.
- Use restrained polite announcements for progress/completion and avoid duplicate transcript/toast announcements.
- Give notification dismissal and clarification controls accessible names.
- Require an explicit action to confirm an interpretation.
- Auto-scroll only when the reader is near the bottom; otherwise offer a "New response" control.
- Use logical CSS and verify LTR/RTL, Arabic text wrapping and narrow screens.
- Translate new interface controls through the existing English/Arabic message mechanism; preserve backend answer wording.
- Mount evidence graphs only when requested. Provide a textual node/relationship list and query text without requiring the canvas.
- Keep questions and answers out of URLs, titles, browser storage, service workers and logs.
- Use POST requests with `cache: 'no-store'`.
- Add copilot-specific proxy `Cache-Control: no-store` and disable that route's access log while retaining existing security headers.
- Keep development data visibly labeled; never fall back to it after a live failure.

## 4. Ordered implementation tasks

All commands below run from the repository root in PowerShell. On Linux/CI, use `npm` instead of `npm.cmd`. New script names must be introduced by their corresponding task.

### Task 1 — Environment sanity and Sonner compatibility gate

**Files:** UI manifest/lockfile; new `NotificationHost.vue`; application shell; an E2E-only compatibility fixture, runner and spec.

First restore dependencies using the lockfile, then pin Sonner. Do not delete the lockfile to repair dependency resolution.

```powershell
node --version
npm.cmd --version
docker version
docker info
npm.cmd ci --prefix ui --ignore-scripts --no-audit --no-fund
npm.cmd install --prefix ui --save-exact vue-sonner@2.0.9 --ignore-scripts --no-audit --no-fund
npm.cmd ls --prefix ui vue vue-sonner vite typescript
npm.cmd exec --prefix ui -- playwright install chromium
npm.cmd run --prefix ui type-check
npm.cmd run --prefix ui build
npm.cmd run --prefix ui test:notifications:compat
```

Implement `test:notifications:compat` as a Node runner that:

- Builds the ordinary production UI.
- Builds an E2E-only fixture importing the same notification host into a separate ignored directory under `ui/node_modules/.cache/`.
- Serves both through isolated containers using the actual UI Dockerfile/nginx configuration.
- Uses `--add-host api:127.0.0.1` for standalone nginx startup; no API or Neo4j instance is required.
- Uses synthetic metadata interception for the ordinary application.
- Cleans up only its own containers/processes in `finally`.

**Acceptance:** four severities, stacking, close/swipe, keyboard dismissal, long Arabic text, desktop/mobile LTR/RTL, visible styling, no horizontal overflow, unchanged CSP, no CSP events/console violations or uncaught errors. Listeners must be installed before navigation.

The fixture must introduce no production route, debug button or window hook.

**Hard stop:** any unresolved environment, dependency, type, build, CSP, RTL or interaction failure stops all subsequent work. Report evidence and ask the user. Previous checks found a missing Windows Rolldown binding and Docker daemon access trouble; neither is presumed fixed.

Do not use `make demo-mini` for this gate: it reloads the demo graph.

### Task 2 — Notification facade and real action integration

**Files:** notification facade/host, application shell, alert evidence-download handlers and focused tests.

Complete severity defaults, dismissal and deduplication. Add truthful download-started feedback and safe download-failure handling.

```powershell
npm.cmd run --prefix ui test:unit -- --run src/lib/__tests__/notifications.spec.ts src/__tests__/App.spec.ts
npm.cmd run --prefix ui lint
npm.cmd run --prefix ui test:notifications:compat
```

**Acceptance:** one host exists before metadata succeeds; no second queue; no duplicate API-error announcements; mandatory notices remain visible.

### Task 3 — Frontend models and current live adapter

**Files:** copilot models/provider/adapter/mapping; API client/type aliases; adapter tests.

Add generated-only POST transport with signal propagation and no-store fetching. Keep the frontend presentation contract independent.

```powershell
npm.cmd run --prefix ui test:unit -- --run src/features/copilot/__tests__/live-adapter.spec.ts src/api/__tests__/client.spec.ts
npm.cmd run --prefix ui type-check
```

**Acceptance:** exact current request fields, correct refusal mapping, safe network/422/501/503 handling, and zero requests for unsupported resubmissions. No generated schema or backend edits.

### Task 4 — In-memory session lifecycle

**Files:** copilot session store and tests.

Implement stable turns, draft revisions, attempt correlation, cancellation, manual retry, reset and resolution actions.

```powershell
npm.cmd run --prefix ui test:unit -- --run src/features/copilot/__tests__/session.spec.ts
npm.cmd run --prefix ui type-check
```

**Acceptance:** duplicate submission blocked; stale attempts cannot overwrite state; retry preserves newer drafts; cancellation/reset invalidate late responses; evidence remains attached to its answer.

### Task 5 — Dedicated live copilot page

**Files:** routed view, feature components, router, navigation, message strings and CSS.

Build the composer, transcript, inline recovery, resolution controls and demand-mounted evidence.

```powershell
npm.cmd run --prefix ui test:unit -- --run src/features/copilot/__tests__/CopilotView.spec.ts
npm.cmd run --prefix ui lint
npm.cmd run --prefix ui type-check
```

**Acceptance:** normal mode calls the live endpoint and shows 501 honestly; navigation retains the session; evidence has a non-graph alternative; components contain no wire-format branching.

### Task 6 — Fail-closed scenario gate

**Files:** Vite configuration, environment declarations, Vitest configuration and provider selection.

Convert Vite configuration to a callback; preserve existing aliases/proxies. Adapt Vitest's configuration merge and force its application-level gate false.

```powershell
npm.cmd run --prefix ui test:unit -- --run src/features/copilot/__tests__/provider-selection.spec.ts
npm.cmd run --prefix ui type-check
npm.cmd run --prefix ui build
```

**Acceptance:** default dev, preview and every build select live mode. Only explicitly opted-in serving can import scenario code.

### Task 7 — Post-build exclusion checks and matrix

**Files:** build-check script/tests, build-only Vite hooks, package scripts and UI CI.

Add `check:copilot-output`, `check:copilot-builds` and `test:copilot-build-guard`.

```powershell
npm.cmd run --prefix ui test:copilot-build-guard
npm.cmd run --prefix ui build
npm.cmd run --prefix ui check:copilot-output
npm.cmd run --prefix ui check:copilot-builds
```

The matrix sets the opt-in to `1` in every child process:

| NODE_ENV | Mode | Source maps |
|---|---|---|
| production | production | disabled |
| production | staging | external |
| development | production | hidden |
| development | staging | inline |

Use separate ignored output directories and `spawn`/`execFile` with argument arrays, without shell interpolation.

**Acceptance:** leaked module identities, renamed/copied fixture assets and fixture strings fail the build. Clean source maps containing only the ordinary guarded importer pass. Missing output fails. Checks use actual custom output directories.

### Task 8 — Synthetic development workflows

**Files:** reserved scenario subtree, development controls and scenario tests.

Add deterministic answer, refusal, unsupported, clarification, confirmation and failure scenarios. Include controllable delays/failures for lifecycle tests. All scenario behavior goes through frontend provider models.

```powershell
npm.cmd run --prefix ui test:unit -- --run src/features/copilot/__tests__/scenarios.spec.ts
npm.cmd run --prefix ui build
# After Task 7 ships in PR 4:
npm.cmd run --prefix ui check:copilot-builds
```

**Acceptance:** choices preserve other grounded values; confirmation requires an explicit click and resubmits the same turn; failures permit deliberate retry; no generated-response casts or live fallback.

### Task 9 — Browser, privacy and production regression tests

**Files:** focused browser runner/specs, shared synthetic test helpers and nginx configuration.

Add `test:copilot:browser`. Its runner must:

- Exercise the opted-in development server.
- Exercise the normal production UI through nginx.
- Run the unchanged API in an isolated test container for a genuine 501 response.
- Intercept metadata with synthetic fixtures so no Neo4j instance is needed.
- Capture actual outgoing request bodies.
- Clean up its own isolated network, containers and processes.

```powershell
npm.cmd run --prefix ui test:copilot:browser
npm.cmd run --prefix ui test:notifications:compat
npm.cmd run --prefix ui check:copilot-builds
```

**Acceptance:** real 501, exact request fields, navigation retention, reload clearing, keyboard use, cancellation/retry, no mock controls in production, no browser persistence, no question-bearing URLs, no-store responses and zero CSP violations.

Preserve security-header inheritance when adding copilot-specific proxy/cache behavior.

### Task 10 — CI, manual review and documentation

**Files:** UI README, this plan, CI/E2E workflows and manual checklist.

Make the build matrix part of ordinary UI CI. Run focused nginx/browser checks in the existing browser-capable workflow. Document local opt-in, live limitations, verification commands and pending human checks.

```powershell
npm.cmd run --prefix ui lint
npm.cmd run --prefix ui type-check
npm.cmd run --prefix ui test:unit -- --run
npm.cmd run --prefix ui build
npm.cmd run --prefix ui check:copilot-builds
npm.cmd run --prefix ui test:notifications:compat
npm.cmd run --prefix ui test:copilot:browser
git diff --exit-code -- contracts api ui/src/api/schema.d.ts
```

**Acceptance:** automated checks pass, protected contract/backend paths are unchanged, and manual findings are recorded explicitly. Do not mark unperformed manual checks as passed.

## 5. PR split

Work ships as separate small PRs, each within the 400-line limit defined in [CONTRIBUTING.md](../../CONTRIBUTING.md).

- **PR 1:** Tasks 1-2.
- **PR 2:** Tasks 3-5; split further if over 400 lines.
- **PR 3:** Tasks 6 and 8.
- **PR 4:** Tasks 7, 9 and 10; scope pending lead approval.

Each PR is branched, tested and reviewed independently. A later PR starts only after the earlier one is merged. Further splits must also respect the 400-line limit and this sequential workflow.

**Dependency note:** Task 8's `check:copilot-builds` acceptance command is introduced by Task 7 in PR 4. PR 3 runs the available scenario/provider tests and normal build; its matrix revalidation waits for PR 4. The permanent module/output exclusion checks are not complete at PR 3, and PR 4's scope remains pending lead approval.

## 6. Test and manual-review checklist

Automated coverage must include:

- Notification dismissal, severity defaults, deduplication and availability during metadata failure.
- Late responses following cancellation/reset and subsequent requests.
- Failure/retry with exact command replay and newer draft preservation.
- Clarification slot preservation and explicit confirmation resubmission.
- Navigation retention and reload clearing.
- Production module/fixture exclusion under all matrix combinations.
- Keyboard submission, IME handling, focus stability and evidence access.
- Production nginx CSP console/event checks and no-store headers.

Manual screen-reader review, defaulting to NVDA with Chromium on Windows:

- Composer, buttons, choices, errors and notices have useful names.
- Progress and new-result announcements occur once and do not reread the entire transcript.
- Toasts and incoming answers do not steal focus.
- Dismissal and confirmation work by keyboard.
- Failed-turn recovery remains discoverable.
- Textual evidence communicates information without the graph.
- "New response" navigation works while reading older content.
- EN/AR direction, reading order and mixed-script content remain understandable.

## 7. Open questions and risks

No product-scope decisions remain open. Verification and future integration still carry these risks:

- **Sonner compatibility:** source inspection supports the choice; Task 1 must establish runtime compatibility. Failure requires a user decision.
- **Environment readiness:** Windows native bindings and Docker access require rechecking before implementation proceeds.
- **Retry cost:** retry may repeat server computation; cancellation cannot promise server-side cancellation. Use explicit manual retry.
- **Fixture drift:** development scenarios describe intended workflows, not current wire compatibility. Recheck mappings when an approved Phase 4 contract arrives.
- **Future integration:** the adapter boundary should contain the contract migration, but backend behavior must still be verified through contract and integration tests.
- **Accessibility:** automated checks cannot establish screen-reader usability. A reviewer must complete the manual checklist.
- **Build leakage:** static gating requires enforcement. Retain module-identity and emitted-output checks permanently.
