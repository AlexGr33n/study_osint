"""Ввічливий HTTP-клієнт: пейсинг, backoff з jitter, Retry-After, класифікація помилок, ротація ключів."""
import email.utils
import logging
import random
import time
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)


class TransientError(Exception):
    """5xx / 409 / мережа / 429 понад ліміт очікування — ціль відкладається до наступного прогону."""


class PermanentError(Exception):
    """403 / 404 / інші 4xx — ціль пропускається, повтор нічого не змінить."""


class KeyPool:
    """Токени одного хоста: найменш нещодавно використаний першим, 429 → кулдаун лише цього ключа, 401 → ключ виключено."""

    def __init__(self, tokens):
        self.cooldown = {t: 0.0 for t in tokens}
        self.last_used = {t: 0.0 for t in tokens}

    def pick(self):
        if not self.cooldown:
            raise PermanentError("усі токени хоста недійсні (401)")
        now = time.monotonic()
        # минулий кулдаун = 0, інакше ключ, що колись ловив 429, програвав би назавжди
        token = min(self.cooldown, key=lambda t: (max(self.cooldown[t] - now, 0.0), self.last_used[t]))
        wait = self.cooldown[token] - now
        if wait > 0:
            log.info("усі ключі на кулдауні, чекаю %.1f с", wait)
            time.sleep(wait)
        self.last_used[token] = time.monotonic()
        return token

    def soonest(self):
        """Скільки чекати до першого вільного ключа (0 — вільний є зараз)."""
        now = time.monotonic()
        return min((max(c - now, 0.0) for c in self.cooldown.values()), default=0.0)

    def cool(self, token, seconds):
        self.cooldown[token] = time.monotonic() + seconds

    def drop(self, token):
        self.cooldown.pop(token, None)
        self.last_used.pop(token, None)


def _parse_time(value):
    """ISO-8601 (X-RateLimit-Reset у Mastodon) → aware datetime або None; без зони вважаємо UTC."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def retry_after_seconds(response):
    """Скільки чекати за заголовками: Retry-After (секунди або HTTP-дата), інакше X-RateLimit-Reset."""
    value = response.headers.get("retry-after")
    if value:
        if value.strip().isdigit():
            return float(value)
        try:
            when = email.utils.parsedate_to_datetime(value)
            when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)  # "-0000" дає naive
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            pass
    reset = _parse_time(response.headers.get("x-ratelimit-reset"))
    if reset:
        return max(0.0, (reset - datetime.now(timezone.utc)).total_seconds())
    return None


class PoliteClient:
    def __init__(self, *, delay=1.5, max_retries=4, max_wait=300.0, backoff_base=1.0, low_watermark=10,
                 tokens_by_host=None, proxy=None, user_agent="study-osint-collector/0.1",
                 journal=None, transport=None, timeout=20.0):
        self.delay = delay
        self.max_retries = max_retries
        self.max_wait = max_wait
        self.backoff_base = backoff_base
        self.low_watermark = low_watermark
        self.pools = {host: KeyPool(tokens) for host, tokens in (tokens_by_host or {}).items()}
        self.journal = journal or (lambda **kw: None)
        self.next_at = {}  # host -> monotonic-час, раніше якого не стукаємо
        self.http = httpx.Client(proxy=proxy or None, transport=transport, timeout=timeout,
                                 headers={"User-Agent": user_agent, "Accept": "application/json"})

    def _pace(self, host):
        wait = self.next_at.get(host, 0.0) - time.monotonic()
        if wait > 0:
            time.sleep(wait)

    def _backoff(self, attempt):
        return min(self.max_wait, self.backoff_base * 2 ** attempt) + random.uniform(0, self.backoff_base)

    def _record(self, host, path, started, response=None, error=None):
        h = response.headers if response is not None else {}
        remaining = h.get("x-ratelimit-remaining")
        self.journal(host=host, path=path, status=response.status_code if response is not None else None,
                     rl_limit=h.get("x-ratelimit-limit"), rl_remaining=remaining,
                     rl_reset=h.get("x-ratelimit-reset"), retry_after=h.get("retry-after"),
                     elapsed_ms=int((time.monotonic() - started) * 1000), error=error)
        log.debug("%s %s -> %s remaining=%s", host, path, getattr(response, "status_code", error), remaining)

    def _adapt(self, host, response):
        """Ліміт майже вичерпано — сповільнюємось до скидання вікна, а не чекаємо на 429."""
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining is not None and remaining.isdigit() and int(remaining) <= self.low_watermark:
            wait = min(self.max_wait, retry_after_seconds(response) or self.delay)
            log.warning("%s: лишилось %s запитів у вікні, пауза %.0f с", host, remaining, wait)
            self.next_at[host] = time.monotonic() + wait

    def get_json(self, url, params=None):
        parsed = httpx.URL(url)
        host, path = parsed.host, parsed.path
        pool = self.pools.get(host)
        last = "немає спроб"
        for attempt in range(self.max_retries + 1):
            self._pace(host)
            token = pool.pick() if pool else None
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            started = time.monotonic()
            try:
                response = self.http.get(url, params=params, headers=headers)
            except httpx.TransportError as exc:
                self._record(host, path, started, error=type(exc).__name__)
                last = f"мережа: {type(exc).__name__}"
                self.next_at[host] = time.monotonic() + self._backoff(attempt)
                continue
            self._record(host, path, started, response)
            self.next_at[host] = time.monotonic() + self.delay
            status = response.status_code

            if status == 200:
                self._adapt(host, response)
                try:
                    return response.json()
                except ValueError:  # HTML-заглушка замість JSON (бачили на проксі/CDN)
                    last = "200, але не JSON"
                    self.next_at[host] = time.monotonic() + self._backoff(attempt)
                    continue
            if status == 429:
                wait = retry_after_seconds(response) or self._backoff(attempt)
                if token:
                    pool.cool(token, wait)
                    wait = pool.soonest()  # довгий кулдаун одного ключа не страшний, якщо є вільний
                if wait > self.max_wait:
                    raise TransientError(f"429, Retry-After {wait:.0f} с > MAX_WAIT — відкладаю ціль")
                log.warning("%s: 429, чекаю %.1f с (спроба %d)", host, wait, attempt + 1)
                if not token:
                    self.next_at[host] = time.monotonic() + wait
                last = "429"
                continue
            if status == 401 and token:
                log.error("%s: токен відхилено (401), виключаю з ротації", host)
                pool.drop(token)
                last = "401"
                continue
            # 3xx теж постійна: редирект на інший хост обійшов би валідацію цілі й пейсинг по хосту
            if 300 <= status < 500 and status != 409:
                raise PermanentError(f"HTTP {status} {path}")
            last = f"HTTP {status}"  # 5xx / 409 — тимчасове
            self.next_at[host] = time.monotonic() + self._backoff(attempt)
        raise TransientError(f"{last} після {self.max_retries + 1} спроб")

    def close(self):
        self.http.close()
