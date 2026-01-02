"""
Настройки для Vercel
"""
from .settings import *

# Разрешенные хосты для Vercel
ALLOWED_HOSTS = [
    '.vercel.app',
    '.now.sh',
    'localhost',
    '127.0.0.1',
]

# Для статических файлов
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Используем whitenoise для статических файлов
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'