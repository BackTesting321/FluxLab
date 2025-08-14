from django.urls import path
from . import views
from .views import dataset_view_page

urlpatterns = [
    path("", views.datasets_list),
    path("scan", views.dataset_scan),
    path("<int:dataset_id>/", views.dataset_detail),
    path("<int:dataset_id>/items", views.dataset_items_list, name="dataset_items_list"),
    path("<int:dataset_id>/items/<int:item_id>/", views.dataset_item_detail, name="dataset_item_detail"),
    path("<int:dataset_id>/files", views.dataset_file_serve, name="dataset_file_serve"),
    path("<int:dataset_id>/thumb", views.dataset_thumb_serve, name="dataset_thumb_serve"),
    path("<int:dataset_id>/upload", views.dataset_upload),
    path("<int:dataset_id>/export", views.dataset_export),
    path("<int:dataset_id>/import", views.dataset_import),
    path("item/<int:item_id>/image", views.item_image),

    # NEW: dataset view page
    path("<int:dataset_id>/view", dataset_view_page, name="dataset_view_page"),
]
