// ДЗ-13 · Патерни, тренди та кластеризація · Elliptic++ у Neo4j Community 2026.10.1 (GDS 2026.10.1, APOC 2026.10.1)
// Підготовка: prep.py → 01_import.cypher без змін. Кластеризація: 03_gds.cypher без змін (запуск 2026-11-13).
// Номер спільноти Louvain 476429 дійсний лише для цього запуску.

// ───────────── Підготовка: перевірка підрахунків ─────────────
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n;              // Transaction 203769, Wallet 822942
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n;             // FLOWS_TO 234355, INPUT 477117, OUTPUT 837124, SENT_TO 2775637

// ───────────── Завдання 1. Тренд ─────────────
// 1.1 частка illicit серед розмічених за кроками
MATCH (t:Transaction) WHERE t.class IN [1, 2]
WITH t.timeStep AS step,
     count(CASE WHEN t.class = 1 THEN 1 END) AS illicit,
     count(*) AS labelled
RETURN step, illicit, labelled,
       round(100.0 * illicit / labelled, 1) AS illicitPct
ORDER BY step;

// 1.2 частка за періодами — через суми, не середнє відсотків → 10.97 % / 2.53 %
MATCH (t:Transaction) WHERE t.class IN [1, 2]
WITH CASE WHEN t.timeStep < 43 THEN '1-42' ELSE '43-49' END AS period, t
RETURN period, count(CASE WHEN t.class = 1 THEN 1 END) AS illicit, count(*) AS labelled,
       round(100.0 * count(CASE WHEN t.class = 1 THEN 1 END) / count(*), 2) AS illicitPct
ORDER BY period;

// ───────────── Завдання 2. Патерни ─────────────
// 2.1 Fan-in: поріг через перцентиль → p99 = 46, p99.9 = 103, max = 11213
MATCH (w:Wallet)
WITH COUNT { (w)<-[:SENT_TO]-() } AS senders
RETURN percentileDisc(senders, 0.99) AS p99,
       percentileDisc(senders, 0.999) AS p999,
       max(senders) AS max;

// класи гаманців вище порогу p99.9 → illicit 22, licit 453, unknown 358
MATCH (w:Wallet)
WITH w, COUNT { (w)<-[:SENT_TO]-() } AS senders
WHERE senders >= 103   // поріг = p99.9
RETURN w.class AS class, count(*) AS wallets
ORDER BY class;

// базові частки класів серед усіх гаманців → illicit 1.73 %, licit 30.51 %, unknown 67.76 %
MATCH (w:Wallet) RETURN w.class AS class, count(*) AS wallets, round(100.0 * count(*) / 822942, 2) AS pct ORDER BY class;

// 2.2 Peel chain: illicit-старти ланцюжка з 5 переходів → 366 (0.1), 357 (0.05), 189 (0.01)
MATCH p = (s:Transaction {class: 1})-[:FLOWS_TO*5]->(:Transaction)
WHERE all(t IN nodes(p) WHERE t.nOut = 2 AND t.outMin < 0.1 * t.outMax)
RETURN count(DISTINCT s) AS starts;

MATCH p = (s:Transaction {class: 1})-[:FLOWS_TO*5]->(:Transaction)
WHERE all(t IN nodes(p) WHERE t.nOut = 2 AND t.outMin < 0.05 * t.outMax)
RETURN count(DISTINCT s) AS starts;

// додатково: «відщеп» < 1 % більшого виходу
MATCH p = (s:Transaction {class: 1})-[:FLOWS_TO*5]->(:Transaction)
WHERE all(t IN nodes(p) WHERE t.nOut = 2 AND t.outMin < 0.01 * t.outMax)
RETURN count(DISTINCT s) AS starts;

// 2.3 Експозиція: топ-3 unknown → 18sJPXgo… 1061, 1781T3nn… 1061, 3BBio7im… 319
MATCH (i:Wallet {class: 1})-[:SENT_TO*1..2]->(u:Wallet {class: 3})
WITH u, count(DISTINCT i) AS exposure
RETURN u.address AS address, exposure
ORDER BY exposure DESC LIMIT 3;

