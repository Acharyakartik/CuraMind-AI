# Security strategy (current + recommended next steps)

## Current controls in this repo

- **Auth + RBAC:** `accounts/models.py` defines role-based users; Django auth is configured in `curamind_ai/settings.py`.
- **Object-level access control:** `django-guardian` is configured and used to gate EMR objects (`emr/views.py`, `emr/signals.py`).
- **Audit logging:** append-only `audit/AuditEvent` + middleware logging (`audit/models.py`, `audit/middleware.py`, `audit/service.py`).
- **Secure-by-default web basics:** CSP middleware is enabled; secure cookie flags are partially configurable (`curamind_ai/settings.py`).
- **Private media access (preview):** preview is now served via an authenticated/authorized view (`emr/views.py`), not a public media URL.

## Encryption at rest (what’s missing)

This repo does **not** implement encryption-at-rest by itself. For production, the standard approach is:

- **Database:** use a managed DB with storage encryption enabled (or encrypted volumes for self-hosted DB).
- **Object storage:** store DICOM/derived assets in private buckets with server-side encryption (SSE-KMS).
- **Backups:** encrypted snapshots/backups with controlled access and retention.
- **Keys:** KMS-managed keys; separate duties for key administrators vs application operators.

If you need **field-level encryption** in Django (e.g., for identifiers inside DB rows), add an encryption library and define which fields require it, with careful key rotation and query limitations.

## Access control sign-off checklist

- Confirm which roles can: create records, assign care team, upload images, view metadata, download originals, export records.
- Confirm break-glass rules (who, when, how audited).
- Confirm admin access: who is staff, who is superuser, and how MFA and network restrictions apply.

