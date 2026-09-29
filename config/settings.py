from pathlib import Path
import os
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = Path(os.environ.get("DJANGO_ENV_FILE", BASE_DIR / ".env"))
load_dotenv(ENV_FILE)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [
        value.strip()
        for value in os.environ.get(name, default).split(",")
        if value.strip()
    ]


DEVELOPMENT_SECRET_KEY = "somlab-local-development-key-change-before-production-2026"
DEBUG = env_bool("DJANGO_DEBUG", True)
configured_secret_key = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if not DEBUG and (
    not configured_secret_key
    or configured_secret_key == DEVELOPMENT_SECRET_KEY
    or configured_secret_key.startswith("replace-with-")
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a strong, unique value in production."
    )
SECRET_KEY = configured_secret_key or DEVELOPMENT_SECRET_KEY

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,[::1]" if DEBUG else "",
)
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain explicit production hostnames."
    )

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        f"https://{'*' if host.startswith('.') else ''}{host.lstrip('.')}"
        for host in ALLOWED_HOSTS
    ]
for origin in CSRF_TRUSTED_ORIGINS:
    parsed_origin = urlparse(origin)
    if (
        parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.netloc
        or (not DEBUG and parsed_origin.scheme != "https")
    ):
        raise ImproperlyConfigured(
            "DJANGO_CSRF_TRUSTED_ORIGINS must contain valid HTTPS origins in production."
        )

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "catalog",
    "orders",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "dashboard.customer_uploads.CustomerVideoUploadMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "core.context_processors.site_context",
        ],
    },
}]

WSGI_APPLICATION = "config.wsgi.application"
database_path = os.environ.get("DJANGO_DB_PATH", "").strip()
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Keep the production database outside the release directory so code
        # deployments cannot accidentally replace it. Local development still
        # defaults to the traditional project-level db.sqlite3 file.
        "NAME": Path(database_path) if database_path else BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "timeout": int(os.environ.get("DJANGO_DB_TIMEOUT", "20")),
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Mogadishu"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "01. Logo"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
CUSTOMER_VIDEO_FFMPEG = os.environ.get("CUSTOMER_VIDEO_FFMPEG", "")
CUSTOMER_VIDEO_PROCESSING_TIMEOUT = int(os.environ.get("CUSTOMER_VIDEO_PROCESSING_TIMEOUT", "7200"))

R2_ENABLED = os.environ.get("R2_ENABLED", "0") == "1"
if R2_ENABLED:
    R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
    R2_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"].rstrip("/")
    if not DEBUG and urlparse(R2_ENDPOINT_URL).scheme != "https":
        raise ImproperlyConfigured("R2_ENDPOINT_URL must use HTTPS in production.")
    if R2_PUBLIC_URL and (
        urlparse(R2_PUBLIC_URL).scheme not in {"http", "https"}
        or not urlparse(R2_PUBLIC_URL).netloc
        or (not DEBUG and urlparse(R2_PUBLIC_URL).scheme != "https")
    ):
        raise ImproperlyConfigured(
            "R2_PUBLIC_URL must be a valid HTTPS URL in production."
        )
    r2_options = {
        "access_key": os.environ["R2_ACCESS_KEY_ID"],
        "secret_key": os.environ["R2_SECRET_ACCESS_KEY"],
        "bucket_name": os.environ.get("R2_BUCKET_NAME", "somlab"),
        "endpoint_url": R2_ENDPOINT_URL,
        "region_name": "auto",
        "signature_version": "s3v4",
        "addressing_style": "path",
        "file_overwrite": False,
        "max_memory_size": 8 * 1024 * 1024,
        "default_acl": None,
        "location": "media",
        "object_parameters": {
            "CacheControl": "public, max-age=86400",
        },
    }
    if R2_PUBLIC_URL:
        r2_options.update({
            "custom_domain": urlparse(R2_PUBLIC_URL).netloc,
            "url_protocol": f"{urlparse(R2_PUBLIC_URL).scheme}:",
            "querystring_auth": False,
        })
        MEDIA_URL = f"{R2_PUBLIC_URL}/media/"
    else:
        r2_options.update({
            "querystring_auth": True,
            "querystring_expire": 3600,
        })
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": r2_options,
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "admin_login"
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    (
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG else "django.core.mail.backends.smtp.EmailBackend"
    ),
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "localhost" if DEBUG else "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "0" if DEBUG else "1") == "1"
EMAIL_USE_SSL = os.environ.get("DJANGO_EMAIL_USE_SSL", "0") == "1"
EMAIL_TIMEOUT = int(os.environ.get("DJANGO_EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL", "Somlab Website <info@somlab.so>"
)
if not DEBUG:
    if EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        raise ImproperlyConfigured("Production inquiry email requires the SMTP backend.")
    if not EMAIL_HOST or not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise ImproperlyConfigured("Production SMTP host, user and password are required.")
    if EMAIL_USE_TLS == EMAIL_USE_SSL:
        raise ImproperlyConfigured("Enable exactly one of SMTP TLS or SSL in production.")

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS", False
    )
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)
    if env_bool("DJANGO_TRUST_PROXY_PROTO", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0
