// hubs: nodes with {{rel_type}} relationships to at least $min_members distinct organisations, by node id,
// each with those relationships by id. {{rel_type}} comes from a fixed list. Parameters: $min_members, $limit.
// lint-values: rel_type=REPRESENTS,DIRECTOR_OF
MATCH (s:Entity)-[r:{{rel_type}}]->(o:Organization)
WITH s, count(DISTINCT o) AS members
WHERE members >= $min_members
WITH s ORDER BY s.id LIMIT $limit
RETURN s.id AS hub,
       COLLECT { MATCH (s)-[r:{{rel_type}}]->(t:Organization)
                 RETURN {rel_type: type(r), rel_id: r.id, source: s.id, target: t.id, share_min: null, share_max: null,
                         share_min_exclusive: false, share_max_exclusive: false,
                         is_nominee: coalesce(r.is_nominee, false), role: coalesce(r.role, ''),
                         start_date: coalesce(r.start_date, ''), end_date: coalesce(r.end_date, ''), control_type: ''}
                 ORDER BY r.id } AS links
ORDER BY hub
