"""
Django settings del ERP CIIDIE.

Configuración por variables de entorno con defaults de desarrollo:
sin variables definidas se comporta igual que siempre (DEBUG, PostgreSQL
local); en el servidor, /etc/erp-ciidie.env define los valores de
producción (ver despliegue/GUIA_DESPLIEGUE.md).
"""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _env(nombre, defecto=''):
    return os.environ.get(nombre, defecto)


def _env_bool(nombre, defecto):
    valor = os.environ.get(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ('1', 'true', 'si', 'sí', 'yes')


def _env_lista(nombre):
    valor = os.environ.get(nombre, '')
    return [item.strip() for item in valor.split(',') if item.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
# En producción DJANGO_SECRET_KEY es obligatoria (la guía genera una).
SECRET_KEY = _env(
    'DJANGO_SECRET_KEY',
    'django-insecure-w^kkkz4bdnc5)5rfbk4k1r3sn41hzo%)4skl*civwat1ia(nt(',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = ['10.3.21.120', 'localhost', '127.0.0.1']

# Orígenes confiables para CSRF cuando se accede por IP/dominio del servidor,
# p. ej.: DJANGO_CSRF_TRUSTED_ORIGINS=http://10.3.21.120
CSRF_TRUSTED_ORIGINS = [
    'http://10.3.21.120:8085',
    'http://localhost:8085',
    'http://127.0.0.1:8085'
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'maquinas',
    'usuarios',
    'mantenimiento',
    'inventario',
    'reservas',
    'reportes',
    'tpm',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'usuarios.middleware.CierreSesionPorInactividadMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'usuarios.middleware.RestriccionEstudianteMiddleware',
]

# ── Sesiones ─────────────────────────────────────────────────────────────────
# La sesión muere al cerrar el navegador y, además, el middleware
# CierreSesionPorInactividadMiddleware la cierra tras este tiempo sin usar
# el sistema (cambiar aquí el límite si 30 minutos resulta corto o largo).
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESION_INACTIVIDAD_MINUTOS = int(_env('SESION_INACTIVIDAD_MINUTOS', '30'))

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.roles_usuario',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Las migraciones se generaron bajo Django 6 (BigAutoField implícito);
# en Django 5.2 hay que declararlo o los modelos derivarían a AutoField.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Database
# DJANGO_DB_ENGINE=mariadb en el servidor; sin definir usa el PostgreSQL
# local de desarrollo de siempre.

if _env('DJANGO_DB_ENGINE') == 'mariadb' or sys.platform == 'linux':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': _env('DJANGO_DB_NAME', 'erp_ciidie_db'),     
            'USER': _env('DJANGO_DB_USER', 'erp_ciidie_user'),  
            'PASSWORD': _env('DJANGO_DB_PASSWORD', 'erpadmindb'),
            'HOST': _env('DJANGO_DB_HOST', 'localhost'),
            'PORT': _env('DJANGO_DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                # Rechaza datos truncados/ inválidos en vez de aceptarlos a medias
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _env('DJANGO_DB_NAME', 'erp_laboratorio'),
            'USER': _env('DJANGO_DB_USER', 'postgres'),
            'PASSWORD': _env('DJANGO_DB_PASSWORD', 'admin'),
            'HOST': _env('DJANGO_DB_HOST', 'localhost'),
            'PORT': _env('DJANGO_DB_PORT', '5432'),
        }
    }

AUTH_USER_MODEL = 'usuarios.Usuario'

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-ec'

TIME_ZONE = 'America/Guayaquil'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Destino de collectstatic — en el servidor Nginx sirve este directorio
STATIC_ROOT = Path(_env('DJANGO_STATIC_ROOT', str(BASE_DIR / 'staticfiles')))

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(_env('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media')))

# ── Solo en modo test: hasher rápido para no pagar PBKDF2 por cada usuario ──
if 'test' in sys.argv:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
