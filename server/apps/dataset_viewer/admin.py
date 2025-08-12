from django.contrib import admin

from .models import Dataset, DatasetItem


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(DatasetItem)
class DatasetItemAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "image_path", "created_at")
    search_fields = ("image_path", "dataset__name")
