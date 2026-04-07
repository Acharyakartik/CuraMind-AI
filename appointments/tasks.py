from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment, AppointmentStatus
from appointments.reporting import generate_appointments_report_csvs
from appointments.models import SchedulerHeartbeat


def _heartbeat_mark_run(name: str) -> None:
    now = timezone.now()
    SchedulerHeartbeat.objects.update_or_create(
        name=name,
        defaults={"last_run_at": now},
    )


def _heartbeat_mark_success(name: str) -> None:
    now = timezone.now()
    SchedulerHeartbeat.objects.update_or_create(
        name=name,
        defaults={"last_run_at": now, "last_success_at": now, "last_error": ""},
    )


def _heartbeat_mark_error(name: str, err: Exception) -> None:
    now = timezone.now()
    SchedulerHeartbeat.objects.update_or_create(
        name=name,
        defaults={"last_run_at": now, "last_error": f"{type(err).__name__}: {err}"},
    )


@shared_task
def sync_appointment_statuses_task(*, days_ahead: int = 1) -> dict[str, int]:
    """
    Periodic task version of `python manage.py sync_appointment_statuses`.
    Returns counts so logs/monitoring can track changes.
    """
    job_name = "sync_appointment_statuses"
    _heartbeat_mark_run(job_name)
    try:
        if days_ahead < 0:
            days_ahead = 0

        now = timezone.now()
        today = timezone.localdate(now)
        last_day = today + timedelta(days=days_ahead)

        with transaction.atomic():
            # If a requested slot is already in progress or past, cancel it (too late to confirm).
            expired_qs = Appointment.objects.filter(status=AppointmentStatus.REQUESTED, scheduled_start__lte=now)
            expired_count = expired_qs.count()
            if expired_count:
                expired_qs.update(
                    status=AppointmentStatus.CANCELED,
                    canceled_at=now,
                )

            scope_qs = (
                Appointment.objects.filter(scheduled_start__date__gte=today, scheduled_start__date__lte=last_day)
                .exclude(status=AppointmentStatus.CANCELED)
                .order_by("doctor_id", "scheduled_start", "created_at", "pk")
            )

            to_confirm_ids: set[int] = set()
            to_cancel_ids: set[int] = set()

            current_key = None
            bucket: list[Appointment] = []

            def flush_bucket():
                nonlocal bucket
                if not bucket:
                    return
                if len(bucket) == 1:
                    appt = bucket[0]
                    if appt.status == AppointmentStatus.REQUESTED:
                        if appt.scheduled_start <= now:
                            to_cancel_ids.add(appt.pk)
                        else:
                            to_confirm_ids.add(appt.pk)
                    bucket = []
                    return

                confirmed_or_completed = [
                    a for a in bucket if a.status in {AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED}
                ]
                if confirmed_or_completed:
                    keep = confirmed_or_completed[0]
                    for extra in confirmed_or_completed[1:]:
                        to_cancel_ids.add(extra.pk)
                    for a in bucket:
                        if a.pk != keep.pk and a.status == AppointmentStatus.REQUESTED:
                            to_cancel_ids.add(a.pk)
                else:
                    keep = bucket[0]
                    if keep.scheduled_start <= now:
                        # Slot already started: cancel all pending requests.
                        for a in bucket:
                            to_cancel_ids.add(a.pk)
                    else:
                        to_confirm_ids.add(keep.pk)
                        for a in bucket[1:]:
                            to_cancel_ids.add(a.pk)
                bucket = []

            for appt in scope_qs:
                key = (appt.doctor_id, appt.scheduled_start, appt.scheduled_end)
                if current_key is None:
                    current_key = key
                if key != current_key:
                    flush_bucket()
                    current_key = key
                bucket.append(appt)
            flush_bucket()

            confirmed_count = 0
            canceled_conflict_count = 0

            if to_confirm_ids:
                confirmed_count = Appointment.objects.filter(
                    pk__in=to_confirm_ids, status=AppointmentStatus.REQUESTED
                ).update(
                    status=AppointmentStatus.CONFIRMED,
                    confirmed_at=now,
                )

            if to_cancel_ids:
                canceled_conflict_count = Appointment.objects.exclude(status=AppointmentStatus.CANCELED).filter(
                    pk__in=to_cancel_ids
                ).update(
                    status=AppointmentStatus.CANCELED,
                    canceled_at=now,
                )

        payload = {
            "expired_canceled": expired_count,
            "auto_confirmed": confirmed_count,
            "conflict_canceled": canceled_conflict_count,
        }
        _heartbeat_mark_success(job_name)
        return payload
    except Exception as e:  # noqa: BLE001
        _heartbeat_mark_error(job_name, e)
        raise


@shared_task
def generate_appointments_nightly_report_task() -> dict[str, str]:
    """
    Generates a CSV report for *yesterday* (localdate) with scheduled times and cancel/confirm times.
    Writes into `BASE_DIR/var/reports/appointments/`.
    """
    job_name = "nightly_appointments_report"
    _heartbeat_mark_run(job_name)
    try:
        now = timezone.now()
        report_date = timezone.localdate(now) - timedelta(days=1)
        paths = generate_appointments_report_csvs(report_date=report_date)
        _heartbeat_mark_success(job_name)
        return paths
    except Exception as e:  # noqa: BLE001
        _heartbeat_mark_error(job_name, e)
        raise
