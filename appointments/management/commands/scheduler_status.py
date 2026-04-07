from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import SchedulerHeartbeat


class Command(BaseCommand):
    help = "Show whether periodic scheduler jobs appear to be running (based on DB heartbeats)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync-max-age-minutes",
            type=int,
            default=10,
            help="Max age (minutes) for sync heartbeat to be considered running (default: 10).",
        )
        parser.add_argument(
            "--report-max-age-hours",
            type=int,
            default=36,
            help="Max age (hours) for nightly report heartbeat to be considered running (default: 36).",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        sync_max_age = timedelta(minutes=int(options["sync_max_age_minutes"]))
        report_max_age = timedelta(hours=int(options["report_max_age_hours"]))

        def show(name: str, max_age: timedelta):
            hb = SchedulerHeartbeat.objects.filter(name=name).first()
            if hb is None or hb.last_run_at is None:
                self.stdout.write(self.style.ERROR(f"{name}: no heartbeat yet"))
                return
            age = now - hb.last_run_at
            last_run_local = timezone.localtime(hb.last_run_at)
            status = "RUNNING" if age <= max_age and not hb.last_error else "STALE"
            style = self.style.SUCCESS if status == "RUNNING" else self.style.WARNING
            age_seconds = int(age.total_seconds())
            age_minutes = max(0, age_seconds // 60)
            self.stdout.write(
                style(
                    f"{name}: {status} (last_run_at_utc={hb.last_run_at.isoformat()}, "
                    f"last_run_local={last_run_local.isoformat()}, age={age_minutes}m, threshold={int(max_age.total_seconds()//60)}m)"
                )
            )
            if hb.last_error:
                self.stdout.write(self.style.ERROR(f"{name}: last_error={hb.last_error}"))

        show("sync_appointment_statuses", sync_max_age)
        show("nightly_appointments_report", report_max_age)
