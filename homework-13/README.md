# ДЗ-13: Патерни, тренди та кластеризація (Elliptic++)

Бриф: [ДЗ-13 на osinter.dev](https://osinter.dev/02-%D0%B4%D0%BE%D0%BC%D0%B0%D1%88%D0%BD%D1%96-%D0%B7%D0%B0%D0%B2%D0%B4%D0%B0%D0%BD%D0%BD%D1%8F/%D0%B4%D0%B7-13-%D0%BF%D0%B0%D1%82%D0%B5%D1%80%D0%BD%D0%B8-%D1%82%D0%B0-%D0%BA%D0%BB%D0%B0%D1%81%D1%82%D0%B5%D1%80%D0%B8%D0%B7%D0%B0%D1%86%D1%96%D1%8F). Скрипти заняття — [`лекція_13_матеріали/`](лекція_13_матеріали/README.md) (prep.py, 01–04 *.cypher, gephi_demo, презентація).

## Що здати

`Gryn_Oleksii_ДЗ13.zip` = вміст `deliver/`:

| Файл | Що це |
|---|---|
| `report.pdf` | завдання 1–3, Gephi, висновок про лід (джерело — `report.html`) |
| `queries.cypher` | усі запити з порогами й номером спільноти 476429 |
| `community.png` / `.svg` / `.gephi` | завдання 4 |
| `import.png` | знімок Neo4j Browser з підрахунками |

## Ключові результати

| Перевірка | Самоперевірка курсу | Мій запуск |
|---|---|---|
| Підрахунки вузлів/ребер | 203 769 / 822 942 / 234 355 / 477 117 / 837 124 / 2 775 637 | збігаються |
| Частка illicit 1–42 → 43–49 | 10,97 % → 2,53 % | 10,97 % → 2,53 % |
| Fan-in p99 / p99.9 / max | 46 / 103 / 11 213 | 46 / 103 / 11 213 |
| Peel chain, поріг 0,1 | 366 | 366 (0,05 → 357) |
| Найбільша експозиція | 1 061 | 1 061 |
| Louvain: спільнот / Q | ≈ 410–450 / ≈ 0,93 | 385 / 0,928 |
| Макс. частка illicit у спільноті ≥ 20 | 28,2 %, lift 16,3 | 42,3 %, lift 24,4 (спільнота 476429, 78 гаманців) |

**Лід:** `1PMBzVZqD7uqsDr8LQKXFyXb7eggRUUfP9`. Сигнал А: єдиний відправник `1FHFZAyf…` — illicit-хаб, у який зайшли 29 гаманців, усі illicit. Сигнал Б (без міток): лід отримав увесь вихід sweep-транзакції 29 → 1 (14,989 BTC). Серед таких отримувачів illicit 12,9 %, lift ≈ 7,5. Упевненість помірна.

## Відтворення

1. `_downloads/` (не в git): 8 CSV Elliptic++ (Google Drive авторів, через `gdown`), Neo4j Community 2026.10.1 zip, `gephi-toolkit-0.11.4-all.jar`.
2. Neo4j: GDS і APOC скопійовано з `products/` і `labs/` у `plugins/`; у `conf/neo4j.conf` додано `dbms.security.procedures.unrestricted=gds.*,apoc.*`, heap 6g, pagecache 3g; `conf/apoc.conf`: `apoc.export.file.enabled=true`. Пароль — у `.env` (не в git).
3. `python лекція_13_матеріали/prep.py _downloads/elliptic _downloads/neo4j-community-2026.10.1/import` (≈ 20 с), далі `cypher-shell -f 01_import.cypher` (≈ 2,5 хв) і `03_gds.cypher` (≈ 35 с).
4. Запити — `deliver/queries.cypher`; виводи — `results/*.csv`. Хелпер: `source .env; source tools/q.sh`.
5. Графік тренду: `python tools/plot_trend.py results/t1_trend.csv deliver/trend.png`.
6. Gephi без GUI: `java --add-opens java.base/java.net=ALL-UNNAMED -cp _downloads/gephi-toolkit-0.11.4-all.jar tools/GephiCommunity.java results/gephi_nodes.csv results/gephi_edges.csv deliver`. Робить ті самі кроки, що й GUI: ForceAtlas2 з Approximate Repulsion і Prevent Overlap, Partition за class, Ranking за pagerank, PNG/SVG, `.gephi`. Розкладка FA2 багатопотокова, тому від запуску до запуску трохи різниться.
7. PDF: `chrome --headless=new --no-pdf-header-footer --user-data-dir=<тимчасова_тека> --print-to-pdf=deliver/report.pdf deliver/report.html` (без окремого `--user-data-dir` при відкритому Chrome PDF мовчки не створюється).

Запуск Neo4j знову: `_downloads/neo4j-community-2026.10.1/bin/neo4j.bat console` → http://localhost:7474.
