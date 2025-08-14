import hashlib
import os
import json

from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from django.shortcuts import render
from pathlib import Path

from .models import Dataset, DatasetItem
from .serializers import (
    DatasetListSerializer,
    DatasetDetailSerializer,
    DatasetItemListSerializer,
    DatasetItemDetailSerializer,
)
from .utils import (
    iter_images,
    open_image_size,
    sha256_file,
    resolve_dataset_image_abs_path,
    thumbnail_path_for,
    get_dataset_root,
    get_masks_dir,
    default_mask_relpath,
    validate_mask_image,
    write_mask_file,
)


# === List/Detail Datasets ===

@api_view(["GET"])
def datasets_list(_request):
    qs = Dataset.objects.annotate(items_count=Count("items"))
    return Response(DatasetListSerializer(qs, many=True).data)


@api_view(["GET"])
def dataset_detail(_request, dataset_id: int):
    qs = Dataset.objects.filter(id=dataset_id).annotate(items_count=Count("items"))
    dataset = qs.first()
    if not dataset:
        raise Http404("Dataset not found")
    return Response(DatasetDetailSerializer(dataset).data)


# === Items ===

ALLOWED_SORT = {"created_at", "width", "height", "image_path"}


@api_view(["GET"])
def dataset_items_list(request, dataset_id: int):
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        return JsonResponse({"detail": "dataset not found"}, status=404)

    qs = DatasetItem.objects.filter(dataset=dataset)

    # filters
    q = request.GET.get("q")
    if q:
        qs = qs.filter(image_path__icontains=q)

    def to_int(name):
        v = request.GET.get(name)
        if v is None:
            return None
        try:
            return int(v)
        except Exception:  # noqa: BLE001
            raise ValueError(f"{name} must be int")

    try:
        min_w, max_w = to_int("min_w"), to_int("max_w")
        min_h, max_h = to_int("min_h"), to_int("max_h")
    except ValueError as e:  # pragma: no cover - trivial
        return JsonResponse({"detail": str(e)}, status=400)

    if min_w is not None:
        qs = qs.filter(width__gte=min_w)
    if max_w is not None:
        qs = qs.filter(width__lte=max_w)
    if min_h is not None:
        qs = qs.filter(height__gte=min_h)
    if max_h is not None:
        qs = qs.filter(height__lte=max_h)

    has_caption = request.GET.get("has_caption")
    if has_caption:
        if has_caption.lower() not in ("true", "false"):
            return JsonResponse(
                {"detail": "has_caption must be true|false"}, status=400
            )
        qs = qs.filter(has_caption=(has_caption.lower() == "true"))

    exts = request.GET.get("ext")
    if exts:
        exts_set = {
            ("." + e.strip().lstrip(".")).lower()
            for e in exts.split(",")
            if e.strip()
        }
        if exts_set:
            q_or = Q()
            for ext in exts_set:
                q_or |= Q(image_path__iendswith=ext)
            qs = qs.filter(q_or)

    order_by = request.GET.get("order_by", "image_path")
    order = request.GET.get("order", "asc")
    if order_by not in ALLOWED_SORT:
        return JsonResponse(
            {"detail": f"order_by must be one of {sorted(ALLOWED_SORT)}"},
            status=400,
        )
    prefix = "" if order == "asc" else "-"
    qs = qs.order_by(prefix + order_by)

    def to_pg(name, default):
        v = request.GET.get(name, default)
        try:
            return int(v)
        except Exception:  # noqa: BLE001
            raise ValueError(f"{name} must be int")

    try:
        page = max(1, to_pg("page", 1))
        page_size = to_pg("page_size", 50)
        if page_size < 1 or page_size > 200:
            return JsonResponse(
                {"detail": "page_size must be in [1..200]"}, status=400
            )
    except ValueError as e:  # pragma: no cover - trivial
        return JsonResponse({"detail": str(e)}, status=400)

    total = qs.count()
    start = (page - 1) * page_size
    items = list(qs[start : start + page_size])

    data = DatasetItemListSerializer(items, many=True).data
    return JsonResponse(
        {"count": total, "page": page, "page_size": page_size, "results": data},
        status=200,
    )

