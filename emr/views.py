from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from guardian.shortcuts import get_objects_for_user

from audit.models import AuditAction
from audit.service import log_event

from .models import MedicalImage, MedicalRecord


def _user_can_view_record(user, record: MedicalRecord) -> bool:
    return (
        get_objects_for_user(
            user,
            "emr.view_medicalrecord",
            klass=MedicalRecord,
            accept_global_perms=False,
        )
        .filter(pk=record.pk)
        .exists()
    )


def _user_can_view_image(user, img: MedicalImage) -> bool:
    if (
        get_objects_for_user(
            user,
            "emr.view_medicalimage",
            klass=MedicalImage,
            accept_global_perms=False,
        )
        .filter(pk=img.pk)
        .exists()
    ):
        return True
    return _user_can_view_record(user, img.record)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    records = get_objects_for_user(
        request.user, "emr.view_medicalrecord", klass=MedicalRecord, accept_global_perms=False
    )
    return render(request, "emr/dashboard.html", {"records": records})


@login_required
def record_detail(request: HttpRequest, record_id) -> HttpResponse:
    record = get_object_or_404(MedicalRecord, id=record_id)
    allowed = _user_can_view_record(request.user, record)
    log_event(
        request=request,
        user=request.user,
        action=AuditAction.VIEW,
        success=bool(allowed),
        object_type="MedicalRecord",
        object_id=str(record.id),
    )
    if not allowed:
        raise Http404()
    return render(request, "emr/record_detail.html", {"record": record})


@login_required
def image_detail(request: HttpRequest, image_id) -> HttpResponse:
    img = get_object_or_404(MedicalImage, id=image_id)
    allowed = _user_can_view_image(request.user, img)
    log_event(
        request=request,
        user=request.user,
        action=AuditAction.VIEW,
        success=bool(allowed),
        object_type="MedicalImage",
        object_id=str(img.id),
    )
    if not allowed:
        raise Http404()
    return render(request, "emr/image_detail.html", {"img": img})


@login_required
def download_original_dicom(request: HttpRequest, image_id) -> HttpResponse:
    img = get_object_or_404(MedicalImage, id=image_id)
    allowed = request.user.has_perm("download_medicalimage", img) or request.user.has_perm(
        "download_medicalrecord", img.record
    )
    log_event(
        request=request,
        user=request.user,
        action=AuditAction.DOWNLOAD,
        success=bool(allowed),
        object_type="MedicalImage",
        object_id=str(img.id),
    )
    if not allowed:
        raise Http404()
    if not img.original_dicom:
        raise Http404()
    return FileResponse(img.original_dicom.open("rb"), as_attachment=True, filename="image.dcm")


@login_required
def view_preview_png(request: HttpRequest, image_id) -> HttpResponse:
    img = get_object_or_404(MedicalImage, id=image_id)
    allowed = _user_can_view_image(request.user, img)
    log_event(
        request=request,
        user=request.user,
        action=AuditAction.VIEW,
        success=bool(allowed),
        object_type="MedicalImagePreview",
        object_id=str(img.id),
    )
    if not allowed:
        raise Http404()
    if not img.preview_png:
        raise Http404()
    return FileResponse(img.preview_png.open("rb"), as_attachment=False, content_type="image/png")
