# Технічний профіль домену `novaposhta.ua`

Згенеровано: 2026-10-07T18:04:50Z (UTC) · скрипт `domain_recon.py` · тільки пасивні джерела

## Реєстрація
- Метод: rdap
- Створено: 2010-10-29 · оновлено: 2025-10-27 · спливає: 2026-10-29
- Реєстратор: Internet Invest LLC
- Реєстрант (організація): ТОВ 'НОВА ПОШТА'
- Статус: active
- NS: nsa1.srv53.org, nsa2.srv53.com, nsa3.srv53.net, nsb1.srv53.com, nsb1.srv53.org, nsb4.srv53.net, nsc2.srv53.org, nsc3.srv53.net, nsc4.srv53.com, nsd3.srv53.net, nsd4.srv53.com, nsd4.srv53.org

## DNS (DoH)
- A: 34.128.190.243
- AAAA: —
- MX: 1 smtp.google.com., 3 aspmx.l.google.com.
- NS: nsa1.srv53.org, nsa2.srv53.com, nsa3.srv53.net, nsb1.srv53.com, nsb1.srv53.org, nsb4.srv53.net, nsc2.srv53.org, nsc3.srv53.net, nsc4.srv53.com, nsd3.srv53.net, nsd4.srv53.com, nsd4.srv53.org
- SPF: `v=spf1 +mx ip4:91.240.48.0/22 include:_spf.google.com include:spf2.esputnik.com ~all`
- DMARC: `v=DMARC1; p=none; rua=mailto:postmaster@novaposhta.ua`
- Верифікаційні TXT (SaaS): MS, apple-domain-verification, atlassian-domain-verification, cisco-ci-domain-verification, dtm-domain-verification, esputnik-verification, globalsign-domain-verification, google-site-verification, teamviewer-sso-verification

## Certificate Transparency
- Джерело: certspotter · сертифікатів: 122
- Перший сертифікат: 2025-10-24 · останній: 2026-10-05 (лише чинні сертифікати — НЕ вік домену)
- Унікальних хостів: 29 — напр.: api-cdn.novaposhta.ua, api.novaposhta.ua, api2.novaposhta.ua, app.novaposhta.ua, application-stage.novaposhta.ua, application.novaposhta.ua, auth-cdn.novaposhta.ua, cdn.novaposhta.ua, courier.novaposhta.ua, developers.novaposhta.ua, humanitarian.novaposhta.ua, knowledge-base.novaposhta.ua, my.novaposhta.ua, new.novaposhta.ua, novadoc.novaposhta.ua
- Видавці: Google Trust Services ×120; DigiCert ×2

## Wayback Machine
- Перший знімок: 2010-10-29 — https://web.archive.org/web/20101029181827/http://www.novaposhta.ua:80/
- Останній знімок: 2026-10-04 — https://web.archive.org/web/20261004190735/https://novaposhta.ua/

## GLEIF (LEI)
- ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ "НОВА ПОШТА ГЛОБАЛ" · LEI 254900WPK1120W91L874 · UA · рег. № 38130410 · entity ACTIVE / LEI LAPSED · Stolichne shose, Building 103, Kyiv, UA · https://search.gleif.org/#/record/254900WPK1120W91L874

## Автоматичні сигнали (перевір вручну — це не висновки)
- [LOW] Домен спливає 2026-10-29 — перевір, чи продовжується
- [LOW] DMARC p=none — ризик спуфінгу від імені домену

## Помилки джерел (зазнач у розділі «Прогалини»)
- https://crt.sh/?q=%25.novaposhta.ua&output=json: TimeoutError: The read operation timed out

## Provenance
Сирі відповіді — у `raw/`, хеші — у `raw/SHA256SUMS`.
