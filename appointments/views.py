from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.db import transaction
from django.utils import timezone

from .forms import ScheduleAppointmentForm
from .models import Appointment, AppointmentStatus


@login_required
def schedule_appointment(request: HttpRequest) -> HttpResponse:
    if not getattr(request.user, "is_patient", False):
        messages.error(request, "Only patients can schedule an appointment from this page.")
        return redirect("emr:dashboard")

    if request.method == "POST":
        form = ScheduleAppointmentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            tz = timezone.get_current_timezone()
            appt: Appointment = form.save(commit=False)
            appt.patient = request.user
            appt.status = AppointmentStatus.REQUESTED
            appt.created_by = request.user
            appt.updated_by = request.user

            appt.scheduled_start, appt.scheduled_end = Appointment.preferred_slot_to_range(
                appt.preferred_date, appt.preferred_time_slot, tz=tz
            )

            with transaction.atomic():
                if not Appointment.is_doctor_free(
                    doctor_id=appt.doctor_id,
                    scheduled_start=appt.scheduled_start,
                    scheduled_end=appt.scheduled_end,
                ):
                    next_slot = Appointment.find_next_available_slot_for_doctor(
                        doctor_id=appt.doctor_id,
                        preferred_date=appt.preferred_date,
                        tz=tz,
                        days_ahead=14,
                    )
                    if next_slot is None:
                        form.add_error(
                            "preferred_time_slot",
                            "Doctor is not available in the next 14 days for the configured time slots. Please choose another doctor.",
                        )
                        return render(request, "appointments/schedule.html", {"form": form})

                    new_date, new_slot_value = next_slot
                    appt.preferred_date = new_date
                    appt.preferred_time_slot = new_slot_value
                    appt.scheduled_start, appt.scheduled_end = Appointment.preferred_slot_to_range(
                        appt.preferred_date, appt.preferred_time_slot, tz=tz
                    )

                    messages.warning(
                        request,
                        f"Selected slot was busy. Appointment moved to {appt.preferred_date} ({appt.preferred_time_slot}).",
                    )

                appt.save()
                form.save_m2m()

            messages.success(request, "Appointment request submitted.")
            return redirect("emr:dashboard")
    else:
        form = ScheduleAppointmentForm(user=request.user)

    return render(request, "appointments/schedule.html", {"form": form})
