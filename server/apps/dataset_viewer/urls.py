from django.urls import path
from . import views

urlpatterns = [
    path("", views.datasets_list, name="datasets_list"),
    path("<int:pk>/", views.dataset_detail, name="dataset_detail"),
    path("<int:pk>/items/", views.dataset_items, name="dataset_items"),
    path("items/<int:item_id>/", views.dataset_item_detail, name="dataset_item_detail"),
    path("items/<int:item_id>/file", views.dataset_item_file, name="dataset_item_file"),
    path("items/<int:item_id>/thumbnail/", views.dataset_item_thumbnail, name="dataset_item_thumbnail"),
    path("scan", views.dataset_scan, name="dataset_scan"),
]
