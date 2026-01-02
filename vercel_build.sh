#!/bin/bash

echo "🚀 Начало сборки на Vercel..."

# Установка зависимостей
pip install -r requirements.txt

# Создание статических файлов
python manage.py collectstatic --noinput

# Создание базы данных SQLite (для демо)
if [ ! -f db.sqlite3 ]; then
    echo "📦 Создание базы данных..."
    python manage.py migrate
    python manage.py createsuperuser --noinput --username admin --email admin@example.com
    python manage.py shell -c "
from django.contrib.auth.models import User
u = User.objects.get(username='admin')
u.set_password('admin123')
u.save()
print('✅ Админ создан: admin / admin123')
"
fi

echo "✅ Сборка завершена!"