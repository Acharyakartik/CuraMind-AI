from __future__ import annotations

from django.db.backends.signals import connection_created
from django.dispatch import receiver
from django.db.utils import OperationalError


@receiver(connection_created)
def _set_sqlite_pragmas(sender, connection, **kwargs):  # noqa: ARG001
    if getattr(connection, "vendor", None) != "sqlite":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=MEMORY;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
    except OperationalError:
        # If the existing DB/journal is in a bad state (locked/corrupt), don't break read-only commands.
        return
