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
        fields = ["id", "name", "root_dir", "items_count", "created_at", "updated_at"]


class DatasetItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetItem
        fields = ["id", "image_path", "width", "height", "sha256", "thumbnail_url", "image_url"]

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(f"/api/datasets/items/{obj.id}/thumbnail/") if request else None

    def get_image_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(f"/api/datasets/items/{obj.id}/file") if request else None
