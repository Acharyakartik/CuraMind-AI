import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure local runtime dirs exist (helps SQLite + file uploads on first run).
(BASE_DIR / "var").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "var" / "media").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "var" / "static").mkdir(parents=True, exist_ok=True)

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "unsafe-dev-key-change-me"),
    ALLOWED_HOSTS=(list, ['*']),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, f"sqlite:///{(BASE_DIR / 'var' / 'db.sqlite3').as_posix()}"),
    CELERY_BROKER_URL=(str, "redis://localhost:6379/0"),
    CELERY_RESULT_BACKEND=(str, "redis://localhost:6379/1"),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
)

environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "adminlte3",
    "adminlte3_theme",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "guardian",
    "csp",
    # Local apps
    "accounts.apps.AccountsConfig",
    "appointments.apps.AppointmentsConfig",
    "emr.apps.EmrConfig",
    "imaging.apps.ImagingConfig",
    "audit.apps.AuditConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "audit.middleware.AuditMiddleware",
]

ROOT_URLCONF = "curamind_ai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            # Make legacy filters available for third-party templates (e.g. admin themes).
            "builtins": ["accounts.templatetags.compat_filters"],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "curamind_ai.wsgi.application"
ASGI_APPLICATION = "curamind_ai.asgi.application"

_db_url_raw = os.environ.get("DATABASE_URL")

# If `.env` sets DATABASE_URL to blank, treat it as unset.
if _db_url_raw is not None and not _db_url_raw.strip():
    _db_url_raw = None

# If a Linux-style SQLite path sneaks into `.env` on Windows (e.g. sqlite:///var/db.sqlite3),
# map it to the project-local `BASE_DIR/var/db.sqlite3` so migrations can run.
if os.name == "nt" and _db_url_raw in {"sqlite:///var/db.sqlite3", "sqlite:////var/db.sqlite3"}:
    _db_url_raw = f"sqlite:///{(BASE_DIR / 'var' / 'db.sqlite3').as_posix()}"

if _db_url_raw is None:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "var" / "db.sqlite3"),
        }
    }
else:
    os.environ["DATABASE_URL"] = _db_url_raw
    DATABASES = {"default": env.db()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "var" / "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "var" / "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

ANONYMOUS_USER_NAME = None

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "emr:dashboard"
LOGOUT_REDIRECT_URL = "login"

SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# CSP: restrict to self by default (adjust when adding CDNs)
CSP_DEFAULT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'self'",)

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 10
