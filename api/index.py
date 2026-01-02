"""
Serverless Function для Vercel с обработкой ошибок
"""

def handler(event, context):
    """Основной обработчик"""
    try:
        # Логируем событие для отладки
        print(f"Event received: {event}")
        print(f"Context: {context}")

        # Получаем путь из события
        path = event.get('path', '/') if event else '/'
        http_method = event.get('httpMethod', 'GET') if event else 'GET'

        # Логируем для отладки
        print(f"Path: {path}, Method: {http_method}")

        # Обрабатываем разные пути
        if path == '/':
            return home_response()
        elif path == '/dashboard':
            return dashboard_response()
        elif path == '/favicon.ico' or path == '/favicon.png':
            # Возвращаем пустой ответ для favicon
            return {
                'statusCode': 204,  # No Content
                'headers': {'Content-Type': 'image/x-icon'},
                'body': ''
            }
        else:
            return not_found_response(path)

    except Exception as e:
        # Логируем ошибку
        print(f"Error in handler: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

        # Возвращаем ошибку
        return error_response(e)

def home_response():
    """Главная страница"""
    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PriceSmart - Система ценообразования</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .success {
                color: #28a745;
                font-size: 24px;
            }
            .nav {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                margin-right: 20px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/">🏠 Главная</a>
                <a href="/dashboard">📊 Панель управления</a>
                <a href="#">🔍 Конкуренты</a>
                <a href="#">💰 Цены</a>
                <a href="#">📄 Отчеты</a>
            </div>
            
            <h1 class="success">✅ PriceSmart успешно работает на Vercel!</h1>
            <p>Система динамического ценообразования для гостиничного бизнеса</p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 30px;">
                <h3>Модули системы:</h3>
                <ul>
                    <li><strong>Анализ конкурентов:</strong> Отслеживание цен с Booking.com, Airbnb, Ostrovok</li>
                    <li><strong>Ценообразование:</strong> AI-алгоритмы расчета оптимальных цен</li>
                    <li><strong>Отчетность:</strong> PDF отчеты с обоснованием цен</li>
                    <li><strong>Панель управления:</strong> Единый интерфейс управления</li>
                </ul>
            </div>
            
            <div style="margin-top: 30px; color: #666;">
                <p><strong>Версия:</strong> 1.0.0 | <strong>Хостинг:</strong> Vercel Serverless Functions</p>
                <p><strong>Статус:</strong> 🟢 Система работает стабильно</p>
            </div>
        </div>
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

def dashboard_response():
    """Панель управления"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Панель управления - PriceSmart</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
        </style>
    </head>
    <body>
        <h1>📊 Панель управления PriceSmart</h1>
        <p>Модуль в разработке...</p>
        <a href="/">← На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html; charset=utf-8'},
        'body': html
    }

def not_found_response(path):
    """Страница 404"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>404 - Страница не найдена</title></head>
    <body>
        <h1>404 - Страница не найдена</h1>
        <p>Путь <code>{path}</code> не существует</p>
        <a href="/">На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'text/html; charset=utf-8'},
        'body': html
    }

def error_response(error):
    """Обработка ошибок"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ошибка сервера</title></head>
    <body>
        <h1>500 - Внутренняя ошибка сервера</h1>
        <p>Произошла ошибка при обработке запроса</p>
        <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
{str(error)}
        </pre>
        <a href="/">На главную</a>
    </body>
    </html>
    """

    return {
        'statusCode': 500,
        'headers': {'Content-Type': 'text/html; charset=utf-8'},
        'body': html
    }

# Альтернативная функция для Vercel
def app(request):
    """Альтернативный обработчик для Vercel"""
    try:
        return handler({}, {})
    except Exception as e:
        return error_response(e)

# Экспортируем функции
__all__ = ['handler', 'app']