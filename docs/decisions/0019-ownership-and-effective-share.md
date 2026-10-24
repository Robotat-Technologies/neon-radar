# 0019. Ownership and effective share calculation

- **Status:** proposed
- **Date:** 2026-10-24
- **Deciders:** @robotat-com (tech lead, graph mentor)

## Context

Contract C3 1.1.0 promises two read-only views of the graph that Phases 4 and 5 build on (`contracts/C3-api.md`, "Ownership and paths (1.1.0)"; `docs/build/PHASE-2.md` 5.3 and M2.12):

- `GET /entities/{entity_id}/ownership`: chains of ownership up (owners) or down (holdings) from one entity, each with an effective share range;
- `GET /paths`: up to 5 shortest paths between two entities over chosen relationship types.

Registers such as the Companies House PSC register publish shares as bands, not figures. The loaders record a band as `share_pct_min` and `share_pct_max` on the `OWNS` relationship, with the open or closed bounds of the statutory band, for example `(25, 50]`: more than 25 and at most 50 percent (PHASE-2.md 5.1 and 3.3). An investigator who follows a chain wants to know what the bands along it allow, without the view claiming more than the registers say. Three things are easy to get wrong:

- **Ownership and control are different links.** Holdings through a trust or a firm load as `CONTROLS` of type `trust-or-firm` (M2.3b), and OFAC relation types load as `CONTROLS`, never `OWNS` (M2.6b), because they give no share.
- **A product of shares is not a sanctions test.** OFAC applies its 50 percent rule to entities owned 50 percent or more, directly or indirectly, in the aggregate, by blocked persons [ofac_50_percent_2014]: the status passes down a chain entity by entity, so multiplying the shares along the chain does not give OFAC's answer (PHASE-2.md 7.2 rule 6). PHASE-2.md 7.2 rule 6 also notes that a band on the PSC register may already describe an indirect holding, so multiplying it again can understate it.
- **Open and closed bounds matter at the threshold.** A path whose maximum is "less than 37.5 percent" cannot reach 37.5 percent; one whose maximum is "at most 50 percent" can reach 50 (the M2.12 fixture table).

## Options considered

1. **Traverse `OWNS` and `CONTROLS` together and give one share per path.** Simple to read, but a control link has no share, so the figure would be invented or silently partial.
2. **Sum the shares of all paths between two entities.** Closer to an aggregate holding, but the paths share relationships, bands are ranges, and the aggregate tests of the sanctions regimes differ by jurisdiction; a sum in the API would look like the result of such a test.
3. **Only `OWNS` in the ownership view; per path, the products of the band bounds as a range with open or closed bounds; no sums** (chosen).

## Decision

We will compute ownership views as follows (`graph/src/neonradar_graph/ownership.py` and the query files in `graph/src/neonradar_graph/queries/`):

- **Only `OWNS`.** The ownership view traverses `OWNS` only. `CONTROLS` and `CONSOLIDATES` (including holdings through a trust or a firm) are reachable through `/paths` and `/network`, but effective shares never include them.
- **Ranges, not figures.** A path's `effective_share_min` and `effective_share_max` are the products of `share_pct_min / 100` and `share_pct_max / 100` along it, times 100, rounded half up to 4 decimals. A bound is null when any relationship lacks it. Each bound is open when any relationship's bound is open, because for positive bounds a product reaches its bound only if every factor reaches its own; the flags are null exactly when their bound is.
- **Round before filtering.** The ownership queries round in Cypher before they filter on `min_share` and order, and Python passes the values through, so a path is kept or dropped on exactly the figure the API returns. `/paths` computes the same product in Python only for a path made entirely of `OWNS` relationships that all point the same way, multiplying in the direction of the relationships as the queries do and rounding half up (`decimal.ROUND_HALF_UP`), so both endpoints give the same figures for the same chain.
- **No sums across paths.** The API returns each path on its own. Aggregation belongs to the reader and to Phase 3's `sanctions_exposure`, which applies each regime's own test (PHASE-1.md 7.2).
- **Never a sanctions test.** An effective share is described as NeonRadar's calculation from the published bands, not a figure any register records, and never as the result of a sanctions ownership test (7.2 rule 6; `EFFECTIVE_SHARE_NOTE` in C3).
- **Simple paths only.** An ownership path never repeats a node (a cycle such as two companies that own each other ends where it would come back); `/paths` leaves out a shortest path that repeats a node.
- **Limits and timeouts.** At most 200 ownership paths from a scan of at most 5,000, at most 5 shortest paths, and a subgraph of at most 500 nodes and 1,000 relationships; `truncated` says when a limit cut something. Every query runs read-only with a 5-second transaction timeout; a timeout answers a 503 problem that suggests a smaller `max_hops` or fewer relationship types. `max_hops` picks one of the query texts rendered from the file (1 to 8 for ownership, 1 to 6 for paths), never text from input.

## Consequences

- Readers see "more than 9.375 and less than 37.5 percent" rather than a single number, which is what the registers support; the UI and the copilot word the bounds from the two flags (7.2).
- A holding through a trust, a firm or an OFAC control link never shows a share. An investigator who needs it follows `/paths` and reads the control links.
- A large aggregate holding spread over many small paths is not visible as one figure in the API; Phase 3's `sanctions_exposure` and the reader do that work.
- Rounding happens once, in one place per endpoint, with the same rule; the oracle tests of M2.12 check both endpoints on the same chains.
- Ownership chains that reach 8 hops on a dense register can time out; the 503 answer tells the caller how to narrow the request. Latencies on `uk-sample` are measured in M2.13.

## Sources

- `docs/build/PHASE-2.md` 3.3, 5.1, 5.3, 7.2 (rule 6 and the ownership row) and M2.12 (the fixture table).
- `contracts/C3-api.md`, "Ownership and paths (1.1.0)".
- [ofac_50_percent_2014]
