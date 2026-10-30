// Ring variant, step 3: drop the projection (always, also after a failure).
CALL gds.graph.drop($graph_name, false)
YIELD graphName
RETURN graphName
