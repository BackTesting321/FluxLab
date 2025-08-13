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

    class Meta:
        model = DatasetItem
        fields = (
            "id",
            "image_path",
            "image_url",
            "thumb_url",
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

class DatasetItemDetailSerializer(serializers.ModelSerializer):
    """Serializer for a single dataset item."""

    caption = serializers.CharField(source="caption_path", allow_blank=True)
    image_url = serializers.SerializerMethodField()
    thumb_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetItem
        fields = (
            "id",
            "image_url",
            "thumb_url",
            "image_path",
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