@api_view(["GET", "DELETE"])
def dataset_item_detail(request, dataset_id: int, item_id: int):
    """Retrieve or delete a single dataset item."""

    item = (
        DatasetItem.objects.filter(id=item_id, dataset_id=dataset_id)
        .select_related("dataset")
        .first()
    )
    if not item:
        raise Http404("Item not found")

    if request.method == "DELETE":
        item.delete()
        return Response(status=204)

    return Response(DatasetItemDetailSerializer(item).data)

@api_view(["GET"])
def item_image(_request, item_id: int):
    item = DatasetItem.objects.select_related("dataset").filter(id=item_id).first()
    if not item:
        raise Http404("Item not found")
    abs_path = os.path.normpath(os.path.join(item.dataset.root_dir, item.image_path))
    root = os.path.normpath(item.dataset.root_dir)
    if not abs_path.startswith(root):
        raise Http404("Invalid path")
    if not os.path.isfile(abs_path):
        raise Http404("File not found")
    return FileResponse(open(abs_path, "rb"))
@api_view(["GET", "POST", "DELETE"])
@parser_classes([MultiPartParser])
def dataset_item_mask(request, item_id: int):
    item = DatasetItem.objects.select_related("dataset").filter(id=item_id).first()
    if not item:
        raise Http404("Item not found")
    dataset = item.dataset
    root = get_dataset_root(dataset)

    if request.method == "GET":
        if not item.mask_path:
            raise Http404("Mask not found")
        abs_mask = (root / item.mask_path).resolve()
        if not abs_mask.is_file():
            raise Http404("Mask not found")
        return FileResponse(open(abs_mask, "rb"), content_type="image/png")

    if request.method == "DELETE":
        delete_flag = request.GET.get("delete_file", "1")
        if item.mask_path:
            abs_mask = (root / item.mask_path).resolve()
            if delete_flag == "1":
                try:
                    abs_mask.unlink()
                except OSError:
                    pass
            item.mask_path = None
            item.save(update_fields=["mask_path"])
        return Response(DatasetItemDetailSerializer(item).data)

    # POST
    if "file" in request.FILES:
        file_obj = request.FILES["file"]
        try:
            validate_mask_image(file_obj, item.width or 0, item.height or 0)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        rel_path = default_mask_relpath(item)
        abs_path = get_dataset_root(dataset) / rel_path
        get_masks_dir(dataset)
        write_mask_file(abs_path, file_obj)
    else:
        existing_path = request.data.get("existing_path")
        if not existing_path:
            return Response({"detail": "file or existing_path required"}, status=400)
        try:
            src_path = resolve_dataset_image_abs_path(dataset, existing_path)
        except ValueError:
            return Response({"detail": "file not found"}, status=404)
        if not src_path.is_file():
            return Response({"detail": "file not found"}, status=404)
        try:
            validate_mask_image(src_path, item.width or 0, item.height or 0)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        rel_path = default_mask_relpath(item)
        abs_path = get_dataset_root(dataset) / rel_path
        get_masks_dir(dataset)
        with open(src_path, "rb") as fsrc:
            write_mask_file(abs_path, fsrc)

    item.mask_path = rel_path
    item.save(update_fields=["mask_path"])
    return Response(DatasetItemDetailSerializer(item).data)


@api_view(["GET"])
def dataset_item_mask_preview(request, item_id: int):
    item = DatasetItem.objects.select_related("dataset").filter(id=item_id).first()
    if not item or not item.mask_path:
        raise Http404("Mask not found")

    try:
        size = int(request.GET.get("size", "128"))
    except ValueError:
        return Response({"detail": "size must be int"}, status=400)
    size = max(1, size)

    root = get_dataset_root(item.dataset)
    mask_abs = (root / item.mask_path).resolve()
    if not mask_abs.is_file():
        raise Http404("Mask not found")

    cache_path = root / ".cache" / "masks" / str(size) / item.mask_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not cache_path.exists():
        from PIL import Image

        with Image.open(mask_abs) as img:
            mask = img.convert("L")
            preview = Image.new("RGBA", mask.size, (0, 0, 0, 0))
            white = Image.new("RGBA", mask.size, (255, 255, 255, 255))
            preview.paste(white, mask=mask)
            preview.thumbnail((size, size), Image.NEAREST)
            preview.save(cache_path, "PNG")

    return FileResponse(open(cache_path, "rb"), content_type="image/png")

