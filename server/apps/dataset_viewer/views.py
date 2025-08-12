import glob
import hashlib
import os

from PIL import Image
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Dataset, DatasetItem
from .serializers import DatasetListSerializer, DatasetScanSerializer


@api_view(["GET"])
def datasets_list(_request):
    datasets = Dataset.objects.all()
    serializer = DatasetListSerializer(datasets, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def dataset_scan(request):
    serializer = DatasetScanSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    name = serializer.validated_data["name"]
    root_dir = serializer.validated_data["root_dir"]

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
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
            except Exception:
                skipped += 1
                continue
            try:
                with open(file_path, "rb") as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                sha256 = ""
            DatasetItem.objects.create(
                dataset=dataset,
                image_path=rel_path,
                width=width,
                height=height,
                sha256=sha256,
            )
            created += 1
    return Response({"created": created, "skipped": skipped})
