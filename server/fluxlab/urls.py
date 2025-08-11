from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health(_): return JsonResponse({"ok": True})

urlpatterns = [
path('admin/', admin.site.urls),
path('api/health', health),
path('api/datasets/', include('dataset_viewer.urls')),
path('api/training/', include('training.urls')),
path('api/promptgen/', include('promptgen.urls')),
path('api/enhance/', include('enhance.urls')),
]
