from __future__ import annotations

from dataclasses import dataclass

from django.utils.deprecation import MiddlewareMixin

from .service import log_request_event


@dataclass(frozen=True)
class _AuditConfig:
    audited_prefixes: tuple[str, ...] = ("/admin/", "/accounts/", "/emr/")


class AuditMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self._cfg = _AuditConfig()

    def process_response(self, request, response):
        path = getattr(request, "path", "") or ""
        if any(path.startswith(p) for p in self._cfg.audited_prefixes):
            log_request_event(request=request, response=response)
        return response

