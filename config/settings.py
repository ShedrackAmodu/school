import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to Python path
sys.path.insert(0, str(BASE_DIR / 'apps'))

# ============================
# CORE DJANGO SETTINGS
# ============================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'aClLR_f-mFhadOdKRnVT-BLWhMJ5JJiQyB7veIS1U-XiSZc1sp-5CzzQzdOJizV00Zw'

# SECURITY SETTINGS - DEBUG is now controlled below based on environment
# Remove the duplicate DEBUG setting at the bottom

# Application definition
INSTALLED_APPS = [
    # Custom apps
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

    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party apps
    "templated_mail",
    'crispy_forms',
    'crispy_bootstrap5',
    'django_extensions',
    'channels',  # Note: PythonAnywhere free tier doesn't support WebSockets

    # Authentication & Social Auth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For serving static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Single-tenant middleware (sets Excellent Academy as default)
    "apps.core.middleware.TenantMiddleware",

    # Allauth middleware
    "allauth.account.middleware.AccountMiddleware",
]

# URL Configuration
ROOT_URLCONF = "config.urls"

# Template Configuration
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
                    "django.contrib.sites.context_processors.site",
                    'apps.core.context_processors.tenant_context',
                    'apps.core.context_processors.current_institution',
                    'apps.communication.context_processors.notification_count',
                    'apps.users.context_processors.user_roles',
                ],
        },
    },
]

# WSGI & ASGI Configuration
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ============================
# DATABASE CONFIGURATION
# ============================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Check if we're on PythonAnywhere (defined early for CHANNEL_LAYERS)
ON_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ

# ============================
# CHANNELS CONFIGURATION
# ============================

if ON_PYTHONANYWHERE:
    # PythonAnywhere doesn't support WebSockets on free tier, so we disable Channels
    # For paid tier, you can enable Redis
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
else:
    # For local development, use InMemoryChannelLayer (Note: For production, use Redis)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ============================
# PASSWORD VALIDATION
# ============================

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

# ============================
# INTERNATIONALIZATION
# ============================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ============================
# STATIC & MEDIA FILES
# ============================

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# For development
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# For production on PythonAnywhere
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================
# AUTHENTICATION
# ============================

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'apps.users.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Login URLs
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# Django Allauth Settings (updated for allauth >= 0.56.0)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_RATE_LIMITS = {
    'confirm_email': '5/180s',
    'login_failed': '10/m',
    'signup': '20/m',
}

# Disable automatic signup via social accounts - we only allow account linking
ACCOUNT_ADAPTER = 'apps.users.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'apps.users.adapters.CustomSocialAccountAdapter'

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = False  # Don't automatically sign up users
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # We'll handle email verification ourselves
SOCIALACCOUNT_QUERY_EMAIL = True  # Ask for email permission from Google

# Social account providers
# TODO: Replace with actual Google OAuth credentials from Google Cloud Console
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'APP': {
            'client_id': 'YOUR_GOOGLE_CLIENT_ID_HERE',  # Replace with actual client ID
            'secret': 'YOUR_GOOGLE_CLIENT_SECRET_HERE',  # Replace with actual client secret
            'key': ''
        }
    }
}

# ============================
# PRIMARY KEY FIELD TYPE
# ============================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================
# ADMINISTRATORS
# ============================

ADMINS = [("Excellent Academy Admin", "supereaglepilot@gmail.com")]
MANAGERS = ADMINS

# ============================
# EMAIL CONFIGURATION
# ============================

# Email Backend Configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', "supereaglepilot@gmail.com")  # Use environment variable
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', "lwuiaxslniodkwcr")  # Use environment variable (app password)
EMAIL_TIMEOUT = 30
DEFAULT_FROM_EMAIL = "noreply@excellentacademy.pythonanywhere.com"
SERVER_EMAIL = "errors@excellentacademy.pythonanywhere.com"

# ============================
# PAYSTACK CONFIGURATION
# ============================

# Paystack API Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', 'sk_test_1234567890abcdef1234567890abcdef1234567890abcdef')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', 'pk_test_1234567890abcdef1234567890abcdef1234567890abcdef')
PAYSTACK_TEST_MODE = os.getenv('PAYSTACK_TEST_MODE', 'True').lower() == 'true'

