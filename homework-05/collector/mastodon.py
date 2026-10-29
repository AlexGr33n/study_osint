"""Адаптер Mastodon: хештег-стрічка інстансу → канонічні записи; інкрементний збір і backfill за id-курсором."""
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser

from . import __version__
from .http import PermanentError
from .store import id_key, utc_now

log = logging.getLogger(__name__)
PAGE_LIMIT = 40  # максимум Mastodon для timelines


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "p":
            self.parts.append("\n\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html):
    parser = _Text()
    parser.feed(html or "")
    return "".join(parser.parts).strip()


def to_utc(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def opted_out(account):
    """Автор вимкнув індексацію (indexable=false / noindex=true) — не збираємо."""
    return account.get("indexable") is False or account.get("noindex") is True


def to_canonical(status, instance, query):
    """Статус Mastodon → канонічний запис author · url · date · text (+media). None — якщо поля відсутні."""
    account = status.get("account") or {}
    acct, uri, created = account.get("acct"), status.get("uri"), status.get("created_at")
    if not (acct and uri and created and status.get("id")):
        return None
    try:
        date = to_utc(created)
    except (TypeError, ValueError):
        return None
    return {
        "uid": hashlib.sha256(f"mastodon|{uri}".encode()).hexdigest(),
        "platform": "mastodon",
        "instance": instance,
        "source_id": str(status["id"]),
        "author": acct if "@" in acct else f"{acct}@{instance}",
        "author_url": account.get("url"),
        "url": status.get("url") or uri,
        "date": date,
        "text": html_to_text(status.get("content")) or status.get("spoiler_text") or "",
        "lang": status.get("language"),
        "media": json.dumps([{"type": m.get("type"), "url": m.get("url"), "description": m.get("description")}
                             for m in status.get("media_attachments") or []], ensure_ascii=False),
        "query": query,
        "collected_at": utc_now(),
        "collector": f"study-osint-collector/{__version__}",
        "raw": json.dumps(status, ensure_ascii=False),
    }


# ASCII-домен з літерним TLD (IDN — у punycode): IP, localhost і «ſ»/«K», які httpx перетворює на інший хост, відсіюються
HOST_RE = re.compile(r"(?=.{1,253}\Z)([a-z0-9-]{1,63}\.)+[a-z][a-z0-9-]{1,62}", re.I | re.A)
TAG_RE = re.compile(r"\w{1,100}")  # хештег Mastodon: літери/цифри/_ будь-якою мовою


def target_key(target):
    return f"{target.get('instance')}#{target.get('tag')}"


def collect_target(client, store, target, max_pages, backfill=False, stats=None):
    """Одна ціль, не більше max_pages сторінок. Статистику пише в stats (видно й після винятку)."""
    key = target_key(target)
    instance, tag = target.get("instance"), target.get("tag")
    # без валідації "a/../b" у тезі httpx нормалізує в інший шлях і ми зберемо чужу стрічку
    # fullmatch, бо `$` у match пропускає хвостовий "\n"
    if not (isinstance(instance, str) and isinstance(tag, str) and HOST_RE.fullmatch(instance)
            and TAG_RE.fullmatch(tag)):
        raise PermanentError(f"невалідна ціль {key!r}")
    url = f"https://{instance}/api/v1/timelines/tag/{tag}"
    stats = Counter() if stats is None else stats
    for _ in range(max_pages):
        cur = store.cursor(key)
        params = {"limit": PAGE_LIMIT}
        if backfill:
            if cur["backfill_done"]:
                break
            if cur["max_id"]:
                params["max_id"] = cur["max_id"]  # старіше за найстаріший зібраний
        elif cur["min_id"]:
            params["min_id"] = cur["min_id"]      # одразу новіше за найновіший зібраний
        page = client.get_json(url, params)
        stats["pages"] += 1
        if not isinstance(page, list):
            raise ValueError(f"неочікувана відповідь: {type(page).__name__}")
        if not page:
            if backfill and cur["max_id"]:  # порожня стрічка без курсора — ще не «кінець історії»
                store.mark(key, "ok", backfill_done=1)
                log.info("%s: backfill дійшов до початку історії", key)
            break
        rows = []
        for status in page:
            if status.get("visibility") != "public" or opted_out(status.get("account") or {}):
                stats["skipped"] += 1
                continue
            row = to_canonical(status, instance, key)
            if row is None:
                stats["malformed"] += 1
                continue
            rows.append(row)
        ids = [str(s["id"]) for s in page if s.get("id")]
        if not ids:
            raise ValueError("сторінка без id статусів — курсор не зсуваю")
        inserted = store.save_page(key, rows, max(ids, key=id_key), min(ids, key=id_key))
        stats["fetched"] += len(page)
        stats["inserted"] += inserted
        stats["duplicates"] += len(rows) - inserted
        if not backfill and not cur["min_id"]:
            break  # перший прогін: лише свіжа сторінка, решта — backfill
        # неповна сторінка ще не «кінець»: деякі сервери ріжуть limit нижче 40 — гортаємо до порожньої
    else:
        if not backfill:
            log.warning("%s: вичерпано %d сторінок, а нові пости ще є — ціль відстає, збільште MAX_PAGES_PER_RUN",
                        key, max_pages)
    if stats["malformed"]:
        log.warning("%s: %d записів без обовʼязкових полів — можливо, змінився API", key, stats["malformed"])
    return stats
