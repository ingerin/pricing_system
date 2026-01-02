"""
Serverless Function для Vercel в папке api
"""


def handler(event, context):
    """Обработчик для Vercel"""

    # Получаем путь
    path = event.get('path', '/')

    # Определяем ответ в зависимости от пути
    if path == '/':
        return home_response()
    elif path == '/dashboard':
        return dashboard_response()
    elif path == '/competitors':
        return competitors_response()
    elif path == '/pricing':
        return pricing_response()
    elif path == '/reports':
        return reports_response()
    elif path == '/health':
        return health_response()
    else:
        return not_found_response(path)


def home_response():
    """Главная страница"""
    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PriceSmart - Система ценообразования</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { font-family: Arial, sans-serif; }
            .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        </style>
    </head>
    <body>
        <!-- Навигация -->
        <nav class="navbar navbar-dark hero">
            <div class="container">
                <span class="navbar-brand mb-0 h1">📊 PriceSmart</span>
            </div>
        </nav>

        <!-- Контент -->
        <div class="container py-5">
            <div class="text-center mb-5">
                <h1 class="display-4">✅ PriceSmart работает!</h1>
                <p class="lead">Система динамического ценообразования для гостиниц</p>
                <p class="text-muted">Хостинг: Vercel Serverless Functions</p>
            </div>

            <!-- Карточки -->
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <h5>🔍 Анализ конкурентов</h5>
                            <p>Отслеживание цен конкурентов</p>
                            <a href="/competitors" class="btn btn-primary">Перейти</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <h5>💰 Ценообразование</h5>
                            <p>AI-алгоритмы расчета цен</p>
                            <a href="/pricing" class="btn btn-success">Перейти</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        <div class="card-body text-center">
                            <h5>📄 Отчеты</h5>
                            <p>PDF отчеты с обоснованием</p>
                            <a href="/reports" class="btn btn-warning">Перейти</a>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Статистика -->
            <div class="row text-center mt-5">
                <div class="col-md-3">
                    <h3>+25%</h3>
                    <p>Рост дохода</p>
                </div>
                <div class="col-md-3">
                    <h3>99%</h3>
                    <p>Точность</p>
                </div>
                <div class="col-md-3">
                    <h3>24/7</h3>
                    <p>Мониторинг</p>
                </div>
                <div class="col-md-3">
                    <h3>100+</h3>
                    <p>Клиентов</p>
                </div>
            </div>

            <!-- Футер -->
            <div class="text-center mt-5">
                <p class="text-muted">© 2024 PriceSmart | Версия 1.0.0</p>
            </div>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html; charset=utf-8'
        },
        'body': html
    }


def dashboard_response():
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
            <h1>📊 Панель управления</h1>
            <p>Здесь будет статистика и графики</p>
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


def competitors_response():
    """Конкуренты"""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Конкуренты - PriceSmart</title></head>
    <body>
        <div style="padding: 20px;">
            <h1>🔍 Анализ конкурентов</h1>
            <p>Модуль в разработке...</p>
            <a href="/">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }


def pricing_response():
    """Ценообразование"""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Цены - PriceSmart</title></head>
    <body>
        <div style="padding: 20px;">
            <h1>💰 Ценообразование</h1>
            <p>Модуль в разработке...</p>
            <a href="/">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }


def reports_response():
    """Отчеты"""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Отчеты - PriceSmart</title></head>
    <body>
        <div style="padding: 20px;">
            <h1>📄 Отчеты</h1>
            <p>Модуль в разработке...</p>
            <a href="/">На главную</a>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }


def health_response():
    """Health check"""
    import json
    import datetime

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'healthy',
            'service': 'PriceSmart',
            'version': '1.0.0',
            'timestamp': datetime.datetime.now().isoformat()
        })
    }


def not_found_response(path):
    """404"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>404 - PriceSmart</title></head>
    <body>
        <h1>404 - Не найдено</h1>
        <p>Путь: {path}</p>
        <a href="/">На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }