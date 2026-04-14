import uuid
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class AppointmentStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    CONFIRMED = "confirmed", "Confirmed"
    COMPLETED = "completed", "Completed"
    CANCELED = "canceled", "Canceled"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class VisitType(models.TextChoices):
    NEW = "new", "New"
    FOLLOW_UP = "follow_up", "Follow-up"


DEPARTMENT_CHOICES = [
    ("general_medicine", "General Medicine"),
    ("cardiology", "Cardiology"),
    ("dermatology", "Dermatology"),
    ("ent", "ENT"),
    ("gastroenterology", "Gastroenterology"),
    ("neurology", "Neurology"),
    ("orthopedics", "Orthopedics"),
    ("pediatrics", "Pediatrics"),
    ("psychiatry", "Psychiatry"),
    ("radiology", "Radiology"),
    ("other", "Other"),
]


TIME_SLOT_CHOICES = [
    ("09:00-10:00", "09:00 - 10:00"),
    ("10:00-11:00", "10:00 - 11:00"),
    ("11:00-12:00", "11:00 - 12:00"),
    ("14:00-15:00", "14:00 - 15:00"),
    ("15:00-16:00", "15:00 - 16:00"),
    ("16:00-17:00", "16:00 - 17:00"),
]


def _report_upload_path(instance: "Appointment", filename: str) -> str:
    return f"private/appointments/{uuid.uuid4()}/{filename}"


class Appointment(models.Model):
    # Core relationship fields
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patient_appointments"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="doctor_appointments"
    )

    # Patient Details (Zoho-style required fields)
    full_name = models.CharField(max_length=120, blank=True, default="")
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    # Appointment Information
    department = models.CharField(max_length=40, choices=DEPARTMENT_CHOICES, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time_slot = models.CharField(max_length=20, choices=TIME_SLOT_CHOICES, blank=True, default="")
    visit_type = models.CharField(max_length=20, choices=VisitType.choices, default=VisitType.NEW)

    # Location / Patient Info
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)

    # Medical Information
    symptoms = models.TextField(blank=True, default="")
    existing_conditions = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)

    # Extra (Optional)
    emergency_contact = models.CharField(max_length=120, blank=True)
    report_upload = models.FileField(upload_to=_report_upload_path, null=True, blank=True)
    invite_guest_email = models.EmailField(blank=True)

    # Final Submission
    consent = models.BooleanField(default=False)

    # Scheduling (can be changed by staff later)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.REQUESTED)
    confirmed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    canceled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Audit fields (requested)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_appointments",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_appointments",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "scheduled_start"]),
            models.Index(fields=["doctor", "scheduled_start"]),
            models.Index(fields=["patient", "preferred_date"]),
            models.Index(fields=["doctor", "preferred_date"]),
        ]

    def __str__(self) -> str:
        return f"Appointment({self.public_id} {self.patient_id} -> {self.doctor_id} @ {self.scheduled_start})"

    def save(self, *args, **kwargs):
        now = timezone.now()
        if self.pk:
            previous = Appointment.objects.filter(pk=self.pk).values_list("status", flat=True).first()
        else:
            previous = None

        if previous != self.status:
            if self.status == AppointmentStatus.CONFIRMED and self.confirmed_at is None:
                self.confirmed_at = now
            if self.status == AppointmentStatus.CANCELED and self.canceled_at is None:
                self.canceled_at = now
            if self.status == AppointmentStatus.COMPLETED and self.completed_at is None:
                self.completed_at = now

        return super().save(*args, **kwargs)

    @property
    def public_id(self) -> str:
        if not self.pk:
            return "APT-??????"
        return f"APT-{int(self.pk):06d}"

    @staticmethod
    def parse_time_slot(slot_value: str) -> tuple[time, time] | None:
        try:
            start_raw, end_raw = slot_value.split("-", 1)
            start_h, start_m = start_raw.split(":", 1)
            end_h, end_m = end_raw.split(":", 1)
            return time(int(start_h), int(start_m)), time(int(end_h), int(end_m))
        except Exception:  # noqa: BLE001
            return None

    @classmethod
    def preferred_slot_to_range(
        cls,
        preferred_date: date,
        preferred_time_slot: str,
        *,
        tz=None,
    ) -> tuple[datetime, datetime]:
        if tz is None:
            tz = timezone.get_current_timezone()

        slot = cls.parse_time_slot(preferred_time_slot)
        if slot is None:
            start_time = timezone.now().time().replace(second=0, microsecond=0)
            end_time = start_time
        else:
            start_time, end_time = slot

        start_dt = timezone.make_aware(datetime.combine(preferred_date, start_time), tz)
        end_dt = timezone.make_aware(datetime.combine(preferred_date, end_time), tz)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=30)
        return start_dt, end_dt

    @classmethod
    def conflicting_for_doctor(
        cls,
        *,
        doctor_id,
        scheduled_start,
        scheduled_end,
        exclude_pk=None,
    ) -> models.QuerySet:
        qs = cls.objects.filter(doctor_id=doctor_id).exclude(status=AppointmentStatus.CANCELED)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        return qs.filter(scheduled_start__lt=scheduled_end, scheduled_end__gt=scheduled_start)

    @classmethod
    def is_doctor_free(
        cls,
        *,
        doctor_id,
        scheduled_start,
        scheduled_end,
        exclude_pk=None,
    ) -> bool:
        return not cls.conflicting_for_doctor(
            doctor_id=doctor_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            exclude_pk=exclude_pk,
        ).exists()

    @classmethod
    def available_time_slots_for_doctor(
        cls,
        *,
        doctor_id,
        preferred_date: date,
        tz=None,
    ) -> list[str]:
        if tz is None:
            tz = timezone.get_current_timezone()

        available: list[str] = []
        for slot_value, _slot_label in TIME_SLOT_CHOICES:
            start_dt, end_dt = cls.preferred_slot_to_range(preferred_date, slot_value, tz=tz)
            if cls.is_doctor_free(doctor_id=doctor_id, scheduled_start=start_dt, scheduled_end=end_dt):
                available.append(slot_value)
        return available

    @classmethod
    def find_next_available_slot_for_doctor(
        cls,
        *,
        doctor_id,
        preferred_date: date,
        tz=None,
        days_ahead: int = 14,
    ) -> tuple[date, str] | None:
        if tz is None:
            tz = timezone.get_current_timezone()

        for offset in range(0, max(0, days_ahead) + 1):
            day = preferred_date + timedelta(days=offset)
            available = cls.available_time_slots_for_doctor(doctor_id=doctor_id, preferred_date=day, tz=tz)
            if available:
                return day, available[0]
        return None


class SchedulerHeartbeat(models.Model):
    """
    Simple persistence to verify periodic jobs are actually running.
    Populated by Celery Beat tasks or Windows Task Scheduler jobs.
    """

    name = models.CharField(max_length=80, unique=True)
    last_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_success_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"SchedulerHeartbeat({self.name})"
