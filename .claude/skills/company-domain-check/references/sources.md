# Джерела для company-domain-check

Усі джерела публічні. «Безкошт.» означає, що базовий пошук доступний без оплати й реєстрації
(умови можуть змінюватись: якщо щось недоступне, зафіксуй це в «Прогалинах»). Пріоритет: офіційний
реєстр → агрегатор → медіа.

## 1. Технічний профіль домену (Крок 1; скрипт робить це автоматично)

| Що | Джерело | Нотатки |
|---|---|---|
| Реєстрація домену | `https://rdap.org/domain/<d>` · `https://lookup.icann.org/` | RDAP замінює WHOIS; для `.ua` реєстр hostmaster.ua часто показує організацію-реєстранта |
| WHOIS (fallback) | порт 43: `whois.iana.org` → referral (`whois.ua`, `whois.verisign-grs.com`…) | Для зон без RDAP |
| DNS | `https://dns.google/resolve?name=<d>&type=MX` · `https://cloudflare-dns.com/dns-query` (`Accept: application/dns-json`) | A/AAAA/NS/MX/TXT, `_dmarc.<d>` |
| Certificate Transparency | `https://crt.sh/?q=%25.<d>&output=json` · `https://api.certspotter.com/v1/issuances?domain=<d>&include_subdomains=true&expand=dns_names` | crt.sh має повну історію, але часто віддає 502. CertSpotter без ключа показує лише чинні сертифікати |
| Історія сайту | `https://web.archive.org/cdx/search/cdx?url=<d>&output=json&limit=1` · `https://web.archive.org/web/*/<d>` | Перший знімок дає нижню межу віку. Порівнюй старі «Про нас», контакти, реквізити |
| Репутація домену | VirusTotal (`https://www.virustotal.com/gui/domain/<d>`) · Google Safe Browsing (`https://transparencyreport.google.com/safe-browsing/search?url=<d>`) · URLhaus (`https://urlhaus.abuse.ch/browse/`) | Лише читання наявних звітів |
| Наявні скани сторінки | urlscan.io: тільки **пошук** наявних сканів | Не надсилай нові скани без потреби: вони публічні й можуть попередити ціль |

## 2. Юрособа: Україна

| Що | Джерело | Нотатки |
|---|---|---|
| ЄДР (юрособи, ФОП, КБВ) | `https://usr.minjust.gov.ua/` | Офіційний, безкошт. Статус, керівник, засновники, КБВ, адреса, КВЕД. Грейд A |
| Агрегатори ЄДР + аналітика | Opendatabot `https://opendatabot.ua/`, YouControl `https://youcontrol.com.ua/`, Clarity Project `https://clarity-project.info/` | Freemium. Позначки «масова адреса», «масовий керівник», історія змін, зв'язки |
| Податки | Відкрита частина Е-кабінету ДПС `https://cabinet.tax.gov.ua/registers` | Реєстр платників ПДВ, анулювання, податковий борг |
| Суди | ЄДРСР `https://reyestr.court.gov.ua/` · стан справ `https://court.gov.ua/fair/` | Шукай за кодом ЄДРПОУ та назвою. Дивись роль (позивач/відповідач) і категорію |
| Виконавчі провадження | АСВП `https://asvpweb.minjust.gov.ua/` · Єдиний реєстр боржників `https://erb.minjust.gov.ua/` | Борги та стягнення |
| Публічні закупівлі | Prozorro `https://prozorro.gov.ua/` · DoZorro `https://dozorro.org/` | Для B2B: реальна діяльність, дискваліфікації, скарги |
| Ліцензії (фінсектор тощо) | Реєстри НБУ та НКЦПФР | Фінпослуги без ліцензії = critical red flag |

## 3. Юрособа: міжнародні реєстри

| Що | Джерело | Нотатки |
|---|---|---|
| LEI | GLEIF `https://search.gleif.org/` (API: `https://api.gleif.org/api/v1/lei-records?filter[fulltext]=<name>`) | Глобальний ідентифікатор, безкошт. Статус LEI `LAPSED` = запис не оновлюється (не обов'язково проблема) |
| Мультиреєстр | OpenCorporates `https://opencorporates.com/` | ~140 юрисдикцій. Перевір дату оновлення запису |
| Велика Британія | Companies House `https://find-and-update.company-information.service.gov.uk/` | Filing history, PSC (бенефіціари), прострочена звітність, зміни директорів |
| США | SEC EDGAR `https://www.sec.gov/edgar/search/` · реєстри штатів (Secretary of State) | Публічні компанії: звіти. Приватні: реєстр штату |
| ЄС | e-Justice «Find a company» (BRIS) `https://e-justice.europa.eu/` | Шлюз до національних реєстрів |
| Офшорні структури | ICIJ Offshore Leaks `https://offshoreleaks.icij.org/` | Тільки як зачіпка (D/C), не як доказ |

## 4. Санкції, PEP, ризикові зв'язки

| Що | Джерело | Нотатки |
|---|---|---|
| Агрегатор санкцій і PEP | OpenSanctions `https://www.opensanctions.org/` | Веб-пошук безкоштовний, API потребує ключа (безкошт. для ЗМІ/НГО/академії). ООН, ЄС, OFAC, UK, UA та ін. API: `/search` → id, `/entities/{id}?nested=true` → зв'язки, `/match` → score. **Score — кандидат, не вердикт** (0.78 без дати народження — лише кандидат) |
| Санкції України | Державний реєстр санкцій РНБО `https://drs.nsdc.gov.ua/` | Офіційний |
| Особи й компанії, причетні до агресії РФ | War & Sanctions `https://war-sanctions.gur.gov.ua/` | Включно з кандидатами на санкції |
| США | OFAC Sanctions Search `https://sanctionssearch.ofac.treas.gov/` | Fuzzy-пошук із відсотком збігу |
| ЄС | EU Sanctions Map `https://www.sanctionsmap.eu/` | |
| Велика Британія | UK Sanctions List (gov.uk) | |
| Корупційні правопорушення | Реєстр НАЗК `https://corruptinfo.nazk.gov.ua/` | Для керівників як посадових осіб |

## 5. Репутація та adverse media

- WebSearch з операторами: `"<назва>"`, `"<код ЄДРПОУ>"`, `site:<медіа>`, `-site:<домен компанії>` (прибрати PR самої компанії).
- Якісні медіа та розслідувальні редакції (для UA: Bihus.Info, Слідство.Інфо, Наші гроші, Economichna Pravda, Forbes Ukraine): грейд B.
- Відгуки (Google Maps, Otzyvua, Trustpilot), форуми, Telegram-канали: грейд C/D. Шукай **патерни** скарг, не окремі відгуки.
- ScamAdviser і подібні «trust score»: автоматичні оцінки (D). Тільки як привід перевірити глибше.

## 6. Етика й обмеження джерел

- Поважай `robots.txt` та умови використання. Роби паузи між запитами; при 429 чекай або бери інше джерело.
- Не використовуй бази витоків, «пробивні» боти й платні дампи персональних даних: це поза межами skill.
- Дані про фізичних осіб (керівники, КБВ) бери тільки з офіційних реєстрів і тільки в ролі посадової особи.
