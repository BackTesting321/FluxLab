from django.urls import path
from . import views
from .views import dataset_view_page

urlpatterns = [
    path("", views.datasets_list),
    path("scan", views.dataset_scan),
    path("<int:dataset_id>/", views.dataset_detail),
    path("<int:dataset_id>/items", views.dataset_items),
    path("<int:dataset_id>/upload", views.dataset_upload),
    path("item/<int:item_id>/image", views.item_image),

    # NEW: dataset view page
    path("<int:dataset_id>/view", dataset_view_page, name="dataset_view_page"),
]
