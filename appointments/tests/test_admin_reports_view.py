from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserRole
from appointments.models import Appointment, AppointmentStatus


class AdminReportViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            password="pass",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )
        self.doctor = User.objects.create_user(username="doc", password="pass", role=UserRole.DOCTOR)
        self.patient = User.objects.create_user(username="pat", password="pass", role=UserRole.PATIENT)

    def test_admin_report_view_renders(self):
        report_date = timezone.localdate(timezone.now())
        tz = timezone.get_current_timezone()
        start, end = Appointment.preferred_slot_to_range(report_date, "09:00-10:00", tz=tz)
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            full_name="Pat",
            mobile_number="+1000000000",
            email="pat@example.com",
            symptoms="x",
            consent=True,
            preferred_date=report_date,
            preferred_time_slot="09:00-10:00",
            scheduled_start=start,
            scheduled_end=end,
            status=AppointmentStatus.REQUESTED,
            created_by=self.patient,
            updated_by=self.patient,
            created_at=timezone.now() - timedelta(minutes=1),
        )

        self.client.force_login(self.admin)
        url = reverse("admin:appointments_schedulerheartbeat_reports")
        resp = self.client.get(url, {"date": report_date.isoformat()})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Appointments Report")
        self.assertContains(resp, "Detail")

