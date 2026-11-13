# Графік частки illicit серед розмічених транзакцій за кроками часу (завдання 1)
import csv, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src, out = sys.argv[1], sys.argv[2]
rows = [r for r in csv.DictReader(open(src, encoding="utf-8"), skipinitialspace=True)]
step = [int(r["step"]) for r in rows]
pct = [float(r["illicitPct"]) for r in rows]
lab = [int(r["labelled"]) for r in rows]
ill = [int(r["illicit"]) for r in rows]
assert len(step) == 49 and sum(lab) == 46564, "очікується 49 кроків і 46 564 розмічених транзакції"

def share(a, b):
    return 100 * sum(ill[a:b]) / sum(lab[a:b])

fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150)
ax.bar(step, lab, color="#d9d9d9", width=0.8, label="розмічених транзакцій (права вісь)", zorder=1)
ax.set_ylabel("розмічених транзакцій")
ax2 = ax.twinx()
ax2.plot(step, pct, color="#d7261e", marker="o", ms=3, lw=1.6, label="частка illicit, %", zorder=3)
ax2.hlines(share(0, 42), 1, 42, colors="#d7261e", linestyles=":", lw=1)
ax2.hlines(share(42, 49), 43, 49, colors="#d7261e", linestyles=":", lw=1)
ax2.text(20, share(0, 42) + 1, f"кроки 1–42: {share(0, 42):.2f} %", color="#d7261e", fontsize=9)
ax2.text(43.2, share(42, 49) + 1.2, f"43–49: {share(42, 49):.2f} %", color="#d7261e", fontsize=9)
ax2.axvline(43, color="black", ls="--", lw=1.2)
ax2.text(43.3, max(pct) * 0.95, "крок 43", fontsize=9)
ax2.set_ylabel("illicit, % від розмічених")
ax.yaxis.tick_right(); ax.yaxis.set_label_position("right")
ax2.yaxis.tick_left(); ax2.yaxis.set_label_position("left")
ax.set_xlabel("крок часу (≈ 2 тижні)")
ax.set_xlim(0.3, 49.7)
ax.set_title("Elliptic++: частка illicit серед розмічених транзакцій за 49 кроками")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax2.legend(h2 + h1, l2 + l1, loc="upper left", fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(out)
print("saved", out)
