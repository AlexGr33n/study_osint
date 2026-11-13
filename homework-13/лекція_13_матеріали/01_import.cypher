// 01_import.cypher — схема та імпорт Elliptic++ (файли лежать у папці import)
CREATE CONSTRAINT tx_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.txId IS UNIQUE;
CREATE CONSTRAINT wallet_addr IF NOT EXISTS FOR (w:Wallet) REQUIRE w.address IS UNIQUE;
CREATE INDEX tx_step IF NOT EXISTS FOR (t:Transaction) ON (t.timeStep);
CREATE INDEX tx_class IF NOT EXISTS FOR (t:Transaction) ON (t.class);
CREATE INDEX w_class IF NOT EXISTS FOR (w:Wallet) ON (w.class);

// Вузли: транзакції
LOAD CSV WITH HEADERS FROM 'file:///tx_nodes.csv' AS row
CALL (row) {
  CREATE (:Transaction {
    txId: toInteger(row.txId), timeStep: toInteger(row.timeStep), class: toInteger(row.class),
    nIn: toInteger(row.num_input_addresses), nOut: toInteger(row.num_output_addresses),
    totalBTC: toFloat(row.total_BTC), fees: toFloat(row.fees),
    outMin: toFloat(row.out_BTC_min), outMax: toFloat(row.out_BTC_max)})
} IN TRANSACTIONS OF 10000 ROWS;

// Вузли: гаманці
LOAD CSV WITH HEADERS FROM 'file:///wallet_nodes.csv' AS row
CALL (row) {
  CREATE (:Wallet {address: row.address, class: toInteger(row.class),
                   firstStep: toInteger(row.firstStep), lastStep: toInteger(row.lastStep)})
} IN TRANSACTIONS OF 20000 ROWS;

// Ребра: потік коштів між транзакціями
LOAD CSV WITH HEADERS FROM 'file:///txs_edgelist.csv' AS row
CALL (row) {
  MATCH (a:Transaction {txId: toInteger(row.txId1)})
  MATCH (b:Transaction {txId: toInteger(row.txId2)})
  CREATE (a)-[:FLOWS_TO]->(b)
} IN TRANSACTIONS OF 20000 ROWS;

// Ребра: гаманець -> транзакція (вхід)
LOAD CSV WITH HEADERS FROM 'file:///AddrTx_edgelist.csv' AS row
CALL (row) {
  MATCH (w:Wallet {address: row.input_address})
  MATCH (t:Transaction {txId: toInteger(row.txId)})
  CREATE (w)-[:INPUT]->(t)
} IN TRANSACTIONS OF 20000 ROWS;

// Ребра: транзакція -> гаманець (вихід)
LOAD CSV WITH HEADERS FROM 'file:///TxAddr_edgelist.csv' AS row
CALL (row) {
  MATCH (t:Transaction {txId: toInteger(row.txId)})
  MATCH (w:Wallet {address: row.output_address})
  CREATE (t)-[:OUTPUT]->(w)
} IN TRANSACTIONS OF 20000 ROWS;

// Ребра: гаманець -> гаманець з вагою n (скільки разів пара зустрілась)
LOAD CSV WITH HEADERS FROM 'file:///sent_to.csv' AS row
CALL (row) {
  MATCH (a:Wallet {address: row.input_address})
  MATCH (b:Wallet {address: row.output_address})
  CREATE (a)-[:SENT_TO {n: toInteger(row.n)}]->(b)
} IN TRANSACTIONS OF 20000 ROWS;

// Перевірка
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n;
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n;
