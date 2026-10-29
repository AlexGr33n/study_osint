# ДЗ-04: Верифікація медіа та протидія маніпуляціям

Курс «AI для OSINT 2026», лекція 4 «Верифікація і протидія маніпуляціям (текст / зображення / відео)».
Методологія: чекліст із 5 кроків і шаблон верифікаційного звіту з лекції (навик `media-verification`).

## Завдання → файли

| Завдання | Файл |
|---|---|
| 1. Три вірусні зображення за останні 6 місяців | таблиця нижче |
| 2. Чекліст + шаблон звіту для кожного | [report-01-brics-selfie.md](report-01-brics-selfie.md), [report-02-charlie-hebdo-cover.md](report-02-charlie-hebdo-cover.md), [report-03-starmer-croatia-jersey.md](report-03-starmer-croatia-jersey.md) |
| 3. ≥ 2 автоматичні детектори, порівняння score | [detectors-comparison.md](detectors-comparison.md): 5 детекторів × 6 файлів |
| 4. Висновок: який рівень дав найбільше | [conclusion.md](conclusion.md) |

## Обрані кейси (травень – жовтень 2026)

| # | Що поширювалось як справжнє | Дата / охоплення | Тип фейку | Вердикт |
|---|---|---|---|---|
| 1 | «Селфі» Путіна з лідерами BRICS на саміті в Нью-Делі | 13.09.2026, Посольство РФ у ПАР, 2,19 млн переглядів | повна генерація, фотореалізм | **згенероване**, висока |
| 2 | «Обкладинка Charlie Hebdo» про мародерство на протестах у Франції | 21.10.2026, 453 тис. переглядів першого поста | повна генерація, ілюстрація | **згенероване**, висока |
| 3 | Стармер і Рейнер у формі Хорватії перед матчем ЧС-2026 | 17.06.2026, 440 тис. переглядів | AI-редагування справжнього фото 2024 р. | **змінене**, висока |

Кейси навмисно різні (фото, ілюстрація, правка справжнього кадру), щоб порівняти, як кожен рівень
перевірки працює на різних типах підробки. Для кожного фейку детектори проганялись і на
**справжньому контрольному знімку** тієї ж події.

## Структура

```
homework-04/
├── README.md
├── report-01-brics-selfie.md            ← звіт за шаблоном лекції
├── report-02-charlie-hebdo-cover.md
├── report-03-starmer-croatia-jersey.md
├── detectors-comparison.md              ← завдання 3
├── conclusion.md                        ← завдання 4
├── tools/
│   ├── detect.py         ← 3 відкриті HF-детектори, запінені на commit прогону
│   ├── forensics.py      ← SHA-256, маркери EXIF/XMP/C2PA, оцінка якості JPEG, ELA-карти
│   ├── test_tools.py     ← самоперевірка (без мережі)
│   └── requirements.txt
├── evidence/
│   ├── samples/          ← 6 файлів, які перевірялись (3 фейки + 3 контролі)
│   ├── originals/        ← скриншоти-першоджерела (оригінал Рейнер 2024, FB-репост, X-пости)
│   ├── ela/              ← ELA-карти
│   ├── detectors-local.json
│   └── forensics.json
└── screenshots/          ← результати Hive і Sightengine по кожному файлу (12 шт.)
```

## Відтворення

```bash
python -m venv venv
venv/Scripts/python -m pip install -r tools/requirements.txt
venv/Scripts/python -I tools/test_tools.py
venv/Scripts/python -I tools/forensics.py evidence/samples evidence/ela > evidence/forensics.json
venv/Scripts/python -I tools/detect.py evidence/samples > evidence/detectors-local.json
```

Hive і Sightengine: файли з `evidence/samples/` завантажено вручну через веб-форми (hivedetect.ai,
sightengine.com/detect-ai-generated-images), без акаунта. SHA-256 усіх файлів є у `evidence/forensics.json`.

## Інструменти

- Пошук кейсів: фактчекінгові розбори (The Quint, Maldita.es, Euronews The Cube, Lead Stories, AFP Fact Check).
- Провенанс: **api.fxtwitter.com** (дата, метрики, оригінальний URL медіа твіту), **Google Lens** («Точні збіги»),
  архіви web.archive.org / perma.cc / archive.ph.
- Метадані / сигнал: власний `forensics.py` (exiftool і ffmpeg на машині не встановлені).
- Детектори: Hive Detect, Sightengine, 3 відкриті моделі Hugging Face.

## Чесні застереження

1. **Оригінальних файлів генератора немає в жодному кейсі.** Перевірялись найкращі доступні копії
   (`name=orig` з X, тобто перестиснення q≈83–85). У кейсі 3 була лише скриншот-копія зі штампом AFP: X-акаунт
   першоджерела без входу недоступний.
2. **SynthID / OpenAI-verify я не запускав**: SynthID Detector вимагає прийняти умови Google і увійти в
   акаунт. Результати водяних знаків взято з публікацій фактчекерів і позначено так у звітах.
3. **Контроль для кейсу 2** — скриншот сайту Charlie Hebdo з інтерфейсом, а не чистий скан обкладинки.
4. Аналітик — модель Claude Opus 5.5 (cutoff — червень 2026). Усі кейси після cutoff встановлено пошуком, а не з пам'яті.
5. Обличчя в кадрах — публічні політики в публічному контексті. Нічого не генерувалось і не деанонімізувалось:
   перевірялась лише справжність матеріалу (етична рамка лекції).
