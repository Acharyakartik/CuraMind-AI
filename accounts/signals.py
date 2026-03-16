from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from audit.service import log_auth_event


@receiver(user_logged_in)
def _user_logged_in(sender, request, user, **kwargs):  # noqa: ARG001
    log_auth_event(request=request, user=user, action="login", success=True)


@receiver(user_logged_out)
def _user_logged_out(sender, request, user, **kwargs):  # noqa: ARG001
    log_auth_event(request=request, user=user, action="logout", success=True)


@receiver(user_login_failed)
def _user_login_failed(sender, credentials, request, **kwargs):  # noqa: ARG001
    # credentials may contain username but we avoid storing raw identifiers beyond what's necessary
    log_auth_event(request=request, user=None, action="login_failed", success=False)

