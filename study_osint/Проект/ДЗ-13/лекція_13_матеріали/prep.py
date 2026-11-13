# prep.py — компактні CSV для імпорту Elliptic++ у Neo4j
# Запуск: python prep.py <папка_з_оригінальними_csv> <папка_import_neo4j>
import sys
import pandas as pd

SRC = sys.argv[1].rstrip('/') + '/'
OUT = sys.argv[2].rstrip('/') + '/'

# 1) Транзакції: id, крок часу, клас + кілька зрозумілих ознак
cols = ['txId', 'Time step', 'in_txs_degree', 'out_txs_degree', 'total_BTC', 'fees',
        'num_input_addresses', 'num_output_addresses', 'out_BTC_min', 'out_BTC_max']
tx = pd.read_csv(SRC + 'txs_features.csv', usecols=cols)
tx = tx.merge(pd.read_csv(SRC + 'txs_classes.csv'), on='txId')
tx = tx.rename(columns={'Time step': 'timeStep'})
tx.to_csv(OUT + 'tx_nodes.csv', index=False)

# 2) Гаманці: адреса, клас, перший/останній крок часу
w = pd.read_csv(SRC + 'wallets_features.csv', usecols=['address', 'Time step'])
w = w.groupby('address')['Time step'].agg(firstStep='min', lastStep='max').reset_index()
w = pd.read_csv(SRC + 'wallets_classes.csv').merge(w, on='address', how='left')
w.to_csv(OUT + 'wallet_nodes.csv', index=False)

# 3) Адреса -> адреса: прибрати self-loops (решта собі), злити дублікати у вагу n
aa = pd.read_csv(SRC + 'AddrAddr_edgelist.csv')
aa = aa[aa.input_address != aa.output_address]
aa = aa.groupby(['input_address', 'output_address']).size().reset_index(name='n')
aa.to_csv(OUT + 'sent_to.csv', index=False)

# 4) tx->tx, addr->tx, tx->addr — без змін
for f in ['txs_edgelist.csv', 'AddrTx_edgelist.csv', 'TxAddr_edgelist.csv']:
    pd.read_csv(SRC + f).to_csv(OUT + f, index=False)

print(len(tx), 'tx |', len(w), 'wallets |', len(aa), 'SENT_TO')
