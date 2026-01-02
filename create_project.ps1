# create_project.ps1
Write-Host "==================================" -ForegroundColor Green
Write-Host "СОЗДАНИЕ PRICESMART ПРОЕКТА" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Проверка Python
Write-Host "1. Проверка Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ОШИБКА: Python не найден!" -ForegroundColor Red
    Write-Host "Установите Python с python.org" -ForegroundColor Red
    pause
    exit
}
Write-Host "Python найден: $pythonVersion" -ForegroundColor Green

# Создание venv
Write-Host "2. Создание виртуального окружения..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "venv" -ErrorAction SilentlyContinue
python -m venv venv

# Проверка создания
if (Test-Path "venv\Scripts\python.exe") {
    Write-Host "VENV успешно создан!" -ForegroundColor Green
} else {
    Write-Host "ОШИБКА: VENV не создан" -ForegroundColor Red
    Write-Host "Пробуем альтернативный метод..." -ForegroundColor Yellow

    # Альтернатива: используем системный Python
    $pythonPath = (Get-Command python).Source
    Write-Host "Используем Python из: $pythonPath" -ForegroundColor Yellow
    & $pythonPath -m venv venv
}

# Активация
Write-Host "3. Активация VENV..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
} else {
    .\venv\Scripts\activate.bat
}

# Установка Django
Write-Host "4. Установка Django..." -ForegroundColor Yellow
pip install django

# Создание проекта
Write-Host "5. Создание Django проекта..." -ForegroundColor Yellow
django-admin startproject config .

Write-Host "==================================" -ForegroundColor Green
Write-Host "ПРОЕКТ СОЗДАН УСПЕШНО!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host "Теперь создайте остальные файлы как в инструкции" -ForegroundColor Cyan
Write-Host "И выполните: python manage.py runserver" -ForegroundColor Cyan