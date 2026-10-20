---
paths:
  - "ui/**"
---
# Frontend rules
- Vue 3.5 single-file components with `<script setup lang="ts">`; no Vapor mode.
- TypeScript pinned to ~6.0.3. Never install typescript@latest.
- API types are generated from contracts/openapi/v1.json into src/api/schema.d.ts; never
  hand-write API types.
- Graph rendering uses Cytoscape.js; never @neo4j-nvl.
- Use CSS logical properties (margin-inline-start, not margin-left) so Arabic RTL works later.
- The standing disclaimer is visible on every page that shows entities or alerts.
- No analytics, no external fonts or CDNs at runtime; everything is bundled.
