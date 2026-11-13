// 03_gds.cypher — кластеризація та центральність з Graph Data Science

RETURN gds.version() AS gds;

// 1. Проєкція в пам'ять: неорієнтований граф гаманців, вага n
CALL gds.graph.project('wallets', 'Wallet',
  {SENT_TO: {orientation: 'UNDIRECTED', properties: 'n'}})
YIELD nodeCount, relationshipCount;

// 2. Компоненти зв'язності (базова «кластеризація»)
CALL gds.wcc.write('wallets', {writeProperty: 'wcc'})
YIELD componentCount, componentDistribution
RETURN componentCount, componentDistribution.max AS largest, componentDistribution.p50 AS median;

// 3. Louvain — спільноти за модулярністю
CALL gds.louvain.write('wallets', {writeProperty: 'louvain', relationshipWeightProperty: 'n'})
YIELD communityCount, modularity, ranLevels;

// 4. Leiden — гарантує зв'язні спільноти
CALL gds.leiden.write('wallets', {writeProperty: 'leiden', relationshipWeightProperty: 'n', gamma: 1.0})
YIELD communityCount, modularity;

// 5. PageRank — на орієнтованій проєкції
CALL gds.graph.project('wallets_dir', 'Wallet', {SENT_TO: {properties: 'n'}})
YIELD nodeCount, relationshipCount;
CALL gds.pageRank.write('wallets_dir', {writeProperty: 'pagerank', maxIterations: 20})
YIELD nodePropertiesWritten, ranIterations;

// 6. Вхідний ступінь (скільки різних відправників)
CALL gds.degree.write('wallets_dir', {writeProperty: 'inDeg', orientation: 'REVERSE'})
YIELD nodePropertiesWritten;

CREATE INDEX w_louvain IF NOT EXISTS FOR (w:Wallet) ON (w.louvain);

// 7. «Чистота» спільнот: де концентруються illicit-гаманці
MATCH (w:Wallet)
WITH w.louvain AS community, count(*) AS size,
     count(CASE WHEN w.class = 1 THEN 1 END) AS illicit,
     count(CASE WHEN w.class = 2 THEN 1 END) AS licit
WHERE size >= 20 AND illicit > 0
RETURN community, size, illicit, licit, round(100.0 * illicit / size, 1) AS illicitPct
ORDER BY illicitPct DESC, size DESC LIMIT 15;

// 8. Ліди: невідомі гаманці в спільнотах, де частка illicit >= 10%
//    (базова частка illicit серед гаманців — 1,7%; максимум у спільноті Louvain — 28%)
MATCH (w:Wallet)
WITH w.louvain AS c, count(*) AS size, count(CASE WHEN w.class = 1 THEN 1 END) AS illicit
WHERE size >= 20 AND illicit >= 0.1 * size
MATCH (u:Wallet {class: 3}) WHERE u.louvain = c
RETURN c AS community, size, illicit, u.address AS lead, round(u.pagerank, 3) AS pr
ORDER BY pr DESC LIMIT 20;

// 9. (Опційно) Ембединги + k-means: кластери за «формою» сусідства
CALL gds.fastRP.mutate('wallets', {embeddingDimension: 64, mutateProperty: 'emb', randomSeed: 42})
YIELD nodePropertiesWritten;
CALL gds.kmeans.write('wallets', {nodeProperty: 'emb', k: 20, randomSeed: 42, writeProperty: 'kmeans'})
YIELD communityDistribution;

// Прибрати проєкції з пам'яті
CALL gds.graph.drop('wallets') YIELD graphName;
CALL gds.graph.drop('wallets_dir') YIELD graphName;
