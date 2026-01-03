from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
import aiohttp
from datetime import datetime
import json

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


class HotelAddressUpdate(BaseModel):
    hotel_id: str
    name: str
    address: str
    lat: float
    lng: float
    city: str = "Москва"


# Данные для карты (тестовые координаты)
COMPETITORS_DATA = {
    "our_hotel": {
        "id": "our_hotel",
        "name": "Наш отель (Central Plaza)",
        "lat": 55.7558,
        "lng": 37.6173,
        "price": 5500,
        "rating": 4.5,
        "color": "#4361ee",
        "address": "Красная площадь, 1",
        "distance": "0 км",
        "city": "Москва"
    },
    "competitors": [
        {
            "id": "hotel1",
            "name": "Luxury Hotel Moscow",
            "lat": 55.7517,
            "lng": 37.6178,
            "price": 6200,
            "rating": 4.8,
            "color": "#ef476f",
            "address": "ул. Тверская, 15",
            "distance": "0.5 км",
            "selected": False
        },
        {
            "id": "hotel2",
            "name": "Business Inn",
            "lat": 55.7570,
            "lng": 37.6150,
            "price": 4800,
            "rating": 4.2,
            "color": "#06d6a0",
            "address": "ул. Большая Дмитровка, 10",
            "distance": "0.8 км",
            "selected": False
        },
        {
            "id": "hotel3",
            "name": "City Center Hotel",
            "lat": 55.7600,
            "lng": 37.6200,
            "price": 5500,
            "rating": 4.5,
            "color": "#ffd166",
            "address": "ул. Петровка, 25",
            "distance": "0.7 км",
            "selected": False
        },
        {
            "id": "hotel4",
            "name": "Comfort Stay",
            "lat": 55.7500,
            "lng": 37.6250,
            "price": 5200,
            "rating": 4.3,
            "color": "#06d6a0",
            "address": "ул. Лубянка, 5",
            "distance": "0.6 км",
            "selected": False
        },
        {
            "id": "hotel5",
            "name": "Premium Suites",
            "lat": 55.7630,
            "lng": 37.6100,
            "price": 7500,
            "rating": 4.9,
            "color": "#073b4c",
            "address": "ул. Воздвиженка, 3",
            "distance": "1.2 км",
            "selected": False
        }
    ]
}

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
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
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
        .address-result {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .address-result:hover {
            background-color: #f8f9fa;
            transform: translateX(5px);
        }
        
        .address-result.border-primary {
            border-width: 2px !important;
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

        /* Стили для карты */
        #competitorsMap {
            height: 400px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 2px solid #dee2e6;
        }

        .map-container {
            position: relative;
        }

        .map-controls {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 5px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .address-result {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .address-result:hover {
            background-color: #f8f9fa;
            transform: translateX(5px);
        }
        
        .address-result.border-primary {
            border-width: 2px !important;
        }
        
        .legend {
            position: absolute;
            bottom: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .legend-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
            font-size: 12px;
        }

        .legend-color {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            margin-right: 8px;
            border: 2px solid white;
        }

        .hotel-card {
            transition: all 0.3s;
            cursor: pointer;
            border: 2px solid transparent;
        }

        .hotel-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .hotel-card.selected {
            border-color: #4361ee;
            background-color: rgba(67, 97, 238, 0.05);
        }

        .price-badge {
            font-size: 1.1rem;
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 10px;
        }

        .price-higher {
            background-color: #ff6b6b;
            color: white;
        }

        .price-lower {
            background-color: #51cf66;
            color: white;
        }

        .price-same {
            background-color: #ffd43b;
            color: #000;
        }

        .selected-hotels-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .selected-item {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 5px;
            border-left: 4px solid #4361ee;
        }

        .filter-panel {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
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
                <div class="row">
                    <div class="col-md-8">
                        <!-- Карта -->
                        <div class="map-container">
                            <div id="competitorsMap"></div>
                            <div class="map-controls">
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-primary" onclick="zoomIn()">
                                        <i class="bi bi-plus"></i>
                                    </button>
                                    <button class="btn btn-outline-primary" onclick="zoomOut()">
                                        <i class="bi bi-dash"></i>
                                    </button>
                                    <button class="btn btn-outline-primary" onclick="resetView()">
                                        <i class="bi bi-geo-alt"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="legend">
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color: #4361ee;"></div>
                                    <span>Наш отель</span>
                                </div>
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color: #ef476f;"></div>
                                    <span>Дороже нас</span>
                                </div>
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color: #06d6a0;"></div>
                                    <span>Дешевле нас</span>
                                </div>
                            </div>
                        </div>

                        <!-- Фильтры -->
                        <div class="filter-panel">
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-body">
                                            <h5 class="card-title"><i class="bi bi-geo-alt"></i> Наш отель</h5>
                                            <div id="currentAddress" class="mb-2">
                                                <p class="mb-1"><strong id="hotelName">Наш отель (Central Plaza)</strong></p>
                                                <p class="mb-1 text-muted" id="hotelAddress">Красная площадь, 1, Москва</p>
                                                <p class="mb-0">
                                                    <span class="badge bg-primary" id="hotelPrice">5,500 ₽</span>
                                                    <span class="badge bg-warning text-dark ms-2" id="hotelRating">4.5 ★</span>
                                                </p>
                                            </div>
                                            <button class="btn btn-outline-primary btn-sm w-100" onclick="showAddressModal()">
                                                <i class="bi bi-pencil"></i> Изменить адрес
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-body">
                                            <h5 class="card-title"><i class="bi bi-funnel"></i> Фильтры</h5>
                                            <div class="row">
                                                <div class="col-md-4">
                                                    <label class="form-label small">Цена до:</label>
                                                    <input type="range" class="form-range" id="priceFilter" min="3000" max="10000" value="10000">
                                                    <small><span id="priceFilterValue">10,000 ₽</span></small>
                                                </div>
                                                <div class="col-md-4">
                                                    <label class="form-label small">Рейтинг:</label>
                                                    <select class="form-select form-select-sm" id="ratingFilter">
                                                        <option value="0">Все</option>
                                                        <option value="4">4.0+</option>
                                                        <option value="4.5">4.5+</option>
                                                        <option value="4.7">4.7+</option>
                                                    </select>
                                                </div>
                                                <div class="col-md-4">
                                                    <label class="form-label small">Расстояние:</label>
                                                    <select class="form-select form-select-sm" id="distanceFilter">
                                                        <option value="5">Все</option>
                                                        <option value="2">До 2 км</option>
                                                        <option value="1" selected>До 1 км</option>
                                                        <option value="0.5">До 500 м</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-4">
                        <!-- Выбранные отели -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="bi bi-check2-circle"></i> Выбранные отели
                                    <span class="badge bg-primary" id="selectedCount">0</span>
                                </h5>
                                <div class="selected-hotels-list" id="selectedList">
                                    <p class="text-muted text-center">Выберите отели на карте</p>
                                </div>
                                <div class="mt-2">
                                    <button class="btn btn-success w-100" id="analyzeBtn" disabled onclick="analyzeSelected()">
                                        <i class="bi bi-graph-up"></i> Анализировать выбранные
                                    </button>
                                    <button class="btn btn-outline-danger w-100 mt-2" onclick="clearSelected()">
                                        <i class="bi bi-trash"></i> Очистить выбор
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Статистика -->
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title"><i class="bi bi-bar-chart"></i> Статистика</h5>
                                <div class="row text-center">
                                    <div class="col-6">
                                        <div class="metric-value" id="statsAvgPrice">5,540 ₽</div>
                                        <small>Средняя цена</small>
                                    </div>
                                    <div class="col-6">
                                        <div class="metric-value" id="statsTotal">5</div>
                                        <small>Всего отелей</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Список всех отелей -->
                <div class="row mt-4" id="hotelsList">
                    <!-- Отели будут загружены здесь -->
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
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Глобальные переменные
        let map = null;
        let markers = {};
        let selectedHotels = new Set();
        let ourHotelPrice = 5500;

        // Инициализация при загрузке
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboardData();
            updateTime();
            checkApiStatus();
            setInterval(updateTime, 60000);
        });

        // Показать вкладку
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            document.getElementById(tabName + 'Tab').style.display = 'block';
            event.target.classList.add('active');

            if (tabName === 'competitors') {
                setTimeout(initMap, 100);
            }
        }

        // Инициализация карты
        function initMap() {
            if (map) return;

            // Центр Москвы
            map = L.map('competitorsMap').setView([55.7558, 37.6173], 14);

            // Добавляем слой карты
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap'
            }).addTo(map);

            // Загружаем данные
            loadMapData();
        }

        // Загрузка данных для карты
        async function loadMapData() {
            try {
                const response = await fetch('/api/competitors/map');
                const data = await response.json();

                // Добавляем наш отель
                addOurHotel(data.our_hotel);

                // Добавляем конкурентов
                data.competitors.forEach(hotel => {
                    addCompetitorMarker(hotel);
                });

                // Обновляем статистику
                updateStats(data.competitors);

                // Показываем список отелей
                renderHotelsList(data.competitors);

            } catch (error) {
                console.error('Ошибка загрузки данных карты:', error);
            }
        }

        // Добавить наш отель на карту
        function addOurHotel(hotel) {
            const icon = L.divIcon({
                className: 'custom-icon',
                html: `
                    <div style="
                        background-color: ${hotel.color};
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        border: 3px solid white;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-size: 20px;
                    ">
                        <i class="bi bi-house-door"></i>
                    </div>
                `,
                iconSize: [40, 40]
            });

            const marker = L.marker([hotel.lat, hotel.lng], { icon: icon })
                .addTo(map)
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <h6><b>${hotel.name}</b></h6>
                        <p><i class="bi bi-geo-alt"></i> ${hotel.address}</p>
                        <p><i class="bi bi-cash"></i> <b>${hotel.price.toLocaleString('ru-RU')} ₽</b></p>
                        <p><i class="bi bi-star"></i> ${hotel.rating} ★</p>
                    </div>
                `);

            markers[hotel.id] = marker;
        }

        // Добавить маркер конкурента
        function addCompetitorMarker(hotel) {
            const priceDiff = hotel.price - ourHotelPrice;
            let priceClass = '';

            if (priceDiff > 500) {
                priceClass = 'price-higher';
            } else if (priceDiff < -500) {
                priceClass = 'price-lower';
            } else {
                priceClass = 'price-same';
            }

            const icon = L.divIcon({
                className: 'custom-icon',
                html: `
                    <div style="
                        background-color: ${hotel.color};
                        width: 35px;
                        height: 35px;
                        border-radius: 50%;
                        border: 2px solid white;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        cursor: pointer;
                        transition: all 0.3s;
                    " onclick="selectHotel('${hotel.id}', event)">
                        <i class="bi bi-building"></i>
                    </div>
                `,
                iconSize: [35, 35]
            });

            const marker = L.marker([hotel.lat, hotel.lng], { icon: icon })
                .addTo(map)
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <h6><b>${hotel.name}</b></h6>
                        <p><i class="bi bi-geo-alt"></i> ${hotel.address}</p>
                        <p><i class="bi bi-signpost"></i> ${hotel.distance} от нас</p>
                        <p><i class="bi bi-cash"></i> <b>${hotel.price.toLocaleString('ru-RU')} ₽</b></p>
                        <p><i class="bi bi-star"></i> ${hotel.rating} ★</p>
                        <p>Разница: <span class="badge ${priceClass}">${priceDiff > 0 ? '+' : ''}${priceDiff} ₽</span></p>
                        <button class="btn btn-sm btn-primary w-100 mt-2" onclick="selectHotel('${hotel.id}')">
                            <i class="bi bi-plus-circle"></i> Выбрать для анализа
                        </button>
                    </div>
                `);

            markers[hotel.id] = marker;
        }

        // Выбрать отель
        function selectHotel(hotelId, event = null) {
            if (event) event.stopPropagation();

            const hotelCard = document.getElementById(`hotel-${hotelId}`);

            if (selectedHotels.has(hotelId)) {
                selectedHotels.delete(hotelId);
                if (hotelCard) hotelCard.classList.remove('selected');
            } else {
                selectedHotels.add(hotelId);
                if (hotelCard) hotelCard.classList.add('selected');
            }

            updateSelectedList();
        }

        // Обновить список выбранных
        function updateSelectedList() {
            const list = document.getElementById('selectedList');
            const count = document.getElementById('selectedCount');
            const analyzeBtn = document.getElementById('analyzeBtn');

            count.textContent = selectedHotels.size;
            analyzeBtn.disabled = selectedHotels.size === 0;

            if (selectedHotels.size === 0) {
                list.innerHTML = '<p class="text-muted text-center">Выберите отели на карте</p>';
                return;
            }

            list.innerHTML = '';
            selectedHotels.forEach(hotelId => {
                // В реальном приложении здесь был бы запрос к API
                const hotel = {
                    id: hotelId,
                    name: hotelId === 'hotel1' ? 'Luxury Hotel Moscow' : 
                          hotelId === 'hotel2' ? 'Business Inn' :
                          hotelId === 'hotel3' ? 'City Center Hotel' :
                          hotelId === 'hotel4' ? 'Comfort Stay' : 'Premium Suites',
                    price: hotelId === 'hotel1' ? 6200 : 
                          hotelId === 'hotel2' ? 4800 :
                          hotelId === 'hotel3' ? 5500 :
                          hotelId === 'hotel4' ? 5200 : 7500
                };

                const item = document.createElement('div');
                item.className = 'selected-item';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${hotel.name}</h6>
                            <small class="text-muted">${hotel.price.toLocaleString('ru-RU')} ₽</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="selectHotel('${hotelId}')">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                `;
                list.appendChild(item);
            });
        }

        // Анализировать выбранные
        function analyzeSelected() {
            if (selectedHotels.size === 0) return;

            alert(`Анализ ${selectedHotels.size} выбранных отелей...\n\nРезультаты анализа:\n• Средняя цена: 5,450 ₽\n• Рекомендуемая цена: 5,500 ₽\n• Ваша позиция: оптимальная`);

            // Показываем во вкладке ценообразования
            showTab('competitors');
        }

        // Очистить выбор
        function clearSelected() {
            selectedHotels.forEach(hotelId => {
                const hotelCard = document.getElementById(`hotel-${hotelId}`);
                if (hotelCard) hotelCard.classList.remove('selected');
            });
            selectedHotels.clear();
            updateSelectedList();
        }

        // Обновить статистику
        function updateStats(competitors) {
            const avgPrice = competitors.reduce((sum, hotel) => sum + hotel.price, 0) / competitors.length;
            document.getElementById('statsAvgPrice').textContent = Math.round(avgPrice).toLocaleString('ru-RU') + ' ₽';
            document.getElementById('statsTotal').textContent = competitors.length;
        }

        // Показать список отелей
        function renderHotelsList(competitors) {
            const container = document.getElementById('hotelsList');
            container.innerHTML = '';

            competitors.forEach(hotel => {
                const priceDiff = hotel.price - ourHotelPrice;
                let priceBadgeClass = '';
                let priceBadgeText = '';

                if (priceDiff > 500) {
                    priceBadgeClass = 'price-higher';
                    priceBadgeText = `+${priceDiff} ₽`;
                } else if (priceDiff < -500) {
                    priceBadgeClass = 'price-lower';
                    priceBadgeText = `${priceDiff} ₽`;
                } else {
                    priceBadgeClass = 'price-same';
                    priceBadgeText = '≈';
                }

                const col = document.createElement('div');
                col.className = 'col-md-4 mb-3';
                col.innerHTML = `
                    <div class="card hotel-card" id="hotel-${hotel.id}" onclick="selectHotel('${hotel.id}')">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="card-title mb-1">${hotel.name}</h6>
                                    <div class="d-flex align-items-center mb-2">
                                        <span class="badge bg-warning text-dark me-2">
                                            <i class="bi bi-star"></i> ${hotel.rating}
                                        </span>
                                        <small class="text-muted">
                                            <i class="bi bi-signpost"></i> ${hotel.distance}
                                        </small>
                                    </div>
                                    <p class="text-muted mb-1 small">
                                        <i class="bi bi-geo-alt"></i> ${hotel.address}
                                    </p>
                                </div>
                                <div class="text-end">
                                    <div class="price-badge ${priceBadgeClass}">
                                        ${hotel.price.toLocaleString('ru-RU')} ₽
                                    </div>
                                    <small class="text-muted d-block mt-1">${priceBadgeText}</small>
                                </div>
                            </div>
                            <div class="mt-3">
                                <button class="btn btn-sm btn-outline-primary w-100" onclick="focusOnMap('${hotel.id}', event)">
                                    <i class="bi bi-map"></i> Показать на карте
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(col);
            });
        }

        // Фокус на карте
        function focusOnMap(hotelId, event) {
            if (event) event.stopPropagation();
            const marker = markers[hotelId];
            if (marker) {
                map.setView(marker.getLatLng(), 16);
                marker.openPopup();
            }
        }

        // Управление картой
        function zoomIn() {
            if (map) map.zoomIn();
        }

        function zoomOut() {
            if (map) map.zoomOut();
        }

        function resetView() {
            if (map) map.setView([55.7558, 37.6173], 14);
        }
        
        // Показать модальное окно смены адреса
        function showAddressModal() {
            // Загружаем текущие данные
            fetch('/api/hotel/address')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('modalHotelName').value = data.name;
                    document.getElementById('modalAddress').value = data.address;
                    document.getElementById('modalCity').value = data.city || 'Москва';
                    document.getElementById('modalLat').value = data.lat;
                    document.getElementById('modalLng').value = data.lng;
                    
                    // Заполняем поля координат
                    document.getElementById('coordLat').value = data.lat;
                    document.getElementById('coordLng').value = data.lng;
                    
                    // Показываем модальное окно (правильный способ для Bootstrap 5)
                    const modal = new bootstrap.Modal(document.getElementById('addressModal'));
                    modal.show();
                })
                .catch(error => {
                    console.error('Ошибка загрузки адреса:', error);
                    // Все равно показываем модальное окно с пустыми полями
                    const modal = new bootstrap.Modal(document.getElementById('addressModal'));
                    modal.show();
                });
        }
        
        // Поиск адреса (с обработкой координат)
        function searchAddress() {
            let query = document.getElementById('addressSearch').value.trim();
            
            if (!query) {
                alert('Введите адрес для поиска');
                return;
            }
            
            // Проверяем, не введены ли координаты
            const coordMatch = query.match(/^(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)$/);
            if (coordMatch) {
                // Если введены координаты, используем обратное геокодирование
                const lat = parseFloat(coordMatch[1]);
                const lng = parseFloat(coordMatch[2]);
                
                document.getElementById('coordLat').value = lat;
                document.getElementById('coordLng').value = lng;
                
                // Запускаем поиск по координатам
                searchByCoordinates();
                return;
            }
            
            // Показываем загрузку
            document.getElementById('searchResults').style.display = 'block';
            document.getElementById('addressResultsList').innerHTML = 
                '<div class="text-center"><div class="spinner-border spinner-border-sm"></div> Поиск...</div>';
            
            // Обычный поиск по адресу
            fetch(`/api/hotel/address/search?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    let html = '';
                    if (data.results.length === 0) {
                        html = '<p class="text-muted">Ничего не найдено. Попробуйте другой запрос.</p>';
                    } else {
                        data.results.forEach((result, index) => {
                            // Сохраняем весь объект в data-атрибут как JSON
                            const jsonData = JSON.stringify(result).replace(/"/g, '&quot;');
                            html += `
                                <div class="card mb-2 address-result" onclick="selectAddress(${index})" 
                                     data-json='${jsonData}'>
                                    <div class="card-body p-2">
                                        <h6 class="card-title mb-1">${result.name}</h6>
                                        <p class="card-text small text-muted mb-1">${result.address}</p>
                                        <small class="text-muted">
                                            Координаты: ${result.lat.toFixed(6)}, ${result.lng.toFixed(6)}
                                        </small>
                                        ${result.description ? `<br><small><i>${result.description}</i></small>` : ''}
                                    </div>
                                </div>
                            `;
                        });
                    }
                    document.getElementById('addressResultsList').innerHTML = html;
                })
                .catch(error => {
                    console.error('Ошибка поиска адреса:', error);
                    document.getElementById('addressResultsList').innerHTML = 
                        '<p class="text-danger">Ошибка поиска адреса</p>';
                });
        }
        
        // Поиск по координатам
        function searchByCoordinates() {
            const lat = document.getElementById('coordLat').value;
            const lng = document.getElementById('coordLng').value;
            
            if (!lat || !lng) {
                alert('Введите широту и долготу');
                return;
            }
            
            // Проверяем, что это числа
            const latNum = parseFloat(lat);
            const lngNum = parseFloat(lng);
            
            if (isNaN(latNum) || isNaN(lngNum)) {
                alert('Координаты должны быть числами');
                return;
            }
            
            // Показываем загрузку
            document.getElementById('searchResults').style.display = 'block';
            document.getElementById('addressResultsList').innerHTML = 
                '<div class="text-center"><div class="spinner-border spinner-border-sm"></div> Поиск адреса...</div>';
            
            // Запрашиваем обратное геокодирование
            fetch(`/api/hotel/address/reverse?lat=${latNum}&lng=${lngNum}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Создаем карточку с результатом
                        const html = `
                            <div class="card mb-2 address-result" 
                                 onclick="selectAddressFromResult(${JSON.stringify(data).replace(/"/g, '&quot;')})">
                                <div class="card-body p-2">
                                    <h6 class="card-title mb-1">${data.name}</h6>
                                    <p class="card-text small text-muted mb-1">${data.address}</p>
                                    <small class="text-muted">
                                        Координаты: ${data.lat.toFixed(6)}, ${data.lng.toFixed(6)}
                                    </small>
                                </div>
                            </div>
                        `;
                        document.getElementById('addressResultsList').innerHTML = html;
                    } else {
                        document.getElementById('addressResultsList').innerHTML = 
                            '<p class="text-danger">Не удалось найти адрес</p>';
                    }
                })
                .catch(error => {
                    console.error('Ошибка поиска по координатам:', error);
                    document.getElementById('addressResultsList').innerHTML = 
                        '<p class="text-danger">Ошибка поиска</p>';
                });
        }
        
        // Выбор адреса из результатов (обновленная версия)
        function selectAddressFromResult(result) {
            document.getElementById('modalHotelName').value = result.name || 'Наш отель';
            document.getElementById('modalAddress').value = result.address;
            document.getElementById('modalCity').value = result.city || 'Москва';
            document.getElementById('modalLat').value = result.lat;
            document.getElementById('modalLng').value = result.lng;
            
            // Заполняем поля координат
            document.getElementById('coordLat').value = result.lat;
            document.getElementById('coordLng').value = result.lng;
        }
        
        // Обновляем существующую функцию selectAddress
        function selectAddress(index) {
            const resultElement = document.querySelectorAll('.address-result')[index];
            if (resultElement && resultElement.dataset.json) {
                try {
                    const result = JSON.parse(resultElement.dataset.json);
                    selectAddressFromResult(result);
                } catch (e) {
                    // Старый формат данных
                    document.getElementById('modalHotelName').value = resultElement.dataset.name || 'Наш отель';
                    document.getElementById('modalAddress').value = resultElement.dataset.address;
                    document.getElementById('modalCity').value = resultElement.dataset.city || 'Москва';
                    document.getElementById('modalLat').value = resultElement.dataset.lat;
                    document.getElementById('modalLng').value = resultElement.dataset.lng;
                    
                    // Заполняем поля координат
                    document.getElementById('coordLat').value = resultElement.dataset.lat;
                    document.getElementById('coordLng').value = resultElement.dataset.lng;
                }
            }
            
            // Подсвечиваем выбранный результат
            document.querySelectorAll('.address-result').forEach(el => {
                el.classList.remove('border-primary');
            });
            resultElement.classList.add('border-primary');
        }
        
        // Автодополнение при вводе адреса
        let autocompleteTimeout;
        document.getElementById('addressSearch').addEventListener('input', function(e) {
            const query = e.target.value.trim();
            
            // Очищаем предыдущий таймер
            clearTimeout(autocompleteTimeout);
            
            if (query.length < 2) {
                document.getElementById('addressSuggestions').innerHTML = '';
                return;
            }
            
            // Устанавливаем задержку для предотвращения множественных запросов
            autocompleteTimeout = setTimeout(() => {
                fetchAutocomplete(query);
            }, 300);
        });
        
        // Запрос автодополнения
        function fetchAutocomplete(query) {
            fetch(`/api/hotel/address/autocomplete?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    const datalist = document.getElementById('addressSuggestions');
                    datalist.innerHTML = '';
                    
                    data.suggestions.forEach(suggestion => {
                        const option = document.createElement('option');
                        option.value = suggestion.display;
                        option.dataset.address = suggestion.full_address;
                        option.dataset.lat = suggestion.lat;
                        option.dataset.lng = suggestion.lng;
                        option.dataset.city = suggestion.city;
                        datalist.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Ошибка автодополнения:', error);
                });
        }
        
        // Обработка выбора из автодополнения
        document.getElementById('addressSearch').addEventListener('change', function(e) {
            const input = e.target;
            const selectedOption = Array.from(document.getElementById('addressSuggestions').options)
                .find(option => option.value === input.value);
            
            if (selectedOption && selectedOption.dataset.address) {
                // Заполняем поля из выбранного варианта
                document.getElementById('modalAddress').value = selectedOption.dataset.address;
                document.getElementById('modalCity').value = selectedOption.dataset.city || 'Москва';
                document.getElementById('modalLat').value = selectedOption.dataset.lat;
                document.getElementById('modalLng').value = selectedOption.dataset.lng;
                document.getElementById('coordLat').value = selectedOption.dataset.lat;
                document.getElementById('coordLng').value = selectedOption.dataset.lng;
                
                // Можно сразу выполнить поиск для получения полной информации
                searchAddress();
            }
        });
        
        // Сохранить адрес (обновленная версия)
        function saveAddress() {
            const hotelData = {
                hotel_id: 'our_hotel',
                name: document.getElementById('modalHotelName').value,
                address: document.getElementById('modalAddress').value,
                lat: parseFloat(document.getElementById('modalLat').value),
                lng: parseFloat(document.getElementById('modalLng').value),
                city: document.getElementById('modalCity').value
            };
            
            if (!hotelData.name || !hotelData.address) {
                alert('Заполните название и адрес отеля');
                return;
            }
            
            fetch('/api/hotel/address/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(hotelData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Обновляем отображение
                    updateHotelDisplay(data.hotel);
                    // Обновляем карту
                    updateOurHotelOnMap(data.hotel);
                    
                    // Закрываем модальное окно (правильный способ для Bootstrap 5)
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addressModal'));
                    modal.hide();
                    
                    // Показываем уведомление
                    showNotification('Адрес успешно обновлен!', 'success');
                }
            })
            .catch(error => {
                console.error('Ошибка сохранения адреса:', error);
                showNotification('Ошибка сохранения адреса', 'error');
            });
        }
        
        // Показать уведомление
        function showNotification(message, type = 'info') {
            // Создаем элемент уведомления
            const alert = document.createElement('div');
            alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            alert.style.top = '20px';
            alert.style.right = '20px';
            alert.style.zIndex = '9999';
            alert.style.minWidth = '300px';
            
            alert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            // Добавляем на страницу
            document.body.appendChild(alert);
            
            // Автоматически удаляем через 3 секунды
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 3000);
        }
        
        // Обновить отображение адреса на странице
        function updateHotelDisplay(hotel) {
            document.getElementById('hotelName').textContent = hotel.name;
            document.getElementById('hotelAddress').textContent = hotel.address;
            document.getElementById('hotelPrice').textContent = hotel.price.toLocaleString('ru-RU') + ' ₽';
            document.getElementById('hotelRating').textContent = hotel.rating + ' ★';
        }
        
        // Обновить наш отель на карте
        function updateOurHotelOnMap(hotel) {
            // Удаляем старый маркер
            if (markers['our_hotel']) {
                map.removeLayer(markers['our_hotel']);
            }
            
            // Создаем новый маркер
            const icon = L.divIcon({
                className: 'custom-icon',
                html: `
                    <div style="
                        background-color: ${hotel.color};
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        border: 3px solid white;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-size: 20px;
                    ">
                        <i class="bi bi-house-door"></i>
                    </div>
                `,
                iconSize: [40, 40]
            });
            
            const marker = L.marker([hotel.lat, hotel.lng], { icon: icon })
                .addTo(map)
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <h6><b>${hotel.name}</b></h6>
                        <p><i class="bi bi-geo-alt"></i> ${hotel.address}</p>
                        <p><i class="bi bi-cash"></i> <b>${hotel.price.toLocaleString('ru-RU')} ₽</b></p>
                        <p><i class="bi bi-star"></i> ${hotel.rating} ★</p>
                    </div>
                `);
            
            markers['our_hotel'] = marker;
            
            // Центрируем карту на новом местоположении
            map.setView([hotel.lat, hotel.lng], 14);
        }
        
        // Загрузить данные об отеле при инициализации
        function loadHotelData() {
            fetch('/api/hotel/address')
                .then(response => response.json())
                .then(data => {
                    updateHotelDisplay(data);
                })
                .catch(error => {
                    console.error('Ошибка загрузки данных отеля:', error);
                });
        }
        
        // Обновить инициализацию
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboardData();
            updateTime();
            checkApiStatus();
            loadHotelData(); // Загружаем данные отеля
            setInterval(updateTime, 60000);
        });
        
        // Фильтр цены
        document.getElementById('priceFilter').addEventListener('input', function(e) {
            document.getElementById('priceFilterValue').textContent = 
                parseInt(e.target.value).toLocaleString('ru-RU') + ' ₽';
        });
        
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
        function updateTime() {
            const now = new Date();
            document.getElementById('lastUpdate').textContent = 
                now.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        }

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

        function loadDashboardData() {
            try {
                const competitorsRes = fetch('/api/competitors');
                const avgPrice = 5500;
                document.getElementById('avgPrice').textContent = avgPrice.toLocaleString('ru-RU') + ' ₽';
                createPriceChart();
            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
            }
        }

        function createPriceChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');
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

        async function calculateOptimalPrice() {
            const basePrice = parseFloat(document.getElementById('basePrice').value);
            const season = parseFloat(document.getElementById('season').value);
            const occupancy = parseInt(document.getElementById('occupancySlider').value) / 100;

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
                document.getElementById('finalPrice').textContent = 
                    result.final_price.toLocaleString('ru-RU') + ' ₽';
                document.getElementById('priceResult').style.display = 'block';
            } catch (error) {
                alert('Ошибка расчета: ' + error.message);
            }
        }

        function applyPrice() {
            const price = document.getElementById('finalPrice').textContent;
            alert('Цена ' + price + ' успешно применена!');
        }

        function calculatePrice() {
            showTab('pricing');
        }

        function analyzeCompetitors() {
            showTab('competitors');
        }

        function generateReport() {
            showTab('reports');
        }

        document.getElementById('occupancySlider').addEventListener('input', function(e) {
            document.getElementById('occupancyValue').textContent = e.target.value + '%';
        });
    </script>
    
    <div class="modal fade" id="addressModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-geo-alt"></i> Изменить адрес отеля</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Название отеля</label>
                                <input type="text" class="form-control" id="modalHotelName" value="Наш отель">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Поиск адреса</label>
                                <div class="input-group mb-2">
                                    <input type="text" class="form-control" id="addressSearch" 
                                           placeholder="Например: Москворечье 19 или Красная площадь"
                                           list="addressSuggestions" autocomplete="off">
                                    <button class="btn btn-primary" onclick="searchAddress()">
                                        <i class="bi bi-search"></i>
                                    </button>
                                </div>
                                <datalist id="addressSuggestions"></datalist>
                                <div class="form-text">Можно вводить адрес, название места или координаты</div>
                            </div>
                            
                            <!-- Блок поиска по координатам -->
                            <div class="card mb-3">
                                <div class="card-body">
                                    <h6 class="card-title"><i class="bi bi-geo"></i> Поиск по координатам</h6>
                                    <div class="row g-2">
                                        <div class="col-md-6">
                                            <input type="text" class="form-control form-control-sm" 
                                                   id="coordLat" placeholder="Широта (55.7558)">
                                        </div>
                                        <div class="col-md-6">
                                            <input type="text" class="form-control form-control-sm" 
                                                   id="coordLng" placeholder="Долгота (37.6173)">
                                        </div>
                                        <div class="col-12">
                                            <button class="btn btn-outline-secondary btn-sm w-100 mt-1" 
                                                    onclick="searchByCoordinates()">
                                                <i class="bi bi-geo-alt"></i> Найти адрес по координатам
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div id="searchResults" style="max-height: 300px; overflow-y: auto; display: none;">
                                <h6>Результаты поиска:</h6>
                                <div id="addressResultsList"></div>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Город</label>
                                <select class="form-select" id="modalCity">
                                    <option value="Москва" selected>Москва</option>
                                    <option value="Санкт-Петербург">Санкт-Петербург</option>
                                    <option value="Казань">Казань</option>
                                    <option value="Сочи">Сочи</option>
                                    <option value="Екатеринбург">Екатеринбург</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Адрес</label>
                                <textarea class="form-control" id="modalAddress" rows="3" placeholder="Полный адрес"></textarea>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Широта (lat)</label>
                                        <input type="number" step="0.000001" class="form-control" id="modalLat" value="55.7558">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Долгота (lng)</label>
                                        <input type="number" step="0.000001" class="form-control" id="modalLng" value="37.6173">
                                    </div>
                                </div>
                            </div>
                            <div class="alert alert-info">
                                <small>
                                    <i class="bi bi-info-circle"></i> 
                                    <strong>Как найти координаты:</strong><br>
                                    1. Откройте <a href="https://yandex.ru/maps" target="_blank">Яндекс.Карты</a><br>
                                    2. Найдите нужный адрес<br>
                                    3. Кликните правой кнопкой → "Что здесь?"<br>
                                    4. Координаты появятся в поисковой строке<br>
                                    Формат: <code>55.7558, 37.6173</code>
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    <button type="button" class="btn btn-primary" onclick="saveAddress()">
                        <i class="bi bi-check-lg"></i> Сохранить адрес
                    </button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


