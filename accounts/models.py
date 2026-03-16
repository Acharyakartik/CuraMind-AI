from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    PATIENT = "patient", "Patient"
    DOCTOR = "doctor", "Doctor"
    NURSE = "nurse", "Nurse"
    ADMIN = "admin", "Admin"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.PATIENT)

    @property
    def is_patient(self) -> bool:
        return self.role == UserRole.PATIENT

    @property
    def is_doctor(self) -> bool:
        return self.role == UserRole.DOCTOR

    @property
    def is_nurse(self) -> bool:
        return self.role == UserRole.NURSE

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN

