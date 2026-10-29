"""CLI: python -m collector run | backfill | export | stats | dashboard"""
import argparse
import csv
import json
import logging
import os
import sys
import tomllib
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from .http import PermanentError, PoliteClient, TransientError
from .mastodon import collect_target, target_key
from .store import EXPORT_FIELDS, Store, utc_now

log = logging.getLogger("collector")
BASE = Path(__file__).resolve().parents[1]  # корінь проєкту: .env, база, логи й цілі не залежать від cwd


def from_base(env, default):
    path = Path(os.getenv(env) or default)
    return path if path.is_absolute() else BASE / path


def parse_tokens(raw):
    """MASTODON_TOKENS="host=token,host=token2" → {host: [token, ...]}"""
    pools = {}
    for item in filter(None, (s.strip() for s in (raw or "").split(","))):
        host, _, token = item.partition("=")
        if token:
            pools.setdefault(host.strip(), []).append(token.strip())
    return pools


def setup_logging(level):
    for stream in (sys.stdout, sys.stderr):  # у пайпі Windows інакше cp1251 і кракозябри
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    (BASE / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(BASE / "logs" / "collector.log", encoding="utf-8")])
    logging.getLogger("httpx").setLevel(logging.WARNING)


def cmd_collect(args, store, backfill):
    targets = tomllib.loads(from_base("TARGETS_FILE", "targets.toml").read_text("utf-8")).get("target", [])
    if not targets:
        log.error("у конфігу немає жодної [[target]]")
        return 2
    if args.target:
        targets = [t for t in targets if target_key(t) == args.target]
        if not targets:
            log.error("ціль %r не знайдена в конфігу", args.target)
            return 2
    client = PoliteClient(
        delay=float(os.getenv("REQUEST_DELAY", "1.5")), max_retries=int(os.getenv("MAX_RETRIES", "4")),
        max_wait=float(os.getenv("MAX_WAIT", "300")), tokens_by_host=parse_tokens(os.getenv("MASTODON_TOKENS")),
        proxy=os.getenv("COLLECTOR_PROXY"), user_agent=os.getenv("USER_AGENT", "study-osint-collector/0.1"),
        journal=store.log_request)
    pages = args.pages or int(os.getenv("MAX_PAGES_PER_RUN", "5"))
    mode = "backfill" if backfill else "incremental"
    total, failed = Counter(), 0
    try:
        for target in targets:
            key, started = target_key(target), utc_now()
            stats, status, error = Counter(), "ok", None
            try:
                collect_target(client, store, target, pages, backfill=backfill, stats=stats)
            except TransientError as exc:   # курсор не зсунуто — наступний прогін продовжить звідси
                status, error = "deferred", str(exc)
            except PermanentError as exc:
                status, error = "skipped", str(exc)
            except Exception as exc:        # збій однієї цілі не валить прогін
                status, error = "error", f"{type(exc).__name__}: {exc}"
                log.exception("%s: несподівана помилка", key)
            if status != "ok":
                failed += 1
                log.error("%s: %s — %s", key, status, error)
            log.info("%s [%s]: сторінок %d, отримано %d, нових %d, дублів %d, пропущено %d",
                     key, mode, stats["pages"], stats["fetched"], stats["inserted"], stats["duplicates"],
                     stats["skipped"])
            total.update(stats)
            try:  # збій журналу (база заблокована, диск) теж не має зупиняти решту цілей
                store.mark(key, status, error)  # успіх скидає застарілий deferred/last_error
                store.log_run(started_at=started, mode=mode, target=key, status=status, error=error,
                              **{k: stats[k] for k in ("pages", "fetched", "inserted", "duplicates", "skipped")})
            except Exception:
                log.exception("%s: не вдалося записати статус прогону", key)
    finally:
        client.close()
    log.info("Прогін %s: нових %d, дублів %d, цілей з помилкою %d/%d",
             mode, total["inserted"], total["duplicates"], failed, len(targets))
    if total["fetched"] == 0 and not backfill:
        log.warning("АЛЕРТ: 0 записів за прогін — перевірте джерело/колектор (або нових постів справді немає)")
    return 1 if targets and failed == len(targets) else 0


def cmd_export(args, store):
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    # utf-8-sig: інакше Excel відкриває кирилицю в CSV кракозябрами
    with out.open("w", encoding="utf-8-sig" if args.format == "csv" else "utf-8", newline="") as f:
        if args.format == "csv":
            writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS)
            writer.writeheader()
        for n, post in enumerate(store.iter_posts(), 1):
            if args.format == "csv":
                writer.writerow({**post, "media": json.dumps(post["media"], ensure_ascii=False)})
            else:
                f.write(json.dumps(post, ensure_ascii=False) + "\n")
    print(f"{n} записів → {out}")


def cmd_stats(store):
    for row in store.query("SELECT query, COUNT(*) n, MIN(date) first, MAX(date) last FROM posts GROUP BY query"):
        print(f"{row['query']:<32} {row['n']:>6}  {row['first']} … {row['last']}")
    print("Курсори:")
    for row in store.query("SELECT * FROM cursors ORDER BY target"):
        print(f"  {row['target']:<30} min_id={row['min_id']} max_id={row['max_id']} "
              f"backfill_done={row['backfill_done']} status={row['status']} {row['last_error'] or ''}")
    print("Відповіді API:", {r["status"]: r["n"] for r in
                             store.query("SELECT status, COUNT(*) n FROM requests GROUP BY status")})


def main(argv=None):
    load_dotenv(BASE / ".env")
    parser = argparse.ArgumentParser(prog="collector", description="Інкрементний колектор Mastodon")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("run", "backfill"):
        p = sub.add_parser(name, help="інкрементний збір нового" if name == "run" else "добір старої історії")
        p.add_argument("--target", help="лише одна ціль, напр. mastodon.social#osint")
        p.add_argument("--pages", type=int, help="сторінок на ціль за прогін (замість MAX_PAGES_PER_RUN)")
    p = sub.add_parser("export", help="вивантажити канонічні записи")
    p.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    p.add_argument("--out", default=BASE / "data" / "sample.jsonl")
    sub.add_parser("stats", help="зведення в консоль")
    p = sub.add_parser("dashboard", help="HTML-дашборд статистики збору")
    p.add_argument("--out", default=BASE / "data" / "dashboard.html")
    args = parser.parse_args(argv)

    setup_logging(os.getenv("LOG_LEVEL", "INFO"))
    db_path = from_base("COLLECTOR_DB", "data/collector.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = Store(db_path)
    try:
        if args.cmd in ("run", "backfill"):
            return cmd_collect(args, store, backfill=args.cmd == "backfill")
        if args.cmd == "export":
            cmd_export(args, store)
        elif args.cmd == "stats":
            cmd_stats(store)
        else:
            from .dashboard import render
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render(store), encoding="utf-8")
            print(f"дашборд → {out}")
        return 0
    finally:
        store.conn.close()


if __name__ == "__main__":
    sys.exit(main())