# ===== API ЭНДПОИНТЫ =====

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
            "competitors_map": "/api/competitors/map",
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


@app.get("/api/competitors/map")
async def get_competitors_map():
    """Данные для карты конкурентов"""
    return COMPETITORS_DATA


@app.post("/api/competitors/analyze")
async def analyze_competitors(competitor_ids: List[str]):
    """Анализ выбранных конкурентов"""
    selected = [c for c in COMPETITORS_DATA["competitors"] if c["id"] in competitor_ids]

    if not selected:
        raise HTTPException(status_code=400, detail="No competitors selected")

    prices = [c["price"] for c in selected]
    avg_price = sum(prices) / len(prices)

    return {
        "selected_count": len(selected),
        "average_price": round(avg_price, 2),
        "our_price": COMPETITORS_DATA["our_hotel"]["price"],
        "price_difference": round(avg_price - COMPETITORS_DATA["our_hotel"]["price"], 2),
        "recommendation": "Рассмотрите корректировку цены на 5-10%",
        "competitors": selected
    }


@app.post("/api/pricing/calculate")
async def calculate_price(request: PricingRequest):
    """Упрощенный расчет цены"""
    try:
        final_price = request.base_price * request.season_factor

        if request.occupancy_rate > 0.8:
            final_price *= 1.2
        elif request.occupancy_rate < 0.4:
            final_price *= 0.9

        if request.competitors_data:
            competitor_prices = [c.get('price', 0) for c in request.competitors_data if 'price' in c]
            if competitor_prices:
                avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
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
    base_price = 5500
    occupancy = 0.78

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


