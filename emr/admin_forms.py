from __future__ import annotations

import io

import pydicom
from django import forms
from django.core.files.base import ContentFile

from .models import MedicalImage


_DICOM_PHI_TAGS = (
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "AccessionNumber",
    "InstitutionName",
    "InstitutionAddress",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "OperatorsName",
)


def _looks_like_dicom(payload: bytes) -> bool:
    if len(payload) >= 132 and payload[128:132] == b"DICM":
        return True
    try:
        pydicom.dcmread(io.BytesIO(payload), stop_before_pixels=True, force=False)
        return True
    except Exception:
        return False


def _basic_deidentify_dicom(payload: bytes) -> bytes:
    ds = pydicom.dcmread(io.BytesIO(payload), stop_before_pixels=False, force=True)
    ds.remove_private_tags()

    for tag_name in _DICOM_PHI_TAGS:
        if hasattr(ds, tag_name):
            try:
                setattr(ds, tag_name, "")
            except Exception:
                # If a tag is invalid to set, skip rather than failing the upload.
                pass

    # Helpful flags (not a guarantee of safe de-identification).
    try:
        ds.PatientIdentityRemoved = "YES"
        ds.DeidentificationMethod = "Basic tag blanking + remove_private_tags"
    except Exception:
        pass

    buf = io.BytesIO()
    ds.save_as(buf, write_like_original=False)
    return buf.getvalue()


class MedicalImageAdminForm(forms.ModelForm):
    class Meta:
        model = MedicalImage
        fields = "__all__"

    def clean_original_dicom(self):
        f = self.cleaned_data.get("original_dicom")
        if not f:
            return f

        payload = f.read()
        f.seek(0)

        if not _looks_like_dicom(payload):
            raise forms.ValidationError("Unsupported file: expected a valid DICOM (.dcm).")

        try:
            sanitized = _basic_deidentify_dicom(payload)
        except Exception as exc:
            raise forms.ValidationError(f"Could not parse DICOM for sanitization: {exc}") from exc

        name = getattr(f, "name", "") or "upload.dcm"
        if not name.lower().endswith(".dcm"):
            name = f"{name}.dcm"
        return ContentFile(sanitized, name=name)

