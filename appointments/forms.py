from __future__ import annotations

from django import forms

from accounts.models import User, UserRole

from .models import Appointment


class ScheduleAppointmentForm(forms.ModelForm):
    consent = forms.BooleanField(required=True)

    class Meta:
        model = Appointment
        fields = [
            # Patient Details
            "full_name",
            "gender",
            "date_of_birth",
            "age",
            "mobile_number",
            "email",
            # Appointment Information
            "department",
            "doctor",
            "preferred_date",
            "preferred_time_slot",
            "visit_type",
            # Location / Patient Info
            "city",
            "address",
            # Medical Information
            "symptoms",
            "existing_conditions",
            "additional_notes",
            # Extra
            "emergency_contact",
            "report_upload",
            "invite_guest_email",
            # Final submission
            "consent",
        ]
        widgets = {
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "symptoms": forms.Textarea(attrs={"rows": 3}),
            "existing_conditions": forms.Textarea(attrs={"rows": 2}),
            "additional_notes": forms.Textarea(attrs={"rows": 2}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user: User | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

        self.fields["doctor"].queryset = (
            User.objects.filter(role=UserRole.DOCTOR, is_active=True).order_by("username")
        )

        if user is not None:
            if not self.initial.get("email") and user.email:
                self.initial["email"] = user.email
            full_name = user.get_full_name()
            if not self.initial.get("full_name") and full_name:
                self.initial["full_name"] = full_name

        self.fields["full_name"].required = True
        self.fields["mobile_number"].required = True
        self.fields["email"].required = True
        self.fields["symptoms"].required = True
        self.fields["preferred_date"].required = True
        self.fields["preferred_time_slot"].required = True
        self.fields["doctor"].required = True

    def clean(self):
        cleaned = super().clean()
        dob = cleaned.get("date_of_birth")
        age = cleaned.get("age")
        if dob is None and age is None:
            # Keep it optional, but if you want to force one of them, enforce here.
            return cleaned
        return cleaned