@app.get("/api/hotel/address")
async def get_hotel_address():
    """Получить текущий адрес нашего отеля"""
    return COMPETITORS_DATA["our_hotel"]


@app.post("/api/hotel/address/update")
async def update_hotel_address(update: HotelAddressUpdate):
    """Обновить адрес нашего отеля"""
    try:
        COMPETITORS_DATA["our_hotel"] = {
            "id": "our_hotel",
            "name": update.name,
            "lat": update.lat,
            "lng": update.lng,
            "price": COMPETITORS_DATA["our_hotel"]["price"],  # Сохраняем цену
            "rating": COMPETITORS_DATA["our_hotel"]["rating"],  # Сохраняем рейтинг
            "color": "#4361ee",
            "address": update.address,
            "distance": "0 км",
            "city": update.city
        }

        return {
            "success": True,
            "message": "Адрес отеля успешно обновлен",
            "hotel": COMPETITORS_DATA["our_hotel"],
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hotel/address/search")
async def search_address(query: str):
    """Поиск адресов через Nominatim (OpenStreetMap)"""
    import aiohttp

    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Слишком короткий запрос")

    try:
        # Используем Nominatim API (бесплатный)
        async with aiohttp.ClientSession() as session:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": 10,
                "countrycodes": "ru",  # ограничиваем Россией
                "accept-language": "ru",
                "viewbox": "37.3,55.5,37.9,56.0",  # примерная область Москвы
                "bounded": 0  # не ограничивать строго
            }

            # Добавляем User-Agent (требуется Nominatim)
            headers = {
                "User-Agent": "HotelPricingApp/1.0 (contact@example.com)"
            }

            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    # Если API не работает, используем мок
                    return await search_address_mock(query)

                data = await response.json()

                results = []
                for item in data:
                    # Формируем читаемый адрес
                    address_parts = []

                    # Используем display_name как основной адрес
                    display_name = item.get("display_name", "")

                    # Парсим адресные компоненты
                    address = item.get("address", {})

                    # Формируем понятное название
                    name_parts = []
                    if address.get("road"):
                        name_parts.append(address.get("road"))
                        if address.get("house_number"):
                            name_parts[-1] += f", {address.get('house_number')}"

                    name = " ".join(name_parts) if name_parts else display_name.split(",")[0]

                    # Формируем полный адрес
                    address_components = []

                    # Добавляем основные компоненты в правильном порядке
                    components_order = [
                        "house_number", "road", "village", "town",
                        "city_district", "city", "state", "country"
                    ]

                    for comp in components_order:
                        if comp in address and address[comp]:
                            address_components.append(address[comp])

                    full_address = ", ".join(address_components) if address_components else display_name

                    # Определяем город
                    city = (
                            address.get("city") or
                            address.get("town") or
                            address.get("village") or
                            "Москва"
                    )

                    results.append({
                        "name": name[:100],  # ограничиваем длину
                        "address": full_address[:200],
                        "lat": float(item["lat"]),
                        "lng": float(item["lon"]),
                        "city": city,
                        "display_name": display_name[:300],
                        "importance": item.get("importance", 0)
                    })

                # Сортируем по важности
                results.sort(key=lambda x: x["importance"], reverse=True)

                return {
                    "query": query,
                    "results": results[:8],
                    "count": len(results),
                    "source": "nominatim"
                }

    except Exception as e:
        print(f"Ошибка геокодирования: {e}")
        # В случае ошибки возвращаем мок-данные
        return await search_address_mock(query)


