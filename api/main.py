from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
from datetime import datetime

app = FastAPI(title="Hotel Dynamic Pricing API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Модели данных
class CompetitorRequest(BaseModel):
    hotel_id: str
    location: str
    check_in: str
    check_out: str
    room_type: str


class PricingRequest(BaseModel):
    hotel_id: str
    base_price: float
    competitors_data: List[Dict[str, Any]]
    season_factor: Optional[float] = 1.0
    occupancy_rate: Optional[float] = 0.7


class ReportRequest(BaseModel):
    hotel_id: str
    period_start: str
    period_end: str
    format: str = "pdf"


# ===== HTML ИНТЕРФЕЙС =====

# HTML шаблон для дашборда
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏨 Hotel Pricing Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #4361ee;
            --secondary: #3a0ca3;
            --success: #4cc9f0;
        }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .dashboard {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin: 10px 0;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 10px 0;
        }
        .btn-action {
            background: #4361ee;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            margin: 5px;
            width: 100%;
            transition: all 0.3s;
        }
        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(67,97,238,0.4);
        }
        .nav-tabs .nav-link {
            border-radius: 10px;
            margin: 0 5px;
        }
        .tab-content {
            padding: 20px 0;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 50px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="dashboard">
            <!-- Заголовок -->
            <div class="header">
                <h1><i class="bi bi-building"></i> Hotel Pricing Dashboard</h1>
                <p class="text-muted">Система динамического ценообразования</p>
            </div>

            <!-- Меню -->
            <ul class="nav nav-tabs" id="dashboardTabs">
                <li class="nav-item">
                    <button class="nav-link active" onclick="showTab('overview')">
                        <i class="bi bi-speedometer2"></i> Обзор
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('pricing')">
                        <i class="bi bi-calculator"></i> Ценообразование
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('competitors')">
                        <i class="bi bi-graph-up"></i> Конкуренты
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" onclick="showTab('reports')">
                        <i class="bi bi-file-bar-graph"></i> Отчеты
                    </button>
                </li>
            </ul>

            <!-- Загрузка -->
            <div id="loading" class="loading">
                <div class="spinner-border text-primary"></div>
                <p class="mt-3">Загрузка данных...</p>
            </div>

            <!-- Вкладка Обзор -->
            <div id="overviewTab" class="tab-content">
                <div class="row">
                    <div class="col-md-3">
                        <div class="metric-card">
                            <i class="bi bi-currency-ruble fs-1"></i>
                            <div class="metric-value" id="avgPrice">5,500 ₽</div>
                            <small>Средняя цена</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-card">
                            <i class="bi bi-people fs-1"></i>
                            <div class="metric-value" id="occupancyRate">78%</div>
                            <small>Заполняемость</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-card">
                            <i class="bi bi-cash-stack fs-1"></i>
                            <div class="metric-value" id="monthRevenue">12.5M ₽</div>
                            <small>Выручка (мес.)</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-card">
                            <i class="bi bi-trophy fs-1"></i>
                            <div class="metric-value" id="marketPosition">#3</div>
                            <small>Позиция на рынке</small>
                        </div>
                    </div>
                </div>

                <div class="row mt-4">
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">Динамика цен</h5>
                                <canvas id="priceChart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">Быстрые действия</h5>
                                <button class="btn-action" onclick="calculatePrice()">
                                    <i class="bi bi-calculator"></i> Рассчитать цену
                                </button>
                                <button class="btn-action" onclick="analyzeCompetitors()">
                                    <i class="bi bi-search"></i> Анализ конкурентов
                                </button>
                                <button class="btn-action" onclick="generateReport()">
                                    <i class="bi bi-file-earmark-pdf"></i> Создать отчет
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Вкладка Ценообразование -->
            <div id="pricingTab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-body">
                        <h4 class="card-title"><i class="bi bi-calculator"></i> Калькулятор цены</h4>

                        <div class="row mt-4">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Базовая цена (₽)</label>
                                    <input type="number" class="form-control" id="basePrice" value="5000">
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">Сезон</label>
                                    <select class="form-select" id="season">
                                        <option value="0.8">Низкий сезон</option>
                                        <option value="1.0" selected>Средний сезон</option>
                                        <option value="1.3">Высокий сезон</option>
                                        <option value="1.6">Пиковый сезон</option>
                                    </select>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Заполняемость: <span id="occupancyValue">78%</span></label>
                                    <input type="range" class="form-range" id="occupancySlider" min="0" max="100" value="78">
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">Стратегия</label>
                                    <select class="form-select" id="strategy">
                                        <option value="0.9">Агрессивная</option>
                                        <option value="1.0" selected>Умеренная</option>
                                        <option value="1.1">Консервативная</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div class="text-center">
                            <button class="btn btn-primary btn-lg" onclick="calculateOptimalPrice()">
                                <i class="bi bi-lightning"></i> Рассчитать оптимальную цену
                            </button>
                        </div>

                        <div id="priceResult" class="mt-4" style="display: none;">
                            <div class="alert alert-success">
                                <h4><i class="bi bi-check-circle"></i> Расчет завершен!</h4>
                                <p class="mb-2">Рекомендуемая цена:</p>
                                <h2 class="metric-value" id="finalPrice">5,500 ₽</h2>
                                <button class="btn-action mt-3" onclick="applyPrice()">
                                    <i class="bi bi-check-lg"></i> Применить эту цену
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Вкладка Конкуренты -->
            <div id="competitorsTab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-body">
                        <h4 class="card-title"><i class="bi bi-graph-up"></i> Анализ конкурентов</h4>

                        <div class="mb-3">
                            <div class="input-group">
                                <input type="text" class="form-control" placeholder="Поиск конкурентов...">
                                <button class="btn btn-primary" onclick="searchCompetitors()">
                                    <i class="bi bi-search"></i> Найти
                                </button>
                            </div>
                        </div>

                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Отель</th>
                                        <th>Цена</th>
                                        <th>Рейтинг</th>
                                        <th>Действия</th>
                                    </tr>
                                </thead>
                                <tbody id="competitorsTable">
                                    <!-- Данные будут загружены -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Вкладка Отчеты -->
            <div id="reportsTab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-body">
                        <h4 class="card-title"><i class="bi bi-file-bar-graph"></i> Управление отчетами</h4>

                        <div class="row">
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <i class="bi bi-currency-exchange fs-1 text-primary"></i>
                                        <h5>Финансовый отчет</h5>
                                        <button class="btn btn-outline-primary mt-2" onclick="generateFinancialReport()">
                                            Создать
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <i class="bi bi-graph-up fs-1 text-success"></i>
                                        <h5>Анализ цен</h5>
                                        <button class="btn btn-outline-primary mt-2" onclick="generatePricingReport()">
                                            Создать
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <i class="bi bi-people fs-1 text-warning"></i>
                                        <h5>Анализ конкурентов</h5>
                                        <button class="btn btn-outline-primary mt-2" onclick="generateCompetitorReport()">
                                            Создать
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="mt-4">
                            <h5>История отчетов</h5>
                            <div id="reportsHistory">
                                <!-- История будет загружена -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Статус -->
            <div class="mt-4 text-center text-muted">
                <small>
                    <i class="bi bi-clock"></i> Обновлено: <span id="lastUpdate">сегодня</span> | 
                    <i class="bi bi-server"></i> API: <span id="apiStatus" class="badge bg-success">Online</span>
                </small>
            </div>
        </div>
    </div>

    <script>
        // Инициализация при загрузке
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboardData();
            updateTime();
            checkApiStatus();
            setInterval(updateTime, 60000); // Обновлять время каждую минуту
        });

        // Показать вкладку
        function showTab(tabName) {
            // Скрыть все вкладки
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });

            // Убрать активные классы
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });

            // Показать выбранную вкладку
            document.getElementById(tabName + 'Tab').style.display = 'block';

            // Активировать кнопку
            event.target.classList.add('active');

            // Загрузить данные для вкладки
            if (tabName === 'competitors') {
                loadCompetitors();
            } else if (tabName === 'reports') {
                loadReports();
            }
        }

        // Обновить время
        function updateTime() {
            const now = new Date();
            document.getElementById('lastUpdate').textContent = 
                now.toLocaleTimeString('ru-RU');
        }

        // Проверить статус API
        async function checkApiStatus() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                document.getElementById('apiStatus').textContent = 'Online';
                document.getElementById('apiStatus').className = 'badge bg-success';
            } catch (error) {
                document.getElementById('apiStatus').textContent = 'Offline';
                document.getElementById('apiStatus').className = 'badge bg-danger';
            }
        }

        // Загрузить данные дашборда
        async function loadDashboardData() {
            try {
                // Загрузка метрик
                const competitorsRes = await fetch('/api/competitors');
                const competitors = await competitorsRes.json();

                // Расчет средней цены
                const avgPrice = competitors.competitors.reduce((sum, c) => sum + c.price, 0) / competitors.competitors.length;
                document.getElementById('avgPrice').textContent = avgPrice.toLocaleString('ru-RU') + ' ₽';

                // Создание графика
                createPriceChart();

            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
            }
        }

        // Создать график цен
        function createPriceChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');

            // Тестовые данные
            const labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
            const ourPrices = [5000, 5200, 5100, 5300, 5500, 6000, 5800];
            const marketPrices = [4800, 5000, 4900, 5100, 5300, 5600, 5400];

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Наша цена',
                            data: ourPrices,
                            borderColor: '#4361ee',
                            backgroundColor: 'rgba(67, 97, 238, 0.1)',
                            borderWidth: 3,
                            tension: 0.3
                        },
                        {
                            label: 'Средняя по рынку',
                            data: marketPrices,
                            borderColor: '#95a5a6',
                            borderDash: [5, 5],
                            borderWidth: 2,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    }
                }
            });
        }

        // Расчет оптимальной цены
        async function calculateOptimalPrice() {
            const basePrice = parseFloat(document.getElementById('basePrice').value);
            const season = parseFloat(document.getElementById('season').value);
            const occupancy = parseInt(document.getElementById('occupancySlider').value) / 100;
            const strategy = parseFloat(document.getElementById('strategy').value);

            try {
                const response = await fetch('/api/pricing/calculate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        hotel_id: 'hotel_001',
                        base_price: basePrice,
                        competitors_data: [],
                        season_factor: season,
                        occupancy_rate: occupancy
                    })
                });

                const result = await response.json();

                // Показать результат
                document.getElementById('finalPrice').textContent = 
                    result.final_price.toLocaleString('ru-RU') + ' ₽';
                document.getElementById('priceResult').style.display = 'block';

            } catch (error) {
                alert('Ошибка расчета: ' + error.message);
            }
        }

        // Применить цену
        function applyPrice() {
            const price = document.getElementById('finalPrice').textContent;
            alert('Цена ' + price + ' успешно применена!');
        }

        // Загрузить конкурентов
        async function loadCompetitors() {
            try {
                const response = await fetch('/api/competitors');
                const data = await response.json();

                const table = document.getElementById('competitorsTable');
                table.innerHTML = '';

                data.competitors.forEach(competitor => {
                    const row = `
                        <tr>
                            <td>${competitor.name}</td>
                            <td><strong>${competitor.price.toLocaleString('ru-RU')} ₽</strong></td>
                            <td>
                                <span class="badge bg-warning text-dark">
                                    <i class="bi bi-star-fill"></i> ${competitor.rating}
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="trackCompetitor('${competitor.name}')">
                                    Отслеживать
                                </button>
                            </td>
                        </tr>
                    `;
                    table.innerHTML += row;
                });

            } catch (error) {
                console.error('Ошибка загрузки конкурентов:', error);
            }
        }

        // Поиск конкурентов
        function searchCompetitors() {
            alert('Поиск конкурентов запущен...');
        }

        // Отслеживание конкурента
        function trackCompetitor(name) {
            alert('Начато отслеживание: ' + name);
        }

        // Загрузить отчеты
        async function loadReports() {
            try {
                const response = await fetch('/api/reports/summary?hotel_id=test&days=7');
                const data = await response.json();

                const container = document.getElementById('reportsHistory');
                container.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h6>Последний отчет</h6>
                            <p>Период: ${data.period_days} дней</p>
                            <p>Средняя цена: ${data.summary.average_price.toLocaleString('ru-RU')} ₽</p>
                            <p>Заполняемость: ${(data.summary.occupancy_rate * 100).toFixed(1)}%</p>
                        </div>
                    </div>
                `;

            } catch (error) {
                console.error('Ошибка загрузки отчетов:', error);
            }
        }

        // Генерация отчетов
        function generateFinancialReport() {
            alert('Финансовый отчет генерируется...');
        }

        function generatePricingReport() {
            alert('Отчет по ценам генерируется...');
        }

        function generateCompetitorReport() {
            alert('Отчет по конкурентам генерируется...');
        }

        // Остальные функции
        function calculatePrice() {
            showTab('pricing');
        }

        function analyzeCompetitors() {
            showTab('competitors');
        }

        function generateReport() {
            showTab('reports');
        }

        // Слайдер заполняемости
        document.getElementById('occupancySlider').addEventListener('input', function(e) {
            document.getElementById('occupancyValue').textContent = e.target.value + '%';
        });
    </script>
</body>
</html>
"""


# ===== API ЭНДПОИНТЫ (ваши существующие) =====

@app.get("/")
async def root():
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/api")
async def api_info():
    return {
        "message": "Hotel Dynamic Pricing API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "competitors": "/api/competitors",
            "pricing": "/api/pricing/calculate",
            "reports": "/api/reports/summary",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/competitors")
async def get_competitors():
    """Упрощенный эндпоинт для тестирования"""
    return {
        "competitors": [
            {
                "name": "Luxury Hotel Moscow",
                "price": 5500,
                "rating": 4.5,
                "service": "mock"
            },
            {
                "name": "Business Inn",
                "price": 4800,
                "rating": 4.2,
                "service": "mock"
            },
            {
                "name": "City Center Hotel",
                "price": 6200,
                "rating": 4.8,
                "service": "mock"
            },
            {
                "name": "Comfort Stay",
                "price": 5200,
                "rating": 4.3,
                "service": "mock"
            },
            {
                "name": "Premium Suites",
                "price": 7500,
                "rating": 4.9,
                "service": "mock"
            }
        ]
    }


@app.post("/api/pricing/calculate")
async def calculate_price(request: PricingRequest):
    """Упрощенный расчет цены"""
    try:
        # Простой расчет
        final_price = request.base_price * request.season_factor

        if request.occupancy_rate > 0.8:
            final_price *= 1.2
        elif request.occupancy_rate < 0.4:
            final_price *= 0.9

        # Если есть данные о конкурентах, учитываем их
        if request.competitors_data:
            competitor_prices = [c.get('price', 0) for c in request.competitors_data if 'price' in c]
            if competitor_prices:
                avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
                # Если наша цена сильно отличается от средней, корректируем
                if final_price > avg_competitor_price * 1.2:
                    final_price = avg_competitor_price * 1.15
                elif final_price < avg_competitor_price * 0.8:
                    final_price = avg_competitor_price * 0.85

        return {
            "hotel_id": request.hotel_id,
            "base_price": request.base_price,
            "final_price": round(final_price, 2),
            "factors": {
                "season": request.season_factor,
                "occupancy": request.occupancy_rate,
                "competitors_considered": len(request.competitors_data) > 0
            },
            "calculated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/summary")
async def get_report_summary(hotel_id: str, days: int = 7):
    """Упрощенный отчет"""
    # Генерация тестовых данных
    base_price = 5500
    occupancy = 0.78

    # Динамика цен
    price_trend = []
    for i in range(days):
        price_trend.append({
            "day": i + 1,
            "price": base_price * (0.95 + (i * 0.02))
        })

    return {
        "hotel_id": hotel_id,
        "period_days": days,
        "summary": {
            "average_price": base_price,
            "occupancy_rate": occupancy,
            "revenue": 1250000,
            "competitors_tracked": 12,
            "price_changes": 3
        },
        "price_trend": price_trend,
        "recommendations": [
            "Рассмотрите повышение цены на выходные на 10-15%",
            "Добавьте пакетные предложения для бизнес-клиентов",
            "Мониторьте акции конкурента 'Business Inn'"
        ],
        "generated_at": datetime.now().isoformat()
    }


# Новые эндпоинты для интерфейса

@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """Метрики для дашборда"""
    return {
        "average_price": 5500,
        "occupancy_rate": 0.78,
        "monthly_revenue": 12500000,
        "market_position": 3,
        "competitors_count": 12,
        "price_change_today": 2.5,
        "occupancy_change_today": 1.2,
        "last_updated": datetime.now().isoformat()
    }


@app.get("/api/competitors/detailed")
async def get_detailed_competitors():
    """Детальная информация о конкурентах"""
    return {
        "competitors": [
            {
                "id": 1,
                "name": "Luxury Hotel Moscow",
                "price": 6200,
                "our_price": 6000,
                "rating": 4.8,
                "reviews": 1280,
                "occupancy": 0.85,
                "platform": "Booking.com",
                "price_difference": 3.3
            },
            {
                "id": 2,
                "name": "Business Inn",
                "price": 4800,
                "our_price": 4900,
                "rating": 4.2,
                "reviews": 560,
                "occupancy": 0.72,
                "platform": "Ostrovok.ru",
                "price_difference": -2.0
            },
            {
                "id": 3,
                "name": "City Center Hotel",
                "price": 5500,
                "our_price": 5400,
                "rating": 4.5,
                "reviews": 890,
                "occupancy": 0.78,
                "platform": "Airbnb",
                "price_difference": 1.9
            }
        ]
    }


@app.post("/api/price/apply")
async def apply_price(hotel_id: str, price: float, room_type: str = "standard"):
    """Применить новую цену"""
    return {
        "success": True,
        "message": f"Цена {price}₽ применена для {room_type}",
        "hotel_id": hotel_id,
        "new_price": price,
        "room_type": room_type,
        "applied_at": datetime.now().isoformat()
    }


# ДЕЙСТВИТЕЛЬНО ВАЖНО для Vercel
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)