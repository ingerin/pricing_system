"""
Простое приложение для Vercel без сложных зависимостей
"""
import os
import sys


def handler(event, context):
    # Простой HTML ответ
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
            body { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
            .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        </style>
    </head>
    <body>
        <!-- Навигация -->
        <nav class="navbar navbar-expand-lg navbar-dark hero">
            <div class="container">
                <a class="navbar-brand" href="#">
                    <i class="fas fa-chart-line"></i> PriceSmart
                </a>
            </div>
        </nav>

        <!-- Герой секция -->
        <div class="container py-5">
            <div class="text-center mb-5">
                <h1 class="display-4 fw-bold mb-3">
                    <i class="fas fa-rocket text-primary"></i><br>
                    PriceSmart на Vercel!
                </h1>
                <p class="lead fs-4">Система динамического ценообразования успешно развернута</p>
                <p class="text-muted">Анализ конкурентов • Умные цены • Автоматические отчеты</p>
            </div>

            <!-- Карточки функций -->
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card h-100 border-primary">
                        <div class="card-body text-center">
                            <i class="fas fa-search-dollar fa-3x text-primary mb-3"></i>
                            <h4>Анализ конкурентов</h4>
                            <p>Отслеживание цен в реальном времени</p>
                            <span class="badge bg-success">Готово</span>
                        </div>
                    </div>
                </div>

                <div class="col-md-4 mb-4">
                    <div class="card h-100 border-success">
                        <div class="card-body text-center">
                            <i class="fas fa-calculator fa-3x text-success mb-3"></i>
                            <h4>Ценообразование</h4>
                            <p>AI-алгоритмы расчета оптимальных цен</p>
                            <span class="badge bg-warning">В разработке</span>
                        </div>
                    </div>
                </div>

                <div class="col-md-4 mb-4">
                    <div class="card h-100 border-warning">
                        <div class="card-body text-center">
                            <i class="fas fa-file-pdf fa-3x text-warning mb-3"></i>
                            <h4>Отчеты</h4>
                            <p>PDF отчеты с обоснованием цен</p>
                            <span class="badge bg-warning">В разработке</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Статистика -->
            <div class="row mt-5">
                <div class="col-md-3 text-center">
                    <h2 class="text-primary">+25%</h2>
                    <p>Средний рост дохода</p>
                </div>
                <div class="col-md-3 text-center">
                    <h2 class="text-success">99%</h2>
                    <p>Точность прогнозов</p>
                </div>
                <div class="col-md-3 text-center">
                    <h2 class="text-warning">24/7</h2>
                    <p>Мониторинг конкурентов</p>
                </div>
                <div class="col-md-3 text-center">
                    <h2 class="text-info">100+</h2>
                    <p>Довольных клиентов</p>
                </div>
            </div>

            <!-- Контакт -->
            <div class="card mt-5">
                <div class="card-body text-center">
                    <h5>Сайт работает на Vercel Platform</h5>
                    <p>Дальнейшая разработка в процессе...</p>
                    <a href="https://github.com" class="btn btn-primary">
                        <i class="fab fa-github"></i> Исходный код
                    </a>
                </div>
            </div>
        </div>

        <!-- Футер -->
        <footer class="mt-5 py-3 bg-light">
            <div class="container text-center">
                <span class="text-muted">© 2024 PriceSmart. Система динамического ценообразования.</span>
            </div>
        </footer>
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