async def search_address_mock(query: str):
    """Мок-поиск адресов с расширенными данными"""
    import re

    # Более умный мок-поиск
    query_lower = query.lower()

    # Стандартные тестовые результаты
    test_results = [
        {
            "name": "Красная площадь, 1",
            "address": "Красная площадь, 1, Москва, Россия",
            "lat": 55.754047,
            "lng": 37.620409,
            "city": "Москва",
            "description": "Историческая площадь"
        },
        {
            "name": "ул. Тверская, 15",
            "address": "ул. Тверская, 15, Москва, Россия",
            "lat": 55.760428,
            "lng": 37.606839,
            "city": "Москва",
            "description": "Центральная улица"
        },
        {
            "name": "Московский Кремль",
            "address": "Московский Кремль, Москва, Россия",
            "lat": 55.751244,
            "lng": 37.618423,
            "city": "Москва",
            "description": "Историческая крепость"
        },
        {
            "name": "Москва-Сити",
            "address": "Пресненская набережная, 8с1, Москва, Россия",
            "lat": 55.748710,
            "lng": 37.539712,
            "city": "Москва",
            "description": "Деловой центр"
        },
        {
            "name": "ВДНХ",
            "address": "проспект Мира, 119, Москва, Россия",
            "lat": 55.829493,
            "lng": 37.631676,
            "city": "Москва",
            "description": "Выставка достижений народного хозяйства"
        }
    ]

    # Если запрос содержит "Москворечье", добавляем соответствующие результаты
    if "москвореч" in query_lower:
        # Ищем номер дома в запросе
        house_match = re.search(r'(\d+[а-я]*)$', query)
        house_number = house_match.group(1) if house_match else "19"

        test_results.insert(0, {
            "name": f"Москворечье, {house_number}",
            "address": f"ул. Москворечье, {house_number}, Москва, Россия",
            "lat": 55.661234,
            "lng": 37.660987,
            "city": "Москва",
            "description": "Жилой район"
        })

    # Если запрос содержит номер дома, пытаемся его обработать
    elif re.search(r'\d+', query):
        street_match = re.match(r'([а-яё\s]+)\s*(\d+[а-я]*)', query, re.IGNORECASE)
        if street_match:
            street_name = street_match.group(1).strip()
            house_number = street_match.group(2)

            test_results.insert(0, {
                "name": f"{street_name}, {house_number}",
                "address": f"{street_name}, {house_number}, Москва, Россия",
                "lat": 55.7 + (len(query) % 100) / 1000,  # Генерация координат
                "lng": 37.6 + (len(query) % 100) / 1000,
                "city": "Москва",
                "description": "По запросу пользователя"
            })

    # Фильтрация результатов по запросу
    filtered_results = []
    for result in test_results:
        # Ищем совпадения в названии, адресе или описании
        if (query_lower in result["name"].lower() or
                query_lower in result["address"].lower() or
                query_lower in result["description"].lower()):
            filtered_results.append(result)

    # Если ничего не найдено, возвращаем все результаты
    results = filtered_results if filtered_results else test_results

    return {
        "query": query,
        "results": results[:5],
        "count": len(results),
        "source": "mock"
    }


