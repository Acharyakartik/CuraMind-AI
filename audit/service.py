from __future__ import annotations

from typing import Any

from .models import AuditAction, AuditEvent


def _ip_from_request(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_event(
    *,
    request,
    user,
    action: str,
    success: bool,
    object_type: str = "",
    object_id: str = "",
    message: str = "",
    extra: dict[str, Any] | None = None,
    status_code: int | None = None,
) -> None:
    actor_role = ""
    if user is not None and hasattr(user, "role"):
        actor_role = str(getattr(user, "role", "") or "")
    AuditEvent.objects.create(
        actor=user if user and getattr(user, "is_authenticated", False) else None,
        actor_role=actor_role,
        action=action,
        success=success,
        object_type=object_type,
        object_id=object_id,
        ip_address=_ip_from_request(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request else ""),
        path=(getattr(request, "path", "")[:300] if request else ""),
        method=((getattr(request, "method", "") or "")[:12] if request else ""),
        status_code=status_code,
        message=message[:300],
        extra=extra or {},
    )


def log_auth_event(*, request, user, action: str, success: bool) -> None:
    if action == "login":
        audit_action = AuditAction.LOGIN
    elif action == "logout":
        audit_action = AuditAction.LOGOUT
    else:
        audit_action = AuditAction.LOGIN_FAILED
    log_event(request=request, user=user, action=audit_action, success=success, object_type="auth", object_id="")


def log_request_event(*, request, response) -> None:
    user = getattr(request, "user", None)
    status_code = int(getattr(response, "status_code", 0) or 0)
    log_event(
        request=request,
        user=user,
        action=AuditAction.ACCESS,
        success=200 <= status_code < 500,
        object_type="http",
        object_id="",
        status_code=status_code,
    )
