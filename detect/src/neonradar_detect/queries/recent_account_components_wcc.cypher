// Ring variant, step 2: weakly connected components (concurrency 4; components are stable, ids are not, so
// the source names each component by its smallest account id).
CALL gds.wcc.stream($graph_name, {concurrency: 4})
YIELD nodeId, componentId
RETURN gds.util.asNode(nodeId).id AS account_id, componentId AS component_id
ORDER BY component_id, account_id