// прямі відправники першої адреси → один: 1FvtWwP3ePJDeR6K7ZePGujUuusUTds8Vy (illicit)
MATCH (x:Wallet)-[:SENT_TO]->(:Wallet {address: '18sJPXgoWoL3Z1pcM22QvWwyyFVhwxrXE9'}) RETURN x.address, x.class;

// для всіх трьох: хто прямий відправник і скільки illicit-гаманців стоїть за ним
UNWIND ['18sJPXgoWoL3Z1pcM22QvWwyyFVhwxrXE9','1781T3nnX2ncqTHYbRcac1R58VR1mFvmqt','3BBio7imFnNJ2cJEMoArJ1QcBzS4NmvAfr'] AS a
MATCH (x:Wallet)-[r:SENT_TO]->(u:Wallet {address: a})
RETURN a AS target, x.address AS sender, x.class AS senderClass, r.n AS n,
       COUNT { (:Wallet {class: 1})-[:SENT_TO]->(x) } AS illicitFeedingSender
ORDER BY target, illicitFeedingSender DESC;

// ───────────── Завдання 3. Спільноти ─────────────
// (спершу весь 03_gds.cypher: Louvain 385 спільнот, Q = 0.928; Leiden 435, Q = 0.926; WCC 2 компоненти)
// 3.1 топ-5 спільнот Louvain за часткою illicit з lift
MATCH (w:Wallet)
WITH count(*) AS total, count(CASE WHEN w.class = 1 THEN 1 END) AS totalIllicit
MATCH (w:Wallet)
WITH 1.0 * totalIllicit / total AS base, w.louvain AS community, count(*) AS size,
     count(CASE WHEN w.class = 1 THEN 1 END) AS illicit,
     count(CASE WHEN w.class = 2 THEN 1 END) AS licit
WHERE size >= 20
RETURN community, size, illicit, licit,
       round(100.0 * illicit / size, 1) AS illicitPct,
       round(illicit / (size * base), 1) AS lift
ORDER BY illicitPct DESC LIMIT 5;

// 3.2 кандидати в ліди у спільноті з першого рядка
MATCH (u:Wallet {louvain: 476429, class: 3})
RETURN u.address AS lead, round(u.pagerank, 2) AS pagerank, u.inDeg AS senders,
       COUNT { (u)-[:SENT_TO]->() } AS receivers, u.firstStep AS firstStep, u.lastStep AS lastStep
ORDER BY pagerank DESC LIMIT 3;

// склад спільноти 476429 → illicit 33, unknown 45, licit 0; усі активні лише на кроці 15
MATCH (w:Wallet {louvain: 476429})
RETURN w.class AS class, count(*) AS n, min(w.firstStep) AS minStep, max(w.lastStep) AS maxStep, round(max(w.pagerank), 2) AS maxPR
ORDER BY class;

// ───────────── Завдання 4. Експорт спільноти для Gephi (блок B з 04_export.cypher) ─────────────
CALL apoc.export.csv.query(
  'MATCH (w:Wallet) WHERE w.louvain = 476429
   RETURN w.address AS Id, w.class AS class, w.louvain AS community,
          w.pagerank AS pagerank, w.firstStep AS firstStep, w.lastStep AS lastStep',
  'gephi_nodes.csv', {});
CALL apoc.export.csv.query(
  'MATCH (a:Wallet)-[r:SENT_TO]->(b:Wallet) WHERE a.louvain = 476429 AND b.louvain = 476429
   RETURN a.address AS Source, b.address AS Target, r.n AS Weight',
  'gephi_edges.csv', {});

