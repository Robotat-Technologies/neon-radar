// entities: what detectors read about entities. Parameters: $ids. By id.
UNWIND $ids AS entity_id
MATCH (n:Entity {id: entity_id})
RETURN n.id AS id, labels(n) AS labels, coalesce(n.schema, '') AS schema, coalesce(n.jurisdiction, '') AS jurisdiction,
       coalesce(n.incorporation_date, '') AS incorporation_date, n.synthetic AS synthetic,
       coalesce(n.accounts_category, '') AS accounts_category, coalesce(n.sector, '') AS sector,
       coalesce(n.status, '') AS status, coalesce(n.dissolution_date, '') AS dissolution_date,
       coalesce(n.datasets, []) AS datasets, coalesce(n.psc_statements, []) AS psc_statements,
       coalesce(n.full, '') AS full, coalesce(n.postal_code, '') AS postal_code, coalesce(n.city, '') AS city,
       coalesce(n.countries, []) AS countries
ORDER BY id
