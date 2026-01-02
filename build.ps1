# build.ps1 - скрипт сборки для Windows/Vercel
Write-Host "🚀 Начало сборки PriceSmart на Vercel..." -ForegroundColor Green

# Установка зависимостей
Write-Host "📦 Устанавливаем зависимости..." -ForegroundColor Yellow
pip install -r requirements.txt

# Создаем статические файлы
Write-Host "🖼️ Собираем статические файлы..." -ForegroundColor Yellow
python manage.py collectstatic --noinput --clear

Write-Host "✅ Сборка завершена!" -ForegroundColor Green