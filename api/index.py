# Минимальная рабочая функция
def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': '<h1>✅ Success!</h1>'
    }

# Самый простой рабочий вариант
def app(request):
    return "PriceSmart работает на Vercel!"

# Экспортируем app
__all__ = ['app']