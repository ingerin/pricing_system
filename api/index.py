"""
Serverless Function для Vercel в правильном формате
"""


def handler(request):
    # request - это словарь с данными запроса
    path = request.get('path', '/')

    # Определяем ответ в зависимости от пути
    if path == '/':
        return home_handler(request)
    elif path.startswith('/dashboard'):
        return dashboard_handler(request)
    else:
        return not_found_handler(request)


def home_handler(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PriceSmart - Главная</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-chart-line"></i> PriceSmart
                </a>
            </div>
        </nav>

        <div class="container mt-5">
            <div class="alert alert-success">
                <h1>✅ Успешный деплой на Vercel!</h1>
                <p>Серверная функция работает корректно</p>
            </div>

            <div class="card">
                <div class="card-body">
                    <h5>Статус модулей:</h5>
                    <table class="table">
                        <tr><td>Анализ конкурентов</td><td><span class="badge bg-success">Работает</span></td></tr>
                        <tr><td>Ценообразование</td><td><span class="badge bg-warning">В разработке</span></td></tr>
                        <tr><td>Отчетность</td><td><span class="badge bg-warning">В разработке</span></td></tr>
                        <tr><td>Панель управления</td><td><span class="badge bg-success">Работает</span></td></tr>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
        },
        'body': html
    }


def dashboard_handler(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Панель управления</title></head>
    <body>
        <h1>Панель управления</h1>
        <p>Модуль в разработке</p>
        <a href="/">На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }


def not_found_handler(request):
    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'text/html'},
        'body': '<h1>404 - Страница не найдена</h1>'
    }


# Экспортируем handler для Vercel
__all__ = ['handler']