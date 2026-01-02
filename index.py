"""
Минимальное приложение для Vercel
"""


def handler(request):
    # Простейший HTML ответ
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PriceSmart - Успех!</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { padding: 20px; }
            .success { color: green; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">✅ PriceSmart работает на Vercel!</h1>
            <p>Версия: 1.0.0</p>
            <p>Хостинг: Vercel Serverless Functions</p>

            <div class="card mt-4">
                <div class="card-body">
                    <h5>Статус системы:</h5>
                    <ul>
                        <li>✅ Серверная функция работает</li>
                        <li>✅ HTML отдается корректно</li>
                        <li>✅ Bootstrap загружен</li>
                        <li>🔜 Django будет добавлен позже</li>
                    </ul>
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
            'Cache-Control': 'no-cache'
        },
        'body': html
    }