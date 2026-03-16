import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditAction(models.TextChoices):
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    LOGIN_FAILED = "login_failed", "Login Failed"
    ACCESS = "access", "Access"
    VIEW = "view", "View"
    DOWNLOAD = "download", "Download"
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"


class AuditEvent(models.Model):
    """
    Immutable audit log row (append-only).

    Rows should never be updated or deleted. Enforce immutability at the model layer,
    and use admin read-only.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )
    actor_role = models.CharField(max_length=20, blank=True)

    action = models.CharField(max_length=20, choices=AuditAction.choices)
    success = models.BooleanField(default=True)

    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=120, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    path = models.CharField(max_length=300, blank=True)
    method = models.CharField(max_length=12, blank=True)
    status_code = models.IntegerField(null=True, blank=True)

    message = models.CharField(max_length=300, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise RuntimeError("AuditEvent is immutable (updates are not allowed).")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # noqa: ARG002
        raise RuntimeError("AuditEvent is immutable (deletes are not allowed).")

    def __str__(self) -> str:
        return f"{self.created_at.isoformat()} {self.action} success={self.success}"

