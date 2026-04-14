from __future__ import annotations

import secrets
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserRole
from appointments.models import Appointment, AppointmentStatus


class Command(BaseCommand):
    help = (
        "Seed multiple appointments for the same doctor/date/time-slot (intentional double-booking) so you can verify "
        "`sync_appointment_statuses` cancels conflicts.\n\n"
        "Example:\n"
        "  python manage.py seed_conflicting_appointments --count 5 --days-ahead 1 --slot 09:00-10:00\n"
        "  python manage.py sync_appointment_statuses --days-ahead 1\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--doctor-username",
            default="doc1",
            help="Doctor username (created if missing). Default: doc1",
        )
        parser.add_argument(
            "--patient-prefix",
            default="pat",
            help="Patient username prefix. Default: pat",
        )
        parser.add_argument(
            "--random-patients",
            action="store_true",
            help="Generate random patient usernames/details (still uses the same doctor+date+slot).",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="How many conflicting appointments to create. Default: 3",
        )
        parser.add_argument(
            "--days-ahead",
            type=int,
            default=1,
            help="Schedule the slot this many days from today (local time). Default: 1",
        )
        parser.add_argument(
            "--slot",
            default="09:00-10:00",
            help="Time slot value (must match TIME_SLOT_CHOICES). Default: 09:00-10:00",
        )
        parser.add_argument(
            "--first-confirmed",
            action="store_true",
            help="Make the first appointment CONFIRMED and the rest REQUESTED (tests 'keep confirmed, cancel requested').",
        )

    def handle(self, *args, **options):
        doctor_username: str = str(options["doctor_username"])
        patient_prefix: str = str(options["patient_prefix"])
        random_patients: bool = bool(options["random_patients"])
        count: int = max(1, int(options["count"]))
        days_ahead: int = max(0, int(options["days_ahead"]))
        slot_value: str = str(options["slot"])
        first_confirmed: bool = bool(options["first_confirmed"])

        doctor, created = User.objects.get_or_create(
            username=doctor_username,
            defaults={
                "role": UserRole.DOCTOR,
                "email": f"{doctor_username}@example.com",
                "is_active": True,
            },
        )
        if not created and getattr(doctor, "role", None) != UserRole.DOCTOR:
            doctor.role = UserRole.DOCTOR
            doctor.save(update_fields=["role"])

        schedule_date = timezone.localdate(timezone.now()) + timedelta(days=days_ahead)
        tz = timezone.get_current_timezone()
        scheduled_start, scheduled_end = Appointment.preferred_slot_to_range(schedule_date, slot_value, tz=tz)

        created_ids: list[int] = []
        for idx in range(count):
            if random_patients:
                username = f"{patient_prefix}-{secrets.token_hex(4)}-{idx + 1}"
            else:
                username = f"{patient_prefix}{idx + 1}"
            patient, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": UserRole.PATIENT,
                    "email": f"{username}@example.com",
                    "is_active": True,
                    "first_name": f"Patient{idx + 1}",
                    "last_name": secrets.token_hex(2) if random_patients else "",
                },
            )
            if getattr(patient, "role", None) != UserRole.PATIENT:
                patient.role = UserRole.PATIENT
                patient.save(update_fields=["role"])

            status = AppointmentStatus.REQUESTED
            if idx == 0 and first_confirmed:
                status = AppointmentStatus.CONFIRMED

            appt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                full_name=patient.get_full_name() or f"Patient {idx + 1}",
                mobile_number=f"+1{secrets.randbelow(9_000_000_000) + 1_000_000_000}",
                email=patient.email or f"{username}@example.com",
                symptoms="Seeded test appointment",
                consent=True,
                preferred_date=schedule_date,
                preferred_time_slot=slot_value,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                status=status,
                created_by=patient,
                updated_by=patient,
                created_at=timezone.now() - timedelta(seconds=(count - idx)),
            )
            created_ids.append(appt.pk)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created_ids)} appointments for doctor={doctor.username} "
                f"slot={schedule_date} {slot_value} (scheduled_start={scheduled_start.isoformat()})."
            )
        )
        self.stdout.write(f"Appointment PKs: {', '.join(str(i) for i in created_ids)}")
        self.stdout.write(
            "Next: run `python manage.py sync_appointment_statuses --days-ahead "
            f"{min(14, max(0, days_ahead))}` and re-check statuses."
        )
