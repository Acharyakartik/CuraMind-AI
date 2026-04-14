from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from appointments.models import Appointment


def generate_appointments_report_csvs(*, report_date: date) -> dict[str, str]:
    """
    Generates 2 CSVs:
    - Detail: all appointments for the report date
    - Summary: per-doctor counts by status

    Output directory: `BASE_DIR/var/reports/appointments/`
    """
    base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    out_dir = base_dir / "var" / "reports" / "appointments"
    out_dir.mkdir(parents=True, exist_ok=True)

    detail_path = out_dir / f"appointments-{report_date.isoformat()}.csv"
    summary_path = out_dir / f"appointments-summary-{report_date.isoformat()}.csv"

    tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.combine(report_date, time.min), tz)
    day_end = day_start + timedelta(days=1)

    appts = (
        Appointment.objects.select_related("doctor", "patient")
        .filter(scheduled_start__gte=day_start, scheduled_start__lt=day_end)
        .order_by("doctor__username", "scheduled_start", "pk")
    )

    with detail_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "public_id",
                "doctor",
                "patient",
                "scheduled_start",
                "scheduled_end",
                "status",
                "created_at",
                "confirmed_at",
                "canceled_at",
                "completed_at",
            ]
        )
        for a in appts:
            w.writerow(
                [
                    a.public_id,
                    getattr(a.doctor, "username", a.doctor_id),
                    getattr(a.patient, "username", a.patient_id),
                    a.scheduled_start.isoformat(),
                    a.scheduled_end.isoformat(),
                    a.status,
                    a.created_at.isoformat() if a.created_at else "",
                    a.confirmed_at.isoformat() if a.confirmed_at else "",
                    a.canceled_at.isoformat() if a.canceled_at else "",
                    a.completed_at.isoformat() if a.completed_at else "",
                ]
            )

    by_doctor: dict[str, dict[str, int]] = {}
    for a in appts:
        doctor = getattr(a.doctor, "username", str(a.doctor_id))
        by_doctor.setdefault(doctor, {"requested": 0, "confirmed": 0, "completed": 0, "canceled": 0})
        by_doctor[doctor][a.status] = by_doctor[doctor].get(a.status, 0) + 1

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doctor", "requested", "confirmed", "completed", "canceled", "total"])
        for doctor in sorted(by_doctor.keys()):
            row = by_doctor[doctor]
            total = sum(row.values())
            w.writerow(
                [
                    doctor,
                    row.get("requested", 0),
                    row.get("confirmed", 0),
                    row.get("completed", 0),
                    row.get("canceled", 0),
                    total,
                ]
            )

    return {"detail": str(detail_path), "summary": str(summary_path)}
