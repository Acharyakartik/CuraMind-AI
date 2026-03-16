from django.urls import path

from . import views

app_name = "emr"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("emr/records/<uuid:record_id>/", views.record_detail, name="record_detail"),
    path("emr/images/<uuid:image_id>/", views.image_detail, name="image_detail"),
    path("emr/images/<uuid:image_id>/download/", views.download_original_dicom, name="download_original_dicom"),
    path("emr/images/<uuid:image_id>/preview.png", views.view_preview_png, name="view_preview_png"),
]
