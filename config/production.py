from .base import *

# Ensure logs directory exists for production logging
import os
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

# Set production site domain for password reset emails
def configure_production_site():
    """Configure the Site model for production with correct domain."""
    try:
        from django.contrib.sites.models import Site
        site_domain = os.environ.get('SITE_DOMAIN', 'NordaLMS.pythonanywhere.com')
        site_name = os.environ.get('SITE_NAME', 'Nexus Intelligence School Management System')

        site, created = Site.objects.get_or_create(
            id=1,
            defaults={'name': site_name, 'domain': site_domain}
        )
        if not created:
            site.name = site_name
            site.domain = site_domain
            site.save()

        print(f'Site configured: {site_name} - {site_domain}')
    except Exception as e:
        print(f'Warning: Could not configure site: {e}')

# Configure site after Django is ready
# This will run when Django loads the production settings
from django.apps import apps
from django.db.models.signals import post_migrate

def configure_site_after_migrate(sender, **kwargs):
    configure_production_site()

post_migrate.connect(configure_site_after_migrate)

DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 't']

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Static files for production
STATIC_ROOT = BASE_DIR / "staticfiles"

# Security settings for production
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ['true', '1', 't']
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Email settings for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@your_production_domain.com")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "errors@your_production_domain.com")

# Logging for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {
        "handlers": ["console", "file"],
        "level": "WARNING",
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/production.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
