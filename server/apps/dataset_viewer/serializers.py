from rest_framework import serializers
from .models import Dataset, DatasetItem


class DatasetListSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dataset
        fields = ["id", "name", "root_dir", "items_count"]


class DatasetDetailSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)
    total_pixels = serializers.IntegerField(read_only=True)
    avg_w = serializers.FloatField(read_only=True)
    avg_h = serializers.FloatField(read_only=True)

    class Meta:
        model = Dataset
        fields = ["id", "name", "root_dir", "items_count", "total_pixels", "avg_w", "avg_h"]


class DatasetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetItem
        fields = ["id", "image_path", "width", "height", "sha256"]
