 
from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='SECRET_K')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())  

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

POSTGRES_LOCALLY = config('POSTGRES_LOCALLY', default=False, cast=bool)
if config('ENVIRONMENT', default='development') == 'production' or POSTGRES_LOCALLY:
    DATABASES['default'] = dj_database_url.parse(config('DATABASE_URL'))

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'taggit',
    'rest_framework',
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
     
    'cloudinary_storage',
    'cloudinary',

 
    'accounts',
    'forum',
    'friends',
    'quiz',
    'materials',
    'GROUPS',
    'chat',
    'payment',
    'GCE',
    'timetable',
    'notifications',
    'legal',
    'dashboard',
   
      
    
    
    
]
 

WEBRTC_ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
    {"urls": "stun:stun2.l.google.com:19302"},
]

import os
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MIDDLEWARE = [
    #'cors-headers.middleware.CorsMiddleware',
    'payment.middleware.SubscriptionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
    #'schoolcamp.rate_middleware.GlobalRateLimitMiddleware',
]


SITE_ID = 1

ROOT_URLCONF = 'schoolcamp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                #'payment.context_processors.subscription',
                'notifications.context_processors.unread_notifications',

            ],
        },
    },
]

#WSGI_APPLICATION = 'schoolcamp.wsgi.application'
ASGI_APPLICATION = 'schoolcamp.asgi.application'
 


 
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/forum/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "mandatory" 
 
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
 
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

 
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Media Files (Cloudinary) ──────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY':    config('CLOUDINARY_API_KEY',    default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
    # Auto-optimize images on upload
    'EAGER_TRANSFORMS': [
        # For images: auto-format, auto-quality, max 1024px
        {'fetch_format': 'auto', 'quality': 'auto:good', 'width': 1024, 'height': 1024, 'crop': 'limit'},
    ],
    # Apply eager transforms to all images
    'EAGER': True,
    # Use eager async for faster uploads
    'EAGER_ASYNC': True,
    # Overwrite existing files with same public_id
    'OVERWRITE': True,
    # Invalidate CDN cache on overwrite
    'INVALIDATE': True,
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATA_UPLOAD_MAX_MEMORY_SIZE = 26_214_400   # 25 MB in bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 26_214_400

# Allowed MIME types — validate these in your upload view too
ALLOWED_UPLOAD_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/mp4',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/zip', 'text/plain',
]

 
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

import os 
REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

import os

MTN_MOMO_SUBSCRIPTION_KEY = os.environ.get('MTN_MOMO_SUBSCRIPTION_KEY')
MTN_MOMO_API_USER = os.environ.get('MTN_MOMO_API_USER')
MTN_MOMO_API_KEY = os.environ.get('MTN_MOMO_API_KEY')
MTN_MOMO_ENVIRONMENT = os.environ.get('MTN_MOMO_ENVIRONMENT', 'sandbox')
MTN_MOMO_CALLBACK_URL = os.environ.get('MTN_MOMO_CALLBACK_URL')

ORANGE_MONEY_CLIENT_ID = os.environ.get('ORANGE_MONEY_CLIENT_ID')
ORANGE_MONEY_CLIENT_SECRET = os.environ.get('ORANGE_MONEY_CLIENT_SECRET')
ORANGE_MONEY_MERCHANT_KEY = os.environ.get('ORANGE_MONEY_MERCHANT_KEY')
ORANGE_MONEY_CALLBACK_URL = os.environ.get('ORANGE_MONEY_CALLBACK_URL')

SUBSCRIPTION_AMOUNT = int(os.environ.get('SUBSCRIPTION_AMOUNT', 500))

EMAIL_BACKEND   = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST      = config('EMAIL_HOST',      default='smtp.gmail.com')
EMAIL_PORT      = config('EMAIL_PORT',      default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS   = config('EMAIL_USE_TLS',   default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SchoolCamp <noreply@schoolcamp.cm>')


# ── HTTPS / Security ──────────────────────────────────────────
SECURE_SSL_REDIRECT          = config('SECURE_SSL', default=False, cast=bool)
SECURE_HSTS_SECONDS          = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD          = True
SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
CSRF_TRUSTED_ORIGINS         = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
X_FRAME_OPTIONS              = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF  = True
SECURE_BROWSER_XSS_FILTER    = True
SECURE_REFERRER_POLICY       = 'same-origin'

# ── Logging ───────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'payment': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}