# Paystack URLs
PAYSTACK_BASE_URL = 'https://api.paystack.co' if not PAYSTACK_TEST_MODE else 'https://api.paystack.co'
PAYSTACK_PAYMENT_URL = f'{PAYSTACK_BASE_URL}/transaction'
PAYSTACK_CUSTOMER_URL = f'{PAYSTACK_BASE_URL}/customer'
PAYSTACK_PLAN_URL = f'{PAYSTACK_BASE_URL}/plan'
PAYSTACK_SUBSCRIPTION_URL = f'{PAYSTACK_BASE_URL}/subscription'

# Paystack Webhook Configuration
PAYSTACK_WEBHOOK_SECRET = os.getenv('PAYSTACK_WEBHOOK_SECRET', 'your_webhook_secret_key')
PAYSTACK_WEBHOOK_URL = '/finance/webhooks/paystack/'

# Paystack Payment Settings
PAYSTACK_CURRENCY = 'NGN'
PAYSTACK_PAYMENT_CHANNELS = ['card', 'bank', 'ussd', 'qr', 'mobile_money']
PAYSTACK_CALLBACK_URL = os.getenv('PAYSTACK_CALLBACK_URL', 'http://localhost:8000/finance/payments/callback/')

# For development, you can set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your environment
# Example: export EMAIL_HOST_USER="your-email@gmail.com"
# Example: export EMAIL_HOST_PASSWORD="your-gmail-app-password"
# If not set, defaults above will be used (but should be set for each developer)

# ============================
# SECURITY SETTINGS
# ============================

if ON_PYTHONANYWHERE:
    # Production settings for PythonAnywhere
    DEBUG = False
    ALLOWED_HOSTS = [
        'excellentacademy.pythonanywhere.com',
        'www.excellentacademy.pythonanywhere.com',
    ]

    # Production security settings
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

    # CSRF trusted origins for PythonAnywhere
    CSRF_TRUSTED_ORIGINS = [
        'https://excellentacademy.pythonanywhere.com',
        'https://www.excellentacademy.pythonanywhere.com',
    ]

    # Single-tenant: no subdomain routing needed
    TENANT_DOMAIN = 'excellentacademy.pythonanywhere.com'
    
    # Adjust static files for PythonAnywhere production
    STATIC_ROOT = BASE_DIR / "static"
    STATICFILES_DIRS = []  # Clear STATICFILES_DIRS in production
    
else:
    # Development settings
    DEBUG = True
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
    
    # Development mode overrides
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'https://localhost:8000',
        'http://127.0.0.1:8000',
        'https://127.0.0.1:8000',
    ]
    
    # Keep development static files setup
    STATICFILES_DIRS = [BASE_DIR / "static"]
    STATIC_ROOT = BASE_DIR / "staticfiles"

# ============================
# LOGGING CONFIGURATION
# ============================

# Create logs directory if it doesn't exist
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
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
            "filename": BASE_DIR / "logs" / "production.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["mail_admins", "file"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# Database settings for PythonAnywhere (keep using SQLite for simplicity)
# If you need MySQL on PythonAnywhere, use this configuration:
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'NordaLMS$default',  # Database name
        'USER': 'NordaLMS',           # PythonAnywhere username
        'PASSWORD': 'your_password',  # Database password
        'HOST': 'NordaLMS.mysql.pythonanywhere-services.com',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
"""

# ============================
# APPLICATION SPECIFIC SETTINGS
# ============================

# Site name for templates
SITE_NAME = "Excellent Academy School Management System"
SITE_DOMAIN = "excellentacademy.pythonanywhere.com"
SITE_ID = 1

# ============================
# SINGLE-TENANT MODE
# ============================

# Single institution setup for Excellent Academy
SINGLE_TENANT_MODE = True
DEFAULT_INSTITUTION_CODE = 'EXCELLENT_ACADEMY'
DEFAULT_INSTITUTION_NAME = 'Excellent Academy'

# Disable institution subdomain routing
TENANT_SUBDOMAIN_ENABLED = False

# Disable institution switching
ALLOW_INSTITUTION_SWITCHING = False

# Cache timeout for institution data (in seconds)
INSTITUTION_CACHE_TIMEOUT = 3600  # 1 hour

# Disable institution-specific branding (use global defaults)
INSTITUTION_BRANDING_ENABLED = False

# Tenant data isolation (not needed for single tenant)
TENANT_DATA_ISOLATION = False
