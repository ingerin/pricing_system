from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
from datetime import datetime
import json
import requests

app = FastAPI(title="Hotel Dynamic Pricing API", version="1.0.0")

YANDEX_MAPS_API_KEY = "1380fad3-8012-4945-ab18-e64e947a94e3"
YANDEX_GEOCODE_URL = "https://geocode-maps.yandex.ru/1.x/"

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


class AddressUpdateRequest(BaseModel):
    hotel_id: str
    new_address: str


class HotelInfoUpdateRequest(BaseModel):
    hotel_id: str
    price: Optional[float] = None
    rating: Optional[float] = None
    name: Optional[str] = None


class NewCompetitorRequest(BaseModel):
    name: str
    address: str
    price: float
    rating: float = 4.0
    lat: Optional[float] = None
    lng: Optional[float] = None


class DeleteCompetitorRequest(BaseModel):
    competitor_id: str


class ReportRequest(BaseModel):
    report_type: str
    period: Optional[str] = "month"
    format: Optional[str] = "pdf"
    hotel_id: str = "our_hotel"


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
        "distance": "0 км"
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
            "color": "#118ab2",
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


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ЯНДЕКС КАРТАМИ =====

async def geocode_address(address: str):
    """Геокодирование адреса через Яндекс API"""
    try:
        params = {
            "apikey": YANDEX_MAPS_API_KEY,
            "geocode": address,
            "format": "json",
            "lang": "ru_RU"
        }

        response = requests.get(YANDEX_GEOCODE_URL, params=params, timeout=10)

        # Добавим отладку
        print(f"Geocode request for: {address}")
        print(f"Response status: {response.status_code}")

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API error: {response.status_code}"
            }

        data = response.json()

        # Отладка структуры ответа
        print(f"Response structure: {data.keys()}")

        feature_members = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])

        if feature_members:
            feature = feature_members[0]
            geo_object = feature["GeoObject"]

            # Получаем координаты (в Яндексе порядок: долгота, широта)
            pos = geo_object["Point"]["pos"]
            lng_str, lat_str = pos.split()
            lat = float(lat_str)
            lng = float(lng_str)

            # Получаем полный адрес
            full_address = geo_object.get("metaDataProperty", {}).get(
                "GeocoderMetaData", {}).get("text", address)

            return {
                "success": True,
                "lat": lat,
                "lng": lng,
                "address": full_address,
                "coordinates": f"{lat},{lng}"
            }
        else:
            return {
                "success": False,
                "error": "Адрес не найден"
            }

    except Exception as e:
        print(f"Geocode error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/search-address")
async def search_address(request: Dict[str, Any]):
    """Поиск адресов для подсказок"""
    query = request.get("query", "")

    if not query or len(query) < 2:
        return {"suggestions": []}

    try:
        params = {
            "apikey": YANDEX_MAPS_API_KEY,
            "geocode": query,
            "format": "json",
            "lang": "ru_RU",
            "results": 5  # Ограничиваем количество результатов
        }

        response = requests.get(YANDEX_GEOCODE_URL, params=params, timeout=5)

        if response.status_code != 200:
            return {"suggestions": []}

        data = response.json()
        feature_members = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])

        suggestions = []
        for feature in feature_members[:5]:  # Берем первые 5
            geo_object = feature["GeoObject"]
            address = geo_object.get("metaDataProperty", {}).get(
                "GeocoderMetaData", {}).get("text", "")

            if address:
                suggestions.append({
                    "address": address,
                    "description": geo_object.get("description", ""),
                    "name": geo_object.get("name", "")
                })

        return {"suggestions": suggestions}

    except Exception as e:
        print(f"Search address error: {e}")
        return {"suggestions": []}


async def calculate_distance(coord1: Dict[str, float], coord2: Dict[str, float]):
    """Простой расчет расстояния между двумя точками (в км)"""
    import math

    lat1, lon1 = coord1["lat"], coord1["lng"]
    lat2, lon2 = coord2["lat"], coord2["lng"]

    # Формула гаверсинусов
    R = 6371.0  # Радиус Земли в км

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    if distance < 1:
        return f"{int(distance * 1000)} м"
    else:
        return f"{distance:.1f} км"


# ===== HTML ИНТЕРФЕЙС (обновленный) =====

