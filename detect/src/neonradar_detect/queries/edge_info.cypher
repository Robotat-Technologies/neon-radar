// edge_info: the evidence relationships with their ends and the properties the wording uses.
// Parameters: $ids. Relationship ids are unique per type (C2), so each type is sought by its own index.
UNWIND $ids AS rid
CALL (rid) {
    MATCH (s)-[r:PAID {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:OWNS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:CONTROLS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:CONSOLIDATES {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:DIRECTOR_OF {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:HOLDS_ACCOUNT {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:HAS_ADDRESS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:REPRESENTS {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:FAMILY_OF {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:ASSOCIATE_OF {id: rid}]->(t) RETURN r, s, t
    UNION
    MATCH (s)-[r:HOLDS_POSITION {id: rid}]->(t) RETURN r, s, t
}
RETURN r.id AS id, type(r) AS type, s.id AS source, t.id AS target, r.synthetic AS synthetic,
       r.amount AS amount, coalesce(r.currency, '') AS currency, r.ts AS ts, coalesce(r.channel, '') AS channel,
       r.share_pct_min AS share_min, r.share_pct_max AS share_max,
       coalesce(r.share_min_exclusive, false) AS share_min_exclusive,
       coalesce(r.share_max_exclusive, false) AS share_max_exclusive,
       coalesce(r.role, r.relationship, '') AS role, coalesce(r.control_type, '') AS control_type,
       coalesce(r.start_date, '') AS start_date, coalesce(r.end_date, '') AS end_date
ORDER BY id
