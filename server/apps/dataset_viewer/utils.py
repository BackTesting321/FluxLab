from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterator, Optional

from PIL import Image


def open_image_size(path: str | Path) -> Optional[tuple[int, int]]:
    try:
        with Image.open(path) as img:
            return img.width, img.height
    except Exception:
        return None


def sha256_file(path: str | Path) -> str:
    h = sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def iter_images(root_dir: str | Path) -> Iterator[str]:
    base = Path(root_dir) / "images"
    patterns = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    for pattern in patterns:
        for path in base.rglob(pattern):
            if path.is_file():
                yield str(path)


def ensure_thumb_cache_dir(base: Path) -> Path:
    path = base / "cache" / "thumbnails"
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_thumbnail(src_path: Path, dst_path: Path, size: int = 256) -> None:
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        if w >= h:
            new_w = size
            new_h = max(1, int(h * (size / w)))
        else:
            new_h = size
            new_w = max(1, int(w * (size / h)))
        img = img.resize((new_w, new_h), Image.LANCZOS)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst_path, "JPEG", quality=85)
