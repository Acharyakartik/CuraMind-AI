from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from appointments.models import SchedulerHeartbeat
from appointments.reporting import generate_appointments_report_csvs


class Command(BaseCommand):
    help = "Generate appointment CSV reports (detail + per-doctor summary) into `var/reports/appointments/`."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default="yesterday",
            help="Report date in YYYY-MM-DD, or 'today'/'yesterday' (default: yesterday).",
        )

    def handle(self, *args, **options):
        job_name = "nightly_appointments_report"
        SchedulerHeartbeat.objects.update_or_create(name=job_name, defaults={"last_run_at": timezone.now()})
        raw = str(options["date"]).strip().lower()
        if raw in {"today", "now"}:
            report_date = timezone.localdate()
        elif raw in {"yesterday", "prev"}:
            report_date = timezone.localdate() - timedelta(days=1)
        else:
            try:
                report_date = date.fromisoformat(raw)
            except ValueError as e:
                raise CommandError("Invalid --date. Use YYYY-MM-DD, today, or yesterday.") from e

        try:
            paths = generate_appointments_report_csvs(report_date=report_date)
            SchedulerHeartbeat.objects.update_or_create(
                name=job_name,
                defaults={"last_run_at": timezone.now(), "last_success_at": timezone.now(), "last_error": ""},
            )
            self.stdout.write(self.style.SUCCESS(f"Report generated for {report_date}:"))
            self.stdout.write(f"- Detail: {paths['detail']}")
            self.stdout.write(f"- Summary: {paths['summary']}")
        except Exception as e:  # noqa: BLE001
            SchedulerHeartbeat.objects.update_or_create(
                name=job_name,
                defaults={"last_run_at": timezone.now(), "last_error": f"{type(e).__name__}: {e}"},
            )
            raise
