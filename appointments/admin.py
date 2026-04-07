from django.contrib import admin
from django.utils import timezone

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
