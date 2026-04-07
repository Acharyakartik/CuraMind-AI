# CuraMind AI (HIPAA-Oriented Telehealth & Diagnostics)

This repo contains a Django + Celery scaffold for **CuraMind AI**, a telehealth and AI-assisted diagnostics platform:

- Patient/Doctor authentication (custom user model with roles)
- Appointment scheduling (model + admin)
- Secure EMR storage (medical records + medical images)
- DICOM handling using `pydicom` (metadata extraction + PNG preview)
- RBAC and object-level permissions using `django-guardian`
- Immutable audit logging (login, access attempts, view/download)
- Celery tasks for non-blocking image processing

## Quickstart (Dev)

1. Create and activate a virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Copy env: `copy .env.example .env` and edit values
4. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
5. Create admin user: `python manage.py createsuperuser`
6. Run server: `python manage.py runserver`

If you see `ModuleNotFoundError` for a package (example: `celery`), it means you installed Django but not the full project deps.
Use `python -m pip install -r requirements.txt` inside your activated venv.

### Celery (Dev)

Requires a broker (default: Redis):

- Start Redis locally or via Docker (`docker-compose.yml`)
- Run worker: `celery -A curamind_ai worker -l info`

## AdminLTE (Django Admin Theme)

The `/admin/` UI uses AdminLTE via `django-adminlte3`.

- Config: `curamind_ai/settings.py` includes `adminlte3` and `adminlte3_theme` before `django.contrib.admin`
- Install: `python -m pip install -r requirements.txt`
- Production: run `python manage.py collectstatic` (serves AdminLTE static assets)

## Workflow Walkthrough

1. Create users in Django Admin (`/admin/`) and set their `role`:
   - Patient: `role=patient`
   - Clinicians: `role=doctor` or `role=nurse` (set `is_staff=True` if they need admin access)
2. Create a `MedicalRecord` in Admin:
   - Set `patient`, `created_by` (doctor), optional `primary_doctor`, and optional `care_team`
   - Object permissions are granted automatically via `emr/signals.py`
3. Upload a `MedicalImage` (DICOM) in Admin:
   - Set `record`, `uploaded_by`, and upload `original_dicom`
4. Enqueue processing:
   - In the MedicalImage admin list, run the action **Enqueue DICOM processing (Celery)**
5. View results:
   - Web UI dashboard: `/` (lists only records you have object permission to view)
   - Audit log: `/admin/audit/auditevent/`

## Appointment Slot Auto-Sync (Confirm/Cancel)

To auto-confirm requested appointments for **today/tomorrow** and auto-cancel **expired** or **double-booked** slot requests, run:

- `python manage.py sync_appointment_statuses`
- Dry-run: `python manage.py sync_appointment_statuses --dry-run`
- Today only: `python manage.py sync_appointment_statuses --days-ahead 0`

Typical technique is to run this command periodically (every 1–5 minutes) using a scheduler (Linux cron, Windows Task Scheduler),
or wire it into a Celery Beat periodic task.

### Always-on scheduler (recommended)

This project includes Celery Beat schedules in `curamind_ai/settings.py` that:

- Every 5 minutes: sync appointment statuses (auto-confirm / auto-cancel conflicts / auto-cancel expired)
- Every night: generate CSV reports under `var/reports/appointments/`

Times follow Django `TIME_ZONE` (currently `Asia/Kolkata`).

Run these in the background (dev):

- Terminal 1: `celery -A curamind_ai worker -l info`
- Terminal 2: `celery -A curamind_ai beat -l info`

### If Docker Desktop / Redis is not available (Windows)

If you see errors like "failed to connect to the docker API ... dockerDesktopLinuxEngine", Docker Desktop is not running.
You can still automate without Docker by using **Windows Task Scheduler** to run management commands on a timer:

- Every 5 minutes (auto-confirm/auto-cancel): `python manage.py sync_appointment_statuses`
- Every night (report CSVs): `python manage.py generate_appointments_report --date yesterday`

## Notes (Compliance)

This scaffold implements **foundational** security patterns (RBAC, object permissions, audit trails, secure session defaults),
but HIPAA compliance depends on your operational controls (BAAs, hosting, encryption/KMS, policies, monitoring, access reviews).

Practical guidance:
- Avoid using Django `superuser` accounts for day-to-day operations in production; superusers bypass permissions by design.
- Grant access via object-level permissions (guardian) to specific clinicians/care teams per record.
