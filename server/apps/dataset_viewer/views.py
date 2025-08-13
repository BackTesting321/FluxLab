import hashlib
import os

from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.shortcuts import render

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

class ItemsPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 500

@api_view(["GET"])
def dataset_items(request, dataset_id: int):
    if not Dataset.objects.filter(id=dataset_id).exists():
        raise Http404("Dataset not found")
    qs = DatasetItem.objects.filter(dataset_id=dataset_id)

    q = request.GET.get("q")
    if q:
        qs = qs.filter(image_path__icontains=q)

    def to_int(v):
        try:
            return int(v)
        except Exception:  # noqa: BLE001
            return None

    mw = to_int(request.GET.get("min_w"))
    xw = to_int(request.GET.get("max_w"))
    mh = to_int(request.GET.get("min_h"))
    xh = to_int(request.GET.get("max_h"))
    if mw is not None:
        qs = qs.filter(width__gte=mw)
    if xw is not None:
        qs = qs.filter(width__lte=xw)
    if mh is not None:
        qs = qs.filter(height__gte=mh)
    if xh is not None:
        qs = qs.filter(height__lte=xh)

    has_caption = request.GET.get("has_caption")
    if has_caption in ("true", "false"):
        if has_caption == "true":
            qs = qs.filter(~Q(caption_path=""), ~Q(caption_path__isnull=True))
        else:
            qs = qs.filter(Q(caption_path="") | Q(caption_path__isnull=True))

    qs = qs.order_by("id")
    paginator = ItemsPagination()
    page = paginator.paginate_queryset(qs, request)
    data = DatasetItemListSerializer(page, many=True).data
    return paginator.get_paginated_response(data)

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
        obj, was_created = DatasetItem.objects.get_or_create(
            dataset=dataset,
            image_path=rel_path,
            defaults={"width": width, "height": height, "sha256": sha},
        )
        if was_created:
            created += 1


def dataset_view_page(request, dataset_id: int):
    """Render the dataset browser page."""
    return render(request, "dataset_viewer/detail.html", {"dataset_id": dataset_id})
