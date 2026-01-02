"""
Минимальная рабочая функция для Vercel
"""

def handler(event, context):
    """
    Простейший обработчик
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html; charset=utf-8"
        },
        "body": """
        <!DOCTYPE html>
        <html>
        <head><title>PriceSmart</title></head>
        <body>
            <h1 style="color: green;">✅ PriceSmart работает на Vercel!</h1>
            <p>Serverless Function успешно выполнена</p>
        </body>
        </html>
        """
    }

# Только handler, ничего больше!
__all__ = ['handler']