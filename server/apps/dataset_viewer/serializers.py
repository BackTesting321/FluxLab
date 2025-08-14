from rest_framework import serializers
from django.conf import settings
from .models import Dataset, DatasetItem


class DatasetListSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dataset
        fields = ["id", "name", "root_dir", "items_count"]


class DatasetDetailSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dataset
        fields = (
            "id",
            "name",
            "root_dir",
            "created_at",
            "updated_at",
            "items_count",
        )


class DatasetItemListSerializer(serializers.ModelSerializer):
    caption = serializers.CharField(source="caption_path", allow_blank=True)
    image_url = serializers.SerializerMethodField()
    thumb_url = serializers.SerializerMethodField()
    has_mask = serializers.SerializerMethodField()
    mask_path = serializers.SerializerMethodField()
    mask_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetItem
        fields = (
            "id",
            "image_path",
            "image_url",
            "thumb_url",
            "has_mask",
            "mask_path",
            "mask_url",
            "width",
            "height",
            "sha256",
            "caption",
            "created_at",
        )

    def get_image_url(self, obj):  # pragma: no cover - trivial
        prefix = settings.FILE_SERVE_PREFIX.rstrip('/')
        return f"{prefix}/{obj.dataset_id}/files?path={obj.image_path}"

    def get_thumb_url(self, obj):  # pragma: no cover - trivial
        prefix = settings.FILE_SERVE_PREFIX.rstrip('/')
        return f"{prefix}/{obj.dataset_id}/thumb?path={obj.image_path}"

    def get_has_mask(self, obj) -> bool:  # pragma: no cover - trivial
        return bool(obj.mask_path)

    def get_mask_path(self, obj):  # pragma: no cover - trivial
        return obj.mask_path or None

    def get_mask_url(self, obj):  # pragma: no cover - trivial
        return f"/api/dataset-items/{obj.id}/mask" if obj.mask_path else None

class DatasetItemDetailSerializer(serializers.ModelSerializer):
    """Serializer for a single dataset item."""

    caption = serializers.CharField(source="caption_path", allow_blank=True)
    image_url = serializers.SerializerMethodField()
    thumb_url = serializers.SerializerMethodField()
    has_mask = serializers.SerializerMethodField()
    mask_path = serializers.SerializerMethodField()
    mask_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetItem
        fields = (
            "id",
            "image_url",
            "thumb_url",
            "image_path",
            "has_mask",
            "mask_path",
            "mask_url",
            "width",
            "height",
            "sha256",
            "caption",
            "created_at",
        )

    def get_image_url(self, obj):  # pragma: no cover - trivial
        prefix = settings.FILE_SERVE_PREFIX.rstrip('/')
        return f"{prefix}/{obj.dataset_id}/files?path={obj.image_path}"

    def get_thumb_url(self, obj):  # pragma: no cover - trivial
        prefix = settings.FILE_SERVE_PREFIX.rstrip('/')
        return f"{prefix}/{obj.dataset_id}/thumb?path={obj.image_path}"

    def get_has_mask(self, obj) -> bool:  # pragma: no cover - trivial
        return bool(obj.mask_path)

    def get_mask_path(self, obj):  # pragma: no cover - trivial
        return obj.mask_path or None

    def get_mask_url(self, obj):  # pragma: no cover - trivial
        return f"/api/dataset-items/{obj.id}/mask" if obj.mask_path else None
