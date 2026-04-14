from __future__ import annotations

from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, UserRole
from appointments.models import Appointment, AppointmentStatus


class SyncAppointmentStatusesTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username="doc-test",
            password="pass",
            role=UserRole.DOCTOR,
            email="doc-test@example.com",
        )
        self.p1 = User.objects.create_user(username="pat1", password="pass", role=UserRole.PATIENT)
        self.p2 = User.objects.create_user(username="pat2", password="pass", role=UserRole.PATIENT)
        self.p3 = User.objects.create_user(username="pat3", password="pass", role=UserRole.PATIENT)

        self.slot_date = timezone.localdate(timezone.now()) + timedelta(days=1)
        tz = timezone.get_current_timezone()
        self.start, self.end = Appointment.preferred_slot_to_range(self.slot_date, "09:00-10:00", tz=tz)

    def _make_appt(self, patient: User, *, status: str = AppointmentStatus.REQUESTED, created_at_offset_s: int = 0):
        return Appointment.objects.create(
            patient=patient,
            doctor=self.doctor,
            full_name=patient.username,
            mobile_number="+1000000000",
            email=f"{patient.username}@example.com",
            symptoms="test",
            consent=True,
            preferred_date=self.slot_date,
            preferred_time_slot="09:00-10:00",
            scheduled_start=self.start,
            scheduled_end=self.end,
            status=status,
            created_by=patient,
            updated_by=patient,
            created_at=timezone.now() + timedelta(seconds=created_at_offset_s),
        )

    def test_sync_conflicts_confirms_one_cancels_rest(self):
        a1 = self._make_appt(self.p1, created_at_offset_s=0)
        a2 = self._make_appt(self.p2, created_at_offset_s=1)
        a3 = self._make_appt(self.p3, created_at_offset_s=2)

        call_command("sync_appointment_statuses", days_ahead=1)

        a1.refresh_from_db()
        a2.refresh_from_db()
        a3.refresh_from_db()

        statuses = {a1.status, a2.status, a3.status}
        self.assertIn(AppointmentStatus.CONFIRMED, statuses)
        self.assertEqual([a1.status, a2.status, a3.status].count(AppointmentStatus.CONFIRMED), 1)
        self.assertEqual([a1.status, a2.status, a3.status].count(AppointmentStatus.CANCELED), 2)

    def test_sync_keeps_confirmed_and_cancels_requested_duplicates(self):
        confirmed = self._make_appt(self.p1, status=AppointmentStatus.CONFIRMED, created_at_offset_s=0)
        requested = self._make_appt(self.p2, status=AppointmentStatus.REQUESTED, created_at_offset_s=1)

        call_command("sync_appointment_statuses", days_ahead=1)

        confirmed.refresh_from_db()
        requested.refresh_from_db()

        self.assertEqual(confirmed.status, AppointmentStatus.CONFIRMED)
        self.assertEqual(requested.status, AppointmentStatus.CANCELED)

    def test_is_doctor_free_detects_overlap(self):
        self._make_appt(self.p1)

        self.assertFalse(
            Appointment.is_doctor_free(
                doctor_id=self.doctor.pk,
                scheduled_start=self.start,
                scheduled_end=self.end,
            )
        )

