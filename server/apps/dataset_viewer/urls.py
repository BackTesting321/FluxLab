from django.urls import path
from . import views

urlpatterns = [
    path("", views.datasets_list),
    path("scan/", views.dataset_scan),
    path("<int:pk>/", views.dataset_detail),
    path("<int:pk>/items/", views.dataset_items),
    path("items/<int:item_id>/thumbnail/", views.dataset_item_thumbnail),
]
