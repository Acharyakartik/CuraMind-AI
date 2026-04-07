from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment, AppointmentStatus
from appointments.models import SchedulerHeartbeat


@dataclass(frozen=True)
class SlotKey:
    doctor_id: int
    scheduled_start: datetime
    scheduled_end: datetime


class Command(BaseCommand):
    help = (
        "Auto-confirm/cancel appointment requests based on current time and slot conflicts.\n\n"
        "Rules:\n"
        "- If status=requested and scheduled_start <= now => cancel (too late)\n"
        "- For slots today/tomorrow: keep at most 1 appointment per doctor+slot\n"
        "  - If any is confirmed/completed => cancel remaining requested (and extra confirmed if any)\n"
        "  - Else (only requested) => confirm 1 (earliest created_at), cancel the rest\n"
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would change, without saving.")
        parser.add_argument(
            "--days-ahead",
            type=int,
            default=1,
            help="How many days ahead (from today) to sync (0=today only, 1=today+tomorrow).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        job_name = "sync_appointment_statuses"
        SchedulerHeartbeat.objects.update_or_create(name=job_name, defaults={"last_run_at": timezone.now()})
        try:
            dry_run: bool = bool(options["dry_run"])
            days_ahead: int = int(options["days_ahead"])
            if days_ahead < 0:
                days_ahead = 0

            now = timezone.now()
            today = timezone.localdate(now)
            last_day = today + timedelta(days=days_ahead)

            qs = (
                Appointment.objects.select_related("doctor")
                .filter(scheduled_start__date__gte=today, scheduled_start__date__lte=last_day)
                .exclude(status=AppointmentStatus.CANCELED)
                .order_by("doctor_id", "scheduled_start", "created_at", "pk")
            )

            expired_requested = (
                # If a requested slot is already in progress or past, cancel it (too late to confirm).
                Appointment.objects.filter(status=AppointmentStatus.REQUESTED, scheduled_start__lte=now)
                .exclude(status=AppointmentStatus.CANCELED)
                .order_by("pk")
            )

            to_confirm: list[Appointment] = []
            to_cancel: list[Appointment] = []

            # 1) Expire old requests (any date).
            expired_count = expired_requested.count()
            if expired_count:
                if not dry_run:
                    expired_requested.update(status=AppointmentStatus.CANCELED, canceled_at=now, updated_by=None)
                self.stdout.write(
                    self.style.WARNING(
                        f"Expired requested appointments canceled: {expired_count} (scheduled_start <= now)"
                    )
                )

            # 2) Resolve double-booking for today/tomorrow (or N days ahead).
            buckets: dict[SlotKey, list[Appointment]] = defaultdict(list)
            for appt in qs:
                buckets[SlotKey(appt.doctor_id, appt.scheduled_start, appt.scheduled_end)].append(appt)

            for _key, appts in buckets.items():
                if len(appts) <= 1:
                    # single entry: optionally auto-confirm if requested and in scope (today..last_day)
                    appt = appts[0]
                    if appt.status == AppointmentStatus.REQUESTED:
                        if appt.scheduled_start <= now:
                            to_cancel.append(appt)
                        else:
                            to_confirm.append(appt)
                    continue

                confirmed_or_completed = [
                    a
                    for a in appts
                    if a.status in {AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED}
                ]

                if confirmed_or_completed:
                    keep = confirmed_or_completed[0]
                    # Extra confirmed/completed duplicates should be canceled (data cleanup).
                    for extra in confirmed_or_completed[1:]:
                        to_cancel.append(extra)
                    for a in appts:
                        if a.pk != keep.pk and a.status == AppointmentStatus.REQUESTED:
                            to_cancel.append(a)
                else:
                    # All requested: confirm the earliest created, cancel the rest.
                    keep = appts[0]
                    if keep.scheduled_start <= now:
                        to_cancel.extend(appts)
                    else:
                        to_confirm.append(keep)
                        for a in appts[1:]:
                            to_cancel.append(a)

            # Apply updates (dedupe by pk).
            confirm_ids = sorted({a.pk for a in to_confirm if a.status == AppointmentStatus.REQUESTED})
            cancel_ids = sorted({a.pk for a in to_cancel if a.status != AppointmentStatus.CANCELED})

            if confirm_ids:
                if not dry_run:
                    Appointment.objects.filter(pk__in=confirm_ids).update(
                        status=AppointmentStatus.CONFIRMED,
                        confirmed_at=now,
                        updated_by=None,
                    )
                self.stdout.write(self.style.SUCCESS(f"Auto-confirmed appointments: {len(confirm_ids)}"))
            else:
                self.stdout.write("Auto-confirmed appointments: 0")

            if cancel_ids:
                if not dry_run:
                    Appointment.objects.filter(pk__in=cancel_ids).update(
                        status=AppointmentStatus.CANCELED,
                        canceled_at=now,
                        updated_by=None,
                    )
                self.stdout.write(self.style.WARNING(f"Auto-canceled appointments (slot conflicts): {len(cancel_ids)}"))
            else:
                self.stdout.write("Auto-canceled appointments (slot conflicts): 0")

            if dry_run:
                self.stdout.write("Dry-run only: no database changes were saved.")

            SchedulerHeartbeat.objects.update_or_create(
                name=job_name,
                defaults={"last_run_at": timezone.now(), "last_success_at": timezone.now(), "last_error": ""},
            )
        except Exception as e:  # noqa: BLE001
            SchedulerHeartbeat.objects.update_or_create(
                name=job_name,
                defaults={"last_run_at": timezone.now(), "last_error": f"{type(e).__name__}: {e}"},
            )
            raise
