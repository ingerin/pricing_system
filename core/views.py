"""
Views (контроллеры) для приложения core.
"""
from django.shortcuts import render

# Главная страница
def home(request):
    return render(request, 'core/home.html')

# Панель управления
def dashboard(request):
    return render(request, 'core/dashboard.html')

# Анализ конкурентов
def competitors(request):
    return render(request, 'core/competitors.html')

# Ценообразование
def pricing(request):
    return render(request, 'core/pricing.html')

# Отчеты
def reports(request):
    return render(request, 'core/reports.html')