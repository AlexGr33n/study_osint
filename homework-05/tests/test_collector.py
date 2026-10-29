"""Тести без мережі: фейковий інстанс Mastodon через httpx.MockTransport."""
from collections import Counter

import httpx
import pytest

from collector import http as http_mod
from collector.http import PermanentError, PoliteClient, TransientError
from collector.mastodon import collect_target, html_to_text, to_canonical
from collector.store import Store

TARGET = {"instance": "fake.social", "tag": "osint"}
KEY = "fake.social#osint"


def status(i, **over):
    s = {"id": str(i), "uri": f"https://fake.social/users/a/statuses/{i}", "url": f"https://fake.social/@a/{i}",
         "created_at": "2026-10-29T07:00:00.000+02:00", "visibility": "public", "language": "uk",
         "content": f"<p>пост {i}</p><p>рядок<br>два</p>", "media_attachments": [],
         "account": {"acct": "a", "url": "https://fake.social/@a", "indexable": True}}
    s.update(over)
    return s


class FakeMastodon:
    """Семантика пагінації Mastodon: max_id → старіше, min_id → одразу новіше, без параметрів → найсвіжіше."""

    def __init__(self, n):
        self.posts = [status(i) for i in range(1, n + 1)]
        self.calls = []
        self.script = []  # черга примусових відповідей (status, headers)

    def __call__(self, request):
        self.calls.append(dict(request.url.params))
        forced = self.script.pop(0) if self.script else None  # None у скрипті = звичайна відповідь
        if forced:
            code, headers = forced
            return httpx.Response(code, headers=headers, json={"error": "x"})
        p, limit = request.url.params, int(request.url.params.get("limit", 20))
        items = sorted(self.posts, key=lambda s: int(s["id"]))
        if "max_id" in p:
            page = [s for s in items if int(s["id"]) < int(p["max_id"])][-limit:]
        elif "min_id" in p:
            page = [s for s in items if int(s["id"]) > int(p["min_id"])][:limit]
        else:
            page = items[-limit:]
        return httpx.Response(200, json=page[::-1], headers={"x-ratelimit-remaining": "299"})


@pytest.fixture
def env(monkeypatch, tmp_path):
    slept = []
    monkeypatch.setattr(http_mod.time, "sleep", slept.append)
    fake = FakeMastodon(130)
    client = PoliteClient(delay=0, backoff_base=0.01, transport=httpx.MockTransport(fake))
    store = Store(tmp_path / "t.db")
    yield fake, client, store, slept
    store.conn.close()
    client.close()


def test_canonical_record():
    row = to_canonical(status(7), "fake.social", KEY)
    assert row["author"] == "a@fake.social"
    assert row["date"] == "2026-10-29T05:00:00Z"
    assert row["text"] == "пост 7\n\nрядок\nдва"
    assert row["uid"] == to_canonical(status(7), "other.instance", KEY)["uid"]  # той самий пост з іншого інстансу
    assert to_canonical(status(8, uri=None), "fake.social", KEY) is None
    assert html_to_text("") == ""


def test_incremental_backfill_and_idempotency(env):
    fake, client, store, _ = env
    first = collect_target(client, store, TARGET, max_pages=5)
    assert first["inserted"] == 40 and store.cursor(KEY)["min_id"] == "130"

    assert collect_target(client, store, TARGET, max_pages=5)["inserted"] == 0  # нічого нового
    assert fake.calls[-1]["min_id"] == "130"

    fake.posts += [status(i) for i in range(131, 181)]
    again = collect_target(client, store, TARGET, max_pages=5)
    assert again["inserted"] == 50 and store.cursor(KEY)["min_id"] == "180"

    back = collect_target(client, store, TARGET, max_pages=1, backfill=True)
    assert back["inserted"] == 40 and store.cursor(KEY)["max_id"] == "51"  # курсор рухається поступово
    collect_target(client, store, TARGET, max_pages=10, backfill=True)
    assert store.cursor(KEY)["backfill_done"] == 1
    assert store.query("SELECT COUNT(*) n FROM posts")[0]["n"] == 180

    # курсор втрачено → повтор з нуля дає лише дублі, не нові рядки
    store.conn.execute("DELETE FROM cursors")
    redo = collect_target(client, store, TARGET, max_pages=1)
    assert redo["inserted"] == 0 and redo["duplicates"] == 40


def test_opt_out_and_private_are_skipped(env):
    fake, client, store, _ = env
    fake.posts = [status(1), status(2, visibility="unlisted"),
                  status(3, account={"acct": "b", "indexable": False}), status(4, account={"acct": "c", "noindex": True})]
    stats = collect_target(client, store, TARGET, max_pages=1)
    assert stats["inserted"] == 1 and stats["skipped"] == 3


