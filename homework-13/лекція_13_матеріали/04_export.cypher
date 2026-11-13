// 04_export.cypher — вивантаження підграфів для Gephi (потрібно apoc.export.file.enabled=true)

// A. Его-мережа (2 кроки) навколо illicit-гаманця -> GraphML
//    Підставте адресу з результатів P5/P6 або топ-PageRank серед illicit
CALL apoc.export.graphml.query(
  'MATCH p = (:Wallet {address: "ADDRESS"})-[:SENT_TO*1..2]-(:Wallet) RETURN p LIMIT 2000',
  'ego_illicit.graphml', {useTypes: true});

// B. Одна спільнота Louvain -> два CSV для «Import Spreadsheet» у Gephi
CALL apoc.export.csv.query(
  'MATCH (w:Wallet) WHERE w.louvain = 123
   RETURN w.address AS Id, w.class AS class, w.louvain AS community,
          w.pagerank AS pagerank, w.firstStep AS firstStep, w.lastStep AS lastStep',
  'gephi_nodes.csv', {});
CALL apoc.export.csv.query(
  'MATCH (a:Wallet)-[r:SENT_TO]->(b:Wallet) WHERE a.louvain = 123 AND b.louvain = 123
   RETURN a.address AS Source, b.address AS Target, r.n AS Weight',
  'gephi_edges.csv', {});

// C. Увесь граф транзакцій з часом (для Timeline у Gephi)
CALL apoc.export.csv.query(
  'MATCH (t:Transaction)
   RETURN t.txId AS Id, t.class AS class, t.timeStep AS start, t.timeStep + 1 AS end',
  'tx_nodes_time.csv', {});
CALL apoc.export.csv.query(
  'MATCH (a:Transaction)-[:FLOWS_TO]->(b:Transaction) RETURN a.txId AS Source, b.txId AS Target',
  'tx_edges.csv', {});
