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