def test_429_honours_retry_after(env):
    fake, client, store, slept = env
    fake.script = [(429, {"retry-after": "7"})]
    assert collect_target(client, store, TARGET, max_pages=1)["inserted"] == 40
    assert 7 in [round(s) for s in slept]


def test_429_beyond_max_wait_defers(env):
    fake, client, store, _ = env
    client.max_wait = 60
    fake.script = [(429, {"retry-after": "3600"})]
    with pytest.raises(TransientError):
        collect_target(client, store, TARGET, max_pages=1)
    assert store.cursor(KEY)["min_id"] is None  # курсор не зрушив


def test_5xx_retries_then_defers_without_moving_cursor(env):
    fake, client, store, _ = env
    collect_target(client, store, TARGET, max_pages=1)
    fake.script = [(503, {})] * (client.max_retries + 1)
    with pytest.raises(TransientError):
        collect_target(client, store, TARGET, max_pages=1)
    assert store.cursor(KEY)["min_id"] == "130"
    fake.script = [(502, {})]
    collect_target(client, store, TARGET, max_pages=1)  # один 502 — повтор і успіх


def test_4xx_is_permanent(env):
    fake, client, store, _ = env
    fake.script = [(404, {})]
    with pytest.raises(PermanentError):
        collect_target(client, store, TARGET, max_pages=1)
    assert len(fake.calls) == 1  # без марних повторів


@pytest.mark.parametrize("bad", [{"instance": "fake.social", "tag": "a/../b"},
                                 {"instance": "fake.social/evil", "tag": "x"}, {"instance": "localhost", "tag": "x"},
                                 {"instance": "10.0.0.10", "tag": "x"}, {"instance": "fake.social", "tag": 5}])
def test_invalid_target_rejected_before_request(env, bad):
    fake, client, store, _ = env
    with pytest.raises(PermanentError):
        collect_target(client, store, bad, max_pages=1)
    assert fake.calls == []


def test_redirect_is_permanent(env):
    fake, client, store, _ = env
    fake.script = [(301, {"location": "https://elsewhere.example/"})]
    with pytest.raises(PermanentError):
        collect_target(client, store, TARGET, max_pages=1)
    assert len(fake.calls) == 1


def test_naive_reset_header_does_not_crash():
    from collector.http import retry_after_seconds
    assert retry_after_seconds(httpx.Response(429, headers={"x-ratelimit-reset": "2000-01-01T00:00:00"})) == 0
    assert retry_after_seconds(httpx.Response(429, headers={"retry-after": "Sat, 01 Jan 2000 00:00:00 -0000"})) == 0


def test_bad_date_is_malformed_not_fatal(env):
    fake, client, store, _ = env
    fake.posts = [status(1), status(2, created_at="вчора")]
    stats = collect_target(client, store, TARGET, max_pages=1)
    assert stats["inserted"] == 1 and stats["malformed"] == 1


def test_non_numeric_ids_keep_cursor_order(env):
    """Pleroma/GoToSocial: id — рядки фіксованої довжини, не числа."""
    fake, client, store, _ = env
    fake.posts = []
    store.save_page(KEY, [], "9ZZZ", "0AAA")
    store.save_page(KEY, [], "A000", "00ZZ")
    cur = store.cursor(KEY)
    assert (cur["min_id"], cur["max_id"]) == ("A000", "00ZZ")


def test_partial_progress_survives_failure(env):
    fake, client, store, _ = env
    collect_target(client, store, TARGET, max_pages=1)
    fake.posts += [status(i) for i in range(131, 221)]
    fake.script = [None] + [(503, {})] * (client.max_retries + 1)  # перша сторінка нормальна, далі 503
    stats = Counter()
    with pytest.raises(TransientError):
        collect_target(client, store, TARGET, max_pages=5, stats=stats)
    assert stats["inserted"] == 40 and store.cursor(KEY)["min_id"] == "170"


def test_target_without_keys_is_rejected(env):
    _, client, store, _ = env
    with pytest.raises(PermanentError):
        collect_target(client, store, {"tag": "osint"}, max_pages=1)


def test_backfill_on_empty_tag_is_not_finished(env):
    fake, client, store, _ = env
    fake.posts = []
    collect_target(client, store, TARGET, max_pages=1, backfill=True)
    assert store.cursor(KEY)["backfill_done"] == 0
    fake.posts = [status(i) for i in range(1, 101)]
    collect_target(client, store, TARGET, max_pages=1)
    collect_target(client, store, TARGET, max_pages=5, backfill=True)
    assert store.query("SELECT COUNT(*) n FROM posts")[0]["n"] == 100


