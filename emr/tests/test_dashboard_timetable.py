from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserRole
from appointments.models import Appointment, AppointmentStatus


class DashboardTimetableTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(username="doc", password="pass", role=UserRole.DOCTOR)
        self.patient = User.objects.create_user(username="pat", password="pass", role=UserRole.PATIENT)

    def test_doctor_dashboard_shows_timetable(self):
        today = timezone.localdate()
        tz = timezone.get_current_timezone()
        start, end = Appointment.preferred_slot_to_range(today, "09:00-10:00", tz=tz)

        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            preferred_date=today,
            preferred_time_slot="09:00-10:00",
            scheduled_start=start,
            scheduled_end=end,
            status=AppointmentStatus.CONFIRMED,
            consent=True,
        )

        self.client.force_login(self.doctor)
        response = self.client.get(reverse("emr:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Doctor Timetable")
        self.assertContains(response, "09:00-10:00")
        self.assertContains(response, self.patient.username)

    def test_patient_dashboard_hides_timetable(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("emr:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Doctor Timetable")
        self.assertNotContains(response, "Next 7 Days")
