from __future__ import annotations

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from .models import MedicalImage, MedicalRecord


def _grant_record_access(record: MedicalRecord) -> None:
    assign_perm("view_medicalrecord", record.patient, record)
    assign_perm("download_medicalrecord", record.patient, record)

    # Creator clinician typically needs access even if primary_doctor isn't set yet.
    assign_perm("view_medicalrecord", record.created_by, record)
    assign_perm("change_medicalrecord", record.created_by, record)
    assign_perm("download_medicalrecord", record.created_by, record)

    if record.primary_doctor_id:
        assign_perm("view_medicalrecord", record.primary_doctor, record)
        assign_perm("change_medicalrecord", record.primary_doctor, record)
        assign_perm("download_medicalrecord", record.primary_doctor, record)

    for member in record.care_team.all():
        assign_perm("view_medicalrecord", member, record)


@receiver(post_save, sender=MedicalRecord)
def _record_saved(sender, instance: MedicalRecord, created: bool, **kwargs):  # noqa: ARG001
    _grant_record_access(instance)


@receiver(m2m_changed, sender=MedicalRecord.care_team.through)
def _care_team_changed(sender, instance: MedicalRecord, action, **kwargs):  # noqa: ARG001
    if action in {"post_add", "post_remove", "post_clear"}:
        _grant_record_access(instance)


@receiver(post_save, sender=MedicalImage)
def _image_saved(sender, instance: MedicalImage, created: bool, **kwargs):  # noqa: ARG001
    assign_perm("view_medicalimage", instance.record.patient, instance)
    assign_perm("download_medicalimage", instance.record.patient, instance)

    assign_perm("view_medicalimage", instance.uploaded_by, instance)
    assign_perm("download_medicalimage", instance.uploaded_by, instance)

    if instance.record.primary_doctor_id:
        assign_perm("view_medicalimage", instance.record.primary_doctor, instance)
        assign_perm("download_medicalimage", instance.record.primary_doctor, instance)

    for member in instance.record.care_team.all():
        assign_perm("view_medicalimage", member, instance)

    # Kick off async processing automatically on upload when Celery is available.
    if created and instance.status == "uploaded":
        try:
            from imaging.tasks import process_dicom_image  # noqa: WPS433
        except ModuleNotFoundError:
            process_dicom_image = None
        if process_dicom_image is not None:
            process_dicom_image.delay(str(instance.id))
