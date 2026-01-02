"""
Главное приложение для Vercel
"""
import os
import sys
from django.core.wsgi import get_wsgi_application

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.vercel_settings')

# Создаем WSGI приложение
app = get_wsgi_application()