"""ДЗ-17: Статистика в OSINT — розрахунки для завдань 1–3 (+ бонус) і чисел для завдання 4.

Запуск:  python analysis.py [шлях_до_csv]   (за замовчуванням data/hw17_water_posts.csv)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8")

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data" / "hw17_water_posts.csv"
df = pd.read_csv(CSV, parse_dates=["date"]).set_index("date")
base = df.loc["2026-08-01":"2026-09-29"]
camp = df.loc["2026-09-30":"2026-10-29"]
assert len(df) == 90 and len(base) == 60 and len(camp) == 30, "неочікувана довжина ряду/періодів"
METRICS = ["posts", "channels", "young_channels", "avg_views", "forwards_share"]
pd.set_option("display.width", 140)


def h(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def d(ts):
    return ts.strftime("%d.%m")


# ---------------------------------------------------------------- Завдання 1
h("ЗАВДАННЯ 1. Базовий період (01.08–29.09), стовпець posts")
p = base["posts"]
q1, q3 = p.quantile(0.25), p.quantile(0.75)  # pandas: лінійна інтерполяція (як numpy за замовчуванням)
iqr = q3 - q1
fence = q3 + 1.5 * iqr
print(f"n = {len(p)}  середнє = {p.mean():.2f}  медіана = {p.median():.1f}  sd (ddof=1) = {p.std(ddof=1):.2f}")
print(f"Q1 = {q1:.2f}  Q3 = {q3:.2f}  IQR = {iqr:.2f}  верхня межа Tukey = Q3 + 1.5·IQR = {fence:.2f}")

out = df[df["posts"] > fence].copy()
# Тип дня: органічний сплеск — без молодих каналів і без стрибка репостів; кампанія — навпаки.
# Пороги взято з базового періоду: max young_channels = 2, max forwards_share = 0.30.
hi_young = out["young_channels"] > base["young_channels"].max()
hi_fwd = out["forwards_share"] > base["forwards_share"].max()
out["тип"] = np.select([hi_young & hi_fwd, ~hi_young & ~hi_fwd], ["кампанія", "органічний"], "змішаний")
print(f"\nДнів вище межі: {len(out)} з 90")
print(out.assign(день=[d(i) for i in out.index]).set_index("день").to_string())
print("\nСередні за типом дня (і базовий період для порівняння):")
cmp_ = out.groupby("тип")[METRICS].mean()
cmp_.loc["база (усі 60 днів)"] = base[METRICS].mean()
cmp_["днів"] = out.groupby("тип").size().reindex(cmp_.index).fillna(len(base)).astype(int)
print(cmp_.round(2).to_string())
org = out[out["тип"] == "органічний"]
assert set(org.index) <= set(base.index), "органічний сплеск поза базовим періодом — перевірити пороги"

# ---------------------------------------------------------------- Завдання 2
h("ЗАВДАННЯ 2. Порівняння періодів: база (n=60) vs кампанія (n=30)")
rows = []
for m in METRICS:
    a, b = base[m], camp[m]
    rows.append({
        "метрика": m, "база": a.mean(), "кампанія": b.mean(),
        "різниця": b.mean() - a.mean(), "у разах": b.mean() / a.mean() if a.mean() else np.inf,
        "p Welch t": stats.ttest_ind(b, a, equal_var=False).pvalue,
        "p Mann-Whitney": stats.mannwhitneyu(b, a, alternative="two-sided").pvalue,
    })
res = pd.DataFrame(rows).set_index("метрика")
alpha, k = 0.05, len(METRICS)
res["p Welch·5 (Бонф.)"] = (res["p Welch t"] * k).clip(upper=1)
res[f"значуще при α/{k}={alpha / k}"] = res["p Welch t"] < alpha / k
with pd.option_context("display.float_format", lambda x: f"{x:.4g}"):
    print(res.to_string())


def ci_mean(x, n_eff=None, level=0.95):
    n = len(x) if n_eff is None else n_eff
    se = x.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.5 + level / 2, df=n - 1)
    return x.mean() - t * se, x.mean() + t * se


ci_b, ci_c = ci_mean(base["posts"]), ci_mean(camp["posts"])
print(f"\n95% ДІ середнього posts: база [{ci_b[0]:.1f}; {ci_b[1]:.1f}], кампанія [{ci_c[0]:.1f}; {ci_c[1]:.1f}]"
      f" → {'перетинаються' if ci_b[1] >= ci_c[0] else 'НЕ перетинаються'}")

print("\nБОНУС. Автокореляція posts з лагом 1 і ефективний розмір вибірки n_eff = n·(1−r)/(1+r)")
for name, x in (("база", base["posts"]), ("кампанія", camp["posts"])):
    r1 = x.autocorr(lag=1)
    n_eff = len(x) * (1 - r1) / (1 + r1)
    lo, hi = ci_mean(x, n_eff=n_eff)  # df = n_eff − 1 може бути дробовим
    print(f"  {name:9s} r1 = {r1:+.3f}  n = {len(x)}  n_eff ≈ {n_eff:.1f}  95% ДІ з n_eff: [{lo:.1f}; {hi:.1f}]")
# r1 кампанії здебільшого створює тренд згасання; перевіряємо r1 залишків після лінійного тренду
xc = camp["posts"].to_numpy(float)
tt = np.arange(len(xc))
resid = pd.Series(xc - np.polyval(np.polyfit(tt, xc, 1), tt))
print(f"  кампанія, r1 залишків після лінійного тренду = {resid.autocorr(1):+.3f}")
# Грубіша, але чесніша одиниця спостереження — тиждень, а не день
def weekly(x):  # лише повні 7-денні блоки: неповний хвіст мав би іншу дисперсію
    x = x.iloc[: len(x) // 7 * 7]
    return x.groupby(np.arange(len(x)) // 7).mean()


wb, wc = weekly(base["posts"]), weekly(camp["posts"])
print(f"  тижневі середні (повні тижні): база {len(wb)}, кампанія {len(wc)} блоків;"
      f" Welch p = {stats.ttest_ind(wc, wb, equal_var=False).pvalue:.2g},"
      f" Mann-Whitney p = {stats.mannwhitneyu(wc, wb, alternative='two-sided').pvalue:.2g}")

# ---------------------------------------------------------------- Завдання 3
h("ЗАВДАННЯ 3. Кореляції Пірсона / Спірмена")
spikes_base = base[base["posts"] > fence].index  # органічні сплески в базі
samples = {
    "усі 90 днів": df,
    "лише база (60)": base,
    "база без сплесків > межі Tukey": base.drop(spikes_base),
    "лише кампанія (30)": camp,
}
crow = []
for label, s in samples.items():
    for y in ("avg_views", "forwards_share"):
        crow.append({"вибірка": label, "пара": f"posts ↔ {y}", "n": len(s),
                     "Пірсон r": stats.pearsonr(s["posts"], s[y])[0],
                     "Спірмен ρ": stats.spearmanr(s["posts"], s[y])[0]})
print(pd.DataFrame(crow).set_index(["вибірка", "пара"]).round(3).to_string())
print(f"(сплески бази, виключені в 3-му рядку: {', '.join(d(i) for i in spikes_base)})")


def partial_r(s, x, y, z):
    """Частковий Пірсон x↔y за контролю z: кореляція залишків лінійних регресій на z."""
    rx = s[x] - np.polyval(np.polyfit(s[z], s[x], 1), s[z])
    ry = s[y] - np.polyval(np.polyfit(s[z], s[y], 1), s[z])
    return stats.pearsonr(rx, ry)[0]


print("\nТретя змінна young_channels (усі 90 днів):")
for a_, b_ in (("young_channels", "posts"), ("young_channels", "forwards_share"), ("posts", "forwards_share")):
    print(f"  Пірсон {a_} ↔ {b_}: {stats.pearsonr(df[a_], df[b_])[0]:+.3f}")
print(f"  частковий posts ↔ forwards_share | young_channels: {partial_r(df, 'posts', 'forwards_share', 'young_channels'):+.3f}")
print(f"  частковий posts ↔ avg_views      | young_channels: {partial_r(df, 'posts', 'avg_views', 'young_channels'):+.3f}")

# ---------------------------------------------------------------- Для завдання 4
h("ДЛЯ ЗАВДАННЯ 4. Динаміка кампанії і залежність ознак A та B")
c = camp.copy()
c["posts / медіана бази"] = (c["posts"] / base["posts"].median()).round(1)
print(c.assign(день=[d(i) for i in c.index]).set_index("день").to_string())
weeks = {"30.09–06.10": ("2026-09-30", "2026-10-06"), "07.10–12.10": ("2026-10-07", "2026-10-12"),
         "13.10–15.10 (друга хвиля)": ("2026-10-13", "2026-10-15"), "16.10–29.10 (плато)": ("2026-10-16", "2026-10-29")}
print("\nСередні по фазах кампанії:")
print(pd.DataFrame({k_: df.loc[a:b, METRICS].mean() for k_, (a, b) in weeks.items()}).T.round(2).to_string())
print(f"\nМінімум posts у кампанії: {camp['posts'].min()} ({d(camp['posts'].idxmin())}) vs max бази {base['posts'].max()};"
      f" днів кампанії вище межі Tukey: {(camp['posts'] > fence).sum()} з 30")
print(f"Залежність A і B: Пірсон young_channels ↔ forwards_share = {stats.pearsonr(df['young_channels'], df['forwards_share'])[0]:+.3f} (90 днів),"
      f" {stats.pearsonr(camp['young_channels'], camp['forwards_share'])[0]:+.3f} (лише кампанія)")


def bayes(prior, lr):
    odds = prior / (1 - prior) * lr
    return odds / (1 + odds)


prior, lr_a, lr_b_naive, lr_b_given_a = 0.15, 8.0, 4.0, 1.5
pa = bayes(prior, lr_a)
print(f"\nBayes: prior {prior:.0%} → після A (LR={lr_a:g}) {pa:.0%}"
      f" → після B наївно (LR={lr_b_naive:g}) {bayes(pa, lr_b_naive):.0%}"
      f" | після B з урахуванням залежності (LR(B|A)={lr_b_given_a:g}) {bayes(pa, lr_b_given_a):.0%}")
