from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "success", "actor", "object_type", "object_id", "ip_address")
    list_filter = ("action", "success", "created_at")
    search_fields = ("actor__username", "object_type", "object_id", "path", "ip_address")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False

