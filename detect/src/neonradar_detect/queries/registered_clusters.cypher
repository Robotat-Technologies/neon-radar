// registered_clusters: addresses with at least $min_members organisations whose HAS_ADDRESS role is
// registered (with $active_only, only organisations without a dissolution date and not in an inactive status),
// by address id; members by organisation id. Parameters: $min_members, $active_only, $limit.
MATCH (o:Organization)-[h:HAS_ADDRESS]->(addr:Address)
WHERE h.role = 'registered' AND (NOT $active_only OR (coalesce(o.dissolution_date, '') = ''
                       AND NOT toLower(coalesce(o.status, '')) IN ['dissolved', 'converted-closed', 'removed', 'closed']))
WITH addr, o, h ORDER BY o.id
WITH addr, collect([o.id, h.id]) AS members
WHERE size(members) >= $min_members
RETURN addr.id AS address, coalesce(addr.full, '') AS full, coalesce(addr.postal_code, '') AS postal_code, members
ORDER BY address
LIMIT $limit