// ───────────── Завдання 5. Перевірка ліда 1PMBzVZqD7uqsDr8LQKXFyXb7eggRUUfP9 ─────────────
// 5.1 хто надсилав ліду → один відправник 1FHFZAyfsGkexc9FK7vigwU2rf5FXvqrLE (illicit, та сама спільнота)
MATCH (s:Wallet)-[r:SENT_TO]->(u:Wallet {address: '1PMBzVZqD7uqsDr8LQKXFyXb7eggRUUfP9'})
RETURN s.address AS sender, s.class AS cls, s.louvain = u.louvain AS sameComm, round(s.pagerank, 2) AS pr,
       COUNT { (s)<-[:SENT_TO]-() } AS sIn, COUNT { (s)-[:SENT_TO]->() } AS sOut, r.n AS n;

// 5.2 хто надсилав відправнику → 29 гаманців, усі illicit, крок 15
MATCH (h:Wallet {address: '1FHFZAyfsGkexc9FK7vigwU2rf5FXvqrLE'})
MATCH (s:Wallet)-[:SENT_TO]->(h)
RETURN s.class AS senderClass, s.louvain = h.louvain AS sameComm, count(*) AS n, min(s.firstStep) AS fs, max(s.lastStep) AS ls;

// 5.3 транзакція, якою лід отримав кошти → tx 246979279: 29 вхідних потоків, 1 вихід 14.989 BTC, клас tx unknown, далі не витрачається
MATCH (t:Transaction)-[:OUTPUT]->(u:Wallet {address: '1PMBzVZqD7uqsDr8LQKXFyXb7eggRUUfP9'})
OPTIONAL MATCH (i:Wallet)-[:INPUT]->(t)
WITH t, collect(DISTINCT i.class) AS inClasses, count(DISTINCT i) AS nInW
RETURN t.txId, t.class, t.timeStep, t.nIn, t.nOut, t.totalBTC, t.outMin, t.outMax, nInW, inClasses,
       COUNT { ()-[:FLOWS_TO]->(t) } AS txIn, COUNT { (t)-[:FLOWS_TO]->() } AS txOut;

// 5.4 сигнал Б без міток: наскільки форма «sweep» (1 вихід, >= 20 вхідних потоків) сама по собі пов'язана з illicit
//     → 171 гаманець, illicit 22 (12.9 %, lift ≈ 7.5 до 1.73 %); серед розмічених 26.5 % проти 5.38 %
MATCH (t:Transaction)-[:OUTPUT]->(w:Wallet)
WHERE t.nOut = 1 AND COUNT { ()-[:FLOWS_TO]->(t) } >= 20
WITH DISTINCT w
RETURN count(*) AS wallets,
       count(CASE WHEN w.class = 1 THEN 1 END) AS illicit,
       count(CASE WHEN w.class = 2 THEN 1 END) AS licit,
       round(100.0 * count(CASE WHEN w.class = 1 THEN 1 END) / count(*), 1) AS illicitPct,
       round(100.0 * count(CASE WHEN w.class = 1 THEN 1 END) / count(CASE WHEN w.class IN [1, 2] THEN 1 END), 1) AS illicitPctOfLabelled;

MATCH (w:Wallet) WHERE w.class IN [1, 2]
RETURN round(100.0 * count(CASE WHEN w.class = 1 THEN 1 END) / count(*), 2) AS illicitPctOfLabelled;

// 5.5 застереження: чи бувають unknown-гаманці учасниками illicit-транзакцій? → ніколи (4545 з 4545 без unknown)
//     мітка гаманця виведена з міток транзакцій, тож «unknown» = «не торкався розміченої illicit-транзакції», а не «чистий»
MATCH (t:Transaction {class: 1})
OPTIONAL MATCH (t)-[:OUTPUT]->(o:Wallet)
WITH t, collect(DISTINCT o.class) AS outCls
OPTIONAL MATCH (i:Wallet)-[:INPUT]->(t)
WITH t, outCls, collect(DISTINCT i.class) AS inCls
RETURN 3 IN outCls AS unknownOut, 3 IN inCls AS unknownIn, count(*) AS txs;
