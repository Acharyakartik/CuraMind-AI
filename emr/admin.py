from django.contrib import admin
from guardian.shortcuts import get_objects_for_user
from guardian.admin import GuardedModelAdmin

from imaging.tasks import process_dicom_image

from .admin_forms import MedicalImageAdminForm
from .models import DicomMetadata, MedicalImage, MedicalRecord


@admin.register(MedicalRecord)
class MedicalRecordAdmin(GuardedModelAdmin):
    list_display = ("id", "patient", "primary_doctor", "created_by", "created_at", "updated_at")
    search_fields = ("patient__username", "primary_doctor__username", "created_by__username", "id")
    filter_horizontal = ("care_team",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return get_objects_for_user(
            request.user,
            "emr.view_medicalrecord",
            klass=qs,
            accept_global_perms=False,
        )


@admin.register(MedicalImage)
class MedicalImageAdmin(GuardedModelAdmin):
    form = MedicalImageAdminForm
    list_display = ("id", "record", "uploaded_by", "status", "created_at", "processed_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "record__id", "uploaded_by__username")
    actions = ("enqueue_processing",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return get_objects_for_user(
            request.user,
            "emr.view_medicalimage",
            klass=qs,
            accept_global_perms=False,
        )

    @admin.action(description="Enqueue DICOM processing (Celery)")
    def enqueue_processing(self, request, queryset):  # noqa: ARG002
        for img in queryset:
            process_dicom_image.delay(str(img.id))


@admin.register(DicomMetadata)
class DicomMetadataAdmin(admin.ModelAdmin):
    list_display = ("image", "modality", "rows", "columns", "extracted_at")
    search_fields = ("image__id", "study_instance_uid", "series_instance_uid", "sop_instance_uid")
