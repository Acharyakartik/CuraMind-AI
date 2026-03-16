import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="medical_records"
    )
    primary_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="primary_records"
    )
    care_team = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="care_team_records")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_records"
    )
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("download_medicalrecord", "Can download medical record exports"),
        ]
        indexes = [models.Index(fields=["patient", "created_at"])]

    def __str__(self) -> str:
        return f"MedicalRecord({self.id})"


def _dicom_upload_path(instance: "MedicalImage", filename: str) -> str:
    return f"private/emr/{instance.record_id}/dicom/{uuid.uuid4()}-{filename}"


def _preview_upload_path(instance: "MedicalImage", filename: str) -> str:
    return f"private/emr/{instance.record_id}/preview/{uuid.uuid4()}-{filename}"


class ImageProcessingStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"


class MedicalImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(MedicalRecord, on_delete=models.PROTECT, related_name="images")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_images"
    )

    original_dicom = models.FileField(upload_to=_dicom_upload_path)
    preview_png = models.ImageField(upload_to=_preview_upload_path, null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=ImageProcessingStatus.choices, default=ImageProcessingStatus.UPLOADED
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        permissions = [
            ("download_medicalimage", "Can download original medical image"),
        ]

    def __str__(self) -> str:
        return f"MedicalImage({self.id})"


class DicomMetadata(models.Model):
    image = models.OneToOneField(MedicalImage, on_delete=models.CASCADE, related_name="dicom")

    modality = models.CharField(max_length=32, blank=True)
    study_instance_uid = models.CharField(max_length=128, blank=True)
    series_instance_uid = models.CharField(max_length=128, blank=True)
    sop_instance_uid = models.CharField(max_length=128, blank=True)

    rows = models.IntegerField(null=True, blank=True)
    columns = models.IntegerField(null=True, blank=True)
    bits_allocated = models.IntegerField(null=True, blank=True)
    photometric_interpretation = models.CharField(max_length=64, blank=True)

    extracted_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self) -> str:
        return f"DicomMetadata(image={self.image_id})"

