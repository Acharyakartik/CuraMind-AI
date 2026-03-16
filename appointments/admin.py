from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "scheduled_start", "scheduled_end", "status")
    list_filter = ("status", "scheduled_start")
    search_fields = ("patient__username", "doctor__username")

