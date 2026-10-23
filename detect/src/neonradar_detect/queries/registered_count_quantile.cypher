// registered_count_quantile: the nearest-rank $q quantile of the number of registered organisations per
// address, over addresses with at least one: the value at position max(1, ceil($q * n)) in ascending order;
// 0 when no address has one. Parameters: $q, $active_only.
MATCH (o:Organization)-[h:HAS_ADDRESS]->(addr:Address)
WHERE h.role = 'registered' AND (NOT $active_only OR (coalesce(o.dissolution_date, '') = ''
                       AND NOT toLower(coalesce(o.status, '')) IN ['dissolved', 'converted-closed', 'removed', 'closed']))
WITH addr, count(DISTINCT o) AS members
WITH members ORDER BY members
WITH collect(members) AS counts
RETURN CASE WHEN size(counts) = 0 THEN 0
            ELSE counts[CASE WHEN ceil($q * size(counts)) < 1 THEN 0 ELSE toInteger(ceil($q * size(counts))) - 1 END]
       END AS value
