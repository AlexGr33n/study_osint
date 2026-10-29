# Довідкові копії репозиторіїв

Незмінні копії зовнішніх skill-репозиторіїв, збережені для вивчення методології. Вони **не підключені**
як активні skills (не лежать у `.claude/skills/`), тож агент не викликає їх автоматично.

## `claude-osint/` — elementalsouls/Claude-OSINT

- Upstream: https://github.com/elementalsouls/Claude-OSINT
- Коміт: `13d920413448c026b52ac74efee0f1eb39dd81ff` (2026-08-31), вендорено 2026-10-07
- Ліцензія: MIT (код) + CC-BY-4.0 (контент), © 2026 Sachin Sharma
- Provenance-штамп: `claude-osint/.VENDOR_INFO`

**Що це.** Наступальний (red-team / bug-bounty) recon-арсенал із 8 skills: `osint-methodology` («як
думати»), `offensive-osint` («що брати в руки» — 80 secret-регексів, валідатори кредів, дорки),
`org-attack-surface`, `email-domain-security`, `exposure-risk-quantification`,
`continuous-exposure-monitoring`, `cloud-saas-exposure`, `identity-provider-recon`.

**Чому копія, а не активний skill.** Репозиторій містить наступальні компоненти: secret-регекси,
bruteforce-wordlists (`skills/osint-autopilot/scripts/wordlist.txt`), 9 валідаторів кредів,
pre-auth user-enumeration oracle (`identity-provider-recon`), `secret_scan.py`, attack-path payloads.
Якби ці skills лежали в `.claude/skills/`, агент міг би автоматично тригерити `offensive-osint`. Тому
копія зберігається тут як **довідка для вивчення**, а не підключається як робочий інструмент.

**Що я з нього взяв у робочий skill `company-domain-check`** (лише методологія та дисципліна, у захисній,
discover-only рамці — див. `.claude/skills/company-domain-check/references/tradecraft.md` і
`attack-surface.md`):

- граф типізованих активів із dedup за ключем і ребрами за правилом трьох;
- finding-картка з двома незалежними осями: **критичність × достовірність**;
- рівні достовірності та шляхи апгрейду (правило трьох для атрибуції);
- гігієна доказів і chain of custody (URL + UTC + SHA-256, незмінний артефакт);
- модель заметності (detectability) + лестниця відступлення замість обходу захисту;
- стійкість джерел (union по категорії, а не один виклик);
- бюджет часу / профіль роботи та умови аборту;
- трек поверхні атаки «тільки обнаруження» (seed → розширення → збагачення → аналіз exposure → звіт).

**Що свідомо НЕ взято** (лишилося тільки в цій копії, у роботу не йде): secret-регекси та `secret_scan.py`,
wordlists і перебір, валідатори кредів, user-enumeration, активні скани/фаззинг/nuclei, breach×identity
для підбору паролів, per-person dossier і attack-path payloads. Обґрунтування — у
`.claude/skills/company-domain-check/references/attack-surface.md`, розділ «Що саме НЕ робимо».

Цей вибір повторює рішення, яке в проєкті вже зафіксовано для верхньої теки `skills/`
(російськомовна адаптація): переносити лише методологію й дисципліну, наступальний арсенал лишати поза рамками.