@app.get("/api/hotel/address/reverse")
async def reverse_geocode(lat: float, lng: float):
    """Обратное геокодирование через Nominatim"""
    import aiohttp

    try:
        # Используем Nominatim API для обратного геокодирования
        async with aiohttp.ClientSession() as session:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
                "accept-language": "ru",
                "zoom": 18  # детализация
            }

            headers = {
                "User-Agent": "HotelPricingApp/1.0 (contact@example.com)"
            }

            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    display_name = data.get("display_name", "")
                    address = data.get("address", {})

                    # Формируем название
                    name_parts = []
                    if address.get("road"):
                        road = address.get("road")
                        if address.get("house_number"):
                            road += f" {address.get('house_number')}"
                        name_parts.append(road)

                    name = " ".join(name_parts) if name_parts else display_name.split(",")[0]

                    # Определяем город
                    city = (
                            address.get("city") or
                            address.get("town") or
                            address.get("village") or
                            address.get("state") or
                            "Неизвестно"
                    )

                    return {
                        "success": True,
                        "name": name,
                        "address": display_name,
                        "lat": lat,
                        "lng": lng,
                        "city": city,
                        "raw": data
                    }

        # Если не получилось, возвращаем координаты
        return {
            "success": True,
            "name": f"Точка ({lat:.6f}, {lng:.6f})",
            "address": f"Координаты: {lat:.6f}, {lng:.6f}",
            "lat": lat,
            "lng": lng,
            "city": "Москва"
        }

    except Exception as e:
        print(f"Ошибка обратного геокодирования: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/hotel/address/autocomplete")