def test_key_returns_to_rotation_after_cooldown(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(http_mod.time, "monotonic", lambda: clock[0])
    pool = http_mod.KeyPool(["k1", "k2"])
    pool.cool("k1", 10)
    clock[0] += 11
    assert {pool.pick(), pool.pick()} == {"k1", "k2"}


@pytest.mark.parametrize("bad", [{"instance": "mastodon.social\n", "tag": "x"}, {"instance": "mastodon.ſocial", "tag": "x"},
                                 {"instance": "Ka.social", "tag": "x"}, {"instance": "fake.social", "tag": "osint\n"}])
def test_unicode_and_newline_tricks_rejected(env, bad):
    fake, client, store, _ = env
    with pytest.raises(PermanentError):
        collect_target(client, store, bad, max_pages=1)
    assert fake.calls == []


def test_cyrillic_tag_still_allowed(env):
    _, client, store, _ = env
    assert collect_target(client, store, {"instance": "fake.social", "tag": "україна"}, max_pages=1)["inserted"] == 40


def test_server_capping_limit_does_not_slow_catch_up(env, monkeypatch):
    fake, client, store, _ = env
    collect_target(client, store, TARGET, max_pages=1)
    fake.posts += [status(i) for i in range(131, 191)]
    original = FakeMastodon.__call__
    monkeypatch.setattr(FakeMastodon, "__call__",
                        lambda self, req: original(self, req.__class__(req.method, req.url.copy_set_param("limit", 20))))
    assert collect_target(client, store, TARGET, max_pages=5)["inserted"] == 60  # 3 неповні сторінки + порожня


def test_lag_warning_when_pages_exhausted(env, caplog):
    fake, client, store, _ = env
    collect_target(client, store, TARGET, max_pages=1)
    fake.posts += [status(i) for i in range(131, 251)]
    collect_target(client, store, TARGET, max_pages=2)
    assert "ціль відстає" in caplog.text and store.cursor(KEY)["min_id"] == "210"


def test_long_retry_after_on_one_key_uses_the_other(monkeypatch):
    monkeypatch.setattr(http_mod.time, "sleep", lambda s: None)
    seen, answers = [], [429, 200]

    def handler(request):
        seen.append(request.headers.get("authorization"))
        return httpx.Response(answers.pop(0), headers={"retry-after": "3600"}, json=[])

    client = PoliteClient(delay=0, max_wait=60, tokens_by_host={"fake.social": ["k1", "k2"]},
                          transport=httpx.MockTransport(handler))
    assert client.get_json("https://fake.social/x") == []
    assert seen == ["Bearer k1", "Bearer k2"]


def test_cli_ignores_cwd_and_survives_journal_failure(monkeypatch, tmp_path, caplog):
    """Запуск з чужої теки не плодить data/ і logs/; збій запису статусу не зупиняє інші цілі."""
    from collector import __main__ as cli
    from collector.store import Store as RealStore

    targets = tmp_path / "t.toml"
    targets.write_text('[[target]]\ninstance = "localhost"\ntag = "a"\n[[target]]\ninstance = "10.0.0.1"\ntag = "b"\n',
                       encoding="utf-8")
    monkeypatch.setenv("TARGETS_FILE", str(targets))
    monkeypatch.setenv("COLLECTOR_DB", str(tmp_path / "db" / "c.db"))
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    def broken_mark(self, *a, **kw):
        raise __import__("sqlite3").OperationalError("database is locked")

    monkeypatch.setattr(RealStore, "mark", broken_mark)
    assert cli.main(["run"]) == 1  # обидві цілі невалідні → код 1, але без трейсбеку
    assert list(cwd.iterdir()) == []
    assert caplog.text.count("не вдалося записати статус прогону") == 2  # друга ціль теж оброблена


def test_key_rotation_cools_only_the_limited_key(monkeypatch, tmp_path):
    monkeypatch.setattr(http_mod.time, "sleep", lambda s: None)
    seen, answers = [], [429, 200]

    def handler(request):
        seen.append(request.headers.get("authorization"))
        return httpx.Response(answers.pop(0), headers={"retry-after": "30"}, json=[])

    client = PoliteClient(delay=0, tokens_by_host={"fake.social": ["k1", "k2"]}, transport=httpx.MockTransport(handler))
    assert client.get_json("https://fake.social/api/v1/timelines/tag/x") == []
    assert seen == ["Bearer k1", "Bearer k2"]  # після 429 на k1 одразу пішов k2
