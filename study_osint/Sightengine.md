---
type: tool
tags: [osint, tool, deepfake, detectors]
status: growing
source: "https://sightengine.com/detect-ai-generated-images — проверено на ДЗ-04, 29.10.2026"
created: 2026-10-29
updated: 2026-10-29
---

# Sightengine

Коммерческий API модерации. На странице detect-ai-generated-images есть бесплатное демо без аккаунта, только загрузка файла.

- **Выдаёт:** GenAI %, face manipulation %, атрибуцию по семействам (Diffusion: GPT, Flux, Imagen/Nano Banana,
  MidJourney…; GAN: StyleGAN).
- **Сильное:** полная генерация (99 % на BRICS и Hebdo, 0 % на контролях). Работает по пикселям, метаданные не нужны.
- **Слабое:** AI-правка (кейс Стармера — 1 %). Атрибуция «Other» 84 % там, где водяной знак указывает на OpenAI.
- **Ещё полезно:** на сайте есть бесплатные C2PA Checker и EXIF Viewer.
- **API:** `api.sightengine.com/1.0/check.json`, `models=genai` (нужны ключи).

## Применения
- [[2026-10-29 ДЗ-04 — верификация трёх вирусных фейков]]

## Связи
- [[Контрольный прогон AI-детекторов]] · [[Hive Detect]]