@api_view(["GET"])
def dataset_file_serve(request, dataset_id: int):
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        raise Http404("Dataset not found")

    rel_path = request.GET.get("path")
    if not rel_path:
        return Response({"detail": "path is required"}, status=400)

    try:
        abs_path = resolve_dataset_image_abs_path(dataset, rel_path)
    except ValueError:
        return Response({"detail": "file not found"}, status=404)

    if not abs_path.is_file():
        return Response({"detail": "file not found"}, status=404)

    ext = abs_path.suffix.lower().lstrip(".")
    mimes = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    if ext not in mimes:
        return Response({"detail": "unsupported media type"}, status=415)

    resp = FileResponse(open(abs_path, "rb"), content_type=mimes[ext])
    resp["Cache-Control"] = "public, max-age=86400"
    etag = sha256_file(abs_path)
    if etag:
        resp["ETag"] = etag
    return resp


@api_view(["GET"])
def dataset_thumb_serve(request, dataset_id: int):
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        raise Http404("Dataset not found")

    rel_path = request.GET.get("path")
    if not rel_path:
        return Response({"detail": "path is required"}, status=400)

    try:
        src_path = resolve_dataset_image_abs_path(dataset, rel_path)
    except ValueError:
        return Response({"detail": "file not found"}, status=404)

    if not src_path.is_file():
        return Response({"detail": "file not found"}, status=404)

    ext = src_path.suffix.lower().lstrip(".")
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        return Response({"detail": "unsupported media type"}, status=415)

    thumb_path = thumbnail_path_for(dataset_id, rel_path)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)

    if not thumb_path.exists():
        from PIL import Image

        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img.thumbnail(settings.THUMBNAIL_SIZE, Image.LANCZOS)
            img.save(thumb_path, "JPEG", quality=85)

    resp = FileResponse(open(thumb_path, "rb"), content_type="image/jpeg")
    resp["Cache-Control"] = "public, max-age=86400"
    etag = sha256_file(thumb_path)
    if etag:
        resp["ETag"] = etag
    return resp

@api_view(["POST"])
@parser_classes([MultiPartParser])
def dataset_upload(request, dataset_id: int):
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        raise Http404("Dataset not found")

    files = request.FILES.getlist("files")
    subdir = request.POST.get("subdir", "").strip().strip("/\\")
    base_images = os.path.join(dataset.root_dir, "images")
    save_dir = os.path.join(base_images, subdir) if subdir else base_images
    os.makedirs(save_dir, exist_ok=True)

    created = 0
    skipped = 0
    for f in files:
        filename = f.name
        target_path = os.path.join(save_dir, filename)
        with open(target_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)

        try:
            from PIL import Image

            with Image.open(target_path) as img:
                w, h = img.size
        except Exception:
            os.remove(target_path)
            skipped += 1
            continue

        with open(target_path, "rb") as inf:
            sha256 = hashlib.sha256(inf.read()).hexdigest()

        rel_path = os.path.relpath(target_path, dataset.root_dir)

        if DatasetItem.objects.filter(dataset=dataset, sha256=sha256).exists():
            skipped += 1
            continue

        DatasetItem.objects.create(
            dataset=dataset,
            image_path=rel_path,
            width=w,
            height=h,
            sha256=sha256,
        )
        created += 1

    return Response({"created": created, "skipped": skipped})

# === Import / Export Metadata ===

from pydantic import BaseModel, ValidationError


class MetadataItem(BaseModel):
    filename: str
    title: str | None = ""
    caption: str | None = ""
    tags: list[str] | None = []
    mask: str | None = ""


@api_view(["GET"])
def dataset_export(request, dataset_id: int):
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        raise Http404("Dataset not found")

    items = DatasetItem.objects.filter(dataset_id=dataset_id).order_by("image_path")
    results: list[dict] = []
    for item in items:
        title = ""
        caption = ""
        tags: list[str] = []
        if item.caption_path:
            abs_caption = os.path.join(dataset.root_dir, item.caption_path)
            if os.path.isfile(abs_caption):
                try:
                    with open(abs_caption, "r", encoding="utf-8") as f:
                        data = f.read().strip()
                    try:
                        obj = json.loads(data)
                        title = obj.get("title", "") or ""
                        caption = obj.get("caption", "") or ""
                        tags = obj.get("tags", []) or []
                    except json.JSONDecodeError:
                        caption = data
                except OSError:
                    pass
        results.append(
            {
                "filename": item.image_path,
                "title": title,
                "caption": caption,
                "tags": tags,
                "mask": item.mask_path or "",
            }
        )

    return Response(results)


