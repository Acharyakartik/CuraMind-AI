from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import UserRole
from emr.models import MedicalRecord


User = get_user_model()


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    role: str
    is_staff: bool = False
    is_superuser: bool = False
    email: str | None = None


class Command(BaseCommand):
    help = "Seed demo users (doctor/nurse/admin/patient) and a few EMR records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset passwords for demo users (password=username).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset_passwords: bool = bool(options["reset_passwords"])

        specs: list[DemoUserSpec] = [
            DemoUserSpec("admin1", UserRole.ADMIN, is_staff=True, is_superuser=True, email="admin1@example.com"),
            DemoUserSpec("doctor1", UserRole.DOCTOR, is_staff=True, email="doctor1@example.com"),
            DemoUserSpec("doctor2", UserRole.DOCTOR, is_staff=True, email="doctor2@example.com"),
            DemoUserSpec("nurse1", UserRole.NURSE, is_staff=True, email="nurse1@example.com"),
            DemoUserSpec("nurse2", UserRole.NURSE, is_staff=True, email="nurse2@example.com"),
            DemoUserSpec("patient1", UserRole.PATIENT, email="patient1@example.com"),
            DemoUserSpec("patient2", UserRole.PATIENT, email="patient2@example.com"),
            DemoUserSpec("patient3", UserRole.PATIENT, email="patient3@example.com"),
            DemoUserSpec("patient4", UserRole.PATIENT, email="patient4@example.com"),
            DemoUserSpec("patient5", UserRole.PATIENT, email="patient5@example.com"),
        ]

        created_count = 0
        updated_count = 0
        password_reset_count = 0

        for spec in specs:
            defaults = {
                "role": spec.role,
                "is_staff": spec.is_staff,
                "is_superuser": spec.is_superuser,
            }
            if spec.email is not None:
                defaults["email"] = spec.email

            user, created = User.objects.update_or_create(username=spec.username, defaults=defaults)
            if created:
                created_count += 1
            else:
                updated_count += 1

            if created or reset_passwords or not user.has_usable_password():
                user.set_password(spec.username)
                user.save(update_fields=["password"])
                password_reset_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo users: created={created_count}, updated={updated_count}, password_set={password_reset_count}"
            )
        )

        doctor1 = User.objects.get(username="doctor1")
        nurse1 = User.objects.get(username="nurse1")
        patient1 = User.objects.get(username="patient1")

        record_specs = [
            "Demo record 1 (created by doctor1)",
            "Demo record 2 (created by doctor1)",
            "Demo record 3 (created by doctor1)",
        ]

        records_created = 0
        for summary in record_specs:
            record, created = MedicalRecord.objects.update_or_create(
                patient=patient1,
                summary=summary,
                defaults={
                    "primary_doctor": doctor1,
                    "created_by": doctor1,
                    "updated_by": doctor1,
                },
            )
            record.care_team.set([doctor1, nurse1])
            if created:
                records_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"MedicalRecord seeded for patient1: total={len(record_specs)}, newly_created={records_created} "
                f"(doctor1 is created_by for all 3)."
            )
        )

