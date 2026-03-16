from django.conf import settings
from django.db import models
from django.utils import timezone


class AppointmentStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    CONFIRMED = "confirmed", "Confirmed"
    COMPLETED = "completed", "Completed"
    CANCELED = "canceled", "Canceled"


class Appointment(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patient_appointments"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="doctor_appointments"
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.REQUESTED)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "scheduled_start"]),
            models.Index(fields=["doctor", "scheduled_start"]),
        ]

    def __str__(self) -> str:
        return f"Appointment({self.patient_id} -> {self.doctor_id} @ {self.scheduled_start})"

