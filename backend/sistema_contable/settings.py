"""
Django settings for sistema_contable project.
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: Usar variables de entorno en producción
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-!(2sc4w)13(5ev2szrmeg7c*k85pp2d5h&xoj7fnoanmti_9*-'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if not DEBUG else ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Mis apps y librerías
    'api',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# JWT: acceso 8 horas (jornada laboral)
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', # CORS
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema_contable.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema_contable.wsgi.application'

# Database
# Configuración explícita para SQLite (Local)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (logos, certificados subidos por usuarios)
# En Docker: MEDIA_ROOT=/app/media para que certificados queden en /app/media/certificados/
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', str(BASE_DIR / 'media')))

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Facturación Asíncrona ---
# Si True, las facturas se procesan en segundo plano (colade tareas). Respuesta inmediata al usuario.
USE_ASYNC_FACTURACION = os.environ.get('USE_ASYNC_FACTURACION', 'true').lower() in ('1', 'true', 'yes')

# --- Ministerio de Hacienda (DTE / Facturación Electrónica) ---
# PRUEBA: Si está definido, se usa esta contraseña en lugar de la BD (para validar espacios/caracteres).
# Ejemplo: MH_PASSWORD_OVERRIDE=2Caballo.Azul  -> quitar después de probar
MH_PASSWORD_OVERRIDE = os.environ.get('MH_PASSWORD_OVERRIDE') or None
# Firma: si True, se firma dentro del backend (no hace falta contenedor firmador).
USE_INTERNAL_FIRMADOR = os.environ.get('USE_INTERNAL_FIRMADOR', 'true').lower() in ('1', 'true', 'yes')
# URL del firmador externo (solo si USE_INTERNAL_FIRMADOR=False). En Docker: FIRMADOR_URL=http://firmador:8113/
DTE_FIRMADOR_URL = os.environ.get('FIRMADOR_URL', 'http://localhost:8113/').rstrip('/') + '/firmardocumento/'
# URL invalidación (Manual MH 4.5). Override solo si necesitas otra URL.
# DTE_ANULAR_URL = "https://apitest.dtes.mh.gob.sv/fesv/anulardte"

# Configuración CORS (Frontend React/Vite)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]