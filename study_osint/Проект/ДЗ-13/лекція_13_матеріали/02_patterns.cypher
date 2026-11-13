// 02_patterns.cypher — патерни та тренди на Cypher

// P0. Тренд: скільки транзакцій кожного класу на кожному кроці часу
MATCH (t:Transaction)
RETURN t.timeStep AS step, count(*) AS total,
       count(CASE WHEN t.class = 1 THEN 1 END) AS illicit,
       count(CASE WHEN t.class = 2 THEN 1 END) AS licit
ORDER BY step;

// P1. Fan-in (консолідація): гаманці, що отримують від багатьох відправників
MATCH (s:Wallet)-[:SENT_TO]->(w:Wallet)
WITH w, count(s) AS senders
WHERE senders >= 100
RETURN w.address AS address, w.class AS class, senders
ORDER BY senders DESC LIMIT 10;

// P2. Fan-out (розпилення): гаманці, що платять багатьом отримувачам
MATCH (w:Wallet)-[:SENT_TO]->(r:Wallet)
WITH w, count(r) AS receivers
WHERE receivers >= 100
RETURN w.address AS address, w.class AS class, receivers
ORDER BY receivers DESC LIMIT 10;

// P3. Peel chain: >=5 послідовних транзакцій з 2 виходами, «відщеп» < 10% від більшого виходу
MATCH p = (s:Transaction {class: 1})-[:FLOWS_TO*5..8]->(:Transaction)
WHERE all(t IN nodes(p) WHERE t.nOut = 2 AND t.outMin < 0.1 * t.outMax)
RETURN length(p) AS hops, [t IN nodes(p) | t.txId] AS chain
LIMIT 5;

// P4. Цикли (round-trip): кошти повертаються до illicit-гаманця за 2–4 кроки
MATCH p = (w:Wallet {class: 1})-[:SENT_TO*2..4]->(w)
RETURN length(p) AS hops, [x IN nodes(p) | x.address] AS cycle
LIMIT 5;

// P5. Куди йдуть кошти від illicit: отримувачі з найбільшою кількістю illicit-відправників
MATCH (i:Wallet {class: 1})-[:SENT_TO]->(r:Wallet)
WHERE r.class <> 1
RETURN r.address AS address, r.class AS class, count(i) AS illicitSenders
ORDER BY illicitSenders DESC LIMIT 10;

// P6. Експозиція: невідомі гаманці, до яких за 1–2 кроки доходять кошти від >=5 illicit-гаманців
MATCH (i:Wallet {class: 1})-[:SENT_TO*1..2]->(u:Wallet {class: 3})
WITH u, count(DISTINCT i) AS exposure
WHERE exposure >= 5
RETURN u.address AS address, exposure
ORDER BY exposure DESC LIMIT 10;

// P7. Найкоротший шлях між двома гаманцями (підставте адреси)
MATCH (a:Wallet {address: $from})
MATCH (b:Wallet {address: $to})
MATCH p = shortestPath((a)-[:SENT_TO*..8]->(b))
RETURN [x IN nodes(p) | x.address] AS path, length(p) AS hops;
