import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(os.getcwd())

# Load environment variables from .env file in setup directory
load_dotenv(BASE_DIR / "setup" / ".env")

# Add apps directory to Python path - ADD THIS LINE
sys.path.insert(0, str(BASE_DIR / 'apps'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True").lower() in ('true', '1', 't')

# SECURITY WARNING: restrict allowed hosts in production!
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(',')

# Application definition
INSTALLED_APPS = [
    'apps.core',
    'apps.users',
    'apps.academics',
    'apps.audit',
    'apps.analytics',
    'apps.attendance',
    'apps.assessment',
    'apps.communication',
    'apps.finance',
    'apps.library',
    'apps.transport',
    'apps.hostels',
    'apps.support',
    'apps.activities',
    'apps.health',
    'rest_framework',

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "templated_mail",
    'crispy_forms',
    'crispy_bootstrap5',
    'django_extensions',
    'channels',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "builtins": [
                "apps.attendance.templatetags.attendance_filters",
                "apps.users.templatetags.user_filters",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'apps.communication.context_processors.notification_count',
                'apps.users.context_processors.user_roles',
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Channels configuration - Using in-memory backend for development
# TODO: Switch to Redis for production
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
MEDIA_URL = "media/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Site framework settings
SITE_ID = 1

# Admins for error reporting
ADMINS = [("Your Name", "your_@nordalms.pythonanywhere.com")]
MANAGERS = ADMINS

# Email settings
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "root@localhost")

# Email timeout and connection settings
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", 30))
EMAIL_SSL_CERTFILE = os.environ.get("EMAIL_SSL_CERTFILE")
EMAIL_SSL_KEYFILE = os.environ.get("EMAIL_SSL_KEYFILE")

# Additional email settings for better reliability
EMAIL_USE_LOCALTIME = False

# Gmail-specific settings for better compatibility
if EMAIL_HOST == "smtp.gmail.com":
    # Ensure TLS is enabled for Gmail
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
    # Gmail requires authentication
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        logger.warning("Gmail SMTP configured but EMAIL_HOST_USER or EMAIL_HOST_PASSWORD not set")

# Simple logging for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
