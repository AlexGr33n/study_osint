# Заняття 13 — матеріали до практики (Neo4j + Gephi, Elliptic++)

Перевірено на повному Elliptic++: Neo4j Community 2026.10.1 (Cypher 25 за замовчуванням),
Graph Data Science 2026.10.1, APOC 2026.10.1; 2 CPU, 7 ГБ RAM, heap 2 ГБ, page cache 1 ГБ.

## Порядок

1. Завантажте Elliptic++: https://github.com/git-disl/EllipticPlusPlus (посилання на Google Drive у README репозиторію).
2. Підготуйте компактні CSV:
   `python prep.py <папка_з_csv_elliptic> <папка_import_neo4j>`
   (txs_features.csv 695 МБ → tx_nodes.csv 14 МБ; петлі в AddrAddr прибираються, дублікати пар зливаються у вагу n)
3. Neo4j:
   - Desktop: база → Plugins → APOC, Graph Data Science → Install.
   - Tarball Community 2026.10.1: GDS лежить у `products/`, APOC — у `labs/`; скопіюйте jar-файли в `plugins/`,
     додайте `dbms.security.procedures.unrestricted=gds.*,apoc.*` і створіть `conf/apoc.conf` з `apoc.export.file.enabled=true`.
   - Docker: команда на слайді «Neo4j: встановлення».
4. Виконайте по черзі:
   - `01_import.cypher` — обмеження, вузли, ребра, перевірка підрахунків (≈ 4 хв)
   - `02_patterns.cypher` — тренд, fan-in, fan-out, peel chain, цикли, експозиція, найкоротший шлях
   - `03_gds.cypher` — WCC, Louvain, Leiden, PageRank, «чистота» спільнот, ліди, FastRP + k-means
   - `04_export.cypher` — вивантаження підграфів для Gephi (підставте адресу і номер спільноти)
5. У Neo4j Browser запити з `CALL … IN TRANSACTIONS` запускайте з префіксом `:auto`.

## Очікувані результати

| Перевірка | Значення |
|---|---|
| Transaction / Wallet | 203 769 / 822 942 |
| FLOWS_TO / INPUT / OUTPUT / SENT_TO | 234 355 / 477 117 / 837 124 / 2 775 637 |
| WCC (гаманці) | 2 компоненти: 822 935 + 7 |
| Louvain / Leiden | 450 спільнот, Q = 0,927 / 428 спільнот, Q = 0,925 |
| Найвища частка illicit у спільноті | 28,2% (базова — 1,7%) |

Номери спільнот Louvain залежать від запуску — орієнтуйтеся на розміри й частки, а не на id.

## Gephi

- `gephi_nodes.csv` / `gephi_edges.csv` → File → Import spreadsheet (спершу вузли, потім ребра, Append to existing workspace).
- `ego_illicit.graphml` → File → Open.
- `tx_nodes_time.csv` + `tx_edges.csv` → Data Laboratory → Merge Columns → Create time interval (start, end, Parse numbers) → Timeline.

### Готові файли в папці gephi_demo (для показу без Neo4j)

Вивантажено скриптом `04_export.cypher` з Elliptic++ (Elmougy & Liu, KDD 2023):

| Файл | Що всередині |
|---|---|
| `gephi_nodes.csv`, `gephi_edges.csv` | Спільнота Louvain з найвищою часткою illicit: 3 985 гаманців (1 123 illicit, 480 licit, 2 382 unknown), 7 013 ребер |
| `ego_illicit.graphml` | Его-мережа (2 кроки, LIMIT 2000 шляхів) illicit-гаманця з найвищим PageRank: 1 319 вузлів, 2 000 ребер |
| `tx_nodes_time.csv`, `tx_edges.csv` | Увесь граф транзакцій з інтервалами часу: 203 769 вузлів, 234 355 ребер |
