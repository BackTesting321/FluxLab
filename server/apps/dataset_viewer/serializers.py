from rest_framework import serializers
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


class DatasetItemSerializer(serializers.ModelSerializer):
    caption = serializers.CharField(source="caption_path", allow_blank=True)

    class Meta:
        model = DatasetItem
        fields = (
            "id",
            "image_path",
            "width",
            "height",
            "sha256",
            "caption",
            "created_at",
        )

class DatasetItemDetailSerializer(serializers.ModelSerializer):
    """Serializer for a single dataset item."""

    caption = serializers.CharField(source="caption_path", allow_blank=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetItem
        fields = (
            "id",
            "image_url",
            "image_path",
            "width",
            "height",
            "sha256",
            "caption",
            "created_at",
        )

    def get_image_url(self, obj):  # pragma: no cover - trivial
        """Return URL used to serve the item's image."""
        return f"/api/datasets/item/{obj.id}/image"
