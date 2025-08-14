from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from dataset_viewer import views as ds_views

def health(_): return JsonResponse({"ok": True})

urlpatterns = [
path('admin/', admin.site.urls),
path('api/health', health),
path('api/datasets/', include('dataset_viewer.urls')),
path('datasets/', include('dataset_viewer.urls')),
path('api/dataset-items/<int:item_id>/mask', ds_views.dataset_item_mask),
path('api/dataset-items/<int:item_id>/mask/preview', ds_views.dataset_item_mask_preview),
path('', include('webui.urls')),
]