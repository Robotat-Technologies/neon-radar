// paid_times: for each (payer account, payee account) pair, the times of every PAID between them, sorted;
// pairs with none are left out. Parameters: $pairs, a list of [payer, payee].
UNWIND $pairs AS pair
MATCH (a:Entity:Account {id: pair[0]})-[r:PAID]->(b:Entity:Account {id: pair[1]})
WITH a.id AS payer, b.id AS payee, r.ts AS ts
ORDER BY payer, payee, ts
RETURN payer, payee, collect(ts) AS times
ORDER BY payer, payee
