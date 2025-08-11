from django.contrib import admin
from .models import Dataset, DatasetItem


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'allow_nsfw', 'created_at')


@admin.register(DatasetItem)
class DatasetItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'dataset', 'rel_path', 'status', 'created_at')
    list_filter = ('status', 'dataset')
    