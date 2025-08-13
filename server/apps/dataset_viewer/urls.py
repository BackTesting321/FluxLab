from django.urls import path
from . import views

urlpatterns = [
    path("", views.datasets_list),
    path("scan", views.dataset_scan),
    path("<int:dataset_id>/", views.dataset_detail),
    path("<int:dataset_id>/items", views.dataset_items),
    path("<int:dataset_id>/upload", views.dataset_upload),
    path("item/<int:item_id>/image", views.item_image),
]
