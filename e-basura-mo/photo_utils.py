"""Save report photos locally."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from config import PHOTOS_DIR

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def save_photo(source_path: str) -> str:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Photo not found: {source_path}")
    ext = src.suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Photo must be JPG, PNG, GIF, WEBP, or BMP.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = PHOTOS_DIR / f"report_{stamp}{ext}"
    shutil.copy2(src, dest)
    return str(dest)
