from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterator, Optional
import pathlib

from django.conf import settings
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


def resolve_dataset_image_abs_path(dataset, rel_path: str) -> pathlib.Path:
    root = pathlib.Path(dataset.root_dir).resolve()
    candidate = (root / rel_path).resolve()
    if root not in candidate.parents and root != candidate.parent:
        raise ValueError("Path traversal detected")
    return candidate


def thumbnail_path_for(dataset_id: int, rel_path: str) -> pathlib.Path:
    return (settings.THUMBNAILS_ROOT / str(dataset_id) / rel_path).with_suffix(".jpg")


def get_dataset_root(dataset) -> Path:
    return Path(dataset.root_dir)


def get_masks_dir(dataset) -> Path:
    path = get_dataset_root(dataset) / "masks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_mask_relpath(item) -> str:
    stem = Path(item.image_path).stem
    return str(Path("masks") / f"{stem}.png")


def validate_mask_image(mask_file, target_w: int, target_h: int) -> None:
    try:
        with Image.open(mask_file) as img:
            w, h = img.size
    except Exception as exc:  # pragma: no cover - simple validation
        raise ValueError("invalid image") from exc
    if w != target_w or h != target_h:
        raise ValueError("mask size mismatch")
    if hasattr(mask_file, "seek"):
        mask_file.seek(0)


def write_mask_file(dst_path: Path, fileobj) -> None:
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, "wb") as out:
        if hasattr(fileobj, "chunks"):
            for chunk in fileobj.chunks():
                out.write(chunk)
        elif hasattr(fileobj, "read"):
            for chunk in iter(lambda: fileobj.read(8192), b""):
                out.write(chunk)
        else:  # pragma: no cover - alt path
            with open(fileobj, "rb") as src:
                for chunk in iter(lambda: src.read(8192), b""):
                    out.write(chunk)
