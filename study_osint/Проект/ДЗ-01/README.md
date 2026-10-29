# Домашнє завдання: локальний AI-агент + skills для OSINT

**Агент:** Claude Code 2.1.210 (Anthropic): desktop-застосунок Claude (вкладка Code) + CLI `claude`.
**Підключені skill-репозиторії (два):**
- [smixs/osint-skill](https://github.com/smixs/osint-skill), коміт `94f382e` (v3.2, early beta, MIT) — підключено як активний skill у `.claude/skills/osint/`.
- [elementalsouls/Claude-OSINT](https://github.com/elementalsouls/Claude-OSINT), коміт `13d9204` (2026-08-31, MIT + CC-BY-4.0) — наступальний recon-арсенал; збережено як **незмінну довідкову копію** в `homework/reference/claude-osint/`, методологію перенесено в мій skill (пояснення нижче і в [`reference/README.md`](reference/README.md)).

**Власний skill:** [`company-domain-check`](../Скиллы/company-domain-check/SKILL.md): перевірка компанії/домену → due diligence memo. Спирається на методологію **обох** репозиторіїв у захисній, discover-only рамці.

## Зміст пакета

```
study_osint/
├── .claude/skills/                      ← звідси Claude Code автоматично підхоплює skills проєкту
│   ├── osint/                           ← smixs/osint-skill (скопійовано з репозиторію без змін)
│   └── company-domain-check/            ← ВЛАСНИЙ SKILL (на базі обох репо)
│       ├── SKILL.md                     ← інструкція для агента (frontmatter + 8 кроків)
│       ├── scripts/domain_recon.py      ← пасивний технічний профіль домену (stdlib Python)
│       ├── references/sources.md        ← каталог джерел: UA та міжнародні реєстри, санкції, суди
│       ├── references/red-flags.md      ← каталог red flags з критичністю та хибними спрацюваннями
│       ├── references/tradecraft.md     ← граф активів, finding-картки, гігієна доказів, заметність (з claude-osint)
│       ├── references/attack-surface.md ← трек поверхні атаки «тільки обнаруження» (з claude-osint)
│       └── assets/memo-template.md      ← шаблон due diligence memo
└── homework/
    ├── README.md                        ← ця нотатка
    ├── logs/01…06                       ← логи встановлення, діагностики, виявлення та запуску
    ├── reference/                       ← довідкові копії (НЕ підключені як активні skills)
    │   ├── README.md                    ← що взято в роботу, що свідомо лишилось поза рамками
    │   └── claude-osint/                ← elementalsouls/Claude-OSINT, незмінна копія + .VENDOR_INFO
    └── example/dd-novaposhta.ua/        ← результат реального прогону skill
        ├── memo.md                      ← due diligence memo
        ├── recon.md / recon.json        ← вивід domain_recon.py
        └── raw/ + raw/SHA256SUMS        ← сирі відповіді джерел із хешами (provenance)
```

## 1. Середовище

| | |
|---|---|
| ОС | Windows 11 Pro, build 10.0.26300, x64 |
| Спосіб запуску | Claude desktop → вкладка **Code** (робоча тека `D:\!Projects\study_osint`); CLI `claude` (`~/.local/bin/claude`) для headless-перевірки |
| Модель | Opus 5.5 (основна сесія), Haiku 4.5 (headless-перевірка) |
| Shell | Git Bash 5.2.26 (MSYS2), PowerShell 5.1 |
| Залежності | Git 2.45.1, Python 3.14.7, Node.js 22.23.1, curl 8.7.1. `jq` відсутній |
| Мережа / API | Ключів платних API немає. Власний skill працює лише з безкоштовними джерелами без ключів: RDAP, WHOIS, DNS-over-HTTPS, CertSpotter / crt.sh, Wayback CDX, GLEIF |

Деталі у [`logs/01-environment.log`](logs/01-environment.log).

## 2. Підключення готових skill-репозиторіїв

**Репо №1 — smixs/osint-skill** (підключено як активний skill):

```bash
git clone --depth 1 https://github.com/smixs/osint-skill.git
cp -r osint-skill/osint .claude/skills/osint          # project scope; варіант для всіх проєктів: ~/.claude/skills/osint
bash .claude/skills/osint/scripts/diagnose.sh          # Phase 0 skill: самодіагностика
```

**Репо №2 — elementalsouls/Claude-OSINT** (підключено як довідкова копія):

```bash
git clone --depth 1 https://github.com/elementalsouls/Claude-OSINT.git
cp -r Claude-OSINT homework/reference/claude-osint     # НЕ в .claude/skills/ — див. нижче «чому копія»
```

**Чому репо №2 — копія, а не активний skill.** Це наступальний (red-team / bug-bounty) арсенал: 80
secret-регексів, 9 валідаторів кредів, pre-auth user-enumeration oracle, bruteforce-wordlists,
attack-path payloads. Якби його 8 skills лежали в `.claude/skills/`, агент міг би автоматично тригерити
`offensive-osint`. Тому репо збережено як **незмінну довідку для вивчення методології**, а в робочий skill
`company-domain-check` перенесено лише методологію й дисципліну в захисній, discover-only рамці. Повний
перелік «що взято / що свідомо лишилось поза рамками» — у [`reference/README.md`](reference/README.md). Це
повторює рішення, вже зафіксоване в проєкті для верхньої теки `skills/` (російськомовна адаптація).

Що перевірено (контрольний список із завдання) — для **обох** репо:

| Перевірка | Результат | Доказ |
|---|---|---|
| Агент бачить skill | ✅ `osint` і `company-domain-check` є в списку `skills` події `system/init`; `company-domain-check` став видимим і в поточній сесії після створення | [`logs/04`](logs/04-skill-discovery.log) |
| Структура файлів зчитується | ✅ smixs: `SKILL.md` + `references/` (4) + `assets/` (1) + `scripts/` (14). claude-osint: 8 skills, `docs/`, `examples/` (87 файлів) | [`logs/02`](logs/02-install-osint-skill.log) |
| Допоміжні матеріали, шаблони, скрипти доступні | ✅ `diagnose.sh` бачить `run_actor.js`, `run-actor.sh`, node 22 | [`logs/03`](logs/03-osint-diagnose.log) |
| Базова логіка запускається | ✅ Phase 0 (`diagnose.sh`) відпрацьовує й будує карту можливостей. ⚠️ Phases 1–2 потребують платних API-ключів, яких немає | [`logs/03`](logs/03-osint-diagnose.log) |

Виявлені обмеження оригінального skill на Windows:
- **`python3` тут є заглушкою Microsoft Store** («Python was not found…»). Через це `perplexity.sh`, `exa.sh`, `tavily.sh`, `brightdata.sh`
  не розберуть JSON навіть із ключами. Рішення: вимкнути App execution alias для `python3` або створити аліас на `python`.
- `first-volley.sh` використовує `tail --pid` (є в Git Bash, але немає на macOS), а `diagnose.sh` перевіряє `jq`.
- SKILL.md написано під OpenClaw (`sessions_spawn`, `web_search`, `web_fetch`). Claude Code зіставляє це зі своїми
  інструментами (Agent/Task, WebSearch, WebFetch) сам, бо SKILL.md є текстом для моделі, а не кодом.
- Автор сам попереджає про **shell injection**: користувацький ввід підставляється в JSON без екранування.

## 3. Як працює skill-репозиторій (механіка)

**Коротко (5–10 речень, як у завданні).** Skill — це тека з файлом `SKILL.md`: YAML-frontmatter (`name`,
`description`) плюс Markdown-інструкція для моделі, а поруч допоміжні `references/`, `assets/`, `scripts/`. Під час
старту сесії Claude Code сканує `~/.claude/skills/*/SKILL.md` і `.claude/skills/*/SKILL.md` проєкту та додає в контекст
моделі **лише `name` + `description`** кожного skill (це видно в логу 04: 135 skills у списку, і жоден не завантажено цілком).
Коли запит користувача збігається з тригерами з `description` («osint», «пробей», «due diligence»…) або користувач
викликає `/osint`, агент через інструмент **Skill** завантажує повне тіло `SKILL.md`. Claude Code при цьому додає рядок
«Base directory for this skill: …», підставляє `$ARGUMENTS` і `${CLAUDE_SKILL_DIR}` і може застосувати `allowed-tools`
із frontmatter. Далі модель виконує інструкцію як робочий процес: маршрутизатор фаз визначає точку входу, а `SKILL.md` прямо
каже, *коли* читати `references/*.md` («ONLY at this phase») і які `scripts/*.sh` запускати через Bash. Скрипти виконуються
поза контекстом моделі, тому в контекст потрапляє тільки їхній вивід, а не код. Це **прогресивне розкриття** (progressive
disclosure): метадані завжди, інструкція за потреби, довідники та скрипти лише на конкретній фазі, тож десятки skills не
забивають контекстне вікно. Практичний сенс підходу: експертна методика (фази, ескалація від дешевого до дорогого, грейди
A/B/C/D, критерії зупинки) пакується в переносний текстовий модуль, який однаково працює в Claude Code, OpenClaw, Codex
й OpenCode без зміни коду агента.

**Розгорнуто, за пунктами завдання:**

1. **Як агент «бачить» skill.** Три рівні завантаження:
   ① метадані з frontmatter (завжди, ~100 токенів на skill) → ② тіло `SKILL.md` (після виклику Skill або `/name`) →
   ③ `references/`, `assets/`, вивід `scripts/` (тільки коли інструкція каже). Тека `.claude/skills/` — project scope
   (бачать усі, хто відкриває проєкт), `~/.claude/skills/` — user scope. Список skills формується **на старті сесії**:
   desktop-сесія, відкрита до появи `.claude/skills`, нових skills не побачила (`Unknown skill`), а новий процес
   `claude -p` побачив обидва ([`logs/04`](logs/04-skill-discovery.log), [`logs/05`](logs/05-demo-run-trace.log)).
2. **Роль `SKILL.md`.** Frontmatter — це «вітрина» для маршрутизації: `description` одночасно пояснює, що вміє skill,
   перелічує тригерні фрази й задає межі (`NOT for: company/product research…`). Від якості `description` залежить, чи
   агент взагалі викличе skill. Тіло — алгоритм: Phase Router, рівні ескалації, Swarm Mode, правила верифікації,
   формула Depth Score, критерії зупинки, антипатерни.
3. **Інші файли.** `references/tools.md` (каталог 55+ Apify-акторів), `platforms.md` (URL-патерни соцмереж),
   `content-extraction.md` (YouTube/подкасти), `psychoprofile.md` (MBTI/Big Five), `assets/dossier-template.md` (формат
   досьє), `scripts/` (обгортки над Perplexity, Exa, Tavily, Jina, Parallel, Apify, Bright Data, `first-volley.sh` для
   паралельного пошуку, `merge-volley.sh` для дедуплікації, `mcp-client.py` як MCP-клієнт для Bright Data).
4. **Логіка роботи.** Phase 0 самодіагностика → 1 seed-пошук усіма рушіями паралельно → 1.5 «внутрішня розвідка»
   (Telegram, пошта, CRM) → 2 витяг із платформ → 3 перехресна перевірка й грейди A–D → 4 психопрофіль →
   5 рекурсивна оцінка повноти (9 обов'язкових перевірок + зважений Depth Score, ≤3 цикли, зупинка на плато) →
   6 досьє за шаблоном. Наскрізні правила: ескалація від дешевого ($0) до дорогого (≤$0.50 без питання), рій
   субагентів, fallback замість повторів, rate limiting.
5. **Що потрібно для повноцінної роботи.** CLI: bash, curl, python3, jq, Node.js 18+ (опційно mcporter, mcpc). API-ключі
   в env: `PERPLEXITY_API_KEY`, `EXA_API_KEY`, `TAVILY_API_KEY`, `JINA_API_KEY`, `PARALLEL_API_KEY`, `APIFY_API_TOKEN`,
   `BRIGHTDATA_MCP_URL` (потрібен хоча б один пошуковий). Для фази 1.5: `tg.py`, `himalaya`, vault/CRM. Від агента:
   Bash, вебпошук/fetch, субагенти. У цьому середовищі без ключів працює лише Phase 0 і пошук вбудованими WebSearch/WebFetch.

**Два стилі `SKILL.md` на прикладі обох репо.** `smixs/osint-skill` — один skill з мінімальним frontmatter
(`name`, `description`) і одним великим тілом-конвеєром. `claude-osint` — **бібліотека з 8 skills**, кожен із
багатшим frontmatter (`version`, `triggers`, `sources`), де `osint-methodology` («як думати») відокремлено від
`offensive-osint` («що брати в руки»), а решта 6 — тематична глибина (org-attack-surface, email-domain-security,
cloud-saas-exposure, identity-provider-recon тощо). Для агента механіка однакова: він однаково сканує обидва набори
й бачить лише метадані, доки skill не викликано. Різниця лише в тому, що бібліотека з багатьох skills тонше
маршрутизує запит за `triggers`, а монолітний skill усе тримає всередині одного тіла.

**Етичне зауваження.** Обидва репо наступальні за духом: `osint-skill` — досьє на **приватних осіб** (психопрофіль,
«точки входу», аналіз особистого листування, обхід CAPTCHA/authwall через Bright Data); `claude-osint` — зовнішня
red-team розвідка (secret-регекси, валідатори кредів, user-enum, перебір). Для навчання я взяв із них лише
**методологію й дисципліну** і переосмислив її в захисній, discover-only рамці; наступальні компоненти не запускав і
не вбудовував у робочий skill. Власний skill свідомо зроблено для **організацій**, із жорсткими межами (Крок 0).

## 4. Власний skill: `company-domain-check`

**Задача:** «Чи безпечно мати справу з цією компанією / довіряти цьому домену, і які ризики?» (перевірка
контрагента, vendor check, підозрілий сайт чи лист). Результат: due diligence memo з рівнем ризику 🟩/🟧/🟥 і рекомендацією.

**Чому ця тема.** Оригінальний `osint` прямо виключає `company/product research without a named person`. Мій skill
закриває цю нішу й зводить найкращі патерни **обох** репо на перевірку організацій.

Перенесено зі **smixs/osint-skill** (конвеєр і верифікація):

| Патерн | Як реалізовано в `company-domain-check` |
|---|---|
| Phase Router | Режими `quick` / `standard` з різним набором кроків |
| Ескалація «дешеве → дороге» | Крок 1 — безкоштовний пасивний скрипт, далі реєстри, далі медіа |
| Грейди A/B/C/D + cross-reference | Таблиця фактів; заяви компанії мають позначку «заявлено компанією», доки їх не підтвердить реєстр |
| Name collision check | Ідентифікація **за кодом**, а не за назвою; розв'язання тезок |
| Completeness check | Чекліст самоперевірки + правило рівня ризику |

Перенесено з **elementalsouls/claude-osint** (дисципліна, у захисній рамці — `references/tradecraft.md`, `attack-surface.md`):

| Патерн | Як реалізовано |
|---|---|
| Граф типізованих активів | Вузли `<тип>:<значення>`, dedup за ключем, ребра лише за правилом трьох (Крок 5) |
| Finding-картка: дві осі | **Критичність × достовірність** як незалежні осі (Крок 6, red-flags.md) |
| Правило трьох для атрибуції | Зв'язок домен ↔ юрособа: ≥3 слабкі АБО 1 сильний + 1 слабкий сигнал |
| Гігієна доказів + chain of custody | `domain_recon.py` зберігає URL + UTC + SHA-256; артефакт незмінний |
| Заметність + лестниця відступлення | Усі джерела рівня Low; на `429`/капчу — відступ, а не обхід |
| Стійкість джерел (union) | crt.sh→CertSpotter, Google→Cloudflare DoH, RDAP→WHOIS; збій → у «Прогалини» |
| Бюджет часу / профіль | Фіксується до збору; умови аборту |
| Трек «тільки обнаруження» | seed → розширення → збагачення → аналіз exposure → звіт; активна валідація поза межами |

**Чого немає в жодному оригіналі (додано в моєму skill):**
- **Gate меж (Крок 0):** тільки організації; посадові особи лише в ролі; discover-only; без обходу захисту.
- **Автоматичні сигнали-евристики** у скрипті: не зареєстрований домен, вік < 90 дн., drop-catch (Wayback
  старший за реєстрацію), hold-статуси, MX/SPF/DMARC. Подано як підказки, а не висновки.
- **Український контекст:** ЄДР, ДПС, ЄДРСР, АСВП, Prozorro, санкції РНБО, War & Sanctions, зв'язки з державою-агресором.
- **Без залежностей і ключів:** скрипт використовує лише stdlib Python і не робить жодного запиту до серверів самої цілі.

**Що з claude-osint свідомо НЕ перенесено:** secret-регекси та `secret_scan.py`, wordlists і перебір, валідатори
кредів, user-enumeration, активні скани/фаззинг/nuclei, breach×identity для підбору паролів, attack-path payloads.
Усе це лишилось тільки в довідковій копії `reference/claude-osint/`. Обґрунтування — `references/attack-surface.md`.

Frontmatter використовує механіку Claude Code: `argument-hint` (підказка для `/company-domain-check`),
`allowed-tools` (WebSearch/WebFetch/Read без додаткових підтверджень), `$ARGUMENTS` і `${CLAUDE_SKILL_DIR}`
(шлях до скрипта не залежить від місця встановлення; підстановку перевірено в бінарнику Claude Code 2.1.210).

## 5. Доказ запуску

| Лог | Що показує |
|---|---|
| [`01-environment.log`](logs/01-environment.log) | ОС, версії Claude Code / Git / Python / Node, вміст `.claude/skills` |
| [`02-install-osint-skill.log`](logs/02-install-osint-skill.log) | Клонування smixs/osint-skill (коміт), копіювання, дерево файлів, frontmatter |
| [`03-osint-diagnose.log`](logs/03-osint-diagnose.log) | Phase 0 оригінального skill (`diagnose.sh`) + поведінка скрипта без ключа |
| [`04-skill-discovery.log`](logs/04-skill-discovery.log) | `claude -p … --output-format stream-json`: подія `system/init` містить `skills: ['company-domain-check', 'osint']` |
| [`05-demo-run-trace.log`](logs/05-demo-run-trace.log) | Трасування прогону власного skill: кроки 0–7, інструменти, джерела |
| [`06-domain-recon-run.log`](logs/06-domain-recon-run.log) | Повний вивід `domain_recon.py` для `novaposhta.ua` |

**Результат прогону:** [`example/dd-novaposhta.ua/memo.md`](example/dd-novaposhta.ua/memo.md). Ціль обрано як
«позитивний контроль»: велика легітимна компанія. Skill коректно дав 🟩. Водночас він показав, що вміє ловити тонкощі:
GLEIF за назвою «Nova Poshta» повернув **іншу юрособу групи** (НОВА ПОШТА ГЛОБАЛ, код 38130410). OpenSanctions для
материнської компанії дав два **хибні fuzzy-збіги** («Quicko», польський список). Агрегатор показав двозначне «9 sanction
lists». DMARC `p=none` на тлі масового фішингу від імені бренду записано як знахідку для власника, а не як red flag
компанії. Прогалини (РНБО напряму, роль у виконавчих провадженнях, `403` Opendatabot) названо чесно.

**Чесні застереження:**
- Headless-процес `claude -p` виявив обидва skills, але сама модель там не відповіла: OAuth-сесія окремого CLI
  прострочена (`Failed to authenticate`). Виявлення skills відбувається локально на етапі init, тому доказ коректний.
- Demo-прогін для `novaposhta.ua` зроблено ще до того, як skill було дороблено під обидва репо: desktop-сесія
  стартувала до появи `.claude/skills`, тому ранній `Skill(company-domain-check)` повертав `Unknown skill`, і прогін
  виконано вручну за `SKILL.md` (так само працюють агенти без нативної підтримки skills, напр. Codex). Після створення
  файлів skill `company-domain-check` став видимим через інструмент Skill уже в тій самій сесії — тобто поточна редакція
  (на базі обох репо) підхоплюється агентом штатно. Memo відображає методологію до розширення, але висновок не змінюється.

**Скріншоти** (`homework/screenshots/`, робляться вручну):
1. Нова сесія Claude Code у цій теці → ввести `/` → у списку видно `company-domain-check` і `osint` (з `argument-hint`).
2. `/company-domain-check example.com quick` → видно рядок «Base directory for this skill…» і запуск `domain_recon.py`.

## Ліцензії та атрибуція

- `smixs/osint-skill`: MIT (скопійовано без змін у `.claude/skills/osint/`).
- `elementalsouls/Claude-OSINT`: MIT (код) + CC-BY-4.0 (контент), © 2026 Sachin Sharma. Незмінна копія —
  у `homework/reference/claude-osint/`. Адаптовано методологію (CC-BY: *«Адаптовано з Claude-OSINT (Sachin Sharma),
  CC BY 4.0»*) у `company-domain-check/references/tradecraft.md` і `attack-surface.md`.
- `company-domain-check`: власна розробка для цього завдання. Конвеєр, грейди A/B/C/D та структуру
  `scripts/`/`references/`/`assets/` запозичено зі smixs/osint-skill; граф активів, finding-картки, гігієну доказів,
  заметність і трек «тільки обнаруження» — з elementalsouls/claude-osint (обидва — у захисній, discover-only рамці).