async def autocomplete_address(query: str):
    """Автодополнение адресов (Photon API)"""
    import aiohttp

    if not query or len(query) < 2:
        return {"suggestions": []}

    try:
        # Используем Photon API для автодополнения (быстрее Nominatim)
        async with aiohttp.ClientSession() as session:
            url = "https://photon.komoot.io/api/"
            params = {
                "q": query,
                "lang": "ru",
                "limit": 8,
                "lat": 55.7558,  # центр Москвы
                "lon": 37.6173,
                "radius": 50000  # 50 км радиус
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    suggestions = []
                    for feature in data.get("features", []):
                        properties = feature.get("properties", {})
                        geometry = feature.get("geometry", {})

                        name = properties.get("name", "")
                        street = properties.get("street", "")
                        housenumber = properties.get("housenumber", "")
                        city = properties.get("city", "Москва")

                        # Формируем отображаемое имя
                        if street and housenumber:
                            display_name = f"{street}, {housenumber}"
                        elif street:
                            display_name = street
                        else:
                            display_name = name

                        # Формируем полный адрес
                        address_parts = []
                        if street:
                            if housenumber:
                                address_parts.append(f"{street}, {housenumber}")
                            else:
                                address_parts.append(street)

                        if city:
                            address_parts.append(city)

                        if properties.get("country"):
                            address_parts.append(properties["country"])

                        full_address = ", ".join(address_parts)

                        suggestions.append({
                            "display": display_name,
                            "full_address": full_address,
                            "lat": geometry.get("coordinates", [])[1] if geometry.get("coordinates") else 55.7558,
                            "lng": geometry.get("coordinates", [])[0] if geometry.get("coordinates") else 37.6173,
                            "city": city
                        })

                    return {"suggestions": suggestions}

    except Exception as e:
        print(f"Ошибка автодополнения: {e}")

    return {"suggestions": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
