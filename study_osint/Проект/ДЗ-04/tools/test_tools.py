"""Самоперевірка tools/ без мережі:  python -I test_tools.py"""
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from detect import ai_score  # noqa: E402
from forensics import ela, jpeg_quality  # noqa: E402


def jpeg_bytes(quality):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "gray").save(buf, "JPEG", quality=quality)
    return buf.getvalue()


# оцінка якості повертає ту якість, з якою Pillow зберіг файл
for q in (30, 50, 75, 85, 95):
    assert jpeg_quality(Image.open(io.BytesIO(jpeg_bytes(q))).quantization) == q, q

# ELA зберігає розмір
assert ela(Image.new("RGB", (40, 30), "white")).size == (40, 30)

# ai_score знаходить AI-мітку незалежно від регістру і порядку
assert ai_score([{"label": "real", "score": 0.9}, {"label": "Artificial", "score": 0.1}]) == 0.1
assert ai_score([{"label": "ai", "score": 0.7}, {"label": "hum", "score": 0.3}]) == 0.7
try:
    ai_score([{"label": "cat", "score": 1.0}])
    raise AssertionError("невідома мітка мала впасти")
except ValueError:
    pass

# forensics.py: EXIF у PNG знаходиться, кирилиця в імені файлу не ламає вивід
with tempfile.TemporaryDirectory() as d:
    exif = Image.Exif()
    exif[0x0131] = "TestSoft"
    Image.new("RGB", (8, 8)).save(Path(d) / "зразок.png", exif=exif)
    Image.new("RGB", (8, 8)).save(Path(d) / "plain.jpg")
    res = subprocess.run([sys.executable, "-I", str(Path(__file__).parent / "forensics.py"), d, str(Path(d) / "ela")],
                         capture_output=True, check=True)
    rep = json.loads(res.stdout.decode("utf-8"))
    assert rep["зразок.png"]["markers"]["exif"] is True
    assert rep["plain.jpg"]["markers"]["exif"] is False
    assert (Path(d) / "ela" / "зразок_ela.png").exists()

print("ok")
