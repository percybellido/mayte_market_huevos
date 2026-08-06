from .base import *
import os
from dotenv import load_dotenv
from pathlib import Path

# ===== CARGA EL .ENV =====
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Busca el .env en diferentes ubicaciones
env_file = None

# 1. Busca en la raíz del proyecto (producción)
raiz_env = BASE_DIR / '.env'
if raiz_env.exists():
    env_file = raiz_env
    print(f"✅ .env cargado desde raíz: {raiz_env}")

# 2. Busca dentro de mayte_market (local)
if not env_file:
    local_env = BASE_DIR / 'mayte_market' / '.env'
    if local_env.exists():
        env_file = local_env
        print(f"✅ .env cargado desde mayte_market: {local_env}")

# 3. Busca en la ruta absoluta de producción (fallback)
if not env_file:
    prod_env = Path('/webapps/mayte/mayte_market_huevos/.env')
    if prod_env.exists():
        env_file = prod_env
        print(f"✅ .env cargado desde ruta absoluta: {prod_env}")

# Carga el archivo si existe
if env_file:
    load_dotenv(env_file)
else:
    print("⚠️  ADVERTENCIA: No se encontró archivo .env")
# =========================

# ===== CONFIGURACIÓN BÁSICA =====
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
# Elimina elementos vacíos
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# ===== CONFIGURACIÓN CSRF PARA HTTP =====
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_HTTPONLY = os.getenv("CSRF_COOKIE_HTTPONLY", "False") == "True"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"
# =======================================

CSRF_FAILURE_VIEW = "applications.users.views.csrf_failure"

# ===== BASE DE DATOS =====
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

# ===== ARCHIVOS ESTÁTICOS =====
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# ===== MEDIA =====
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ===== EMAIL =====
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# ===== LOGGING =====
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.security.csrf": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}