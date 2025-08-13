import glob
import hashlib
import os
from io import BytesIO
from PIL import Image

from django.conf import settings
from django.db.models import Count
from django.http import FileResponse, Http404, HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Dataset, DatasetItem
from .serializers import (
    DatasetListSerializer,
    DatasetDetailSerializer,
    DatasetItemSerializer,
)


# === Helpers ===

def _abs_image_path(item: DatasetItem) -> str:
    return os.path.join(item.dataset.root_dir, item.image_path)


def _thumb_path_for(item: DatasetItem) -> str:
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "thumbnails"), exist_ok=True)
    key = (item.sha256 or item.image_path.replace("/", "_").replace("\\", "_"))
    return os.path.join(settings.MEDIA_ROOT, "thumbnails", f"{key}.jpg")


# === List/Detail Datasets ===

@api_view(["GET"])
def datasets_list(_request):
    qs = Dataset.objects.annotate(items_count=Count("items"))
    return Response(DatasetListSerializer(qs, many=True).data)


@api_view(["GET"])
def dataset_detail(_request, pk: int):
    try:
        ds = Dataset.objects.annotate(items_count=Count("items")).get(pk=pk)
    except Dataset.DoesNotExist:
        raise Http404
    return Response(DatasetDetailSerializer(ds).data)


# === Items ===

@api_view(["GET"])
def dataset_items(request, pk: int):
    try:
        ds = Dataset.objects.get(pk=pk)
    except Dataset.DoesNotExist:
        raise Http404
    qs = DatasetItem.objects.filter(dataset=ds).order_by("id")
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(qs, request)
    ser = DatasetItemSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(ser.data)


@api_view(["GET"])
def dataset_item_detail(request, item_id: int):
    try:
        item = DatasetItem.objects.select_related("dataset").get(pk=item_id)
    except DatasetItem.DoesNotExist:
        raise Http404
    return Response(DatasetItemSerializer(item, context={"request": request}).data)


@api_view(["GET"])
def dataset_item_file(_request, item_id: int):
    try:
        item = DatasetItem.objects.select_related("dataset").get(pk=item_id)
    except DatasetItem.DoesNotExist:
        raise Http404
    abs_path = _abs_image_path(item)
    if not os.path.isfile(abs_path):
        raise Http404
    return FileResponse(open(abs_path, "rb"))


@api_view(["GET"])
def dataset_item_thumbnail(_request, item_id: int):
    try:
        item = DatasetItem.objects.select_related("dataset").get(pk=item_id)
    except DatasetItem.DoesNotExist:
        raise Http404

    thumb_path = _thumb_path_for(item)
    if os.path.isfile(thumb_path):
        return FileResponse(open(thumb_path, "rb"), content_type="image/jpeg")

    abs_path = _abs_image_path(item)
    if not os.path.isfile(abs_path):
        raise Http404

    try:
        with Image.open(abs_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            if w >= h:
                new_w = 200
                new_h = max(1, int(h * (200 / w)))
            else:
                new_h = 200
                new_w = max(1, int(w * (200 / h)))
            img = img.resize((new_w, new_h), Image.LANCZOS)
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            img.save(thumb_path, "JPEG", quality=85)
    except Exception:
        return HttpResponse(status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    return FileResponse(open(thumb_path, "rb"), content_type="image/jpeg")


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

    dataset, _ = Dataset.objects.get_or_create(name=name, defaults={"root_dir": root_dir})
    if dataset.root_dir != root_dir:
        dataset.root_dir = root_dir
        dataset.save(update_fields=["root_dir"])

    images_dir = os.path.join(root_dir, "images")
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
    created = 0
    skipped = 0

    for pattern in patterns:
        for file_path in glob.glob(os.path.join(images_dir, "**", pattern), recursive=True):
            rel_path = os.path.relpath(file_path, root_dir)
            if DatasetItem.objects.filter(dataset=dataset, image_path=rel_path).exists():
                skipped += 1
                continue
            # read size
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
            except Exception:
                skipped += 1
                continue
            # read sha256
            try:
                with open(file_path, "rb") as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                sha256 = ""

            DatasetItem.objects.create(
                dataset=dataset,
                image_path=rel_path.replace("\\", "/"),
                width=width,
                height=height,
                sha256=sha256,
            )
            created += 1

    return Response({"created": created, "skipped": skipped})
