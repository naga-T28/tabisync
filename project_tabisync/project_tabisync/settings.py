from pathlib import Path
import os
from dotenv import load_dotenv

# .envファイルの読み込み
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# BASE_DIRの設定
BASE_DIR = Path(__file__).resolve().parent.parent

# DEBUG設定
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Turnstile keys（Cloudflare管理画面から取得）
TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# HTTPS利用の有無（本番・ステージング環境でhttps使ってなければFalseに）
USE_HTTPS = os.environ.get("USE_HTTPS", "True") == "True"

if not DEBUG:
    # 本番環境設定

    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise Exception("SECRET_KEYが設定されていません。本番環境で必須です。")

    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
        raise Exception("ALLOWED_HOSTSが設定されていません。本番環境で必須です。")

    # セキュリティ設定
    SECURE_SSL_REDIRECT = USE_HTTPS
    SESSION_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SECURE = USE_HTTPS
    SECURE_HSTS_SECONDS = 31536000 if USE_HTTPS else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = USE_HTTPS
    SECURE_HSTS_PRELOAD = USE_HTTPS
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


    # CSRF_TRUSTED_ORIGINSの設定（https:// または http://を付ける）
    CSRF_TRUSTED_ORIGINS = []
    for host in ALLOWED_HOSTS:
        host = host.strip()
        if not host:
            continue
        if USE_HTTPS:
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
        else:
            CSRF_TRUSTED_ORIGINS.append(f"http://{host}")

    # 静的ファイル設定
    STATIC_URL = '/static/'
    STATICFILES_DIRS = [BASE_DIR / "static"]
    STATIC_ROOT = BASE_DIR / 'staticfiles'

    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

    # データベース設定（例: PostgreSQL）
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

    # ログ設定
    LOG_DIR = BASE_DIR / 'logs'
    if not LOG_DIR.exists():
        LOG_DIR.mkdir()

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'WARNING',
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'django.log',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': True,
            },
        },
    }

else:
    # 開発環境設定

    SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key')
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1","https://staging.tabisync.com", "http://192.168.0.238"]

    STATIC_URL = '/static/'
    STATICFILES_DIRS = [BASE_DIR / "static"]
    STATIC_ROOT = BASE_DIR / 'staticfiles'

    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tabisync.apps.TabisyncConfig',  # add_2025.06.07
    'django.contrib.sites',
    'django.contrib.sitemaps',
    "whitenoise.runserver_nostatic", # add_2026.01.19
    "django_ckeditor_5",
]

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading", "|",
            "bold", "italic", "underline",
            "link",
            "bulletedList", "numberedList",
            "|",
            "undo", "redo",
        ],
        "removePlugins": [
            "Image", "ImageUpload", "ImageToolbar", "ImageCaption", "ImageStyle"
        ],
    }
}


SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = 'project_tabisync.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],  # add_2025.06.07
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project_tabisync.wsgi.application'

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# メール設定

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
CONTACT_RECEIVER_EMAIL = os.environ.get("CONTACT_RECEIVER_EMAIL")

# Internationalization

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_TZ = True

# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
