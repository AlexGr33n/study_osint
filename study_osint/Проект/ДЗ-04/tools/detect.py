"""Прогін відкритих AI-image детекторів (Hugging Face) по папці зразків.

Використання:  python -I detect.py <папка_зразків> > detectors-local.json
Кожна модель фіксується з commit-хешем ревізії — щоб прогін був відтворюваний.
"""
import json
import sys
from pathlib import Path

from PIL import Image
from transformers import pipeline

# модель → commit, з яким робився прогін 29.10.2026 (без пінування HF віддасть найновішу ревізію)
MODELS = {
    "umm-maybe/AI-image-detector": "c7e223baf11bc40528af364ba7bdea030ef42f9e",            # ViT, 2022
    "Ateeqq/ai-vs-human-image-detector": "60e82406916921b823616bee33397baab38af3f0",      # SigLIP, 2025
    "haywoodsloan/ai-image-detector-deploy": "4ae1822603cb1ec980c217cfde1ef1b8e0477a16",  # SwinV2, 2026
}
# мітки «згенероване» у різних моделях називаються по-різному
AI_LABELS = {"artificial", "ai", "fake", "ai-generated", "ai_generated", "aigenerated"}


def ai_score(preds):
    for p in preds:
        if p["label"].lower() in AI_LABELS:
            return round(p["score"], 4)
    raise ValueError(f"невідома мітка AI: {preds}")


def main(folder):
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    out = {"models": MODELS, "results": {}}
    for m, rev in MODELS.items():
        clf = pipeline("image-classification", model=m, revision=rev, device=-1)
        for f in files:
            with Image.open(f) as im:
                preds = clf(im.convert("RGB"), top_k=None)
            out["results"].setdefault(f.name, {})[m] = {"ai_score": ai_score(preds), "raw": preds}
    sys.stdout.reconfigure(encoding="utf-8")  # Windows-консоль інакше падає на не-ASCII іменах файлів
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
