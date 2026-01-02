import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    # Пытаемся импортировать Django
    from django.core.wsgi import get_wsgi_application
    from django.http import HttpResponse
    
    # Создаем приложение
    application = get_wsgi_application()
    
    # Простая функция-обработчик
    def handler(request, context):
        # Используем Django для обработки
        response = application(request)
        
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.content.decode('utf-8') if response.content else ''
        }
    
except Exception as e:
    # Фоллбэк если Django не загружается
    def handler(request, context):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>PriceSmart</title></head>
        <body>
            <h1>PriceSmart</h1>
            <p>Добро пожаловать в систему ценообразования</p>
            <p>Ошибка загрузки Django: {str(e)}</p>
        </body>
        </html>
        """
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': html
        }