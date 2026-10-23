// L18: before an overlay load, remove the previous overlay (every node whose id starts with
// syn-ov-, with its relationships, including the HOLDS_ACCOUNT links from base organisations) and
// every detection result, which an overlay change makes stale
MATCH (n:Entity) WHERE n.id STARTS WITH 'syn-ov-'
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n:Sanction) WHERE n.id STARTS WITH 'syn-ov-'
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n) WHERE n:Alert OR n:DetectionRun
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
