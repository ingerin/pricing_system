"""
Главное приложение PriceSmart для Vercel
"""
import json
import os
from datetime import datetime

def handler(event, context):
    """Обработчик для Vercel Serverless Functions"""

    try:
        # Получаем путь из запроса
        path = event.get('path', '/')
        method = event.get('httpMethod', 'GET')

        # Логируем для отладки
        print(f"[{datetime.now()}] Request: {method} {path}")

        # Маршрутизация
        if path == '/':
            return home_handler()
        elif path == '/dashboard':
            return dashboard_handler()
        elif path == '/competitors':
            return competitors_handler()
        elif path == '/pricing':
            return pricing_handler()
        elif path == '/reports':
            return reports_handler()
        elif path == '/health':
            return health_handler()
        else:
            return not_found_handler(path)

    except Exception as e:
        # Обработка ошибок
        return error_handler(e)

def home_handler():
    """Главная страница"""
    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PriceSmart - Система ценообразования</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .navbar-brand { font-weight: 700; }
            .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .module-card { transition: transform 0.3s; }
            .module-card:hover { transform: translateY(-5px); }
        </style>
    </head>
    <body>
        <!-- Навигация -->
        <nav class="navbar navbar-expand-lg navbar-dark hero">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-chart-line"></i> PriceSmart
                </a>
                <div class="navbar-nav">
                    <a class="nav-link" href="/dashboard">Панель</a>
                    <a class="nav-link" href="/competitors">Конкуренты</a>
                    <a class="nav-link" href="/pricing">Цены</a>
                    <a class="nav-link" href="/reports">Отчеты</a>
                </div>
            </div>
        </nav>
        
        <!-- Герой -->
        <div class="container py-5">
            <div class="text-center mb-5">
                <h1 class="display-4 mb-3">
                    <i class="fas fa-rocket text-primary"></i><br>
                    PriceSmart на Vercel
                </h1>
                <p class="lead">Система динамического ценообразования для гостиничного бизнеса</p>
                <p class="text-muted">Анализ конкурентов • Умное ценообразование • Автоматические отчеты</p>
            </div>
            
            <!-- Модули -->
            <div class="row">
                <div class="col-md-3 mb-4">
                    <div class="card module-card h-100 border-primary">
                        <div class="card-body text-center">
                            <i class="fas fa-search-dollar fa-3x text-primary mb-3"></i>
                            <h4>Анализ конкурентов</h4>
                            <p>Отслеживание цен в реальном времени с популярных платформ</p>
                            <a href="/competitors" class="btn btn-outline-primary">Перейти</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-3 mb-4">
                    <div class="card module-card h-100 border-success">
                        <div class="card-body text-center">
                            <i class="fas fa-calculator fa-3x text-success mb-3"></i>
                            <h4>Ценообразование</h4>
                            <p>AI-алгоритмы расчета оптимальных цен на основе рыночных данных</p>
                            <a href="/pricing" class="btn btn-outline-success">Перейти</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-3 mb-4">
                    <div class="card module-card h-100 border-warning">
                        <div class="card-body text-center">
                            <i class="fas fa-file-pdf fa-3x text-warning mb-3"></i>
                            <h4>Отчетность</h4>
                            <p>PDF отчеты с детальным обоснованием ценовой стратегии</p>
                            <a href="/reports" class="btn btn-outline-warning">Перейти</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-3 mb-4">
                    <div class="card module-card h-100 border-info">
                        <div class="card-body text-center">
                            <i class="fas fa-chart-bar fa-3x text-info mb-3"></i>
                            <h4>Аналитика</h4>
                            <p>Детальная аналитика и прогнозы на основе исторических данных</p>
                            <a href="/dashboard" class="btn btn-outline-info">Перейти</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Статистика -->
            <div class="row mt-5 text-center">
                <div class="col-md-3">
                    <h2 class="text-primary">+25%</h2>
                    <p>Средний рост дохода</p>
                </div>
                <div class="col-md-3">
                    <h2 class="text-success">99%</h2>
                    <p>Точность прогнозов</p>
                </div>
                <div class="col-md-3">
                    <h2 class="text-warning">24/7</h2>
                    <p>Мониторинг конкурентов</p>
                </div>
                <div class="col-md-3">
                    <h2 class="text-info">100+</h2>
                    <p>Довольных клиентов</p>
                </div>
            </div>
        </div>
        
        <!-- Футер -->
        <footer class="mt-5 py-3 bg-light">
            <div class="container text-center">
                <span class="text-muted">© 2024 PriceSmart. Хостинг: Vercel | Версия: 1.0.0</span>
            </div>
        </footer>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-cache'
        },
        'body': html
    }

def dashboard_handler():
    """Панель управления"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Панель управления - PriceSmart</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1><i class="fas fa-tachometer-alt"></i> Панель управления</h1>
            <p>Модуль в разработке...</p>
            <a href="/" class="btn btn-primary">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }

def competitors_handler():
    """Анализ конкурентов"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Анализ конкурентов - PriceSmart</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1><i class="fas fa-search-dollar"></i> Анализ конкурентов</h1>
            <p>Модуль в разработке...</p>
            <a href="/" class="btn btn-primary">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }

def pricing_handler():
    """Ценообразование"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ценообразование - PriceSmart</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1><i class="fas fa-calculator"></i> Ценообразование</h1>
            <p>Модуль в разработке...</p>
            <a href="/" class="btn btn-primary">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }

def reports_handler():
    """Отчеты"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Отчеты - PriceSmart</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1><i class="fas fa-file-pdf"></i> Отчеты</h1>
            <p>Модуль в разработке...</p>
            <a href="/" class="btn btn-primary">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }

def health_handler():
    """Health check"""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'healthy',
            'service': 'PriceSmart',
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat()
        })
    }

def not_found_handler(path):
    """404 страница"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>404 - PriceSmart</title></head>
    <body>
        <h1>404 - Страница не найдена</h1>
        <p>Путь <code>{path}</code> не существует</p>
        <a href="/">На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }

def error_handler(error):
    """Обработка ошибок"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ошибка - PriceSmart</title></head>
    <body>
        <h1>500 - Внутренняя ошибка сервера</h1>
        <pre>{str(error)}</pre>
        <a href="/">На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 500,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }

# Экспортируем handler для Vercel
__all__ = ['handler']