# HTML шаблон для дашборда с добавленной функциональностью
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
            height: 500px;
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
        
        .selected-marker {
            border-color: #4361ee !important;
            border-width: 3px !important;
            box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.3) !important;
        }
        
        /* Стиль для нашего отеля в списке */
        .hotel-card.our-hotel {
            border: 2px solid #4361ee;
            background-color: rgba(67, 97, 238, 0.05);
        }

        .hotel-card.our-hotel:hover {
            border-color: #3a0ca3;
            box-shadow: 0 5px 15px rgba(67, 97, 238, 0.2);
        }

        .price-badge.price-our-hotel {
            background-color: #4361ee;
            color: white;
        }

        /* Подсветка нашего отеля при наведении в списке */
        .hotel-card.our-hotel .card-title {
            color: #4361ee;
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

        /* Модальное окно для изменения адреса */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }

        .address-search {
            position: relative;
            margin-bottom: 20px;
        }

        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
            display: none;
            z-index: 1000;
        }

        .search-result-item {
            padding: 10px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        }

        .search-result-item:hover {
            background: #f0f0f0;
        }

        /* Кнопка изменения адреса */
        .btn-change-address {
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: #4361ee;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .btn-change-address:hover {
            background: #3a0ca3;
        }

        /* Стили для формы редактирования */
        .edit-form-group {
            margin-bottom: 15px;
        }

        .edit-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }

        .current-value {
            color: #666;
            font-size: 0.9rem;
        }

        .price-input-group {
            position: relative;
        }

        .price-symbol {
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: #666;
        }

        .price-input {
            padding-left: 30px;
        }

        .rating-slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .rating-value {
            font-weight: bold;
            min-width: 40px;
            text-align: center;
            font-size: 1.1rem;
        }

        /* Иконки рейтинга */
        .rating-stars {
            display: flex;
            gap: 2px;
            margin: 10px 0;
        }

        .star-icon {
            color: #ffd43b;
            font-size: 1.2rem;
        }

        /* Статистика отеля */
        .hotel-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }

        .stat-item {
            text-align: center;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 5px;
        }

        .stat-value {
            font-size: 1.3rem;
            font-weight: bold;
            color: #4361ee;
        }

        /* Кнопки управления отелем */
        .hotel-controls {
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .btn-hotel-control {
            background: #4361ee;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
            min-width: 160px;
            justify-content: center;
        }

        .btn-hotel-control:hover {
            background: #3a0ca3;
        }

        .btn-success {
            background: #51cf66 !important;
            border-color: #51cf66 !important;
        }

        .btn-success:hover {
            background: #40c057 !important;
            border-color: #40c057 !important;
        }

        .btn-edit-info {
            background: #ff6b6b;
        }

        .btn-edit-info:hover {
            background: #ff5252;
        }

        /* Контейнер для графика */
        .chart-container {
            position: relative;
            height: 500px;
            width: 100%;
        }

        canvas {
            display: block;
            max-height: 100%;
        }

        /* Стили для модальных окон с информацией об отелях */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 3000;
            display: none;
            align-items: center;
            justify-content: center;
            overflow-y: auto;
            padding: 20px;
        }

        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            animation: modalSlideIn 0.3s ease-out;
        }

        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Стили для сравнения */
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
        }

        .comparison-table th,
        .comparison-table td {
            padding: 10px;
            text-align: center;
            border: 1px solid #dee2e6;
        }

        .comparison-table th {
            background-color: #f8f9fa;
            font-weight: 600;
        }

        /* Улучшенные стили для карточек сравнения */
        .comparison-card {
            transition: transform 0.3s;
            height: 100%;
        }

        .comparison-card:hover {
            transform: translateY(-5px);
        }

        /* Анимация для появления попапа */
        .leaflet-popup-content-wrapper {
            animation: popupFadeIn 0.2s ease-out;
        }

        @keyframes popupFadeIn {
            from {
                opacity: 0;
                transform: scale(0.9);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        /* Анимация для успешного применения цены */
        @keyframes priceUpdate {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .price-updated {
            animation: priceUpdate 0.5s ease-in-out;
        }
        
        /* Стили для кнопки применения цены */
        .btn-action {
            position: relative;
            overflow: hidden;
        }
        
        .btn-action:after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 5px;
            height: 5px;
            background: rgba(255, 255, 255, 0.5);
            opacity: 0;
            border-radius: 100%;
            transform: scale(1, 1) translate(-50%);
            transform-origin: 50% 50%;
        }
        
        .btn-action:focus:not(:active)::after {
            animation: ripple 1s ease-out;
        }
        
        @keyframes ripple {
            0% {
                transform: scale(0, 0);
                opacity: 0.5;
            }
            20% {
                transform: scale(25, 25);
                opacity: 0.3;
            }
            100% {
                opacity: 0;
                transform: scale(40, 40);
            }
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

            <!-- Модальное окно изменения адреса -->
            <div id="addressModal" class="modal-overlay">
                <div class="modal-content">
                    <h4><i class="bi bi-geo-alt"></i> Изменить адрес отеля</h4>

                    <div class="address-search">
                        <label class="form-label">Введите новый адрес:</label>
                        <div class="input-group">
                            <input type="text" 
                                   class="form-control" 
                                   id="addressInput" 
                                   placeholder="Например: Москва, Красная площадь, 1"
                                   onkeyup="searchAddress(event)">
                            <button class="btn btn-primary" onclick="searchAddress()">
                                <i class="bi bi-search"></i>
                            </button>
                        </div>

                        <div id="searchResults" class="search-results">
                            <!-- Результаты поиска будут здесь -->
                        </div>

                        <div class="mt-2">
                            <small class="text-muted">Начните вводить адрес, появятся подсказки</small>
                        </div>
                    </div>

                    <div id="selectedAddressPreview" class="mb-3" style="display: none;">
                        <div class="alert alert-success">
                            <h6><i class="bi bi-check-circle"></i> Выбранный адрес:</h6>
                            <p id="selectedAddressText"></p>
                            <small id="selectedCoordinates" class="text-muted"></small>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between">
                        <button class="btn btn-outline-secondary" onclick="closeAddressModal()">
                            <i class="bi bi-x"></i> Отмена
                        </button>
                        <button class="btn btn-primary" id="confirmAddressBtn" onclick="updateHotelAddress()" disabled>
                            <i class="bi bi-check-lg"></i> Применить адрес
                        </button>
                    </div>
                </div>
            </div>

            <!-- Модальное окно редактирования информации об отеле -->
            <div id="hotelInfoModal" class="modal-overlay">
                <div class="modal-content">
                    <h4><i class="bi bi-pencil-square"></i> Редактировать информацию об отеле</h4>

                    <div id="currentHotelInfo" class="mb-4">
                        <!-- Текущая информация будет загружена здесь -->
                    </div>

                    <form id="hotelInfoForm">
                        <div class="edit-form-group">
                            <div class="edit-label">
                                <label class="form-label">Название отеля</label>
                                <span class="current-value" id="currentName"></span>
                            </div>
                            <input type="text" class="form-control" id="hotelNameInput" 
                                   placeholder="Введите новое название">
                        </div>

                        <div class="edit-form-group">
                            <div class="edit-label">
                                <label class="form-label">Цена за ночь (₽)</label>
                                <span class="current-value" id="currentPrice"></span>
                            </div>
                            <div class="price-input-group">
                                <span class="price-symbol">₽</span>
                                <input type="number" class="form-control price-input" 
                                       id="hotelPriceInput" min="1000" max="50000" step="100">
                            </div>
                            <small class="text-muted">Цена должна быть в диапазоне 1000 - 50000 ₽</small>
                        </div>

                        <div class="edit-form-group">
                            <div class="edit-label">
                                <label class="form-label">Рейтинг</label>
                                <span class="current-value" id="currentRating"></span>
                            </div>
                            <div class="rating-slider-container">
                                <input type="range" class="form-range" id="hotelRatingInput" 
                                       min="1" max="5" step="0.1" value="4.5">
                                <div class="rating-value">
                                    <span id="ratingValueDisplay">4.5</span> ★
                                </div>
                            </div>
                            <div class="rating-stars" id="ratingStars">
                                <!-- Звезды будут сгенерированы JavaScript -->
                            </div>
                            <small class="text-muted">Перетащите ползунок для изменения рейтинга</small>
                        </div>

                        <div class="hotel-stats">
                            <div class="stat-item">
                                <div class="stat-label">Позиция на рынке</div>
                                <div class="stat-value" id="marketPositionStat">#3</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Средняя цена конкурентов</div>
                                <div class="stat-value" id="avgCompetitorPrice">5,540 ₽</div>
                            </div>
                        </div>

                        <div class="d-flex justify-content-between mt-4">
                            <button type="button" class="btn btn-outline-secondary" onclick="closeHotelInfoModal()">
                                <i class="bi bi-x"></i> Отмена
                            </button>
                            <button type="button" class="btn btn-primary" onclick="updateHotelInfo()">
                                <i class="bi bi-check-lg"></i> Сохранить изменения
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Модальное окно добавления конкурента -->
            <div id="addCompetitorModal" class="modal-overlay">
                <div class="modal-content">
                    <h4><i class="bi bi-plus-circle"></i> Добавить нового конкурента</h4>

                    <form id="addCompetitorForm">
                        <div class="edit-form-group">
                            <label class="form-label">Название отеля *</label>
                            <input type="text" class="form-control" id="competitorNameInput" 
                                   placeholder="Например: Президент Отель" required>
                        </div>

                        <div class="edit-form-group">
                            <label class="form-label">Адрес *</label>
                            <div class="address-search">
                                <div class="input-group">
                                    <input type="text" class="form-control" id="competitorAddressInput" 
                                           placeholder="Например: Москва, ул. Тверская, 10"
                                           onkeyup="searchCompetitorAddress(event)">
                                    <button class="btn btn-primary" type="button" onclick="searchCompetitorAddress()">
                                        <i class="bi bi-search"></i>
                                    </button>
                                </div>
                                <div id="competitorSearchResults" class="search-results">
                                    <!-- Результаты поиска будут здесь -->
                                </div>
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="edit-form-group">
                                    <label class="form-label">Цена за ночь (₽) *</label>
                                    <div class="price-input-group">
                                        <span class="price-symbol">₽</span>
                                        <input type="number" class="form-control price-input" 
                                               id="competitorPriceInput" min="1000" max="50000" step="100" 
                                               value="5000" required>
                                    </div>
                                    <small class="text-muted">Цена должна быть в диапазоне 1000 - 50000 ₽</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="edit-form-group">
                                    <label class="form-label">Рейтинг *</label>
                                    <div class="rating-slider-container">
                                        <input type="range" class="form-range" id="competitorRatingInput" 
                                               min="1" max="5" step="0.1" value="4.5">
                                        <div class="rating-value">
                                            <span id="competitorRatingValueDisplay">4.5</span> ★
                                        </div>
                                    </div>
                                    <div class="rating-stars" id="competitorRatingStars">
                                        <!-- Звезды будут сгенерированы JavaScript -->
                                    </div>
                                    <small class="text-muted">Перетащите ползунок для изменения рейтинга</small>
                                </div>
                            </div>
                        </div>

                        <div id="selectedCompetitorAddressPreview" class="mb-3" style="display: none;">
                            <div class="alert alert-info">
                                <h6><i class="bi bi-check-circle"></i> Выбранный адрес:</h6>
                                <p id="selectedCompetitorAddressText"></p>
                                <small id="selectedCompetitorCoordinates" class="text-muted"></small>
                            </div>
                        </div>

                        <div class="d-flex justify-content-between mt-4">
                            <button type="button" class="btn btn-outline-secondary" onclick="closeAddCompetitorModal()">
                                <i class="bi bi-x"></i> Отмена
                            </button>
                            <button type="submit" class="btn btn-success" id="addCompetitorBtn">
                                <i class="bi bi-plus-lg"></i> Добавить конкурента
                            </button>
                        </div>
                    </form>
                </div>
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
                            <div class="metric-value" id="monthRevenue">12.5K ₽</div>
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
                                <div class="chart-container">
                                    <canvas id="priceChart"></canvas>
                                </div>
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
                                
                                <!-- Добавлен новый параграф с рекомендацией -->
                                <p class="mb-3" id="priceRecommendation">
                                    <i class="bi bi-lightbulb"></i> Рекомендуется для максимизации прибыли
                                </p>
                                
                                <div class="d-flex gap-2">
                                    <button class="btn btn-primary btn-action" onclick="applyPrice()">
                                        <i class="bi bi-check-lg"></i> Применить эту цену
                                    </button>
                                    <button class="btn btn-outline-secondary" onclick="document.getElementById('priceResult').style.display='none'">
                                        <i class="bi bi-x"></i> Закрыть
                                    </button>
                                </div>
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
                            <!-- Кнопки управления отелем -->
                            <div class="hotel-controls">
                                <button class="btn-hotel-control" onclick="openAddressModal()">
                                    <i class="bi bi-geo-alt"></i> Изменить адрес
                                </button>
                                <button class="btn-hotel-control btn-edit-info" onclick="openHotelInfoModal()">
                                    <i class="bi bi-pencil"></i> Редактировать отель
                                </button>
                                <button class="btn-hotel-control btn-success" onclick="openAddCompetitorModal()">
                                    <i class="bi bi-plus-circle"></i> Добавить конкурента
                                </button>
                            </div>

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
                                    <span>Дороже нас (на 500+ ₽)</span>
                                </div>
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color: #ffd166;"></div>
                                    <span>Примерно одинаково (±500 ₽)</span>
                                </div>
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color: #06d6a0;"></div>
                                    <span>Дешевле нас (на 500+ ₽)</span>
                                </div>
                            </div>
                        </div>

                        <!-- Фильтры -->
                        <div class="filter-panel">
                            <div class="row">
                                <div class="col-md-4">
                                    <label class="form-label">Ценовой диапазон</label>
                                    <input type="range" class="form-range" id="priceFilter" min="3000" max="10000" value="10000">
                                    <small>До: <span id="priceFilterValue">10,000 ₽</span></small>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label">Минимальный рейтинг</label>
                                    <select class="form-select" id="ratingFilter">
                                        <option value="0" selected>Все</option>
                                        <option value="4">4.0+</option>
                                        <option value="4.5">4.5+</option>
                                        <option value="4.7">4.7+</option>
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label">Расстояние</label>
                                    <select class="form-select" id="distanceFilter">
                                        <option value="5" selected>Все</option>
                                        <option value="2">До 2 км</option>
                                        <option value="1">До 1 км</option>
                                        <option value="0.5">До 500 м</option>
                                    </select>
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

                        <!-- Информация о нашем отеле -->
                        <div class="card mt-3">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="bi bi-house-door"></i> Наш отель
                                    <button class="btn btn-sm btn-outline-primary float-end" onclick="openHotelInfoModal()">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                </h5>
                                <div class="mt-3">
                                    <div class="d-flex justify-content-between mb-2">
                                        <span>Цена:</span>
                                        <strong id="ourHotelPriceDisplay">5,500 ₽</strong>
                                    </div>
                                    <div class="d-flex justify-content-between mb-2">
                                        <span>Рейтинг:</span>
                                        <div>
                                            <span id="ourHotelRatingDisplay">4.5</span>
                                            <i class="bi bi-star-fill text-warning"></i>
                                        </div>
                                    </div>
                                    <div class="d-flex justify-content-between">
                                        <span>Адрес:</span>
                                        <small class="text-muted text-end" id="ourHotelAddressDisplay">Красная площадь, 1</small>
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

        <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Глобальные переменные
        let map = null;
        let markers = {};
        let selectedHotels = new Set();
        let ourHotelPrice = null;
        let ourHotelData = null;
        let selectedAddress = null;
        let priceChart = null;
        let allCompetitorsData = [];
        let selectedCompetitorAddress = null;

        // Инициализация при загрузке
        document.addEventListener('DOMContentLoaded', function() {
        loadCurrentHotelInfo().then(() => {
            loadDashboardData();
            updateTime();
            checkApiStatus();
            setInterval(updateTime, 60000);
            initRatingStars();
            loadReportsHistory();
        });
        
            // Добавляем обработчики для модальных окон
            document.getElementById('addressModal').addEventListener('click', function(e) {
                if (e.target === this) {
                    closeAddressModal();
                }
            });

            document.getElementById('hotelInfoModal').addEventListener('click', function(e) {
                if (e.target === this) closeHotelInfoModal();
            });

            document.getElementById('addCompetitorModal').addEventListener('click', function(e) {
                if (e.target === this) closeAddCompetitorModal();
            });

            // Закрытие модальных окон по Escape
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    closeAddressModal();
                    closeHotelInfoModal();
                }
            });
            // Добавляем обработчики для фильтров
            const priceFilterElement = document.getElementById('priceFilter');
            const ratingFilterElement = document.getElementById('ratingFilter');
            const distanceFilterElement = document.getElementById('distanceFilter');

            if (priceFilterElement) {
                priceFilterElement.addEventListener('input', function(e) {
                    const priceFilterValueElement = document.getElementById('priceFilterValue');
                    if (priceFilterValueElement) {
                        priceFilterValueElement.textContent = 
                            parseInt(e.target.value).toLocaleString('ru-RU') + ' ₽';
                    }
                    // Применяем фильтры при изменении
                    applyFilters();
                });
            }

            if (ratingFilterElement) {
                ratingFilterElement.addEventListener('change', function() {
                    applyFilters();
                });
            }

            if (distanceFilterElement) {
                distanceFilterElement.addEventListener('change', function() {
                    applyFilters();
                });
            }
        });

        // ===== ФУНКЦИИ ДЛЯ ИЗМЕНЕНИЯ АДРЕСА =====

        function openAddressModal() {
            document.getElementById('addressModal').style.display = 'flex';
            document.getElementById('addressInput').focus();
        }

        function closeAddressModal() {
            document.getElementById('addressModal').style.display = 'none';
            resetAddressModal();
        }

        function resetAddressModal() {
            document.getElementById('addressInput').value = '';
            document.getElementById('searchResults').innerHTML = '';
            document.getElementById('searchResults').style.display = 'none';
            document.getElementById('selectedAddressPreview').style.display = 'none';
            document.getElementById('confirmAddressBtn').disabled = true;
            selectedAddress = null;
        }

        async function searchAddress(event = null) {
            const query = document.getElementById('addressInput').value.trim();

            if (!query || query.length < 2) {
                document.getElementById('searchResults').style.display = 'none';
                return;
            }

            // Если нажата Enter - сразу ищем
            if (event && event.key === 'Enter') {
                await performGeocode(query);
                return;
            }

            try {
                // Получаем подсказки от API
                const response = await fetch('/api/search-address', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query })
                });

                const data = await response.json();
                const resultsDiv = document.getElementById('searchResults');
                resultsDiv.innerHTML = '';

                if (data.suggestions && data.suggestions.length > 0) {
                    data.suggestions.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'search-result-item';
                        div.textContent = item.address;
                        div.onclick = () => selectAddressFromList(item.address);
                        resultsDiv.appendChild(div);
                    });
                    resultsDiv.style.display = 'block';
                } else {
                    // Если нет результатов от API, показываем локальные примеры
                    showLocalExamples(query, resultsDiv);
                }

            } catch (error) {
                console.error('Ошибка поиска адреса:', error);
                // При ошибке показываем локальные примеры
                const resultsDiv = document.getElementById('searchResults');
                showLocalExamples(query, resultsDiv);
            }
        }

        function showLocalExamples(query, resultsDiv) {
            const examples = [
                "Москва, Красная площадь, 1",
                "Москва, Тверская улица, 10",
                "Москва, Арбат, 25",
                "Москва, Ленинский проспект, 90",
                "Москва, Пресненская набережная, 12",
                "Санкт-Петербург, Невский проспект, 1",
                "Екатеринбург, улица Ленина, 1"
            ];

            const results = examples.filter(addr => 
                addr.toLowerCase().includes(query.toLowerCase())
            );

            resultsDiv.innerHTML = '';

            if (results.length > 0) {
                results.forEach(addr => {
                    const div = document.createElement('div');
                    div.className = 'search-result-item';
                    div.textContent = addr;
                    div.onclick = () => selectAddressFromList(addr);
                    resultsDiv.appendChild(div);
                });
                resultsDiv.style.display = 'block';
            } else {
                resultsDiv.style.display = 'none';
            }
        }

        async function performGeocode(query) {
            try {
                const response = await fetch('/api/geocode', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ address: query })
                });

                const result = await response.json();

                if (result.success) {
                    selectAddressFromResult(result);
                } else {
                    alert('Адрес не найден: ' + (result.error || 'Неизвестная ошибка'));
                }
            } catch (error) {
                console.error('Ошибка геокодирования:', error);
                alert('Ошибка при поиске адреса. Проверьте подключение к интернету.');
            }
        }

        function selectAddressFromList(address) {
            // Отправляем выбранный адрес на геокодирование
            performGeocode(address);
        }

        function selectAddressFromResult(result) {
            selectedAddress = result;

            document.getElementById('selectedAddressText').textContent = result.address;
            document.getElementById('selectedCoordinates').textContent = `Координаты: ${result.coordinates}`;
            document.getElementById('selectedAddressPreview').style.display = 'block';
            document.getElementById('searchResults').style.display = 'none';
            document.getElementById('confirmAddressBtn').disabled = false;
        }

        async function updateHotelAddress() {
            if (!selectedAddress) return;

            try {
                const response = await fetch('/api/hotel/update-address', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        hotel_id: 'our_hotel',
                        new_address: selectedAddress.address
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Обновляем данные нашего отеля
                    ourHotelData.lat = selectedAddress.lat;
                    ourHotelData.lng = selectedAddress.lng;
                    ourHotelData.address = selectedAddress.address;

                    // Обновляем маркер на карте
                    if (markers.our_hotel) {
                        map.removeLayer(markers.our_hotel);
                    }
                    addOurHotel(ourHotelData);

                    // Центрируем карту на новом местоположении
                    map.setView([selectedAddress.lat, selectedAddress.lng], 15);

                    applyFilters();

                    alert('Адрес успешно изменен!');
                    closeAddressModal();

                    // Перезагружаем данные о конкурентах (расстояния пересчитаются на сервере)
                    loadMapData();

                } else {
                    alert('Ошибка при обновлении адреса: ' + result.error);
                }
            } catch (error) {
                console.error('Ошибка обновления адреса:', error);
                alert('Ошибка при обновлении адреса');
            }
        }

        // ===== ФУНКЦИИ ДЛЯ РЕДАКТИРОВАНИЯ ИНФОРМАЦИИ ОБ ОТЕЛЕ =====

        function initRatingStars() {
            // Инициализация звезд рейтинга
            const ratingStars = document.getElementById('ratingStars');
            if (!ratingStars) return;

            ratingStars.innerHTML = '';
            for (let i = 0; i < 5; i++) {
                const star = document.createElement('i');
                star.className = 'bi bi-star-fill star-icon';
                ratingStars.appendChild(star);
            }
        }

        function updateRatingStars(rating) {
            const stars = document.querySelectorAll('#ratingStars .star-icon');
            if (!stars.length) return;

            stars.forEach((star, index) => {
                if (index < Math.floor(rating)) {
                    star.className = 'bi bi-star-fill star-icon';
                } else if (index < rating) {
                    star.className = 'bi bi-star-half star-icon';
                } else {
                    star.className = 'bi bi-star star-icon';
                }
            });
        }

        function openHotelInfoModal() {
            // Загружаем текущие данные отеля
            loadCurrentHotelInfo();
            document.getElementById('hotelInfoModal').style.display = 'flex';
        }

        function closeHotelInfoModal() {
            document.getElementById('hotelInfoModal').style.display = 'none';
        }

        async function loadCurrentHotelInfo() {
            try {
                const response = await fetch('/api/competitors/map');
                const data = await response.json();

                ourHotelData = data.our_hotel;

                // Проверяем, что данные загрузились
                if (!ourHotelData) {
                    console.error('Данные отеля не загрузились');
                    return;
                }
        
                // Обновляем текущие значения
                document.getElementById('currentName').textContent = ourHotelData.name;
                document.getElementById('currentPrice').textContent = ourHotelData.price.toLocaleString('ru-RU') + ' ₽';
                document.getElementById('currentRating').textContent = ourHotelData.rating + ' ★';

                // Устанавливаем значения в форму
                document.getElementById('hotelNameInput').value = ourHotelData.name;
                document.getElementById('hotelPriceInput').value = ourHotelData.price;
                document.getElementById('hotelRatingInput').value = ourHotelData.rating;
                document.getElementById('ratingValueDisplay').textContent = ourHotelData.rating;

                // Обновляем звезды рейтинга
                updateRatingStars(ourHotelData.rating);

                // Обновляем статистику
                updateStats(data.competitors);

                // Обновляем информацию в боковой панели
                updateOurHotelDisplay();

                return ourHotelData;
        
            } catch (error) {
                console.error('Ошибка загрузки данных отеля:', error);
                alert('Ошибка загрузки данных отеля');
                return null;
            }
        }

        function updateOurHotelDisplay() {
            if (!ourHotelData) {
                console.warn('ourHotelData не инициализирована в updateOurHotelDisplay');
                return;
            }

            const priceDisplay = document.getElementById('ourHotelPriceDisplay');
            const ratingDisplay = document.getElementById('ourHotelRatingDisplay');
            const addressDisplay = document.getElementById('ourHotelAddressDisplay');
            
            if (priceDisplay) {
                priceDisplay.textContent = ourHotelData.price.toLocaleString('ru-RU') + ' ₽';
                // Добавляем анимацию при обновлении
                priceDisplay.parentElement.classList.add('price-updated');
                setTimeout(() => {
                    priceDisplay.parentElement.classList.remove('price-updated');
                }, 500);
            }
            
            if (ratingDisplay) ratingDisplay.textContent = ourHotelData.rating;
            if (addressDisplay) addressDisplay.textContent = ourHotelData.address;
        
            // Обновляем метрики на главной вкладке
            const avgPriceElement = document.getElementById('avgPrice');
            if (avgPriceElement) {
                avgPriceElement.textContent = ourHotelData.price.toLocaleString('ru-RU') + ' ₽';
                avgPriceElement.parentElement.classList.add('price-updated');
                setTimeout(() => {
                    avgPriceElement.parentElement.classList.remove('price-updated');
                }, 500);
            }
        }

        async function updateHotelInfo() {
            const name = document.getElementById('hotelNameInput').value.trim();
            const price = parseFloat(document.getElementById('hotelPriceInput').value);
            const rating = parseFloat(document.getElementById('hotelRatingInput').value);

            // Валидация
            if (!name) {
                alert('Пожалуйста, введите название отеля');
                return;
            }

            if (isNaN(price) || price < 1000 || price > 50000) {
                alert('Цена должна быть в диапазоне 1000 - 50000 ₽');
                return;
            }

            if (isNaN(rating) || rating < 1 || rating > 5) {
                alert('Рейтинг должен быть в диапазоне 1.0 - 5.0');
                return;
            }

            try {
                const response = await fetch('/api/hotel/update-info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        hotel_id: 'our_hotel',
                        name: name,
                        price: price,
                        rating: rating
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Обновляем данные нашего отеля
                    ourHotelData.name = name;
                    ourHotelData.price = price;
                    ourHotelData.rating = rating;

                    // Обновляем маркер нашего отеля
                    if (markers.our_hotel) {
                        map.removeLayer(markers.our_hotel);
                    }
                    addOurHotel(ourHotelData);

                    // Удаляем и перерисовываем все маркеры конкурентов с новыми цветами
                    Object.keys(markers).forEach(key => {
                        if (key !== 'our_hotel') {
                            map.removeLayer(markers[key]);
                        }
                    });

                    // Загружаем данные конкурентов и перерисовываем их
                    const competitorsResponse = await fetch('/api/competitors/map');
                    const competitorsData = await competitorsResponse.json();

                    competitorsData.competitors.forEach(hotel => {
                        addCompetitorMarker(hotel);
                    });

                    // Обновляем отображение
                    updateOurHotelDisplay();

                    // Перерисовываем список отелей
                    renderHotelsList(competitorsData.competitors);

                    // Обновляем статистику
                    updateStats(competitorsData.competitors);

                    // Применяем фильтры после обновления
                    applyFilters();

                    alert('Информация об отеле успешно обновлена!');
                    closeHotelInfoModal();

                } else {
                    alert('Ошибка при обновлении информации: ' + result.error);
                }
            } catch (error) {
                console.error('Ошибка обновления информации:', error);
                alert('Ошибка при обновлении информации');
            }
        }

        // Обработчик изменения ползунка рейтинга
        document.getElementById('hotelRatingInput').addEventListener('input', function(e) {
            const rating = parseFloat(e.target.value);
            document.getElementById('ratingValueDisplay').textContent = rating.toFixed(1);
            updateRatingStars(rating);
        });

        // ===== ФУНКЦИИ ДЛЯ ДОБАВЛЕНИЯ КОНКУРЕНТА =====

        function openAddCompetitorModal() {
            document.getElementById('addCompetitorModal').style.display = 'flex';
            document.getElementById('competitorNameInput').focus();
            initCompetitorRatingStars();
            resetCompetitorModal();
        }

        function closeAddCompetitorModal() {
            document.getElementById('addCompetitorModal').style.display = 'none';
            resetCompetitorModal();
        }

        function resetCompetitorModal() {
            document.getElementById('competitorNameInput').value = '';
            document.getElementById('competitorAddressInput').value = '';
            document.getElementById('competitorPriceInput').value = '5000';
            document.getElementById('competitorRatingInput').value = '4.5';
            document.getElementById('competitorRatingValueDisplay').textContent = '4.5';
            document.getElementById('competitorSearchResults').innerHTML = '';
            document.getElementById('competitorSearchResults').style.display = 'none';
            document.getElementById('selectedCompetitorAddressPreview').style.display = 'none';
            selectedCompetitorAddress = null;

            // Обновляем звезды рейтинга
            updateCompetitorRatingStars(4.5);
        }

        function initCompetitorRatingStars() {
            const ratingStars = document.getElementById('competitorRatingStars');
            if (!ratingStars) return;

            ratingStars.innerHTML = '';
            for (let i = 0; i < 5; i++) {
                const star = document.createElement('i');
                star.className = 'bi bi-star-fill star-icon';
                ratingStars.appendChild(star);
            }

            // Обработчик изменения ползунка рейтинга
            document.getElementById('competitorRatingInput').addEventListener('input', function(e) {
                const rating = parseFloat(e.target.value);
                document.getElementById('competitorRatingValueDisplay').textContent = rating.toFixed(1);
                updateCompetitorRatingStars(rating);
            });
        }

        function updateCompetitorRatingStars(rating) {
            const stars = document.querySelectorAll('#competitorRatingStars .star-icon');
            if (!stars.length) return;

            stars.forEach((star, index) => {
                if (index < Math.floor(rating)) {
                    star.className = 'bi bi-star-fill star-icon';
                } else if (index < rating) {
                    star.className = 'bi bi-star-half star-icon';
                } else {
                    star.className = 'bi bi-star star-icon';
                }
            });
        }

        async function searchCompetitorAddress(event = null) {
            const query = document.getElementById('competitorAddressInput').value.trim();

            if (!query || query.length < 2) {
                document.getElementById('competitorSearchResults').style.display = 'none';
                return;
            }

            // Если нажата Enter - сразу ищем
            if (event && event.key === 'Enter') {
                await performCompetitorGeocode(query);
                return;
            }

            try {
                const response = await fetch('/api/search-address', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query })
                });

                const data = await response.json();
                const resultsDiv = document.getElementById('competitorSearchResults');
                resultsDiv.innerHTML = '';

                if (data.suggestions && data.suggestions.length > 0) {
                    data.suggestions.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'search-result-item';
                        div.textContent = item.address;
                        div.onclick = () => selectCompetitorAddressFromList(item.address);
                        resultsDiv.appendChild(div);
                    });
                    resultsDiv.style.display = 'block';
                } else {
                    showCompetitorLocalExamples(query, resultsDiv);
                }
            } catch (error) {
                console.error('Ошибка поиска адреса:', error);
                const resultsDiv = document.getElementById('competitorSearchResults');
                showCompetitorLocalExamples(query, resultsDiv);
            }
        }

        function showCompetitorLocalExamples(query, resultsDiv) {
            const examples = [
                "Москва, Красная площадь, 1",
                "Москва, Тверская улица, 10",
                "Москва, Арбат, 25",
                "Москва, Ленинский проспект, 90",
                "Москва, Пресненская набережная, 12",
                "Санкт-Петербург, Невский проспект, 1",
                "Екатеринбург, улица Ленина, 1"
            ];

            const results = examples.filter(addr => 
                addr.toLowerCase().includes(query.toLowerCase())
            );

            resultsDiv.innerHTML = '';

            if (results.length > 0) {
                results.forEach(addr => {
                    const div = document.createElement('div');
                    div.className = 'search-result-item';
                    div.textContent = addr;
                    div.onclick = () => selectCompetitorAddressFromList(addr);
                    resultsDiv.appendChild(div);
                });
                resultsDiv.style.display = 'block';
            } else {
                resultsDiv.style.display = 'none';
            }
        }

        async function performCompetitorGeocode(query) {
            try {
                const response = await fetch('/api/geocode', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ address: query })
                });

                const result = await response.json();

                if (result.success) {
                    selectCompetitorAddressFromResult(result);
                } else {
                    alert('Адрес не найден: ' + (result.error || 'Неизвестная ошибка'));
                }
            } catch (error) {
                console.error('Ошибка геокодирования:', error);
                alert('Ошибка при поиске адреса. Проверьте подключение к интернету.');
            }
        }

        function selectCompetitorAddressFromList(address) {
            performCompetitorGeocode(address);
        }

        function selectCompetitorAddressFromResult(result) {
            selectedCompetitorAddress = result;

            document.getElementById('selectedCompetitorAddressText').textContent = result.address;
            document.getElementById('selectedCompetitorCoordinates').textContent = `Координаты: ${result.coordinates}`;
            document.getElementById('selectedCompetitorAddressPreview').style.display = 'block';
            document.getElementById('competitorSearchResults').style.display = 'none';
        }

        // Обработчик формы добавления конкурента
        document.getElementById('addCompetitorForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            await addNewCompetitor();
        });

        async function addNewCompetitor() {
            const name = document.getElementById('competitorNameInput').value.trim();
            const addressInput = document.getElementById('competitorAddressInput').value.trim();
            const price = parseFloat(document.getElementById('competitorPriceInput').value);
            const rating = parseFloat(document.getElementById('competitorRatingInput').value);

            // Валидация
            if (!name) {
                alert('Пожалуйста, введите название отеля');
                return;
            }

            if (!addressInput && !selectedCompetitorAddress) {
                alert('Пожалуйста, введите адрес или выберите из списка');
                return;
            }

            const address = selectedCompetitorAddress ? selectedCompetitorAddress.address : addressInput;

            if (isNaN(price) || price < 1000 || price > 50000) {
                alert('Цена должна быть в диапазоне 1000 - 50000 ₽');
                return;
            }

            if (isNaN(rating) || rating < 1 || rating > 5) {
                alert('Рейтинг должен быть в диапазоне 1.0 - 5.0');
                return;
            }

            try {
                const response = await fetch('/api/competitors/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: name,
                        address: address,
                        price: price,
                        rating: rating
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Добавляем нового конкурента в локальные данные
                    allCompetitorsData.push(result.competitor);

                    // Применяем фильтры (новый конкурент появится на карте и в списке)
                    applyFilters();

                    alert('Конкурент успешно добавлен!');
                    closeAddCompetitorModal();

                } else {
                    alert('Ошибка при добавлении конкурента: ' + result.message);
                }
            } catch (error) {
                console.error('Ошибка добавления конкурента:', error);
                alert('Ошибка при добавлении конкурента');
            }
        }

        // Функция удаления конкурента
        async function deleteCompetitor(competitorId) {
            if (!confirm('Вы уверены, что хотите удалить этого конкурента?')) {
                return;
            }

            try {
                const response = await fetch('/api/competitors/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        competitor_id: competitorId
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Удаляем конкурента из локальных данных
                    allCompetitorsData = allCompetitorsData.filter(hotel => hotel.id !== competitorId);

                    // Удаляем из выбранных, если был выбран
                    if (selectedHotels.has(competitorId)) {
                        selectedHotels.delete(competitorId);
                        updateSelectedList();
                    }

                    // Применяем фильтры (конкурент исчезнет с карты и из списка)
                    applyFilters();

                    alert('Конкурент успешно удален!');

                } else {
                    alert('Ошибка при удалении конкурента: ' + result.message);
                }
            } catch (error) {
                console.error('Ошибка удаления конкурента:', error);
                alert('Ошибка при удалении конкурента');
            }
        }

        // ===== ОСТАЛЬНЫЕ ФУНКЦИИ =====

        // Показать вкладку
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });

            // Используем event из параметра функции
            const clickedElement = window.event ? window.event.target : arguments[0] ? arguments[0].target : null;
            if (clickedElement) {
                clickedElement.classList.add('active');
            }

            document.getElementById(tabName + 'Tab').style.display = 'block';

            if (tabName === 'competitors') {
                setTimeout(initMap, 100);
            } else if (tabName === 'overview') {
                // Если график еще не создан, создаем его
                if (!priceChart) {
                    setTimeout(createPriceChart, 100);
                }
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

                ourHotelData = data.our_hotel;
                allCompetitorsData = data.competitors;
                ourHotelPrice = ourHotelData.price;

                // Очищаем все маркеры
                if (map) {
                    Object.keys(markers).forEach(key => {
                        map.removeLayer(markers[key]);
                    });
                }
                markers = {};

                // Добавляем наш отель
                addOurHotel(ourHotelData);

                // Применяем фильтры для конкурентов
                applyFilters();

                // Инициализируем состояние кнопок после загрузки
                setTimeout(() => {
                    allCompetitorsData.forEach(hotel => {
                        const isSelected = selectedHotels.has(hotel.id);
                        if (isSelected) {
                            updateHotelSelectionUI(hotel.id, true);
                        }
                    });
                }, 100);
        
            } catch (error) {
                console.error('Ошибка загрузки данных карты:', error);
            }
        }

        // Функция применения фильтров
        function applyFilters() {
            if (!map || !allCompetitorsData.length) return;

            // Получаем значения фильтров
            const maxPrice = parseInt(document.getElementById('priceFilter').value);
            const minRating = parseFloat(document.getElementById('ratingFilter').value);
            const maxDistance = parseFloat(document.getElementById('distanceFilter').value);

            // Фильтруем отели (кроме нашего отеля)
            const filteredCompetitors = allCompetitorsData.filter(hotel => {
                // Фильтр по цене
                if (hotel.price > maxPrice) return false;

                // Фильтр по рейтингу
                if (minRating > 0 && hotel.rating < minRating) return false;

                // Фильтр по расстоянию (извлекаем числовое значение)
                const distanceStr = hotel.distance;
                let distanceNum = 0;

                if (distanceStr.includes('км')) {
                    distanceNum = parseFloat(distanceStr);
                } else if (distanceStr.includes('м')) {
                    distanceNum = parseInt(distanceStr) / 1000;
                }

                if (maxDistance < 5 && distanceNum > maxDistance) return false;

                return true;
            });

            // Очищаем только маркеры конкурентов (не трогаем наш отель)
            Object.keys(markers).forEach(key => {
                if (key !== 'our_hotel' && markers[key]) {
                    map.removeLayer(markers[key]);
                }
            });
        
            // Удаляем только маркеры конкурентов из объекта markers
            Object.keys(markers).forEach(key => {
                if (key !== 'our_hotel') {
                    delete markers[key];
                }
            });
        
            // Очищаем выбранные отели конкурентов, которые не прошли фильтрацию
            selectedHotels.forEach(hotelId => {
                if (hotelId !== 'our_hotel' && !filteredCompetitors.some(hotel => hotel.id === hotelId)) {
                    selectedHotels.delete(hotelId);
                }
            });

            // Обновляем список выбранных
            updateSelectedList();

            // Добавляем отфильтрованных конкурентов
            filteredCompetitors.forEach(hotel => {
                // ПЕРЕСОЗДАЕМ маркер с актуальным состоянием выбора
                addCompetitorMarker(hotel);
            });

            // Обновляем список всех отелей (включая наш отель)
            renderHotelsList([ourHotelData, ...filteredCompetitors]);

            // Обновляем статистику (только по конкурентам)
            updateStats(filteredCompetitors);

            // Возвращаем отфильтрованные данные
            return filteredCompetitors;
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
                        cursor: pointer;
                    " onclick="showHotelInfo('${hotel.id}', event)">
                        <i class="bi bi-house-door"></i>
                    </div>
                `,
                iconSize: [40, 40]
            });

            const marker = L.marker([hotel.lat, hotel.lng], { icon: icon })
                .addTo(map)
                .on('click', function() {
                    showHotelInfoModal(hotel);
                })
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <h6><b>${hotel.name}</b></h6>
                        <p><i class="bi bi-geo-alt"></i> ${hotel.address}</p>
                        <p><i class="bi bi-cash"></i> <b>${hotel.price.toLocaleString('ru-RU')} ₽</b></p>
                        <p><i class="bi bi-star"></i> ${hotel.rating} ★</p>
                        <button class="btn btn-sm btn-outline-primary w-100 mt-2" onclick="showHotelInfoModalFromPopup('${hotel.id}')">
                            <i class="bi bi-info-circle"></i> Подробная информация
                        </button>
                    </div>
                `);

            markers[hotel.id] = marker;
        }

        // Добавить маркер конкурента
        function addCompetitorMarker(hotel) {
            if (!ourHotelData) {
                console.warn('ourHotelData не инициализирована в addCompetitorMarker');
                return;
            }
            
            const priceDiff = hotel.price - ourHotelData.price;
            let priceClass = '';
            let priceText = '';
            let markerColor = '';

            // Определяем цвет маркера и текст разницы цен
            if (priceDiff > 500) {
                priceClass = 'price-higher';
                priceText = `+${priceDiff} ₽`;
                markerColor = '#ef476f'; // Красный для дороже
            } else if (priceDiff < -500) {
                priceClass = 'price-lower';
                priceText = `${priceDiff} ₽`;
                markerColor = '#06d6a0'; // Зеленый для дешевле
            } else {
                priceClass = 'price-same';
                priceText = '≈';
                markerColor = '#ffd166'; // Желтый для примерно одинаково
            }

            // Проверяем, выбран ли отель
            const isSelected = selectedHotels.has(hotel.id);

            const icon = L.divIcon({
                className: 'custom-icon',
                html: `
                    <div style="
                        background-color: ${markerColor};
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
                        ${isSelected ? 'border-color: #4361ee; border-width: 3px;' : ''}
                    " onclick="showHotelInfo('${hotel.id}', event)">
                        <i class="bi bi-building"></i>
                    </div>
                `,
                iconSize: [35, 35]
            });

            // Используем функцию createPopupContent для создания содержимого попапа
            const popupContent = createPopupContent(hotel, isSelected);
            
            const marker = L.marker([hotel.lat, hotel.lng], { icon: icon })
                .addTo(map)
                .on('click', function() {
                    showHotelInfoModal(hotel);
                })
                .bindPopup(popupContent);
            
            markers[hotel.id] = marker;
        }
        
        // Функция создания содержимого попапа
        function createPopupContent(hotel, isSelected) {
            if (!ourHotelData) return '';
            
            const priceDiff = hotel.price - ourHotelData.price;
            let priceClass = '';
            let priceText = '';
            
            if (priceDiff > 500) {
                priceClass = 'price-higher';
                priceText = `+${priceDiff} ₽`;
            } else if (priceDiff < -500) {
                priceClass = 'price-lower';
                priceText = `${priceDiff} ₽`;
            } else {
                priceClass = 'price-same';
                priceText = '≈';
            }
            
            return `
                <div style="min-width: 200px;">
                    <h6><b>${hotel.name}</b></h6>
                    <p><i class="bi bi-geo-alt"></i> ${hotel.address}</p>
                    <p><i class="bi bi-signpost"></i> ${hotel.distance} от нас</p>
                    <p><i class="bi bi-cash"></i> <b>${hotel.price.toLocaleString('ru-RU')} ₽</b></p>
                    <p><i class="bi bi-star"></i> ${hotel.rating} ★</p>
                    <p>Разница: <span class="badge ${priceClass}">${priceText}</span></p>
                    <div class="d-flex gap-2 mt-2">
                        <button class="btn btn-sm ${isSelected ? 'btn-outline-primary' : 'btn-primary'} w-50" 
                                onclick="selectHotel('${hotel.id}', event)">
                            <i class="bi ${isSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> 
                            ${isSelected ? 'Убрать' : 'Выбрать'}
                        </button>
                        <button class="btn btn-sm btn-outline-info w-50" 
                                onclick="showHotelInfoModalFromPopup('${hotel.id}')">
                            <i class="bi bi-info-circle"></i> Подробнее
                        </button>
                    </div>
                </div>
            `;
        }

        // Выбрать/убрать отель
        function selectHotel(hotelId, event = null) {
            if (event) event.stopPropagation();

            const isOurHotel = hotelId === 'our_hotel';
            if (isOurHotel) {
                alert('Это наш отель. Вы не можете выбрать его для анализа.');
                return;
            }

            const wasSelected = selectedHotels.has(hotelId);
            
            if (wasSelected) {
                // Убираем из выбранных
                selectedHotels.delete(hotelId);
            } else {
                // Добавляем в выбранные
                selectedHotels.add(hotelId);
            }

            // Сохраняем состояние открытого попапа
            const marker = markers[hotelId];
            const wasPopupOpen = marker && marker._popup && marker._popup.isOpen();

            // Обновляем UI для всех мест, где отображается этот отель
            updateHotelSelectionUI(hotelId, !wasSelected);

            // Обновляем список выбранных
            updateSelectedList();
            
            // ОБНОВЛЯЕМ ВСЕГДА содержимое попапа, даже если он не открыт
            if (marker) {
                updateMapPopupContent(hotelId);
                
                // Если попап был открыт, открываем его заново с обновленным содержимым
                if (wasPopupOpen) {
                    setTimeout(() => {
                        if (marker._popup) {
                            marker.openPopup();
                        }
                    }, 50);
                }
            }
        }
        
        // Обновить UI выбора отеля во всех местах
        function updateHotelSelectionUI(hotelId, isNowSelected) {
            // 1. Обновляем карточку в списке
            const hotelCard = document.getElementById(`hotel-${hotelId}`);
            if (hotelCard) {
                hotelCard.classList.toggle('selected', isNowSelected);
                
                // Обновляем кнопку в карточке
                const cardButton = hotelCard.querySelector('.btn-outline-success, .btn-outline-primary');
                if (cardButton) {
                    cardButton.innerHTML = `<i class="bi ${isNowSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> ${isNowSelected ? 'Убрать' : 'Выбрать'}`;
                    cardButton.classList.toggle('btn-outline-primary', isNowSelected);
                    cardButton.classList.toggle('btn-outline-success', !isNowSelected);
                }
            }
        
            // 2. Обновляем маркер на карте
            const marker = markers[hotelId];
            if (marker) {
                // Обновляем иконку маркера
                const iconDiv = marker.getElement()?.querySelector('div');
                if (iconDiv) {
                    if (isNowSelected) {
                        iconDiv.style.borderColor = '#4361ee';
                        iconDiv.style.borderWidth = '3px';
                        iconDiv.style.boxShadow = '0 0 0 3px rgba(67, 97, 238, 0.3)';
                    } else {
                        iconDiv.style.borderColor = 'white';
                        iconDiv.style.borderWidth = '2px';
                        iconDiv.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
                    }
                }
                
                // ОБНОВЛЯЕМ ВСЕГДА содержимое попапа (даже если он не открыт)
                updateMapPopupContent(hotelId);
            }
        
            // 3. Обновляем модальное окно с деталями если оно открыто
            const detailModal = document.getElementById('hotelDetailModal');
            if (detailModal && detailModal.style.display === 'flex') {
                // Находим кнопку в модальном окне
                const modalButton = detailModal.querySelector('.btn-primary, .btn-outline-primary');
                if (modalButton && (modalButton.textContent.includes('анализ') || modalButton.textContent.includes('Добавить') || modalButton.textContent.includes('Убрать'))) {
                    modalButton.innerHTML = `<i class="bi ${isNowSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> ${isNowSelected ? 'Убрать из анализа' : 'Добавить в анализ'}`;
                    modalButton.classList.toggle('btn-primary', !isNowSelected);
                    modalButton.classList.toggle('btn-outline-primary', isNowSelected);
                }
            }
        
            // 4. Обновляем модальное окно сравнения если оно открыто
            const comparisonModal = document.getElementById('comparisonModal');
            if (comparisonModal && comparisonModal.style.display === 'flex') {
                const compButton = comparisonModal.querySelector('.btn-primary, .btn-outline-primary');
                if (compButton && (compButton.textContent.includes('анализ') || compButton.textContent.includes('Добавить') || compButton.textContent.includes('Убрать'))) {
                    compButton.innerHTML = `<i class="bi ${isNowSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> ${isNowSelected ? 'Убрать из анализа' : 'Добавить в анализ'}`;
                    compButton.classList.toggle('btn-primary', !isNowSelected);
                    compButton.classList.toggle('btn-outline-primary', isNowSelected);
                }
            }
        }
        
        // Обновить содержимое попапа на карте
        function updateMapPopupContent(hotelId) {
            const marker = markers[hotelId];
            if (!marker) return;
            
            const hotel = allCompetitorsData.find(h => h.id === hotelId);
            if (!hotel || !ourHotelData) return;
            
            const isSelected = selectedHotels.has(hotelId);
            
            // Используем общую функцию для создания содержимого
            const popupContent = createPopupContent(hotel, isSelected);
            
            // Обновляем содержимое попапа
            marker.bindPopup(popupContent);
        }
        
        // Функция для обновления текста кнопки в карточке отеля
        function updateSelectButton(hotelCard, isSelected) {
            const button = hotelCard.querySelector('.btn-outline-success, .btn-outline-primary');
            if (button) {
                button.innerHTML = `<i class="bi ${isSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> ${isSelected ? 'Убрать' : 'Выбрать'}`;
                button.classList.toggle('btn-outline-primary', isSelected);
                button.classList.toggle('btn-outline-success', !isSelected);
            }
        }
        
        // Функция для обновления текста кнопки в попапе на карте
        function updateMapPopupButton(hotelId, isSelected) {
            // Обновляем все открытые попапы с этим отелем
            const popup = markers[hotelId]?._popup;
            if (popup && popup.isOpen()) {
                // Закрываем и открываем заново с обновленным содержимым
                markers[hotelId].closePopup();
                
                // Создаем новое содержимое попапа
                const hotel = allCompetitorsData.find(h => h.id === hotelId);
                if (!hotel || !ourHotelData) return;
                
                const priceDiff = hotel.price - ourHotelData.price;
                let priceClass = '';
                let priceText = '';
        
                if (priceDiff > 500) {
                    priceClass = 'price-higher';
                    priceText = `+${priceDiff} ₽`;
                } else if (priceDiff < -500) {
                    priceClass = 'price-lower';
                    priceText = `${priceDiff} ₽`;
                } else {
                    priceClass = 'price-same';
                    priceText = '≈';
                }
        
                const popupContent = `
                    <div style="min-width: 200px;">
                        <h6><b>${hotel.name}</b></h6>
                        <p><i class="bi bi-geo-alt"></i> ${hotel.address}</p>
                        <p><i class="bi bi-signpost"></i> ${hotel.distance} от нас</p>
                        <p><i class="bi bi-cash"></i> <b>${hotel.price.toLocaleString('ru-RU')} ₽</b></p>
                        <p><i class="bi bi-star"></i> ${hotel.rating} ★</p>
                        <p>Разница: <span class="badge ${priceClass}">${priceText}</span></p>
                        <div class="d-flex gap-2 mt-2">
                            <button class="btn btn-sm ${isSelected ? 'btn-outline-primary' : 'btn-primary'} w-50" 
                                    onclick="selectHotel('${hotelId}', event)">
                                <i class="bi ${isSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> 
                                ${isSelected ? 'Убрать' : 'Выбрать'}
                            </button>
                            <button class="btn btn-sm btn-outline-info w-50" 
                                    onclick="showHotelInfoModalFromPopup('${hotelId}')">
                                <i class="bi bi-info-circle"></i> Подробнее
                            </button>
                        </div>
                    </div>
                `;
                
                markers[hotelId].bindPopup(popupContent).openPopup();
            }
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
                const hotel = allCompetitorsData.find(h => h.id === hotelId);
                if (!hotel) return;

                const item = document.createElement('div');
                item.className = 'selected-item';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${hotel.name}</h6>
                            <small class="text-muted">${hotel.price.toLocaleString('ru-RU')} ₽</small>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary me-2" onclick="focusOnMap('${hotelId}', event)">
                                <i class="bi bi-map"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="selectHotel('${hotelId}', event)">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    </div>
                `;
                list.appendChild(item);
            });
        }

        // Анализировать выбранные отели (обновленная функция)
        async function analyzeSelected() {
            if (selectedHotels.size === 0) return;

            try {
                // Показываем индикатор загрузки
                const analyzeBtn = document.getElementById('analyzeBtn');
                const originalText = analyzeBtn.innerHTML;
                analyzeBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Анализ...';
                analyzeBtn.disabled = true;
        
                // Собираем данные о выбранных отелях
                const selectedData = [];
                let totalPrice = 0;
                let totalRating = 0;
                let selectedCount = 0;
        
                selectedHotels.forEach(hotelId => {
                    const hotel = allCompetitorsData.find(h => h.id === hotelId);
                    if (hotel) {
                        selectedData.push(hotel);
                        totalPrice += hotel.price;
                        totalRating += hotel.rating;
                        selectedCount++;
                    }
                });
        
                // Если отели найдены, анализируем
                if (selectedCount > 0) {
                    const avgPrice = Math.round(totalPrice / selectedCount);
                    const avgRating = (totalRating / selectedCount).toFixed(1);
                    
                    // Сравниваем с нашим отелем
                    if (!ourHotelData) {
                        await loadCurrentHotelInfo();
                    }
        
                    const ourPrice = ourHotelData.price;
                    const ourRating = ourHotelData.rating;
                    const priceDiff = ourPrice - avgPrice;
                    const ratingDiff = ourRating - avgRating;
        
                    // Определяем рекомендацию
                    let recommendation = '';
                    let recommendationType = 'info';
        
                    if (priceDiff > 500) {
                        if (ratingDiff > 0.3) {
                            recommendation = 'Ваш отель значительно дороже, но имеет более высокий рейтинг. Рассмотрите пакетные предложения или дополнительные услуги для обоснования цены.';
                        } else {
                            recommendation = 'Ваш отель значительно дороже конкурентов. Рекомендуется снизить цену на 5-15% или улучшить сервис.';
                            recommendationType = 'danger';
                        }
                    } else if (priceDiff < -500) {
                        if (ratingDiff > 0) {
                            recommendation = 'Ваш отель дешевле конкурентов, но имеет более высокий рейтинг. Вы можете повысить цену на 5-10% без потери клиентов.';
                            recommendationType = 'success';
                        } else {
                            recommendation = 'Ваш отель дешевле конкурентов. Вы можете постепенно повышать цену, добавив дополнительные услуги.';
                        }
                    } else {
                        if (ratingDiff > 0.3) {
                            recommendation = 'Цены сопоставимы, но ваш рейтинг выше. Используйте это в маркетинге и рассмотрите повышение цены на 3-5%.';
                            recommendationType = 'success';
                        } else if (ratingDiff < -0.3) {
                            recommendation = 'Цены сопоставимы, но рейтинг конкурентов выше. Проанализируйте отзывы гостей и улучшите сервис.';
                            recommendationType = 'warning';
                        } else {
                            recommendation = 'Ваша ценовая позиция оптимальна. Поддерживайте текущую стратегию.';
                        }
                    }
        
                    // Показываем результаты анализа
                    showAnalysisResults({
                        selectedCount: selectedCount,
                        avgPrice: avgPrice,
                        avgRating: avgRating,
                        ourPrice: ourPrice,
                        ourRating: ourRating,
                        priceDiff: priceDiff,
                        ratingDiff: ratingDiff,
                        recommendation: recommendation,
                        recommendationType: recommendationType,
                        selectedHotels: selectedData
                    });
        
                } else {
                    alert('Не удалось найти данные выбранных отелей');
                }
        
                // Восстанавливаем кнопку
                analyzeBtn.innerHTML = originalText;
                analyzeBtn.disabled = false;
        
            } catch (error) {
                console.error('Ошибка анализа:', error);
                alert('Произошла ошибка при анализе выбранных отелей');
                
                // Восстанавливаем кнопку
                const analyzeBtn = document.getElementById('analyzeBtn');
                analyzeBtn.innerHTML = '<i class="bi bi-graph-up"></i> Анализировать выбранные';
                analyzeBtn.disabled = false;
            }
        }
        
        // Функция для отображения результатов анализа
        function showAnalysisResults(data) {
            const modalHtml = `
                <div id="analysisResultsModal" class="modal-overlay" style="display: flex;">
                    <div class="modal-content" style="max-width: 900px;">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4><i class="bi bi-graph-up-arrow"></i> Результаты анализа</h4>
                            <button class="btn btn-sm btn-outline-secondary" onclick="closeAnalysisResultsModal()">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
        
                        <div class="row mb-4">
                            <div class="col-md-3">
                                <div class="card text-center">
                                    <div class="card-body">
                                        <h6 class="card-title">Анализируемых отелей</h6>
                                        <div class="metric-value">${data.selectedCount}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card text-center">
                                    <div class="card-body">
                                        <h6 class="card-title">Средняя цена</h6>
                                        <div class="metric-value">${data.avgPrice.toLocaleString('ru-RU')} ₽</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card text-center">
                                    <div class="card-body">
                                        <h6 class="card-title">Средний рейтинг</h6>
                                        <div class="metric-value">${data.avgRating}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card text-center">
                                    <div class="card-body">
                                        <h6 class="card-title">Разница в цене</h6>
                                        <div class="metric-value ${data.priceDiff > 0 ? 'text-success' : data.priceDiff < 0 ? 'text-danger' : 'text-warning'}">
                                            ${data.priceDiff > 0 ? '+' : ''}${data.priceDiff} ₽
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h5 class="card-title">Наш отель</h5>
                                        <div class="d-flex justify-content-between mb-2">
                                            <span>Цена:</span>
                                            <strong>${data.ourPrice.toLocaleString('ru-RU')} ₽</strong>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <span>Рейтинг:</span>
                                            <strong>${data.ourRating} ★</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h5 class="card-title">Конкуренты (среднее)</h5>
                                        <div class="d-flex justify-content-between mb-2">
                                            <span>Цена:</span>
                                            <strong>${data.avgPrice.toLocaleString('ru-RU')} ₽</strong>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <span>Рейтинг:</span>
                                            <strong>${data.avgRating} ★</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
        
                        <div class="card mt-4">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="bi bi-lightbulb"></i> Рекомендация
                                    <span class="badge bg-${data.recommendationType} float-end">
                                        ${getRecommendationLevel(data.priceDiff, data.ratingDiff)}
                                    </span>
                                </h5>
                                <p>${data.recommendation}</p>
                                
                                <div class="mt-3">
                                    <h6>Конкретные действия:</h6>
                                    <ul>
                                        ${getActionItems(data.priceDiff, data.ratingDiff)}
                                    </ul>
                                </div>
                            </div>
                        </div>
        
                        <div class="card mt-4">
                            <div class="card-body">
                                <h5 class="card-title"><i class="bi bi-list-ol"></i> Проанализированные отели</h5>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Отель</th>
                                                <th>Цена</th>
                                                <th>Рейтинг</th>
                                                <th>Расстояние</th>
                                                <th>Разница с нами</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${data.selectedHotels.map(hotel => {
                                                const priceDiff = hotel.price - data.ourPrice;
                                                const ratingDiff = hotel.rating - data.ourRating;
                                                return `
                                                    <tr>
                                                        <td>${hotel.name}</td>
                                                        <td>${hotel.price.toLocaleString('ru-RU')} ₽</td>
                                                        <td>${hotel.rating} ★</td>
                                                        <td>${hotel.distance}</td>
                                                        <td>
                                                            <span class="badge ${priceDiff > 500 ? 'bg-danger' : priceDiff < -500 ? 'bg-success' : 'bg-warning'}">
                                                                ${priceDiff > 0 ? '+' : ''}${priceDiff} ₽
                                                            </span>
                                                            <span class="badge ${ratingDiff > 0.3 ? 'bg-danger' : ratingDiff < -0.3 ? 'bg-success' : 'bg-warning'} ms-1">
                                                                ${ratingDiff > 0 ? '+' : ''}${ratingDiff.toFixed(1)}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                `;
                                            }).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
        
                        <div class="mt-4">
                            <!-- ИЗМЕНЯЕМ ЭТУ КНОПКУ: добавляем вызов функции closeAnalysisResultsModal() -->
                            <button class="btn btn-primary w-100" onclick="closeAnalysisResultsModalAndGoToPricing()">
                                <i class="bi bi-calculator"></i> Перейти к расчету цены
                            </button>
                        </div>
                    </div>
                </div>
            `;
        
            // Закрываем другие модальные окна
            closeAllModals();
        
            // Добавляем модальное окно на страницу
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHtml;
            document.body.appendChild(modalContainer);
        
            // Сохраняем данные анализа для использования после закрытия
            window.analysisData = data;
        
            // Добавляем обработчик закрытия
            const modalElement = document.getElementById('analysisResultsModal');
            if (modalElement) {
                modalElement.addEventListener('click', function(e) {
                    if (e.target === this) {
                        closeAnalysisResultsModal();
                    }
                });
            }
        }
        
        // Добавляем новую функцию для закрытия модального окна и перехода к ценообразованию
        function closeAnalysisResultsModalAndGoToPricing() {
            // Закрываем модальное окно
            closeAnalysisResultsModal();
            
            // Переходим на вкладку ценообразования
            showTab('pricing');
            
            // Автоматически заполняем поля данными из анализа
            setTimeout(() => {
                // Заполняем базовую цену средней ценой конкурентов
                const basePriceInput = document.getElementById('basePrice');
                if (basePriceInput && window.analysisData) {
                    basePriceInput.value = window.analysisData.avgPrice;
                }
                
            }, 300);
        }
        
        // Существующая функция остается без изменений
        function closeAnalysisResultsModal() {
            const modal = document.getElementById('analysisResultsModal');
            if (modal) {
                modal.remove();
            }
            // Очищаем данные анализа
            window.analysisData = null;
        }
        
        // Вспомогательные функции для анализа
        function getRecommendationLevel(priceDiff, ratingDiff) {
            if (Math.abs(priceDiff) > 1000 || Math.abs(ratingDiff) > 0.5) {
                return 'Высокий приоритет';
            } else if (Math.abs(priceDiff) > 500 || Math.abs(ratingDiff) > 0.3) {
                return 'Средний приоритет';
            } else {
                return 'Низкий приоритет';
            }
        }
        
        function getActionItems(priceDiff, ratingDiff) {
            const actions = [];
            
            if (priceDiff > 500) {
                if (ratingDiff > 0.3) {
                    actions.push('Провести маркетинговую кампанию, подчеркивающую преимущества более высокого рейтинга');
                    actions.push('Предложить пакетные предложения (завтрак + трансфер)');
                    actions.push('Ввести программу лояльности для постоянных клиентов');
                } else {
                    actions.push('Снизить цену на 5-10% в течение следующей недели');
                    actions.push('Проанализировать отзывы конкурентов с высоким рейтингом');
                    actions.push('Предложить временные скидки на бронирование через сайт');
                }
            } else if (priceDiff < -500) {
                if (ratingDiff > 0) {
                    actions.push('Постепенно повысить цену на 3-5% каждые 2 недели');
                    actions.push('Усилить маркетинг, акцентируя внимание на качестве сервиса');
                    actions.push('Предложить премиум-номера по повышенной цене');
                } else {
                    actions.push('Проверить соответствие цены и качества услуг');
                    actions.push('Проанализировать структуру затрат');
                    actions.push('Рассмотреть возможность улучшения услуг без значительного роста цен');
                }
            } else {
                actions.push('Поддерживать текущий уровень цен');
                actions.push('Мониторить изменения у конкурентов еженедельно');
                actions.push('Улучшать качество сервиса для повышения рейтинга');
            }
            
            return actions.map(action => `<li>${action}</li>`).join('');
        }
        
        
        // Функция для закрытия всех модальных окон
        function closeAllModals() {
            const modals = document.querySelectorAll('.modal-overlay');
            modals.forEach(modal => {
                if (modal.id !== 'addressModal' && 
                    modal.id !== 'hotelInfoModal' && 
                    modal.id !== 'addCompetitorModal' &&
                    modal.id !== 'loadingModal') {
                    modal.remove();
                }
            });
        }
        
        // Обновляем функцию очистки выбранных, чтобы она закрывала модальное окно анализа
        function clearSelected() {
            // Закрываем окно результатов анализа, если оно открыто
            closeAnalysisResultsModal();
            
            // Сначала обновляем все кнопки
            selectedHotels.forEach(hotelId => {
                const hotelCard = document.getElementById(`hotel-${hotelId}`);
                if (hotelCard) {
                    hotelCard.classList.remove('selected');
                    updateHotelSelectionUI(hotelId, false);
                }
            });
            
            // Затем очищаем Set
            selectedHotels.clear();
            updateSelectedList();
        }

        // Обновить статистику
        function updateStats(competitors) {
            if (!ourHotelData) return;
            
            // Проверяем, есть ли конкуренты
            let avgPrice = 0;
            if (competitors.length > 0) {
                avgPrice = competitors.reduce((sum, hotel) => sum + hotel.price, 0) / competitors.length;
            }
            
            // Обновляем отображение средней цены
            const statsAvgPriceElement = document.getElementById('statsAvgPrice');
            if (statsAvgPriceElement) {
                if (competitors.length > 0) {
                    statsAvgPriceElement.textContent = Math.round(avgPrice).toLocaleString('ru-RU') + ' ₽';
                } else {
                    statsAvgPriceElement.textContent = '0 ₽';
                }
            }
            
            // Обновляем количество отелей
            const statsTotalElement = document.getElementById('statsTotal');
            if (statsTotalElement) {
                statsTotalElement.textContent = competitors.length;
            }
            
            // Обновляем статистику в модальном окне
            const avgCompetitorPriceElement = document.getElementById('avgCompetitorPrice');
            if (avgCompetitorPriceElement) {
                if (competitors.length > 0) {
                    avgCompetitorPriceElement.textContent = Math.round(avgPrice).toLocaleString('ru-RU') + ' ₽';
                } else {
                    avgCompetitorPriceElement.textContent = '0 ₽';
                }
            }
            
            // Рассчитываем позицию на рынке (только если есть конкуренты)
            if (competitors.length > 0) {
                const allHotels = [...competitors, ourHotelData];
                allHotels.sort((a, b) => a.price - b.price);
                const position = allHotels.findIndex(hotel => hotel.id === 'our_hotel') + 1;
                
                const marketPositionElement = document.getElementById('marketPositionStat');
                if (marketPositionElement) {
                    marketPositionElement.textContent = `#${position}`;
                }
            } else {
                const marketPositionElement = document.getElementById('marketPositionStat');
                if (marketPositionElement) {
                    marketPositionElement.textContent = '#1';
                }
            }
        }
        
        // Обновить все кнопки выбора
        function updateAllSelectButtons() {
            // Обновляем кнопки в списке отелей
            selectedHotels.forEach(hotelId => {
                const hotelCard = document.getElementById(`hotel-${hotelId}`);
                if (hotelCard) {
                    updateSelectButton(hotelCard, true);
                }
                // Обновляем попапы на карте
                updateMapPopupButton(hotelId, true);
            });
            
            // Для невыбранных отелей тоже обновляем (на всякий случай)
            allCompetitorsData.forEach(hotel => {
                if (!selectedHotels.has(hotel.id)) {
                    const hotelCard = document.getElementById(`hotel-${hotel.id}`);
                    if (hotelCard) {
                        updateSelectButton(hotelCard, false);
                    }
                }
            });
        }
        
        // Функция для перерисовки всех маркеров конкурентов
        function redrawAllCompetitorMarkers(competitors) {
            if (!map) {
                console.warn('Карта не инициализирована');
                return;
            }
            
            if (!ourHotelData) {
                console.warn('ourHotelData не инициализирована');
                return;
            }
            
            // Удаляем все маркеры конкурентов
            Object.keys(markers).forEach(key => {
                if (key !== 'our_hotel' && markers[key]) {
                    map.removeLayer(markers[key]);
                }
            });

            // Добавляем маркеры конкурентов с новыми цветами
            if (competitors && competitors.length > 0) {
                competitors.forEach(hotel => {
                    addCompetitorMarker(hotel);
                });
            }
        }

        // Показать список отелей
        function renderHotelsList(hotels) {
            const container = document.getElementById('hotelsList');
            if (!container) return;

            container.innerHTML = '';

            hotels.forEach(hotel => {
                // Для нашего отеля не считаем разницу цен
                const isOurHotel = hotel.id === 'our_hotel';
                let priceBadgeClass = '';
                let priceBadgeText = '';
                let priceDiff = 0;

                if (!isOurHotel) {
                    priceDiff = hotel.price - ourHotelData.price;

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
                } else {
                    // Для нашего отеля используем специальный класс
                    priceBadgeClass = 'price-our-hotel';
                }

                // Проверяем, выбран ли отель
                const isSelected = selectedHotels.has(hotel.id);

                // Создаем специальный CSS класс для нашего отеля
                const hotelCardClass = isOurHotel ? 'hotel-card our-hotel' : 'hotel-card';

                const col = document.createElement('div');
                col.className = 'col-md-4 mb-3';
                col.innerHTML = `
                    <div class="card ${hotelCardClass} ${isSelected ? 'selected' : ''}" id="hotel-${hotel.id}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="card-title mb-1">
                                        ${hotel.name}
                                        ${isOurHotel ? '<span class="badge bg-primary ms-2">Наш отель</span>' : ''}
                                    </h6>
                                    <div class="d-flex align-items-center mb-2">
                                        <span class="badge ${isOurHotel ? 'bg-primary' : 'bg-warning text-dark'} me-2">
                                            <i class="bi ${isOurHotel ? 'bi-house-door' : 'bi-star'}"></i> ${hotel.rating}
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
                                    ${!isOurHotel ? `<small class="text-muted d-block mt-1">${priceBadgeText}</small>` : ''}
                                </div>
                            </div>
                            <div class="mt-3">
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm ${isOurHotel ? 'btn-outline-primary' : 'btn-outline-secondary'} w-50" onclick="focusOnMap('${hotel.id}', event)">
                                        <i class="bi bi-map"></i> На карте
                                    </button>
                                    ${!isOurHotel ? `
                                    <button class="btn btn-sm btn-outline-danger w-50" onclick="deleteCompetitor('${hotel.id}', event)">
                                        <i class="bi bi-trash"></i> Удалить
                                    </button>
                                    ` : ''}
                                </div>
                                ${!isOurHotel ? `
                                <button class="btn btn-sm ${isSelected ? 'btn-outline-primary' : 'btn-outline-success'} w-100 mt-2" onclick="selectHotel('${hotel.id}', event)">
                                    <i class="bi ${isSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> ${isSelected ? 'Убрать' : 'Выбрать'}
                                </button>
                                ` : ''}
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
            if (map && ourHotelData) {
                map.setView([ourHotelData.lat, ourHotelData.lng], 14);
            }
        }

        // Фильтр цены
        const priceFilterElement = document.getElementById('priceFilter');
        if (priceFilterElement) {
            priceFilterElement.addEventListener('input', function(e) {
                const priceFilterValueElement = document.getElementById('priceFilterValue');
                if (priceFilterValueElement) {
                    priceFilterValueElement.textContent = 
                        parseInt(e.target.value).toLocaleString('ru-RU') + ' ₽';
                }
            });
        }

        // История отчетов
        let reportsHistory = [];
        
        // Инициализация истории отчетов при загрузке
        async function loadReportsHistory() {
            try {
                // Загружаем историю из localStorage или инициализируем пустую
                const savedHistory = localStorage.getItem('reportsHistory');
                if (savedHistory) {
                    reportsHistory = JSON.parse(savedHistory);
                } else {
                    // Создаем демо-отчеты
                    reportsHistory = [
                        {
                            id: '1',
                            type: 'Финансовый',
                            title: 'Отчет по выручке за июль',
                            date: '2024-07-15',
                            size: '2.4 MB',
                            status: 'Готов',
                            format: 'PDF'
                        },
                        {
                            id: '2',
                            type: 'Анализ цен',
                            title: 'Сравнительный анализ цен конкурентов',
                            date: '2024-07-10',
                            size: '1.8 MB',
                            status: 'Готов',
                            format: 'PDF'
                        },
                        {
                            id: '3',
                            type: 'Анализ конкурентов',
                            title: 'Итоги недели по конкурентам',
                            date: '2024-07-08',
                            size: '3.1 MB',
                            status: 'Готов',
                            format: 'Excel'
                        },
                        {
                            id: '4',
                            type: 'Финансовый',
                            title: 'Отчет по выручке за июнь',
                            date: '2024-06-30',
                            size: '2.2 MB',
                            status: 'Готов',
                            format: 'PDF'
                        },
                        {
                            id: '5',
                            type: 'Анализ цен',
                            title: 'Динамика цен за месяц',
                            date: '2024-06-25',
                            size: '1.5 MB',
                            status: 'Готов',
                            format: 'PDF'
                        }
                    ];
                    saveReportsHistory();
                }
                
                // Отображаем историю
                renderReportsHistory();
                
            } catch (error) {
                console.error('Ошибка загрузки истории отчетов:', error);
                // Инициализируем пустую историю
                reportsHistory = [];
                renderReportsHistory();
            }
        }
        
        // Сохранение истории в localStorage
        function saveReportsHistory() {
            try {
                localStorage.setItem('reportsHistory', JSON.stringify(reportsHistory));
            } catch (error) {
                console.error('Ошибка сохранения истории:', error);
            }
        }
        
        // Отображение истории отчетов
        function renderReportsHistory() {
            const reportsHistoryElement = document.getElementById('reportsHistory');
            if (!reportsHistoryElement) return;
            
            if (reportsHistory.length === 0) {
                reportsHistoryElement.innerHTML = `
                    <div class="text-center py-4">
                        <i class="bi bi-file-text fs-1 text-muted"></i>
                        <p class="mt-2">История отчетов пуста</p>
                    </div>
                `;
                return;
            }
            
            // Сортируем по дате (новые сверху)
            const sortedHistory = [...reportsHistory].sort((a, b) => new Date(b.date) - new Date(a.date));
            
            reportsHistoryElement.innerHTML = sortedHistory.map(report => `
                <div class="card mb-2">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="d-flex align-items-center mb-2">
                                    <span class="badge ${getReportTypeColor(report.type)} me-2">
                                        ${report.type}
                                    </span>
                                    <small class="text-muted">
                                        <i class="bi bi-calendar"></i> ${formatDate(report.date)}
                                    </small>
                                </div>
                                <h6 class="card-title mb-1">${report.title}</h6>
                                <div class="d-flex align-items-center gap-3">
                                    <small class="text-muted">
                                        <i class="bi bi-file-earmark"></i> ${report.format}
                                    </small>
                                    <small class="text-muted">
                                        <i class="bi bi-hdd"></i> ${report.size}
                                    </small>
                                    <span class="badge ${getStatusColor(report.status)}">
                                        ${report.status}
                                    </span>
                                </div>
                            </div>
                            <div class="d-flex flex-column gap-1">
                                <button class="btn btn-sm btn-outline-primary" onclick="downloadReport('${report.id}')">
                                    <i class="bi bi-download"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="viewReport('${report.id}')">
                                    <i class="bi bi-eye"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteReport('${report.id}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        // Вспомогательные функции для отчетов
        function getReportTypeColor(type) {
            const colors = {
                'Финансовый': 'bg-primary',
                'Анализ цен': 'bg-success',
                'Анализ конкурентов': 'bg-warning text-dark',
                'Общий': 'bg-info'
            };
            return colors[type] || 'bg-secondary';
        }
        
        function getStatusColor(status) {
            const colors = {
                'Готов': 'bg-success',
                'В процессе': 'bg-warning text-dark',
                'Ошибка': 'bg-danger',
                'Ожидание': 'bg-secondary'
            };
            return colors[status] || 'bg-secondary';
        }
        
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        }
        
        // Функции для работы с отчетами
        async function generateFinancialReport() {
            showReportLoading('Финансовый отчет');
            
            try {
                // Имитируем генерацию отчета
                await simulateReportGeneration();
                
                // Создаем новый отчет
                const newReport = {
                    id: generateReportId(),
                    type: 'Финансовый',
                    title: `Финансовый отчет ${getCurrentMonth()} ${new Date().getFullYear()}`,
                    date: new Date().toISOString().split('T')[0],
                    size: getRandomSize(2, 4) + ' MB',
                    status: 'Готов',
                    format: 'PDF'
                };
                
                // Добавляем в историю
                addReportToHistory(newReport);
                
                showReportSuccess('Финансовый отчет успешно создан!');
                
            } catch (error) {
                showReportError('Ошибка при создании финансового отчета');
                console.error('Ошибка генерации финансового отчета:', error);
            }
        }
        
        async function generatePricingReport() {
            showReportLoading('Анализ цен');
            
            try {
                // Имитируем генерацию отчета
                await simulateReportGeneration();
                
                // Создаем новый отчет
                const newReport = {
                    id: generateReportId(),
                    type: 'Анализ цен',
                    title: `Анализ цен конкурентов за ${getCurrentWeek()}`,
                    date: new Date().toISOString().split('T')[0],
                    size: getRandomSize(1, 3) + ' MB',
                    status: 'Готов',
                    format: 'PDF'
                };
                
                // Добавляем в историю
                addReportToHistory(newReport);
                
                showReportSuccess('Отчет по ценам успешно создан!');
                
            } catch (error) {
                showReportError('Ошибка при создании отчета по ценам');
                console.error('Ошибка генерации отчета по ценам:', error);
            }
        }
        
        async function generateCompetitorReport() {
            showReportLoading('Анализ конкурентов');
            
            try {
                // Имитируем генерацию отчета
                await simulateReportGeneration();
                
                // Создаем новый отчет
                const newReport = {
                    id: generateReportId(),
                    type: 'Анализ конкурентов',
                    title: `Анализ конкурентов ${getCurrentMonth()}`,
                    date: new Date().toISOString().split('T')[0],
                    size: getRandomSize(2, 5) + ' MB',
                    status: 'Готов',
                    format: 'Excel'
                };
                
                // Добавляем в историю
                addReportToHistory(newReport);
                
                showReportSuccess('Отчет по конкурентам успешно создан!');
                
            } catch (error) {
                showReportError('Ошибка при создании отчета по конкурентам');
                console.error('Ошибка генерации отчета по конкурентам:', error);
            }
        }
        
        // Вспомогательные функции для генерации отчетов
        function showReportLoading(reportType) {
            const loadingModal = document.getElementById('loadingModal');
            if (!loadingModal) {
                // Создаем модальное окно загрузки если его нет
                const modalHtml = `
                    <div id="loadingModal" class="modal-overlay" style="display: flex;">
                        <div class="modal-content text-center" style="max-width: 400px;">
                            <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;"></div>
                            <h5 class="mt-3">Создание отчета...</h5>
                            <p id="loadingReportType">${reportType}</p>
                            <div class="progress mt-3" style="height: 10px;">
                                <div id="loadingProgress" class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                `;
                
                const modalContainer = document.createElement('div');
                modalContainer.innerHTML = modalHtml;
                document.body.appendChild(modalContainer);
            } else {
                loadingModal.style.display = 'flex';
                document.getElementById('loadingReportType').textContent = reportType;
                document.getElementById('loadingProgress').style.width = '0%';
            }
            
            // Анимация прогресса
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 10;
                if (progress > 90) progress = 90;
                document.getElementById('loadingProgress').style.width = progress + '%';
            }, 200);
            
            window.reportProgressInterval = progressInterval;
        }
        
        function showReportSuccess(message) {
            clearInterval(window.reportProgressInterval);
            
            const loadingModal = document.getElementById('loadingModal');
            if (loadingModal) {
                document.getElementById('loadingProgress').style.width = '100%';
                
                setTimeout(() => {
                    loadingModal.style.display = 'none';
                    
                    // Показываем сообщение об успехе
                    const successAlert = `
                        <div id="reportSuccessAlert" class="alert alert-success alert-dismissible fade show" 
                             style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                            <i class="bi bi-check-circle"></i> ${message}
                            <button type="button" class="btn-close" onclick="document.getElementById('reportSuccessAlert').remove()"></button>
                        </div>
                    `;
                    
                    const alertContainer = document.createElement('div');
                    alertContainer.innerHTML = successAlert;
                    document.body.appendChild(alertContainer);
                    
                    // Автоматически скрываем через 5 секунд
                    setTimeout(() => {
                        const alertElement = document.getElementById('reportSuccessAlert');
                        if (alertElement) {
                            alertElement.remove();
                        }
                    }, 5000);
                    
                }, 500);
            }
        }

        function showReportError(message) {
            clearInterval(window.reportProgressInterval);
            
            const loadingModal = document.getElementById('loadingModal');
            if (loadingModal) {
                loadingModal.style.display = 'none';
                
                // Показываем сообщение об ошибке
                const errorAlert = `
                    <div id="reportErrorAlert" class="alert alert-danger alert-dismissible fade show" 
                         style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                        <i class="bi bi-exclamation-triangle"></i> ${message}
                        <button type="button" class="btn-close" onclick="document.getElementById('reportErrorAlert').remove()"></button>
                    </div>
                `;
                
                const alertContainer = document.createElement('div');
                alertContainer.innerHTML = errorAlert;
                document.body.appendChild(alertContainer);
                
                // Автоматически скрываем через 5 секунд
                setTimeout(() => {
                    const alertElement = document.getElementById('reportErrorAlert');
                    if (alertElement) {
                        alertElement.remove();
                    }
                }, 5000);
            }
        }

        async function simulateReportGeneration() {
            // Имитация задержки генерации отчета
            return new Promise(resolve => {
                setTimeout(() => {
                    resolve();
                }, 1500 + Math.random() * 1000);
            });
        }
        
        function generateReportId() {
            return 'report_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
        
        function getCurrentMonth() {
            const months = [
                'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
            ];
            return months[new Date().getMonth()];
        }
        
        function getCurrentWeek() {
            const today = new Date();
            const firstDayOfWeek = new Date(today.setDate(today.getDate() - today.getDay() + 1));
            const lastDayOfWeek = new Date(today.setDate(today.getDate() - today.getDay() + 7));
            
            const formatDate = (date) => {
                return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
            };
            
            return `${formatDate(firstDayOfWeek)} - ${formatDate(lastDayOfWeek)}`;
        }
        
        function getRandomSize(min, max) {
            return (min + Math.random() * (max - min)).toFixed(1);
        }
        
        function addReportToHistory(report) {
            // Добавляем отчет в начало истории
            reportsHistory.unshift(report);
            
            // Сохраняем в localStorage
            saveReportsHistory();
            
            // Обновляем отображение
            renderReportsHistory();
        }
        
        // Функции для управления отчетами
        function downloadReport(reportId) {
            const report = reportsHistory.find(r => r.id === reportId);
            if (!report) return;
            
            showReportLoading(`Скачивание: ${report.title}`);
            
            setTimeout(() => {
                showReportSuccess(`Отчет "${report.title}" скачан`);
                
                // Имитация скачивания
                const link = document.createElement('a');
                link.href = '#'; // В реальном приложении здесь будет ссылка на файл
                link.download = `${report.title}.${report.format.toLowerCase()}`;
                link.click();
            }, 1000);
        }
        
        function viewReport(reportId) {
            const report = reportsHistory.find(r => r.id === reportId);
            if (!report) return;
            
            // Показываем модальное окно с предпросмотром отчета
            const previewModal = `
                <div id="reportPreviewModal" class="modal-overlay" style="display: flex;">
                    <div class="modal-content" style="max-width: 800px; max-height: 90vh;">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4>
                                <i class="bi bi-file-text"></i> ${report.title}
                            </h4>
                            <button class="btn btn-sm btn-outline-secondary" onclick="closeReportPreview()">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                        
                        <div class="card">
                            <div class="card-body">
                                <div class="row mb-4">
                                    <div class="col-md-3">
                                        <div class="text-center">
                                            <i class="bi bi-file-earmark-pdf fs-1 text-danger" style="font-size: 4rem !important;"></i>
                                            <p class="mt-2">${report.format} документ</p>
                                        </div>
                                    </div>
                                    <div class="col-md-9">
                                        <div class="row">
                                            <div class="col-6">
                                                <p class="mb-1"><strong>Тип:</strong></p>
                                                <p class="mb-1"><strong>Дата создания:</strong></p>
                                                <p class="mb-1"><strong>Размер:</strong></p>
                                                <p class="mb-1"><strong>Статус:</strong></p>
                                            </div>
                                            <div class="col-6">
                                                <p class="mb-1">${report.type}</p>
                                                <p class="mb-1">${formatDate(report.date)}</p>
                                                <p class="mb-1">${report.size}</p>
                                                <p class="mb-1">
                                                    <span class="badge ${getStatusColor(report.status)}">
                                                        ${report.status}
                                                    </span>
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle"></i>
                                    Это предпросмотр отчета. Для полного просмотра скачайте файл.
                                </div>
                                
                                <div class="mt-4 text-center">
                                    <button class="btn btn-primary me-2" onclick="downloadReport('${reportId}')">
                                        <i class="bi bi-download"></i> Скачать полную версию
                                    </button>
                                    <button class="btn btn-outline-secondary" onclick="closeReportPreview()">
                                        <i class="bi bi-x"></i> Закрыть
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            closeAllModals();
            
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = previewModal;
            document.body.appendChild(modalContainer);
            
            const modalElement = document.getElementById('reportPreviewModal');
            if (modalElement) {
                modalElement.addEventListener('click', function(e) {
                    if (e.target === this) {
                        closeReportPreview();
                    }
                });
            }
        }
        
        function closeReportPreview() {
            const modal = document.getElementById('reportPreviewModal');
            if (modal) {
                modal.remove();
            }
        }
        
        function deleteReport(reportId) {
            if (!confirm('Вы уверены, что хотите удалить этот отчет?')) {
                return;
            }
            
            // Удаляем отчет из истории
            reportsHistory = reportsHistory.filter(r => r.id !== reportId);
            
            // Сохраняем изменения
            saveReportsHistory();
            
            // Обновляем отображение
            renderReportsHistory();
            
            // Показываем сообщение об успешном удалении
            const successAlert = `
                <div id="deleteSuccessAlert" class="alert alert-success alert-dismissible fade show" 
                     style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                    <i class="bi bi-check-circle"></i> Отчет успешно удален
                    <button type="button" class="btn-close" onclick="document.getElementById('deleteSuccessAlert').remove()"></button>
                </div>
            `;
            
            const alertContainer = document.createElement('div');
            alertContainer.innerHTML = successAlert;
            document.body.appendChild(alertContainer);
            
            setTimeout(() => {
                const alertElement = document.getElementById('deleteSuccessAlert');
                if (alertElement) {
                    alertElement.remove();
                }
            }, 3000);
        }


        // Остальные функции
        function updateTime() {
            const lastUpdateElement = document.getElementById('lastUpdate');
            if (lastUpdateElement) {
                const now = new Date();
                lastUpdateElement.textContent = 
                    now.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
            }
        }

        async function checkApiStatus() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                const apiStatusElement = document.getElementById('apiStatus');
                if (apiStatusElement) {
                    apiStatusElement.textContent = 'Online';
                    apiStatusElement.className = 'badge bg-success';
                }
            } catch (error) {
                const apiStatusElement = document.getElementById('apiStatus');
                if (apiStatusElement) {
                    apiStatusElement.textContent = 'Offline';
                    apiStatusElement.className = 'badge bg-danger';
                }
            }
        }

        function loadDashboardData() {
            try {
                const avgPrice = 5500;
                const avgPriceElement = document.getElementById('avgPrice');
                if (avgPriceElement) {
                    avgPriceElement.textContent = avgPrice.toLocaleString('ru-RU') + ' ₽';
                }
                createPriceChart();
            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
            }
        }

        function createPriceChart() {
            const ctx = document.getElementById('priceChart');
            if (!ctx) {
                console.error('Canvas элемент #priceChart не найден');
                return;
            }

            try {
                // Если график уже существует, уничтожаем его
                if (priceChart) {
                    priceChart.destroy();
                }

                const labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
                const ourPrices = [5000, 5200, 5100, 5300, 5500, 6000, 5800];
                const marketPrices = [4800, 5000, 4900, 5100, 5300, 5600, 5400];

                // Найдем минимальное и максимальное значения для установки границ
                const allPrices = [...ourPrices, ...marketPrices];
                const minValue = Math.min(...allPrices) * 0.95; // -5% от минимума
                const maxValue = Math.max(...allPrices) * 1.05; // +5% от максимума

                priceChart = new Chart(ctx.getContext('2d'), {
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
                                tension: 0.3,
                                fill: true,
                                pointBackgroundColor: '#4361ee',
                                pointBorderColor: '#ffffff',
                                pointBorderWidth: 2,
                                pointRadius: 5
                            },
                            {
                                label: 'Средняя по рынку',
                                data: marketPrices,
                                borderColor: '#95a5a6',
                                borderDash: [5, 5],
                                borderWidth: 2,
                                tension: 0.3,
                                pointBackgroundColor: '#95a5a6',
                                pointBorderColor: '#ffffff',
                                pointBorderWidth: 2,
                                pointRadius: 5
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    padding: 20,
                                    usePointStyle: true
                                }
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                callbacks: {
                                    label: function(context) {
                                        let label = context.dataset.label || '';
                                        if (label) {
                                            label += ': ';
                                        }
                                        label += context.parsed.y.toLocaleString('ru-RU') + ' ₽';
                                        return label;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    padding: 10
                                }
                            },
                            y: {
                                beginAtZero: false,
                                min: Math.floor(minValue / 100) * 100, // Округляем до сотен
                                max: Math.ceil(maxValue / 100) * 100, // Округляем до сотен
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.05)'
                                },
                                ticks: {
                                    padding: 10,
                                    callback: function(value) {
                                        return value.toLocaleString('ru-RU') + ' ₽';
                                    }
                                }
                            }
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index'
                        },
                        elements: {
                            point: {
                                hoverRadius: 7
                            }
                        },
                        layout: {
                            padding: {
                                top: 20,
                                right: 20,
                                bottom: 10,
                                left: 10
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Ошибка создания графика:', error);
            }
        }

        async function calculateOptimalPrice() {
            const basePrice = parseFloat(document.getElementById('basePrice').value);
            const season = parseFloat(document.getElementById('season').value);
            const occupancy = parseInt(document.getElementById('occupancySlider').value) / 100;

            // Получаем текущие данные о конкурентах
            const competitors = await getCompetitorsData();
            
            // Формируем данные конкурентов для расчета
            const competitorsData = competitors.map(hotel => ({
                price: hotel.price,
                rating: hotel.rating,
                distance: hotel.distance
            }));
        
            try {
                const response = await fetch('/api/pricing/calculate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        hotel_id: 'our_hotel',
                        base_price: basePrice,
                        competitors_data: competitorsData,
                        season_factor: season,
                        occupancy_rate: occupancy
                    })
                });
        
                const result = await response.json();
                
                // Обновляем отображение результата
                const finalPriceElement = document.getElementById('finalPrice');
                if (finalPriceElement) {
                    finalPriceElement.textContent = 
                        result.final_price.toLocaleString('ru-RU') + ' ₽';
                }
                
                // Показываем панель с результатом
                const priceResultElement = document.getElementById('priceResult');
                if (priceResultElement) {
                    priceResultElement.style.display = 'block';
                    
                    // Добавляем информацию о расчете
                    const factors = result.factors || {};
                    let detailsHtml = `
                        <div class="mt-3">
                            <h6>Детали расчета:</h6>
                            <ul class="mb-0">
                                <li>Базовая цена: ${basePrice.toLocaleString('ru-RU')} ₽</li>
                                <li>Сезонный коэффициент: ${season.toFixed(1)}x</li>
                                <li>Заполняемость: ${(occupancy * 100).toFixed(0)}%</li>
                                <li>Учтено конкурентов: ${competitorsData.length}</li>
                            </ul>
                        </div>
                    `;
                    
                    // Проверяем, есть ли уже детали
                    const existingDetails = priceResultElement.querySelector('.calculation-details');
                    if (existingDetails) {
                        existingDetails.innerHTML = detailsHtml;
                    } else {
                        const detailsDiv = document.createElement('div');
                        detailsDiv.className = 'calculation-details';
                        detailsDiv.innerHTML = detailsHtml;
                        priceResultElement.querySelector('.alert').appendChild(detailsDiv);
                    }
                }
            } catch (error) {
                alert('Ошибка расчета: ' + error.message);
            }
        }

        async function applyPrice() {
            const finalPriceElement = document.getElementById('finalPrice');
            if (!finalPriceElement) {
                alert('Элемент с ценой не найден');
                return;
            }
            
            // Извлекаем цену из текста (убираем пробелы и символ ₽)
            const priceText = finalPriceElement.textContent;
            const price = parseFloat(priceText.replace(/\s/g, '').replace('₽', ''));
            
            if (isNaN(price) || price < 1000 || price > 50000) {
                alert('Некорректная цена. Пожалуйста, пересчитайте ещё раз.');
                return;
            }
            
            // Проверяем, загружены ли данные о нашем отеле
            if (!ourHotelData) {
                // Если данные не загружены, загружаем их
                try {
                    await loadCurrentHotelInfo();
                } catch (error) {
                    alert('Не удалось загрузить данные отеля. Пожалуйста, обновите страницу.');
                    return;
                }
            }
            
            // Проверяем еще раз после загрузки
            if (!ourHotelData) {
                alert('Данные отеля не загружены. Пожалуйста, обновите страницу.');
                return;
            }
            
            try {
                // Обновляем цену через API
                const response = await fetch('/api/hotel/update-info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        hotel_id: 'our_hotel',
                        price: price
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Обновляем данные нашего отеля локально
                    ourHotelData.price = price;
                    
                    // Обновляем отображение цены
                    updateOurHotelDisplay();
                    
                    // Обновляем маркер нашего отеля на карте (если карта инициализирована)
                    if (map && markers.our_hotel) {
                        map.removeLayer(markers.our_hotel);
                        addOurHotel(ourHotelData);
                    }
                    
                    // Перерисовываем маркеры конкурентов с новыми цветами (если они есть)
                    if (map && allCompetitorsData && allCompetitorsData.length > 0) {
                        redrawAllCompetitorMarkers(allCompetitorsData);
                    }
                    
                    // Применяем фильтры (если мы на вкладке конкурентов)
                    if (document.getElementById('competitorsTab').style.display !== 'none') {
                        applyFilters();
                    }
                    
                    alert('Цена успешно применена! Новая цена: ' + price.toLocaleString('ru-RU') + ' ₽');
                    
                } else {
                    alert('Ошибка при применении цены: ' + result.error);
                }
            } catch (error) {
                console.error('Ошибка применения цены:', error);
                alert('Ошибка при применении цены: ' + error.message);
            }
        }
        
        async function getCompetitorsData() {
            try {
                const response = await fetch('/api/competitors/map');
                const data = await response.json();
                return data.competitors;
            } catch (error) {
                console.error('Ошибка загрузки данных конкурентов:', error);
                return [];
            }
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

        const occupancySliderElement = document.getElementById('occupancySlider');
        if (occupancySliderElement) {
            occupancySliderElement.addEventListener('input', function(e) {
                const occupancyValueElement = document.getElementById('occupancyValue');
                if (occupancyValueElement) {
                    occupancyValueElement.textContent = e.target.value + '%';
                }
            });
        }

        // ===== ФУНКЦИИ ДЛЯ ОТОБРАЖЕНИЯ ИНФОРМАЦИИ ОБ ОТЕЛЕ =====

        // Временно показывать информацию в алерте (можно заменить на модальное окно)
        function showHotelInfo(hotelId, event) {
            if (event) event.stopPropagation();

            // Находим отель по ID
            let hotel;
            if (hotelId === 'our_hotel') {
                hotel = ourHotelData;
            } else {
                hotel = allCompetitorsData.find(h => h.id === hotelId);
            }

            if (!hotel) {
                console.error('Отель не найден:', hotelId);
                return;
            }

            // Открываем попап маркера
            if (markers[hotelId]) {
                markers[hotelId].openPopup();
            }
        }

        // Модальное окно с подробной информацией об отеле
        function showHotelInfoModal(hotel) {
            // Если это наш отель
            const isOurHotel = hotel.id === 'our_hotel';
            const isSelected = selectedHotels.has(hotel.id);

            // Рассчитываем разницу цен (только для конкурентов)
            let priceDiff = 0;
            let priceDiffClass = '';
            let priceDiffText = '';

            if (!isOurHotel && ourHotelData) {
                priceDiff = hotel.price - ourHotelData.price;
                if (priceDiff > 500) {
                    priceDiffClass = 'price-higher';
                    priceDiffText = `Дороже на ${priceDiff} ₽`;
                } else if (priceDiff < -500) {
                    priceDiffClass = 'price-lower';
                    priceDiffText = `Дешевле на ${Math.abs(priceDiff)} ₽`;
                } else {
                    priceDiffClass = 'price-same';
                    priceDiffText = 'Примерно одинаково';
                }
            }

            // Создаем HTML для модального окна
            const modalHtml = `
                <div id="hotelDetailModal" class="modal-overlay" style="display: flex;">
                    <div class="modal-content" style="max-width: 800px;">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4><i class="bi ${isOurHotel ? 'bi-house-door' : 'bi-building'}"></i> ${hotel.name}</h4>
                            <button class="btn btn-sm btn-outline-secondary" onclick="closeHotelDetailModal()">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>

                        <div class="row">
                            <div class="col-md-8">
                                <div class="mb-3">
                                    <h6><i class="bi bi-geo-alt"></i> Адрес</h6>
                                    <p class="mb-2">${hotel.address}</p>
                                    <small class="text-muted">Координаты: ${hotel.lat.toFixed(6)}, ${hotel.lng.toFixed(6)}</small>
                                </div>

                                ${!isOurHotel ? `
                                <div class="mb-3">
                                    <h6><i class="bi bi-signpost"></i> Расстояние от нашего отеля</h6>
                                    <p>${hotel.distance}</p>
                                </div>
                                ` : ''}

                                <div class="mb-3">
                                    <h6><i class="bi bi-star"></i> Услуги и удобства</h6>
                                    <div class="d-flex flex-wrap gap-2">
                                        <span class="badge bg-light text-dark">Wi-Fi</span>
                                        <span class="badge bg-light text-dark">Парковка</span>
                                        <span class="badge bg-light text-dark">Завтрак</span>
                                        <span class="badge bg-light text-dark">Кондиционер</span>
                                        <span class="badge bg-light text-dark">Тренажерный зал</span>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <div class="metric-value text-primary">
                                            ${hotel.price.toLocaleString('ru-RU')} ₽
                                        </div>
                                        <small>Цена за ночь</small>

                                        ${!isOurHotel ? `
                                        <div class="mt-3">
                                            <span class="badge ${priceDiffClass}">${priceDiffText}</span>
                                        </div>
                                        ` : ''}
                                    </div>
                                </div>

                                <div class="card mt-3">
                                    <div class="card-body text-center">
                                        <div class="d-flex align-items-center justify-content-center">
                                            <h4 class="mb-0 me-2">${hotel.rating}</h4>
                                            <div class="text-warning">
                                                ${getRatingStars(hotel.rating)}
                                            </div>
                                        </div>
                                        <small>Рейтинг</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="row mt-3">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6><i class="bi bi-graph-up"></i> Статистика</h6>
                                        <div class="row text-center">
                                            <div class="col-6">
                                                <div class="metric-value">${Math.round(hotel.price * 0.9).toLocaleString('ru-RU')} ₽</div>
                                                <small>Средняя цена</small>
                                            </div>
                                            <div class="col-6">
                                                <div class="metric-value">${isOurHotel ? '78%' : '72%'}</div>
                                                <small>Заполняемость</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6><i class="bi bi-calendar-check"></i> Доступность</h6>
                                        <div class="d-flex justify-content-between mb-2">
                                            <span>Сегодня:</span>
                                            <span class="badge bg-success">Свободно</span>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <span>Завтра:</span>
                                            <span class="badge bg-warning text-dark">2 номера</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        ${!isOurHotel ? `
                        <div class="mt-4">
                            <div class="d-flex gap-2">
                                <button class="btn ${isSelected ? 'btn-outline-primary' : 'btn-primary'} w-50" 
                                        onclick="selectHotel('${hotel.id}'); closeHotelDetailModal()">
                                    <i class="bi ${isSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> 
                                    ${isSelected ? 'Убрать из анализа' : 'Добавить в анализ'}
                                </button>
                                <button class="btn btn-outline-info w-50" onclick="compareWithOurHotel('${hotel.id}')">
                                    <i class="bi bi-arrow-left-right"></i> Сравнить
                                </button>
                            </div>
                            <button class="btn btn-outline-danger w-100 mt-2" onclick="deleteCompetitor('${hotel.id}')">
                                <i class="bi bi-trash"></i> Удалить конкурента
                            </button>
                        </div>
                        ` : `
                        <div class="mt-4">
                            <div class="d-flex gap-2">
                                <button class="btn btn-primary w-50" onclick="openAddressModal(); closeHotelDetailModal()">
                                    <i class="bi bi-geo-alt"></i> Изменить адрес
                                </button>
                                <button class="btn btn-outline-primary w-50" onclick="openHotelInfoModal(); closeHotelDetailModal()">
                                    <i class="bi bi-pencil"></i> Редактировать
                                </button>
                            </div>
                        </div>
                        `}
                    </div>
                </div>
            `;

            // Добавляем модальное окно на страницу
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHtml;
            document.body.appendChild(modalContainer);

            // Добавляем обработчик закрытия по клику на фон
            const modalElement = document.getElementById('hotelDetailModal');
            if (modalElement) {
                modalElement.addEventListener('click', function(e) {
                    if (e.target === this) {
                        closeHotelDetailModal();
                    }
                });
            }
        }

        // Функция для закрытия модального окна
        function closeHotelDetailModal() {
            const modal = document.getElementById('hotelDetailModal');
            if (modal) {
                modal.remove();
            }
        }

        // Вспомогательная функция для получения звезд рейтинга
        function getRatingStars(rating) {
            let stars = '';
            for (let i = 1; i <= 5; i++) {
                if (i <= Math.floor(rating)) {
                    stars += '<i class="bi bi-star-fill"></i>';
                } else if (i - 0.5 <= rating) {
                    stars += '<i class="bi bi-star-half"></i>';
                } else {
                    stars += '<i class="bi bi-star"></i>';
                }
            }
            return stars;
        }

        // Функция для вызова из попапа
        function showHotelInfoModalFromPopup(hotelId) {
            let hotel;
            if (hotelId === 'our_hotel') {
                hotel = ourHotelData;
            } else {
                hotel = allCompetitorsData.find(h => h.id === hotelId);
            }

            if (hotel) {
                // Закрываем попап перед открытием модального окна
                if (markers[hotelId]) {
                    markers[hotelId].closePopup();
                }

                // Показываем модальное окно
                showHotelInfoModal(hotel);
            }
            
             setTimeout(() => {
                refreshAllMapMarkers();
            }, 100);
        }
        
        // Принудительно обновить все маркеры на карте
        function refreshAllMapMarkers() {
            if (!map) return;
            
            // Сохраняем текущее состояние выбранных отелей
            const currentSelectedHotels = new Set(selectedHotels);
            
            // Пересоздаем все маркеры конкурентов
            allCompetitorsData.forEach(hotel => {
                if (markers[hotel.id]) {
                    map.removeLayer(markers[hotel.id]);
                    delete markers[hotel.id];
                }
                addCompetitorMarker(hotel);
            });
            
            // Восстанавливаем состояние выбранных отелей в UI
            currentSelectedHotels.forEach(hotelId => {
                updateHotelSelectionUI(hotelId, true);
            });
        }
        
        // Функция сравнения с нашим отелем
        function compareWithOurHotel(competitorId) {
            const competitor = allCompetitorsData.find(h => h.id === competitorId);
            if (!competitor || !ourHotelData) return;

            const priceDiff = competitor.price - ourHotelData.price;
            const ratingDiff = competitor.rating - ourHotelData.rating;
            const isSelected = selectedHotels.has(competitorId);

            let comparisonHtml = `
                <div id="comparisonModal" class="modal-overlay" style="display: flex;">
                    <div class="modal-content" style="max-width: 800px;">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4><i class="bi bi-arrow-left-right"></i> Сравнение отелей</h4>
                            <button class="btn btn-sm btn-outline-secondary" onclick="closeComparisonModal()">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h5 class="card-title text-center">${ourHotelData.name}</h5>
                                        <div class="text-center mb-3">
                                            <div class="metric-value text-primary">${ourHotelData.price.toLocaleString('ru-RU')} ₽</div>
                                            <small>Цена за ночь</small>
                                        </div>
                                        <div class="text-center">
                                            <div class="d-flex align-items-center justify-content-center">
                                                <h4 class="mb-0 me-2">${ourHotelData.rating}</h4>
                                                <div class="text-warning">
                                                    ${getRatingStars(ourHotelData.rating)}
                                                </div>
                                            </div>
                                            <small>Рейтинг</small>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h5 class="card-title text-center">${competitor.name}</h5>
                                        <div class="text-center mb-3">
                                            <div class="metric-value text-primary">${competitor.price.toLocaleString('ru-RU')} ₽</div>
                                            <small>Цена за ночь</small>
                                        </div>
                                        <div class="text-center">
                                            <div class="d-flex align-items-center justify-content-center">
                                                <h4 class="mb-0 me-2">${competitor.rating}</h4>
                                                <div class="text-warning">
                                                    ${getRatingStars(competitor.rating)}
                                                </div>
                                            </div>
                                            <small>Рейтинг</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="row mt-4">
                            <div class="col-md-12">
                                <div class="card">
                                    <div class="card-body">
                                        <h6><i class="bi bi-bar-chart"></i> Сравнительный анализ</h6>
                                        <table class="table table-bordered">
                                            <thead>
                                                <tr>
                                                    <th>Параметр</th>
                                                    <th>Наш отель</th>
                                                    <th>Конкурент</th>
                                                    <th>Разница</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td>Цена</td>
                                                    <td>${ourHotelData.price.toLocaleString('ru-RU')} ₽</td>
                                                    <td>${competitor.price.toLocaleString('ru-RU')} ₽</td>
                                                    <td>
                                                        <span class="badge ${priceDiff > 0 ? 'bg-danger' : priceDiff < 0 ? 'bg-success' : 'bg-warning'}">
                                                            ${priceDiff > 0 ? '+' : ''}${priceDiff} ₽
                                                        </span>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td>Рейтинг</td>
                                                    <td>${ourHotelData.rating}</td>
                                                    <td>${competitor.rating}</td>
                                                    <td>
                                                        <span class="badge ${ratingDiff > 0 ? 'bg-danger' : ratingDiff < 0 ? 'bg-success' : 'bg-warning'}">
                                                            ${ratingDiff > 0 ? '+' : ''}${ratingDiff.toFixed(1)}
                                                        </span>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td>Расстояние</td>
                                                    <td>-</td>
                                                    <td>${competitor.distance}</td>
                                                    <td>-</td>
                                                </tr>
                                            </tbody>
                                        </table>

                                        <div class="mt-3">
                                            <h6>Рекомендации:</h6>
                                            <ul>
                                                ${priceDiff > 500 ? `
                                                <li>Конкурент значительно дороже. Рассмотрите возможность повышения цены на 5-10%</li>
                                                ` : priceDiff < -500 ? `
                                                <li>Конкурент значительно дешевле. Проверьте, не слишком ли высока ваша цена</li>
                                                ` : `
                                                <li>Цены сопоставимы. Ваша ценовая позиция оптимальна</li>
                                                `}

                                                ${ratingDiff > 0.3 ? `
                                                <li>У конкурента выше рейтинг. Проанализируйте отзывы гостей</li>
                                                ` : ratingDiff < -0.3 ? `
                                                <li>Ваш рейтинг выше. Используйте это в маркетинге</li>
                                                ` : `
                                                <li>Рейтинги сопоставимы. Уровень сервиса аналогичен</li>
                                                `}
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="mt-4">
                            <button class="btn ${isSelected ? 'btn-outline-primary' : 'btn-primary'} w-100" 
                                    onclick="selectHotel('${competitorId}'); closeComparisonModal()">
                                <i class="bi ${isSelected ? 'bi-dash-circle' : 'bi-plus-circle'}"></i> 
                                ${isSelected ? 'Убрать из анализа' : 'Добавить в анализ'}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // Закрываем текущие модальные окна
            closeHotelDetailModal();

            // Добавляем модальное окно сравнения
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = comparisonHtml;
            document.body.appendChild(modalContainer);

            // Добавляем обработчик закрытия
            const modalElement = document.getElementById('comparisonModal');
            if (modalElement) {
                modalElement.addEventListener('click', function(e) {
                    if (e.target === this) {
                        closeComparisonModal();
                    }
                });
            }
        }

        function closeComparisonModal() {
            const modal = document.getElementById('comparisonModal');
            if (modal) {
                modal.remove();
            }
        }
    </script>
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
            "geocode": "/api/geocode",
            "search_address": "/api/search-address",
            "update_address": "/api/hotel/update-address",
            "update_info": "/api/hotel/update-info",
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


@app.post("/api/geocode")
async def geocode_endpoint(request: Dict[str, Any]):
    """Геокодирование адреса"""
    address = request.get("address", "")

    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    # В реальном приложении используйте реальный API ключ
    result = await geocode_address(address)

    if not result["success"]:
        # Для демо возвращаем случайные координаты если API не доступен
        import random
        lat = 55.7558 + (random.random() - 0.5) * 0.1
        lng = 37.6173 + (random.random() - 0.5) * 0.1

        result = {
            "success": True,
            "lat": lat,
            "lng": lng,
            "address": address,
            "coordinates": f"{lat:.6f},{lng:.6f}",
            "note": "Используются тестовые координаты"
        }

    return result


@app.post("/api/hotel/update-address")
async def update_hotel_address(request: AddressUpdateRequest):
    """Обновление адреса отеля"""
    try:
        # Получаем координаты для нового адреса
        geocode_result = await geocode_address(request.new_address)

        if not geocode_result["success"]:
            raise HTTPException(status_code=400,
                                detail=f"Не удалось найти адрес: {geocode_result.get('error', 'Неизвестная ошибка')}")

        # Обновляем данные нашего отеля
        COMPETITORS_DATA["our_hotel"]["address"] = geocode_result["address"]
        COMPETITORS_DATA["our_hotel"]["lat"] = geocode_result["lat"]
        COMPETITORS_DATA["our_hotel"]["lng"] = geocode_result["lng"]

        # Пересчитываем расстояния до конкурентов
        our_coords = {"lat": geocode_result["lat"], "lng": geocode_result["lng"]}

        for competitor in COMPETITORS_DATA["competitors"]:
            competitor_coords = {"lat": competitor["lat"], "lng": competitor["lng"]}
            distance = await calculate_distance(our_coords, competitor_coords)
            competitor["distance"] = distance

        return {
            "success": True,
            "message": "Адрес успешно обновлен",
            "hotel_id": request.hotel_id,
            "new_address": geocode_result["address"],
            "coordinates": {
                "lat": geocode_result["lat"],
                "lng": geocode_result["lng"]
            },
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.post("/api/hotel/update-info")
async def update_hotel_info(request: HotelInfoUpdateRequest):
    """Обновление информации об отеле (цена, рейтинг, название)"""
    try:
        hotel = COMPETITORS_DATA["our_hotel"]

        # Обновляем название, если передано
        if request.name is not None:
            hotel["name"] = request.name

        # Обновляем цену, если передана
        if request.price is not None:
            # Валидация цены
            if request.price < 1000 or request.price > 50000:
                raise HTTPException(status_code=400, detail="Цена должна быть в диапазоне 1000 - 50000 ₽")
            hotel["price"] = request.price

        # Обновляем рейтинг, если передан
        if request.rating is not None:
            # Валидация рейтинга
            if request.rating < 1.0 or request.rating > 5.0:
                raise HTTPException(status_code=400, detail="Рейтинг должен быть в диапазоне 1.0 - 5.0")
            hotel["rating"] = request.rating

        # Пересчитываем метрики
        competitors_prices = [c["price"] for c in COMPETITORS_DATA["competitors"]]
        all_prices = competitors_prices + [hotel["price"]]
        avg_price = sum(all_prices) / len(all_prices)

        # Рассчитываем позицию на рынке
        sorted_prices = sorted(all_prices)
        position = sorted_prices.index(hotel["price"]) + 1

        return {
            "success": True,
            "message": "Информация об отеле успешно обновлена",
            "hotel_id": request.hotel_id,
            "updated_data": {
                "name": hotel["name"],
                "price": hotel["price"],
                "rating": hotel["rating"]
            },
            "market_metrics": {
                "average_price": round(avg_price, 2),
                "market_position": position,
                "total_hotels": len(all_prices)
            },
            "updated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/competitors/add")
async def add_competitor(request: NewCompetitorRequest):
    """Добавление нового конкурента"""
    try:
        # Если координаты не переданы, геокодируем адрес
        if request.lat is None or request.lng is None:
            geocode_result = await geocode_address(request.address)
            if not geocode_result["success"]:
                raise HTTPException(status_code=400, detail=f"Не удалось найти адрес: {geocode_result.get('error')}")
            lat = geocode_result["lat"]
            lng = geocode_result["lng"]
        else:
            lat = request.lat
            lng = request.lng

        # Рассчитываем расстояние до нашего отеля
        our_coords = {
            "lat": COMPETITORS_DATA["our_hotel"]["lat"],
            "lng": COMPETITORS_DATA["our_hotel"]["lng"]
        }
        competitor_coords = {"lat": lat, "lng": lng}
        distance = await calculate_distance(our_coords, competitor_coords)

        # Генерируем уникальный ID
        import uuid
        competitor_id = f"hotel_{str(uuid.uuid4())[:8]}"

        # Определяем цвет на основе разницы цен
        price_diff = request.price - COMPETITORS_DATA["our_hotel"]["price"]
        if price_diff > 500:
            color = "#ef476f"  # Красный для дороже
        elif price_diff < -500:
            color = "#06d6a0"  # Зеленый для дешевле
        else:
            color = "#ffd166"  # Желтый для примерно одинаково

        # Создаем нового конкурента
        new_competitor = {
            "id": competitor_id,
            "name": request.name,
            "lat": lat,
            "lng": lng,
            "price": request.price,
            "rating": request.rating,
            "color": color,
            "address": request.address,
            "distance": distance,
            "selected": False
        }

        # Добавляем в список
        COMPETITORS_DATA["competitors"].append(new_competitor)

        return {
            "success": True,
            "message": "Конкурент успешно добавлен",
            "competitor": new_competitor,
            "added_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/competitors/delete")
async def delete_competitor(request: DeleteCompetitorRequest):
    """Удаление конкурента"""
    try:
        # Ищем конкурента
        competitor_index = None
        for i, competitor in enumerate(COMPETITORS_DATA["competitors"]):
            if competitor["id"] == request.competitor_id:
                competitor_index = i
                break

        if competitor_index is None:
            raise HTTPException(status_code=404, detail="Конкурент не найден")

        # Удаляем конкурента
        deleted_competitor = COMPETITORS_DATA["competitors"].pop(competitor_index)

        return {
            "success": True,
            "message": "Конкурент успешно удален",
            "competitor": deleted_competitor,
            "deleted_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/competitors/all")
async def get_all_competitors():
    """Получение всех конкурентов (с нашим отелем)"""
    return COMPETITORS_DATA


@app.post("/api/competitors/analyze-selected")
async def analyze_selected_competitors(request: Dict[str, Any]):
    """Анализ выбранных конкурентов с расчетом рекомендаций"""
    try:
        competitor_ids = request.get("competitor_ids", [])
        hotel_id = request.get("hotel_id", "our_hotel")

        # Получаем наш отель
        our_hotel = COMPETITORS_DATA["our_hotel"]

        # Находим выбранных конкурентов
        selected_competitors = []
        for competitor in COMPETITORS_DATA["competitors"]:
            if competitor["id"] in competitor_ids:
                selected_competitors.append(competitor)

        if not selected_competitors:
            return {
                "success": False,
                "message": "Не выбрано ни одного конкурента"
            }

        # Рассчитываем средние показатели
        total_price = sum(c["price"] for c in selected_competitors)
        total_rating = sum(c["rating"] for c in selected_competitors)
        avg_price = total_price / len(selected_competitors)
        avg_rating = total_rating / len(selected_competitors)

        # Рассчитываем разницы
        price_diff = our_hotel["price"] - avg_price
        rating_diff = our_hotel["rating"] - avg_rating

        # Определяем рекомендации
        recommendations = []
        priority = "low"

        if price_diff > 500:
            if rating_diff > 0.3:
                recommendations.append({
                    "type": "info",
                    "text": "Ваш отель значительно дороже, но имеет более высокий рейтинг",
                    "actions": [
                        "Предложить пакетные услуги для обоснования цены",
                        "Усилить маркетинг, подчеркивающий качество сервиса"
                    ]
                })
            else:
                recommendations.append({
                    "type": "danger",
                    "text": "Ваш отель значительно дороже конкурентов",
                    "actions": [
                        "Снизить цену на 5-15%",
                        "Проанализировать отзывы конкурентов с высоким рейтингом"
                    ]
                })
                priority = "high"
        elif price_diff < -500:
            if rating_diff > 0:
                recommendations.append({
                    "type": "success",
                    "text": "Ваш отель дешевле и имеет более высокий рейтинг",
                    "actions": [
                        "Можно повысить цену на 5-10%",
                        "Увеличить маркетинговые активности"
                    ]
                })
                priority = "medium"
            else:
                recommendations.append({
                    "type": "warning",
                    "text": "Ваш отель дешевле конкурентов",
                    "actions": [
                        "Постепенно повышать цену",
                        "Добавить дополнительные услуги"
                    ]
                })
        else:
            if rating_diff > 0.3:
                recommendations.append({
                    "type": "success",
                    "text": "Цены сопоставимы, ваш рейтинг выше",
                    "actions": [
                        "Использовать преимущество в маркетинге",
                        "Рассмотреть повышение цены на 3-5%"
                    ]
                })
            elif rating_diff < -0.3:
                recommendations.append({
                    "type": "warning",
                    "text": "Цены сопоставимы, но рейтинг конкурентов выше",
                    "actions": [
                        "Проанализировать отзывы гостей",
                        "Улучшить качество сервиса"
                    ]
                })
                priority = "medium"
            else:
                recommendations.append({
                    "type": "info",
                    "text": "Ваша позиция на рынке оптимальна",
                    "actions": [
                        "Поддерживать текущую стратегию",
                        "Продолжать мониторинг конкурентов"
                    ]
                })

        return {
            "success": True,
            "analysis": {
                "selected_count": len(selected_competitors),
                "average_price": round(avg_price, 2),
                "average_rating": round(avg_rating, 2),
                "our_hotel": {
                    "price": our_hotel["price"],
                    "rating": our_hotel["rating"]
                },
                "differences": {
                    "price": round(price_diff, 2),
                    "rating": round(rating_diff, 2)
                },
                "recommendations": recommendations,
                "priority": priority,
                "competitors": selected_competitors
            },
            "analyzed_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/generate")
async def generate_report(request: ReportRequest):
    """Генерация отчета"""
    try:
        # Валидация типа отчета
        valid_types = ["financial", "pricing", "competitors", "summary"]
        if request.report_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Неверный тип отчета. Допустимые: {valid_types}")

        # Получаем данные для отчета
        report_data = await prepare_report_data(request)

        # Генерируем отчет
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.report_type}"

        # Возвращаем информацию об отчете
        return {
            "success": True,
            "report_id": report_id,
            "report_type": request.report_type,
            "period": request.period,
            "format": request.format,
            "size_kb": len(str(report_data)) // 1024,
            "download_url": f"/api/reports/download/{report_id}",
            "preview_url": f"/api/reports/preview/{report_id}",
            "generated_at": datetime.now().isoformat(),
            "hotel_id": request.hotel_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def prepare_report_data(request: ReportRequest):
    """Подготовка данных для отчета"""
    # Для финансового отчета
    if request.report_type == "financial":
        return {
            "hotel": COMPETITORS_DATA["our_hotel"],
            "revenue_data": {
                "current_month": 1250000,
                "previous_month": 1180000,
                "growth_percent": 5.93,
                "average_daily_rate": 5500,
                "occupancy_rate": 78
            },
            "expenses": {
                "staff": 450000,
                "utilities": 120000,
                "marketing": 80000,
                "maintenance": 60000,
                "other": 40000
            },
            "summary": {
                "net_profit": 500000,
                "profit_margin": 40,
                "recommendations": [
                    "Увеличить маркетинговый бюджет на 10%",
                    "Рассмотреть автоматизацию процессов для снижения затрат",
                    "Провести акцию для повышения загрузки в будни"
                ]
            }
        }

    # Для анализа цен
    elif request.report_type == "pricing":
        competitors = COMPETITORS_DATA["competitors"]
        avg_competitor_price = sum(c["price"] for c in competitors) / len(competitors)

        return {
            "our_hotel": COMPETITORS_DATA["our_hotel"],
            "competitors": competitors,
            "pricing_analysis": {
                "average_competitor_price": avg_competitor_price,
                "price_difference": COMPETITORS_DATA["our_hotel"]["price"] - avg_competitor_price,
                "market_position": "Средняя цена рынка",
                "recommendations": get_pricing_recommendations(COMPETITORS_DATA["our_hotel"]["price"],
                                                               avg_competitor_price)
            },
            "price_trend": [
                {"day": "Пн", "our_price": 5000, "market_avg": 4800},
                {"day": "Вт", "our_price": 5200, "market_avg": 5000},
                {"day": "Ср", "our_price": 5100, "market_avg": 4900},
                {"day": "Чт", "our_price": 5300, "market_avg": 5100},
                {"day": "Пт", "our_price": 5500, "market_avg": 5300},
                {"day": "Сб", "our_price": 6000, "market_avg": 5600},
                {"day": "Вс", "our_price": 5800, "market_avg": 5400}
            ]
        }

    # Для анализа конкурентов
    elif request.report_type == "competitors":
        return {
            "competitors_count": len(COMPETITORS_DATA["competitors"]),
            "competitors": COMPETITORS_DATA["competitors"],
            "analysis": {
                "price_range": {
                    "min": min(c["price"] for c in COMPETITORS_DATA["competitors"]),
                    "max": max(c["price"] for c in COMPETITORS_DATA["competitors"]),
                    "average": sum(c["price"] for c in COMPETITORS_DATA["competitors"]) / len(
                        COMPETITORS_DATA["competitors"])
                },
                "rating_range": {
                    "min": min(c["rating"] for c in COMPETITORS_DATA["competitors"]),
                    "max": max(c["rating"] for c in COMPETITORS_DATA["competitors"]),
                    "average": sum(c["rating"] for c in COMPETITORS_DATA["competitors"]) / len(
                        COMPETITORS_DATA["competitors"])
                },
                "top_competitors": sorted(COMPETITORS_DATA["competitors"], key=lambda x: x["rating"], reverse=True)[:3]
            },
            "recommendations": [
                "Мониторить цены конкурентов ежедневно",
                "Анализировать отзывы конкурентов с высоким рейтингом",
                "Предложить уникальные услуги для выделения на фоне конкурентов"
            ]
        }


def get_pricing_recommendations(our_price, avg_competitor_price):
    """Получение рекомендаций по ценообразованию"""
    price_diff = our_price - avg_competitor_price

    if price_diff > 500:
        return ["Рассмотреть снижение цены на 5-10%", "Предложить пакетные услуги для обоснования цены"]
    elif price_diff < -500:
        return ["Рассмотреть повышение цены на 5-8%", "Акцентировать внимание на качестве сервиса в маркетинге"]
    else:
        return ["Поддерживать текущий уровень цен", "Продолжать мониторинг конкурентов"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
