#!/usr/bin/env python3
"""Пасивний технічний профіль домену для skill `company-domain-check`.

Жодного запиту до серверів самої цілі: тільки публічні реєстри та агрегатори
(RDAP/WHOIS, DNS-over-HTTPS, Certificate Transparency, Wayback Machine, GLEIF).
Кожна сира відповідь зберігається в <out>/raw/ разом із SHA-256 і часом UTC —
це ланцюжок походження (provenance) для memo.

Тільки стандартна бібліотека Python 3.9+.

Приклади:
    python domain_recon.py example.com
    python domain_recon.py https://www.novaposhta.ua/uk --company "Nova Poshta" --out dd-novaposhta.ua
    python domain_recon.py example.com --skip ct,wayback --timeout 20
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "company-domain-check/1.0 (passive OSINT study; +https://github.com/smixs/osint-skill)"
SOURCES = ("rdap", "dns", "ct", "wayback", "gleif")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Recorder:
    """Робить HTTP/WHOIS-запити й фіксує provenance кожної відповіді."""

    def __init__(self, out_dir: Path, timeout: int):
        self.raw_dir = out_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.provenance: list[dict] = []
        self.errors: list[dict] = []

    def _save(self, name: str, source: str, body: bytes, status) -> dict:
        path = self.raw_dir / name
        path.write_bytes(body)
        rec = {
            "file": f"raw/{name}",
            "source": source,
            "retrieved_utc": utc_now(),
            "status": status,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        self.provenance.append(rec)
        return rec

    def http(self, name: str, url: str, headers: dict | None = None, timeout: int | None = None):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                body = resp.read()
                self._save(name, url, body, resp.status)
                return resp.status, body
        except urllib.error.HTTPError as e:
            body = e.read() or b""
            self._save(name, url, body, e.code)
            self.errors.append({"source": url, "error": f"HTTP {e.code}"})
            return e.code, body
        except Exception as e:  # timeout, DNS, TLS…
            self.errors.append({"source": url, "error": f"{type(e).__name__}: {e}"})
            return None, b""

    def json(self, name: str, url: str, headers: dict | None = None, timeout: int | None = None):
        status, body = self.http(name, url, headers, timeout)
        if status != 200 or not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            self.errors.append({"source": url, "error": "invalid JSON"})
            return None

    def whois(self, name: str, server: str, query: str) -> str | None:
        try:
            with socket.create_connection((server, 43), timeout=self.timeout) as s:
                s.sendall(query.encode("idna") + b"\r\n")
                chunks = []
                while chunk := s.recv(4096):
                    chunks.append(chunk)
        except Exception as e:
            self.errors.append({"source": f"whois://{server}", "error": f"{type(e).__name__}: {e}"})
            return None
        body = b"".join(chunks)
        self._save(name, f"whois://{server}/{query}", body, "ok")
        for enc in ("utf-8", "cp1251", "latin-1"):
            try:
                return body.decode(enc)
            except UnicodeDecodeError:
                continue
        return body.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- helpers

def normalize_domain(raw: str) -> str:
    raw = raw.strip()
    if "://" not in raw:
        raw = "http://" + raw
    host = urllib.parse.urlsplit(raw).hostname or ""
    host = host.rstrip(".").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        sys.exit(f"Не схоже на домен: {raw!r}")
    return host.encode("idna").decode("ascii")  # кирилиця (.укр) → punycode


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%b-%Y", "%Y%m%d%H%M%S"):
        try:
            v = value.replace("Z", "+0000")
            v = re.sub(r"([+-]\d\d):?(\d\d)?$", lambda m: m.group(1) + (m.group(2) or "00"), v) if "%z" in fmt else v
            dt = datetime.strptime(v, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d") if dt else None


def vcard_field(entity: dict, field: str) -> str | None:
    try:
        for item in entity["vcardArray"][1]:
            if item[0] == field and isinstance(item[3], str) and item[3].strip():
                return item[3].strip()
    except (KeyError, IndexError, TypeError):
        pass
    return None


# --------------------------------------------------------------------------- collectors

def collect_rdap(rec: Recorder, domain: str) -> dict:
    data = rec.json("rdap.json", f"https://rdap.org/domain/{domain}", {"Accept": "application/rdap+json"})
    if data:
        events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}
        out = {
            "method": "rdap",
            "created": iso(parse_date(events.get("registration"))),
            "updated": iso(parse_date(events.get("last changed"))),
            "expires": iso(parse_date(events.get("expiration"))),
            "status": data.get("status", []),
            "nameservers": sorted(ns.get("ldhName", "").lower() for ns in data.get("nameservers", [])),
            "registrar": None,
            "registrant_org": None,
        }
        for ent in data.get("entities", []):
            roles = ent.get("roles", [])
            if "registrar" in roles:
                out["registrar"] = vcard_field(ent, "fn") or ent.get("handle")
            if "registrant" in roles:
                org = vcard_field(ent, "org") or vcard_field(ent, "fn")
                if org and "redacted" not in org.lower():
                    out["registrant_org"] = org
        return out
    return collect_whois(rec, domain)


def collect_whois(rec: Recorder, domain: str) -> dict:
    """Fallback для зон без RDAP: IANA → referral WHOIS-сервер (порт 43)."""
    iana = rec.whois("whois-iana.txt", "whois.iana.org", domain) or ""
    m = re.search(r"^(?:refer|whois):\s*(\S+)", iana, re.M | re.I)
    if not m:
        return {"method": "none", "error": "RDAP недоступний, WHOIS-сервер зони не знайдено"}
    text = rec.whois("whois.txt", m.group(1), domain) or ""

    def grab(*keys):
        for k in keys:
            mm = re.search(rf"^\s*{k}\s*:\s*(.+)$", text, re.M | re.I)
            if mm:
                return mm.group(1).strip()
        return None

    if re.search(r"no match|not found|no entries found|no data found|^status:\s*free", text, re.I | re.M):
        return {"method": f"whois:{m.group(1)}", "registered": False}
    return {
        "method": f"whois:{m.group(1)}",
        "created": iso(parse_date(grab("Creation Date", "created", "Registered on", "Registration Time"))),
        "updated": iso(parse_date(grab("Updated Date", "modified", "Last updated", "changed"))),
        "expires": iso(parse_date(grab("Registry Expiry Date", "Expiration Date", "expires", "paid-till"))),
        "status": re.findall(r"^\s*(?:Domain )?status\s*:\s*(\S+)", text, re.M | re.I),
        "nameservers": sorted({n.lower().rstrip(".") for n in
                               re.findall(r"^\s*(?:Name Server|nserver)\s*:\s*(\S+)", text, re.M | re.I)}),
        "registrar": grab("Registrar", "registrar"),
        "registrant_org": grab("Registrant Organization", "org", "organization"),
    }


def doh(rec: Recorder, name: str, rtype: str) -> list[str]:
    url = f"https://dns.google/resolve?name={urllib.parse.quote(name)}&type={rtype}"
    data = rec.json(f"dns-{name}-{rtype}.json", url)
    if data is None:  # fallback на Cloudflare
        url = f"https://cloudflare-dns.com/dns-query?name={urllib.parse.quote(name)}&type={rtype}"
        data = rec.json(f"dns-{name}-{rtype}-cf.json", url, {"Accept": "application/dns-json"})
    if not data:
        return []
    want = {"A": 1, "NS": 2, "MX": 15, "TXT": 16, "AAAA": 28}[rtype]
    return sorted(a["data"].strip('"') if rtype != "TXT" else a["data"].replace('" "', "").strip('"')
                  for a in data.get("Answer", []) if a.get("type") == want)


def collect_dns(rec: Recorder, domain: str) -> dict:
    out = {t: doh(rec, domain, t) for t in ("A", "AAAA", "NS", "MX", "TXT")}
    out["NS"] = [n.rstrip(".").lower() for n in out["NS"]]
    spf = [t for t in out["TXT"] if t.lower().startswith("v=spf1")]
    dmarc = [t for t in doh(rec, f"_dmarc.{domain}", "TXT") if t.lower().startswith("v=dmarc1")]
    policy = None
    if dmarc:
        m = re.search(r"\bp\s*=\s*(\w+)", dmarc[0], re.I)
        policy = m.group(1).lower() if m else None
    out["SPF"] = spf[0] if spf else None
    out["DMARC"] = dmarc[0] if dmarc else None
    out["DMARC_policy"] = policy
    # верифікаційні TXT часто показують, якими SaaS користується організація
    out["TXT_verifications"] = sorted({t.split("=")[0] for t in out["TXT"]
                                       if re.match(r"^[\w.-]+-(site-)?verification=|^MS=", t, re.I)})
    return out


def collect_ct(rec: Recorder, domain: str, pages: int) -> dict:
    """Certificate Transparency: crt.sh, при збої — CertSpotter."""
    certs: list[dict] = []
    source = None
    data = rec.json("ct-crtsh.json", f"https://crt.sh/?q=%25.{domain}&output=json", timeout=max(rec.timeout, 60))
    if isinstance(data, list) and data:
        source = "crt.sh"
        for c in data:
            certs.append({"not_before": c.get("not_before"), "issuer": c.get("issuer_name"),
                          "names": (c.get("name_value") or "").split("\n")})
    else:
        source = "certspotter"
        after = None
        for page in range(pages):
            url = (f"https://api.certspotter.com/v1/issuances?domain={domain}"
                   f"&include_subdomains=true&expand=dns_names&expand=issuer")
            if after:
                url += f"&after={after}"
            batch = rec.json(f"ct-certspotter-{page}.json", url)
            if not batch:
                break
            for c in batch:
                certs.append({"not_before": c.get("not_before"),
                              "issuer": (c.get("issuer") or {}).get("friendly_name") or (c.get("issuer") or {}).get("name"),
                              "names": c.get("dns_names", [])})
            after = batch[-1].get("id")
            time.sleep(1)
    if not certs:
        return {"source": source, "certificates": 0}
    dates = sorted(d for d in (parse_date(c["not_before"]) for c in certs) if d)
    names = sorted({n.lower().lstrip("*.") for c in certs for n in c["names"]
                    if n and n.lower().rstrip(".").endswith(domain)})
    issuers: dict[str, int] = {}
    for c in certs:
        key = str(c["issuer"])[:80]
        issuers[key] = issuers.get(key, 0) + 1
    return {
        "source": source,
        "certificates": len(certs),
        "first_seen": iso(dates[0]) if dates else None,
        "last_seen": iso(dates[-1]) if dates else None,
        "hostnames_count": len(names),
        "hostnames": names[:200],
        "top_issuers": sorted(issuers.items(), key=lambda kv: -kv[1])[:5],
        "partial": source == "certspotter" and len(certs) >= 100 * pages,
        # CertSpotter без ключа віддає лише чинні сертифікати → first_seen тут НЕ вік домену
        "history_complete": source == "crt.sh",
    }


def collect_wayback(rec: Recorder, domain: str) -> dict:
    base = (f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json"
            f"&fl=timestamp,original,statuscode&filter=!statuscode:5..")
    t = max(rec.timeout, 60)
    first = rec.json("wayback-first.json", base + "&limit=1", timeout=t)
    time.sleep(2)  # archive.org швидко віддає 429
    # limit=-1 по всьому індексу дуже повільний, тому шукаємо останній знімок лише за ~2 роки
    since = datetime.now(timezone.utc).year - 1
    last = rec.json("wayback-last.json", base + f"&from={since}&limit=-1", timeout=max(t, 90))

    def pick(rows):
        if rows and len(rows) > 1:
            ts = rows[1][0]
            return {"date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", "url": f"https://web.archive.org/web/{ts}/{rows[1][1]}"}
        return None

    return {"first_snapshot": pick(first), "last_snapshot": pick(last)}


def collect_gleif(rec: Recorder, company: str) -> list[dict]:
    q = urllib.parse.quote(company)
    data = rec.json("gleif.json", f"https://api.gleif.org/api/v1/lei-records?filter%5Bfulltext%5D={q}&page%5Bsize%5D=5")
    out = []
    for r in (data or {}).get("data", []):
        a = r.get("attributes", {})
        ent, reg = a.get("entity", {}), a.get("registration", {})
        addr = ent.get("legalAddress", {})
        out.append({
            "lei": a.get("lei"),
            "legal_name": (ent.get("legalName") or {}).get("name"),
            "other_names": [n.get("name") for n in ent.get("otherNames", [])][:3],
            "jurisdiction": ent.get("jurisdiction"),
            "registered_as": ent.get("registeredAs"),
            "entity_status": ent.get("status"),
            "lei_status": reg.get("status"),
            "legal_address": ", ".join(filter(None, [*(addr.get("addressLines") or []), addr.get("city"), addr.get("country")])),
            "url": f"https://search.gleif.org/#/record/{a.get('lei')}",
        })
    return out


# --------------------------------------------------------------------------- analysis

def signals(domain: str, r: dict) -> list[dict]:
    """Автоматичні сигнали. Це підказки для аналітика, а НЕ висновки."""
    s: list[dict] = []
    now = datetime.now(timezone.utc)

    def add(sev, code, text):
        s.append({"severity": sev, "code": code, "text": text})

    reg = r.get("registration") or {}
    if reg.get("registered") is False:
        add("high", "not-registered", "Домен НЕ зареєстровано (WHOIS: no match). Якщо його вказано в листі, рахунку "
                                      "чи рекламі, адреса вигадана або з помилкою; перевір написання")
        return s
    created = parse_date(reg.get("created"))
    if created:
        age = (now - created).days
        if age < 90:
            add("high", "young-domain", f"Домен зареєстровано {age} дн. тому — типово для фішингу/скаму")
        elif age < 365:
            add("medium", "young-domain", f"Домен молодший за рік ({age} дн.)")
    else:
        add("info", "no-created", "Дату реєстрації домену не отримано — перевір вручну")
    expires = parse_date(reg.get("expires"))
    if expires and (expires - now).days < 30:
        add("low", "expiring", f"Домен спливає {iso(expires)} — перевір, чи продовжується")
    bad = [st for st in reg.get("status", []) if re.search(r"hold|redemption|pendingdelete", st, re.I)]
    if bad:
        add("high", "registry-status", f"Проблемний статус у реєстрі: {', '.join(bad)}")

    dns = r.get("dns") or {}
    if dns and not dns.get("A") and not dns.get("AAAA"):
        add("medium", "no-a", "Домен не резолвиться (немає A/AAAA) — сайт не працює або припаркований")
    if dns and not dns.get("MX"):
        add("medium", "no-mx", "Немає MX: пошта на цьому домені не приймається — дивно для компанії з email на домені")
    if dns and dns.get("MX") is not None and not dns.get("SPF"):
        add("low", "no-spf", "Немає SPF — домен легше підробити у листах (знахідка для власника)")
    if dns and dns.get("DMARC_policy") in (None, "none"):
        add("low", "weak-dmarc", f"DMARC {'відсутній' if not dns.get('DMARC') else 'p=none'} — ризик спуфінгу від імені домену")

    wb = (r.get("wayback") or {}).get("first_snapshot")
    if wb and created:
        first = parse_date(wb["date"])
        if first and (created - first).days > 180:
            add("medium", "drop-catch", f"Перший знімок Wayback ({wb['date']}) раніший за поточну реєстрацію "
                                        f"({iso(created)}): домен, імовірно, перереєстровано — історія сайту "
                                        f"може належати попередньому власнику")
    elif r.get("wayback") is not None and not wb:
        add("info", "no-wayback", "Немає знімків у Wayback Machine — публічна історія сайту відсутня")

    ct = r.get("ct") or {}
    ct_first = parse_date(ct.get("first_seen"))
    if (ct.get("history_complete") and created and ct_first
            and (ct_first - created).days > 365 * 3 and (now - ct_first).days < 180):
        add("medium", "late-ct", "Перші сертифікати з'явились лише нещодавно, хоча домен старий — можлива зміна власника/призначення")
    return s


# --------------------------------------------------------------------------- report

def render_md(domain: str, r: dict) -> str:
    L = [f"# Технічний профіль домену `{domain}`", "",
         f"Згенеровано: {r['generated_utc']} (UTC) · скрипт `domain_recon.py` · тільки пасивні джерела", ""]
    reg = r.get("registration")
    if reg:
        L += ["## Реєстрація", f"- Метод: {reg.get('method')}",
              f"- Створено: {reg.get('created') or '—'} · оновлено: {reg.get('updated') or '—'} · спливає: {reg.get('expires') or '—'}",
              f"- Реєстратор: {reg.get('registrar') or '—'}",
              f"- Реєстрант (організація): {reg.get('registrant_org') or 'приховано / не вказано'}",
              f"- Статус: {', '.join(reg.get('status') or []) or '—'}",
              f"- NS: {', '.join(reg.get('nameservers') or []) or '—'}", ""]
    dns = r.get("dns")
    if dns:
        L += ["## DNS (DoH)", f"- A: {', '.join(dns['A']) or '—'}", f"- AAAA: {', '.join(dns['AAAA']) or '—'}",
              f"- MX: {', '.join(dns['MX']) or '—'}", f"- NS: {', '.join(dns['NS']) or '—'}",
              f"- SPF: `{dns['SPF']}`" if dns["SPF"] else "- SPF: —",
              f"- DMARC: `{dns['DMARC']}`" if dns["DMARC"] else "- DMARC: —",
              f"- Верифікаційні TXT (SaaS): {', '.join(dns['TXT_verifications']) or '—'}", ""]
    ct = r.get("ct")
    if ct:
        L += ["## Certificate Transparency", f"- Джерело: {ct.get('source')} · сертифікатів: {ct.get('certificates')}"
              + (" (неповно, перші сторінки)" if ct.get("partial") else ""),
              f"- Перший сертифікат: {ct.get('first_seen') or '—'} · останній: {ct.get('last_seen') or '—'}"
              + ("" if ct.get("history_complete") else " (лише чинні сертифікати — НЕ вік домену)"),
              f"- Унікальних хостів: {ct.get('hostnames_count', 0)}"
              + (f" — напр.: {', '.join(ct.get('hostnames', [])[:15])}" if ct.get("hostnames") else ""),
              f"- Видавці: {'; '.join(f'{k} ×{v}' for k, v in ct.get('top_issuers', [])) or '—'}", ""]
    wb = r.get("wayback")
    if wb is not None:
        f, l = wb.get("first_snapshot"), wb.get("last_snapshot")
        L += ["## Wayback Machine",
              f"- Перший знімок: {f['date'] + ' — ' + f['url'] if f else '—'}",
              f"- Останній знімок: {l['date'] + ' — ' + l['url'] if l else '— (за останні ~2 роки не знайдено)'}", ""]
    if r.get("gleif") is not None:
        L += ["## GLEIF (LEI)"]
        L += [f"- {g['legal_name']} · LEI {g['lei']} · {g['jurisdiction']} · рег. № {g['registered_as'] or '—'} · "
              f"entity {g['entity_status']} / LEI {g['lei_status']} · {g['legal_address']} · {g['url']}"
              for g in r["gleif"]] or ["- Збігів не знайдено (це нормально для більшості МСБ)"]
        L += [""]
    L += ["## Автоматичні сигнали (перевір вручну — це не висновки)"]
    L += [f"- [{x['severity'].upper()}] {x['text']}" for x in r["signals"]] or ["- Немає"]
    if r["errors"]:
        L += ["", "## Помилки джерел (зазнач у розділі «Прогалини»)"]
        L += [f"- {e['source']}: {e['error']}" for e in r["errors"]]
    L += ["", "## Provenance", "Сирі відповіді — у `raw/`, хеші — у `raw/SHA256SUMS`."]
    return "\n".join(L) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # консоль Windows за замовчуванням не UTF-8
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Пасивний технічний профіль домену (company-domain-check)")
    ap.add_argument("domain", help="домен або URL")
    ap.add_argument("--company", help="юридична назва для пошуку LEI у GLEIF")
    ap.add_argument("--out", help="тека результатів (за замовчуванням ./dd-<domain>)")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--ct-pages", type=int, default=3, help="скільки сторінок CertSpotter читати")
    ap.add_argument("--skip", default="", help=f"через кому: {','.join(SOURCES)}")
    args = ap.parse_args()

    domain = normalize_domain(args.domain)
    skip = {x.strip() for x in args.skip.split(",") if x.strip()}
    out_dir = Path(args.out or f"dd-{domain}")
    rec = Recorder(out_dir, args.timeout)
    result: dict = {"domain": domain, "generated_utc": utc_now(), "tool": "domain_recon.py 1.0"}

    steps = [("rdap", "registration", lambda: collect_rdap(rec, domain)),
             ("dns", "dns", lambda: collect_dns(rec, domain)),
             ("ct", "ct", lambda: collect_ct(rec, domain, args.ct_pages)),
             ("wayback", "wayback", lambda: collect_wayback(rec, domain))]
    if args.company:
        steps.append(("gleif", "gleif", lambda: collect_gleif(rec, args.company)))
    for key, field, fn in steps:
        if key in skip:
            continue
        print(f"[{utc_now()}] {key}…", file=sys.stderr, flush=True)
        try:
            result[field] = fn()
        except Exception as e:  # одне джерело не валить увесь прогін
            rec.errors.append({"source": key, "error": f"{type(e).__name__}: {e}"})

    result["signals"] = signals(domain, result)
    result["errors"] = rec.errors
    result["provenance"] = rec.provenance

    (out_dir / "recon.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "raw" / "SHA256SUMS").write_text(
        "".join(f"{p['sha256']}  {p['file'][4:]}\n" for p in rec.provenance), encoding="utf-8")
    md = render_md(domain, result)
    (out_dir / "recon.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"→ {out_dir / 'recon.json'}, {out_dir / 'recon.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
