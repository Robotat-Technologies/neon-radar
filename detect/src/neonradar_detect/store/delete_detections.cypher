// delete_detections: C2 1.2.0 L19. Detections are a function of the graph, so a detection load
// first removes every :Alert and :DetectionRun with their PRODUCED and FLAGS relationships
// (`neonradar detect run --keep-previous` skips this statement). No parameters.
MATCH (n)
WHERE n:Alert OR n:DetectionRun
DETACH DELETE n
