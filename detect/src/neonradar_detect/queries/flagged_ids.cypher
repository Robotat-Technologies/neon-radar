// flagged_ids: ids of the :Entity nodes with one flag label, sorted. {{flag}} comes from a fixed list.
// lint-values: flag=Sanctioned,PEP,RCA
MATCH (n:Entity:{{flag}})
RETURN n.id AS id
ORDER BY id
