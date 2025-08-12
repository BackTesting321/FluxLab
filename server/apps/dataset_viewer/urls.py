from django.urls import path

from . import views

urlpatterns = [
    path("", views.datasets_list),
    path("scan", views.dataset_scan),
]