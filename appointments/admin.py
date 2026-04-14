import io

from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.contrib import admin
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone

from accounts.models import UserRole

from .models import Appointment, AppointmentStatus, SchedulerHeartbeat


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("public_id", "patient", "doctor", "preferred_date", "preferred_time_slot", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "preferred_date", "department", "visit_type")
    search_fields = ("patient__username", "doctor__username", "full_name", "email", "mobile_number")
    actions = ("mark_confirmed", "mark_completed", "mark_canceled", "mark_requested")

    @admin.action(description="Mark selected appointments as Confirmed")
    def mark_confirmed(self, request, queryset):
        now = timezone.now()
        queryset.update(status=AppointmentStatus.CONFIRMED, confirmed_at=now, updated_by=request.user)

    @admin.action(description="Mark selected appointments as Completed")
    def mark_completed(self, request, queryset):
        now = timezone.now()
        queryset.update(status=AppointmentStatus.COMPLETED, completed_at=now, updated_by=request.user)

    @admin.action(description="Mark selected appointments as Canceled")
    def mark_canceled(self, request, queryset):
        now = timezone.now()
        queryset.update(status=AppointmentStatus.CANCELED, canceled_at=now, updated_by=request.user)

    @admin.action(description="Mark selected appointments as Requested")
    def mark_requested(self, request, queryset):
        queryset.update(status=AppointmentStatus.REQUESTED, updated_by=request.user)

    def save_model(self, request, obj, form, change):
        if getattr(obj, "created_by_id", None) is None:
            obj.created_by = request.user
        obj.updated_by = request.user
        return super().save_model(request, obj, form, change)


@admin.register(SchedulerHeartbeat)
class SchedulerHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("name", "last_run_at", "last_success_at", "updated_at")
    search_fields = ("name",)
    change_list_template = "admin/appointments/schedulerheartbeat/change_list.html"

    @staticmethod
    def _is_scheduler_admin(user) -> bool:
        if not getattr(user, "is_active", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return getattr(user, "role", None) == UserRole.ADMIN

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "run-sync/",
                self.admin_site.admin_view(self.run_sync_view),
                name="appointments_schedulerheartbeat_run_sync",
            ),
            path(
                "run-report/",
                self.admin_site.admin_view(self.run_report_view),
                name="appointments_schedulerheartbeat_run_report",
            ),
            path(
                "reports/",
                self.admin_site.admin_view(self.report_view),
                name="appointments_schedulerheartbeat_reports",
            ),
        ]
        return custom + urls

    def report_view(self, request: HttpRequest) -> HttpResponse:
        if not self._is_scheduler_admin(request.user):
            raise PermissionDenied

        raw = str(request.GET.get("date", "today")).strip().lower()
        if raw in {"today", "now"}:
            report_date = timezone.localdate()
        elif raw in {"yesterday", "prev"}:
            report_date = timezone.localdate() - timedelta(days=1)
        elif raw in {"tomorrow", "next"}:
            report_date = timezone.localdate() + timedelta(days=1)
        else:
            try:
                report_date = date.fromisoformat(raw)
            except ValueError:
                messages.error(request, "Invalid date. Use YYYY-MM-DD, today, tomorrow, or yesterday.")
                return redirect(".")

        tz = timezone.get_current_timezone()

        def _range_for(d: date):
            start = timezone.make_aware(datetime.combine(d, time.min), tz)
            return start, start + timedelta(days=1)

        day_start, day_end = _range_for(report_date)

        appts = (
            Appointment.objects.select_related("doctor", "patient")
            .filter(scheduled_start__gte=day_start, scheduled_start__lt=day_end)
            .order_by("doctor__username", "scheduled_start", "pk")
        )
        appt_count = appts.count()

        # If the user asks for "today" but there are no appointments today, show the next
        # day that has appointments so the page doesn't look broken to admins.
        if appt_count == 0 and raw in {"today", "now"}:
            next_appt = (
                Appointment.objects.filter(scheduled_start__gte=day_end)
                .order_by("scheduled_start")
                .only("scheduled_start")
                .first()
            )
            if next_appt is not None:
                next_date = timezone.localdate(next_appt.scheduled_start, timezone=tz)
                if next_date != report_date:
                    messages.info(
                        request,
                        f"No appointments for {report_date.isoformat()}. Showing next date with appointments: {next_date.isoformat()}.",
                    )
                    report_date = next_date
                    day_start, day_end = _range_for(report_date)
                    appts = (
                        Appointment.objects.select_related("doctor", "patient")
                        .filter(scheduled_start__gte=day_start, scheduled_start__lt=day_end)
                        .order_by("doctor__username", "scheduled_start", "pk")
                    )
                    appt_count = appts.count()
        max_rows = 500
        appts_limited = list(appts[:max_rows])

        by_doctor: dict[str, dict[str, int]] = {}
        total = {"requested": 0, "confirmed": 0, "completed": 0, "canceled": 0, "total": 0}
        for a in appts_limited:
            doctor = getattr(a.doctor, "username", str(a.doctor_id))
            by_doctor.setdefault(doctor, {"requested": 0, "confirmed": 0, "completed": 0, "canceled": 0, "total": 0})
            by_doctor[doctor][a.status] = by_doctor[doctor].get(a.status, 0) + 1
            by_doctor[doctor]["total"] += 1
            total[a.status] = total.get(a.status, 0) + 1
            total["total"] += 1

        out_dir = Path(getattr(settings, "BASE_DIR", Path.cwd())) / "var" / "reports" / "appointments"
        detail_path = out_dir / f"appointments-{report_date.isoformat()}.csv"
        summary_path = out_dir / f"appointments-summary-{report_date.isoformat()}.csv"

        context = dict(
            self.admin_site.each_context(request),
            title=f"Appointments Report ({report_date.isoformat()})",
            report_date=report_date,
            doctor_rows=[(k, by_doctor[k]) for k in sorted(by_doctor.keys())],
            totals=total,
            appointment_count=appt_count,
            appointment_limit=max_rows,
            appointments=appts_limited,
            csv_detail_path=str(detail_path),
            csv_summary_path=str(summary_path),
            csv_detail_exists=detail_path.exists(),
            csv_summary_exists=summary_path.exists(),
        )
        from django.template.response import TemplateResponse

        return TemplateResponse(request, "admin/appointments/schedulerheartbeat/report_view.html", context)

    def run_sync_view(self, request: HttpRequest) -> HttpResponse:
        if not self._is_scheduler_admin(request.user):
            raise PermissionDenied
        if request.method != "POST":
            return redirect("..")

        out = io.StringIO()
        call_command("sync_appointment_statuses", days_ahead=1, stdout=out)
        messages.success(request, "Ran sync_appointment_statuses (days_ahead=1).")
        output = out.getvalue().strip()
        if output:
            messages.info(request, output)
        return redirect("..")

    def run_report_view(self, request: HttpRequest) -> HttpResponse:
        if not self._is_scheduler_admin(request.user):
            raise PermissionDenied
        if request.method != "POST":
            return redirect("..")

        out = io.StringIO()
        call_command("generate_appointments_report", date="yesterday", stdout=out)
        messages.success(request, "Ran nightly_appointments_report for yesterday.")
        output = out.getvalue().strip()
        if output:
            messages.info(request, output)
        return redirect("..")
