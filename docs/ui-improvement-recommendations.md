# Senior UI Improvement Recommendations

This document records recommended follow-up work for the NeonRadar UI. These items are intentionally not included in the warning-message collapse change and can be implemented incrementally.

## High priority

### Persist the notice collapse preference

The panel currently resets to expanded after a full page reload.

- Store only the UI preference in `localStorage`, for example:
  - `neonradar.notices.collapsed`
- Do not store notice text, entity IDs, question text, or investigation data.

### Make the collapsed state more actionable

The summary status helps, but the real-data state should have especially strong visual prominence.

- Consider adding a short status description such as:
  - “Review data context before continuing”
- Keep the full API-provided disclaimer inside the expanded panel.

### Standardize all error states

The application uses several different error presentations:

- `ui/src/App.vue`
- `ui/src/views/AlertsView.vue`
- `ui/src/components/ErrorMessage.vue`

Use one shared error-panel pattern with:

- Consistent iconography
- A clear heading
- A retry action
- `role="alert"` where the error is urgent
- `role="status"` only for non-urgent informational failures

### Improve loading states

Replace plain “Loading…” text with lightweight skeletons for:

- Alert rows
- Search results
- Entity properties
- Graph side panels

Keep layout dimensions stable while data loads to avoid content shifting.

### Improve empty states

Empty results should explain what happened and provide the next action.

Examples:

- No filters: “No alerts are available.”
- With filters: “No alerts match these filters.”
- Search with no results: offer to broaden or clear the search.

## Medium priority

### Make the alerts workflow more efficient

- Add result counts near the filter bar.
- Show active filters as removable chips.
- Preserve scroll position when loading more results.
- Consider replacing “More alerts” with cursor-aware pagination text such as “Load 25 more”.

### Improve filter usability

- Add explicit labels or helper text for entity IDs.
- Support clearing each filter independently.
- Show when a filter is currently loading.
- Consider debouncing entity searches rather than requiring a full form submission for every exploratory change.

### Strengthen graph interaction affordances

Add a small control group for:

- Fit graph
- Zoom in/out
- Reset selection
- Center on selected entity

Also:

- Add a visible legend explaining node and edge styles.
- Ensure the graph has a useful empty state when no relationships are available.
- Provide a keyboard-accessible alternative to graph-only discovery.

### Improve evidence hierarchy

Separate:

- Entity identity
- Source records
- Relationships
- Pattern evidence
- Review metadata

Also:

- Use consistent source badges and timestamps.
- Make provenance visible without requiring users to inspect every card manually.

### Improve responsive behavior

The desktop sidebar and workspace layout are strong, but mobile users would benefit from:

- A compact menu toggle
- A clearer current-page indicator
- Less vertical duplication in headers
- Better handling of long entity names and IDs

Check the layout at 320px, 375px, and 768px widths.

### Make destructive or consequential actions harder to mis-trigger

Any future review, export, or data-loading controls should include:

- Clear action labels
- Confirmation for irreversible actions
- Disabled/loading states
- A visible completion state

## Accessibility and quality

### Add automated accessibility checks

Add axe or an equivalent accessibility check to the Playwright suite.

Prioritize:

- Focus order
- Accessible names for icon-only buttons
- Color contrast
- Form-label association
- Keyboard graph alternatives
- Focus restoration after route changes

### Add visual regression coverage

The UI has many states that can regress without breaking unit tests:

- Expanded and collapsed notices
- Real-data notice
- Empty alerts
- API error state
- Mobile navigation
- Graph loading and empty states

Add a small set of screenshot baselines for those states.

### Centralize design tokens

Continue moving repeated colors, spacing, borders, and focus styles into CSS variables.

Add semantic tokens such as:

- `--color-warning-surface`
- `--color-warning-border`
- `--color-danger-surface`
- `--color-focus-ring`

This will make the UI easier to maintain and support a future dark theme.

### Add a dark/high-contrast theme strategy

The current palette is readable in the default light mode, but warning and synthetic/real-data states should be tested under:

- High contrast
- Forced colors
- Dark mode
- Reduced motion

## Current scope note

The warning-message collapse behavior is implemented and verified separately. The items in this document are recommended follow-up improvements and are not silently included in that change.
