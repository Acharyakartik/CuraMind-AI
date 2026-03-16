from __future__ import annotations

import io

import numpy as np
import pydicom
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from emr.models import DicomMetadata, ImageProcessingStatus, MedicalImage


def _to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    arr = arr - np.min(arr)
    denom = np.max(arr) or 1.0
    arr = (arr / denom) * 255.0
    return arr.astype(np.uint8)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_dicom_image(self, medical_image_id: str) -> str:  # noqa: ARG001
    img = MedicalImage.objects.select_related("record").get(id=medical_image_id)
    img.status = ImageProcessingStatus.PROCESSING
    img.processing_error = ""
    img.save(update_fields=["status", "processing_error"])

    try:
        with img.original_dicom.open("rb") as fp:
            ds = pydicom.dcmread(fp, stop_before_pixels=False, force=True)

        meta, _ = DicomMetadata.objects.get_or_create(image=img)
        meta.modality = str(getattr(ds, "Modality", "") or "")
        meta.study_instance_uid = str(getattr(ds, "StudyInstanceUID", "") or "")
        meta.series_instance_uid = str(getattr(ds, "SeriesInstanceUID", "") or "")
        meta.sop_instance_uid = str(getattr(ds, "SOPInstanceUID", "") or "")
        meta.rows = int(getattr(ds, "Rows", 0) or 0) or None
        meta.columns = int(getattr(ds, "Columns", 0) or 0) or None
        meta.bits_allocated = int(getattr(ds, "BitsAllocated", 0) or 0) or None
        meta.photometric_interpretation = str(getattr(ds, "PhotometricInterpretation", "") or "")
        meta.save()

        # Generate a basic preview if pixel data exists.
        if hasattr(ds, "pixel_array"):
            px = ds.pixel_array
            if px.ndim == 3:
                px = px[0]
            px8 = _to_uint8(px)
            pil = Image.fromarray(px8)
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            img.preview_png.save("preview.png", ContentFile(buf.getvalue()), save=False)

        img.status = ImageProcessingStatus.PROCESSED
        img.processed_at = timezone.now()
        img.processing_error = ""
        img.save(update_fields=["status", "processed_at", "processing_error", "preview_png"])
        return medical_image_id
    except Exception as exc:
        img.status = ImageProcessingStatus.FAILED
        img.processing_error = str(exc)[:300]
        img.save(update_fields=["status", "processing_error"])
        raise

