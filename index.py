"""
САМЫЙ ПРОСТОЙ рабочий вариант для Vercel
"""

def handler(event, context):
    try:
        # Простейший HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PriceSmart - Работает!</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .success { color: green; font-size: 24px; }
            </style>
        </head>
        <body>
            <h1 class="success">✅ PriceSmart</h1>
            <p>Серверная функция работает корректно</p>
            <p><strong>Версия:</strong> 1.0.0</p>
            <p><strong>Время:</strong> Простой ответ без ошибок</p>
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

    except Exception as e:
        # Если ошибка, вернем ее в ответе
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f'<h1>Ошибка:</h1><pre>{str(e)}</pre>'
        }