@api_view(["POST"])
def dataset_import(request, dataset_id: int):
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        raise Http404("Dataset not found")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return Response({"detail": "invalid json"}, status=400)

    if not isinstance(payload, list):
        return Response({"detail": "invalid format"}, status=400)

    items: list[MetadataItem] = []
    filenames: set[str] = set()
    for raw in payload:
        try:
            meta = MetadataItem(**raw)
        except ValidationError as e:  # pragma: no cover - validation is trivial
            return Response({"detail": e.errors()}, status=400)
        if meta.filename in filenames:
            return Response({"detail": f"duplicate filename: {meta.filename}"}, status=400)
        filenames.add(meta.filename)
        items.append(meta)

    qs = DatasetItem.objects.filter(dataset_id=dataset_id)
    db_map = {obj.image_path: obj for obj in qs}
    db_names = set(db_map.keys())

    if filenames != db_names:
        missing = sorted(db_names - filenames)
        extra = sorted(filenames - db_names)
        return Response(
            {"detail": "filenames mismatch", "missing": missing, "extra": extra},
            status=400,
        )

    for meta in items:
        item = db_map[meta.filename]
        # determine caption path
        caption_rel = item.caption_path
        if not caption_rel:
            base, _ = os.path.splitext(meta.filename)
            caption_rel = base + ".json"
            item.caption_path = caption_rel

        abs_caption = os.path.join(dataset.root_dir, caption_rel)
        os.makedirs(os.path.dirname(abs_caption), exist_ok=True)
        with open(abs_caption, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": meta.title or "",
                    "caption": meta.caption or "",
                    "tags": meta.tags or [],
                },
                f,
                ensure_ascii=False,
            )

        item.has_caption = bool(meta.caption)
        item.mask_path = meta.mask or None
        item.save(update_fields=["caption_path", "mask_path", "has_caption"])

    return Response({"updated": len(items)})

# === Scan ===

from rest_framework import serializers


class DatasetScanSerializer(serializers.Serializer):
    name = serializers.CharField()
    root_dir = serializers.CharField()


@api_view(["POST"])
def dataset_scan(request):
    ser = DatasetScanSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    name = ser.validated_data["name"]
    root_dir = ser.validated_data["root_dir"]

    if not os.path.isdir(root_dir):
        return Response(
            {"detail": "root_dir does not exist"}, status=400
        )

    dataset, _ = Dataset.objects.get_or_create(
        name=name, defaults={"root_dir": root_dir}
    )
    if dataset.root_dir != root_dir:
        dataset.root_dir = root_dir
        dataset.save(update_fields=["root_dir"])

    created = 0
    skipped = 0
    for file_path in iter_images(root_dir):
        rel_path = os.path.relpath(file_path, root_dir).replace("\\", "/")
        size = open_image_size(file_path)
        if not size:
            skipped += 1
            continue
        width, height = size
        sha = sha256_file(file_path)
        base, _ = os.path.splitext(file_path)
        has_caption = os.path.exists(base + ".txt") or os.path.exists(base + ".json")
        mask_rel = default_mask_relpath(
            type("X", (), {"image_path": rel_path})()
        )
        mask_abs = Path(root_dir) / mask_rel
        has_mask = mask_abs.is_file()
        defaults = {
            "width": width,
            "height": height,
            "sha256": sha,
            "has_caption": has_caption,
            "mask_path": mask_rel if has_mask else None,
        }
        obj, was_created = DatasetItem.objects.get_or_create(
            dataset=dataset,
            image_path=rel_path,
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated_fields: list[str] = []
            if obj.has_caption != has_caption:
                obj.has_caption = has_caption
                updated_fields.append("has_caption")
            expected_mask = mask_rel if has_mask else None
            if obj.mask_path != expected_mask:
                obj.mask_path = expected_mask
                updated_fields.append("mask_path")
            if updated_fields:
                obj.save(update_fields=updated_fields)

    return Response({"created": created, "skipped": skipped})

    def dataset_view_page(request, dataset_id: int):
        """Render the dataset browser page."""
        return render(request, "dataset_viewer/detail.html", {"dataset_id": dataset_id})
