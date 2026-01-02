@echo off
echo ============================================
echo АВТОМАТИЧЕСКАЯ УСТАНОВКА PRICESMART
echo ============================================

echo 1. Переход в папку проектов...
cd /d "C:\Users\3d200\PycharmProjects"

echo 2. Очистка старого проекта...
if exist pricing_system rmdir /s /q pricing_system

echo 3. Создание структуры...
mkdir pricing_system
cd pricing_system
mkdir config
mkdir core
mkdir core\templates
mkdir core\templates\core
mkdir static
mkdir static\css

echo 4. Создание venv...
python -m venv venv

echo 5. Активация venv...
call venv\Scripts\activate.bat

echo 6. Установка Django...
pip install django

echo 7. Создание manage.py...
django-admin startproject config .

echo 8. Копирование файлов...
echo Создайте файлы вручную как в инструкции!

echo ============================================
echo СТРУКТУРА СОЗДАНА!
echo ============================================
echo 1. Скопируйте файлы из инструкции
echo 2. Затем выполните:
echo    python manage.py migrate
echo    python manage.py runserver
echo ============================================

pause