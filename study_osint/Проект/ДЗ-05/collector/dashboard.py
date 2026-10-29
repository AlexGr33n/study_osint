"""Статичний HTML-дашборд зі статистикою збору (лише таблиці, без JS і зовнішніх залежностей)."""
from html import escape

from .store import utc_now

SECTIONS = [
    ("Записи за цілями", "SELECT query AS ціль, COUNT(*) AS записів, MIN(date) AS найстаріший, "
                         "MAX(date) AS найновіший FROM posts GROUP BY query ORDER BY записів DESC"),
    ("Записи за днями (UTC)", "SELECT substr(date, 1, 10) AS день, COUNT(*) AS записів FROM posts "
                              "GROUP BY день ORDER BY день DESC LIMIT 21"),
    ("Мови", "SELECT COALESCE(lang, '—') AS мова, COUNT(*) AS записів FROM posts GROUP BY lang "
             "ORDER BY записів DESC LIMIT 10"),
    ("Курсори", "SELECT target AS ціль, min_id, max_id, backfill_done, status, last_error, updated_at "
                "FROM cursors ORDER BY target"),
    ("Відповіді API", "SELECT host, status, COUNT(*) AS запитів, MIN(CAST(rl_remaining AS INTEGER)) AS мін_remaining, "
                      "MAX(rl_limit) AS ліміт, ROUND(AVG(elapsed_ms)) AS сер_мс FROM requests "
                      "GROUP BY host, status ORDER BY host, status"),
    ("Останні прогони", "SELECT finished_at, mode, target, pages, fetched, inserted, duplicates, skipped, status, "
                        "error FROM runs ORDER BY finished_at DESC LIMIT 25"),
]


def _table(rows):
    if not rows:
        return "<p class=muted>немає даних</p>"
    head = "".join(f"<th>{escape(k)}</th>" for k in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{escape('' if v is None else str(v))}</td>" for v in r.values()) + "</tr>"
                   for r in rows)
    return f"<div class=scroll><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def render(store):
    total = store.query("SELECT COUNT(*) n, COUNT(DISTINCT author) a FROM posts")[0]
    req = store.query("SELECT COUNT(*) n, SUM(status = 429) r FROM requests")[0]
    cards = [("записів", total["n"]), ("авторів", total["a"]), ("запитів", req["n"]), ("відповідей 429", req["r"] or 0)]
    sections = "".join(f"<h2>{escape(title)}</h2>{_table(store.query(sql))}" for title, sql in SECTIONS)
    return f"""<!doctype html>
<html lang=uk><head><meta charset=utf-8><meta name=viewport content="width=device-width, initial-scale=1">
<title>Статистика збору</title>
<style>
:root {{ --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --line:#e7e5e4; --card:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1c1917; --fg:#f5f5f4; --muted:#a8a29e; --line:#44403c; --card:#292524; }} }}
body {{ background:var(--bg); color:var(--fg); font:14px/1.45 system-ui, sans-serif; margin:0 auto; padding:24px 16px; max-width:1100px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:16px; margin:28px 0 8px; }}
.muted {{ color:var(--muted); }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:12px; margin-top:16px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px; }}
.card b {{ display:block; font-size:24px; font-variant-numeric:tabular-nums; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; background:var(--card); }}
th, td {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; white-space:nowrap; font-variant-numeric:tabular-nums; }}
th {{ color:var(--muted); font-weight:600; }}
</style></head><body>
<h1>Статистика збору Mastodon</h1><p class=muted>згенеровано {utc_now()}</p>
<div class=cards>{"".join(f"<div class=card><b>{v}</b><span class=muted>{k}</span></div>" for k, v in cards)}</div>
{sections}
</body></html>
"""
