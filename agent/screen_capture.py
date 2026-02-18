import io
from typing import Optional, Tuple

from mss import mss
from PIL import Image
import hashlib


def capture_jpeg_bytes(max_width: int = 1280, quality: int = 80) -> bytes:
    with mss() as sct:
        mon = sct.monitors[1]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)

        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


def capture_size() -> Tuple[int, int]:
    with mss() as sct:
        mon = sct.monitors[1]
        return mon["width"], mon["height"]


def frame_diff_ratio(prev: Optional[bytes], curr: bytes) -> float:
    """Estimate how different two JPEG frames are (0.0 = identical, 1.0 = totally different).

    Uses a fast downsampled pixel comparison — not perceptual, but good enough
    for detecting "nothing changed on screen" vs "something moved".
    """
    if prev is None:
        return 1.0

    THUMB = (64, 36)  # tiny thumbnail for fast comparison
    try:
        img_a = Image.open(io.BytesIO(prev)).convert("L").resize(THUMB)
        img_b = Image.open(io.BytesIO(curr)).convert("L").resize(THUMB)
        pixels_a = img_a.tobytes()
        pixels_b = img_b.tobytes()
        total = len(pixels_a)
        diff = sum(abs(a - b) for a, b in zip(pixels_a, pixels_b))
        return diff / (total * 255)
    except Exception:
        return 1.0
