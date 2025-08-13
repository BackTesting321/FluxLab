import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Count, F, Sum
from django.http import FileResponse, Http404
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Dataset, DatasetItem
from .serializers import (
    DatasetListSerializer,
    DatasetDetailSerializer,
    DatasetItemSerializer,
)
from .utils import (
    ensure_thumb_cache_dir,
    iter_images,
    make_thumbnail,
    open_image_size,
    sha256_file,
)


# === List/Detail Datasets ===

@api_view(["GET"])
def datasets_list(_request):
    qs = Dataset.objects.annotate(items_count=Count("items"))
    return Response(DatasetListSerializer(qs, many=True).data)


@api_view(["GET"])
def dataset_detail(_request, pk: int):
    ds = (
        Dataset.objects.filter(pk=pk)
        .annotate(
            items_count=Count("items"),
            total_pixels=Sum(F("items__width") * F("items__height")),
            avg_w=Avg("items__width"),
            avg_h=Avg("items__height"),
        )
        .first()
    )
    if not ds:
        raise Http404
    return Response(DatasetDetailSerializer(ds).data)


# === Items ===

@api_view(["GET"])
def dataset_items(request, pk: int):
    try:
        ds = Dataset.objects.get(pk=pk)
    except Dataset.DoesNotExist:
        raise Http404
    qs = DatasetItem.objects.filter(dataset=ds)
    params = request.query_params

    def _int_param(name):
        try:
            return int(params.get(name))
        except (TypeError, ValueError):
            return None

    min_w = _int_param("min_w")
    if min_w is not None:
        qs = qs.filter(width__gte=min_w)
    max_w = _int_param("max_w")
    if max_w is not None:
        qs = qs.filter(width__lte=max_w)
    min_h = _int_param("min_h")
    if min_h is not None:
        qs = qs.filter(height__gte=min_h)
    max_h = _int_param("max_h")
    if max_h is not None:
        qs = qs.filter(height__lte=max_h)
    q = params.get("q")
    if q:
        qs = qs.filter(image_path__icontains=q)
    qs = qs.order_by("id")

    paginator = PageNumberPagination()
    try:
        paginator.page_size = int(params.get("page_size", settings.REST_FRAMEWORK.get("PAGE_SIZE", 50)))
    except (TypeError, ValueError, AttributeError):
        paginator.page_size = settings.REST_FRAMEWORK.get("PAGE_SIZE", 50)
    page = paginator.paginate_queryset(qs, request)
    ser = DatasetItemSerializer(page, many=True)
    return Response(
        {
            "count": paginator.page.paginator.count,
            "page": paginator.page.number,
            "page_size": paginator.page.paginator.per_page,
            "results": ser.data,
        }
    )


@api_view(["GET"])
def dataset_item_thumbnail(_request, item_id: int):
    try:
        item = DatasetItem.objects.select_related("dataset").get(pk=item_id)
    except DatasetItem.DoesNotExist:
        raise Http404
    src_path = Path(item.dataset.root_dir) / item.image_path
    if not src_path.is_file():
        raise Http404("Source image not found")

    cache_dir = ensure_thumb_cache_dir(Path(settings.MEDIA_ROOT))
    if item.sha256:
        cache_name = f"{item.sha256}.jpg"
    else:
        cache_name = hashlib.sha1(str(src_path).encode("utf-8")).hexdigest() + ".jpg"
    dst_path = cache_dir / cache_name
    if not dst_path.exists():
        try:
            make_thumbnail(src_path, dst_path)
        except Exception:
            raise Http404

    return FileResponse(open(dst_path, "rb"), content_type="image/jpeg")


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
        else:
            skipped += 1

    return Response({"created": created, "skipped": skipped})
