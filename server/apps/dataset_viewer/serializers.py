import os

from rest_framework import serializers

from .models import Dataset


class DatasetListSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = ("id", "name", "items_count")

    def get_items_count(self, obj: Dataset) -> int:
        return obj.items.count()


class DatasetScanSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    root_dir = serializers.CharField(max_length=1024)

    def validate_root_dir(self, value: str) -> str:
        if not os.path.isdir(value):
            raise serializers.ValidationError("Directory does not exist")
        return value