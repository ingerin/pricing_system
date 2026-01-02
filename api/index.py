"""
Минимальная рабочая функция для Vercel
"""


def handler(event, context):
    """Обработчик для Vercel"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PriceSmart - Успех!</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .success { color: green; font-size: 24px; }
        </style>
    </head>
    <body>
        <h1 class="success">✅ PriceSmart работает!</h1>
        <p>Serverless Function успешно выполнена</p>
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


# Альтернативная функция для Vercel
def app(request):
    return handler({}, {})


# Экспортируем обе функции
__all__ = ['handler', 'app']