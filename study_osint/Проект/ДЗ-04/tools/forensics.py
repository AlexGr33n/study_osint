"""Рівні 1–2 чекліста: метадані/провенанс-маркери + ELA + таблиці квантування JPEG.

Використання:  python -I forensics.py <папка_зразків> <папка_для_ELA>
Друкує JSON по кожному файлу і зберігає ELA-карти (<ім'я>_ela.png).
"""
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

# байтові маркери: C2PA живе в JUMBF-боксах, IPTC DigitalSourceType — у XMP
MARKERS = {
    "c2pa": b"c2pa",
    "jumbf": b"jumb",
    "xmp": b"http://ns.adobe.com/xap/1.0/",
    "DigitalSourceType": b"DigitalSourceType",
    "trainedAlgorithmicMedia": b"trainedAlgorithmicMedia",
}


def jpeg_quality(qtables):
    # оцінка якості за таблицею яскравості (формула libjpeg, зворотна до масштабування)
    std = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
           14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
           18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
           49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99]
    q0 = qtables[0]  # Pillow віддає таблицю в natural order, як std
    scale = sum(q0[i] / std[i] for i in range(64)) / 64 * 100
    return round((200 - scale) / 2) if scale <= 100 else round(5000 / scale)


def ela(img, quality=90, gain=15):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    diff = ImageChops.difference(img, Image.open(buf))
    return diff.point(lambda v: min(255, v * gain))


def main(src, out):
    Path(out).mkdir(parents=True, exist_ok=True)
    report = {}
    for f in sorted(Path(src).iterdir()):
        if f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        raw = f.read_bytes()
        with Image.open(f) as im:
            r = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "format": im.format,
                "size": im.size,
                "markers": {k: (m in raw) for k, m in MARKERS.items()},
            }
            # байтовий пошук "Exif\0\0" пропускає PNG eXIf і WebP EXIF — питаємо Pillow
            r["markers"]["exif"] = bool(im.getexif())
            if im.format == "JPEG":
                r["jpeg_quality_est"] = jpeg_quality(im.quantization)
                r["progressive"] = bool(im.info.get("progressive"))
            rgb = im.convert("RGB")
        ela(rgb).save(Path(out) / f"{f.stem}_ela.png")
        report[f.name] = r
    sys.stdout.reconfigure(encoding="utf-8")  # Windows-консоль інакше падає на не-ASCII іменах файлів
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
