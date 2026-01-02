from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

router = APIRouter()
logger = logging.getLogger(__name__)


class Season(Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    PEAK = "peak"


class PricingStrategy(Enum):
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    CONSERVATIVE = "conservative"
    PREMIUM = "premium"


class PricingRequest(BaseModel):
    hotel_id: str
    base_price: float
    check_in: str
    check_out: str
    room_type: str
    competitors: List[Dict[str, Any]]
    occupancy_rate: float = 0.7
    season: Season = Season.MID
    strategy: PricingStrategy = PricingStrategy.MODERATE
    events: Optional[List[str]] = None
    demand_forecast: Optional[float] = None


class PricingEngine:
    def __init__(self):
        self.models = {}

    def calculate_optimal_price(self, request: PricingRequest) -> Dict[str, Any]:
        """
        Расчет оптимальной цены с учетом множества факторов
        """
        # Базовый расчет
        base_price = request.base_price

        # Корректировка по сезону
        season_factor = self._get_season_factor(request.season)

        # Корректировка по загрузке
        occupancy_factor = self._get_occupancy_factor(request.occupancy_rate)

        # Анализ конкурентов
        competitor_factor = self._analyze_competitors(request.competitors, base_price)

        # Стратегия ценообразования
        strategy_factor = self._get_strategy_factor(request.strategy)

        # Корректировка на события
        event_factor = self._get_event_factor(request.events)

        # Расчет итоговой цены
        final_price = base_price * season_factor * occupancy_factor * competitor_factor * strategy_factor * event_factor

        # Округление
        final_price = self._round_price(final_price)

        return {
            "base_price": round(base_price, 2),
            "final_price": round(final_price, 2),
            "factors": {
                "season": round(season_factor, 3),
                "occupancy": round(occupancy_factor, 3),
                "competition": round(competitor_factor, 3),
                "strategy": round(strategy_factor, 3),
                "events": round(event_factor, 3)
            },
            "recommendation": self._generate_recommendation(
                final_price, request.competitors
            ),
            "valid_until": (datetime.now() + timedelta(hours=6)).isoformat()
        }

    def _get_season_factor(self, season: Season) -> float:
        factors = {
            Season.LOW: 0.8,
            Season.MID: 1.0,
            Season.HIGH: 1.3,
            Season.PEAK: 1.6
        }
        return factors.get(season, 1.0)

    def _get_occupancy_factor(self, occupancy_rate: float) -> float:
        if occupancy_rate < 0.3:
            return 0.9  # Снижаем цену при низкой загрузке
        elif occupancy_rate > 0.9:
            return 1.3  # Повышаем при высокой
        else:
            return 1.0

    def _analyze_competitors(self, competitors: List[Dict], our_price: float) -> float:
        if not competitors:
            return 1.0

        competitor_prices = [c.get("price_per_night", 0) for c in competitors]
        avg_competitor_price = np.mean(competitor_prices)

        if our_price < avg_competitor_price * 0.8:
            # Мы значительно дешевле конкурентов
            return 1.1  # Можно повысить
        elif our_price > avg_competitor_price * 1.2:
            # Мы значительно дороже
            return 0.9  # Стоит снизить
        else:
            return 1.0

    def _get_strategy_factor(self, strategy: PricingStrategy) -> float:
        factors = {
            PricingStrategy.AGGRESSIVE: 0.85,  # Захват рынка
            PricingStrategy.MODERATE: 1.0,  # Баланс
            PricingStrategy.CONSERVATIVE: 1.1,  # Максимизация прибыли
            PricingStrategy.PREMIUM: 1.3  # Премиум позиционирование
        }
        return factors.get(strategy, 1.0)

    def _get_event_factor(self, events: Optional[List[str]]) -> float:
        if not events:
            return 1.0

        factor = 1.0
        for event in events:
            if "conference" in event.lower() or "festival" in event.lower():
                factor *= 1.3
            elif "holiday" in event.lower():
                factor *= 1.2
        return min(factor, 1.5)  # Максимум +50%

    def _round_price(self, price: float) -> float:
        # Округление до психологически приятных цен
        if price < 1000:
            return round(price / 50) * 50
        elif price < 5000:
            return round(price / 100) * 100
        else:
            return round(price / 500) * 500

    def _generate_recommendation(self, price: float, competitors: List[Dict]) -> str:
        if not competitors:
            return "Нет данных о конкурентах для рекомендации"

        competitor_prices = [c.get("price_per_night", 0) for c in competitors]
        avg_price = np.mean(competitor_prices)

        if price < avg_price * 0.9:
            return "Цена ниже среднерыночной. Можно рассмотреть повышение."
        elif price > avg_price * 1.1:
            return "Цена выше среднерыночной. Рассмотрите специальные предложения."
        else:
            return "Цена соответствует рыночной. Текущий уровень оптимален."


# Инициализация движка
pricing_engine = PricingEngine()


@router.post("/calculate")
async def calculate_price(request: PricingRequest):
    """
    Расчет оптимальной цены
    """
    try:
        result = pricing_engine.calculate_optimal_price(request)

        # Логируем расчет
        logger.info(f"Price calculated for {request.hotel_id}: {result}")

        return {
            "success": True,
            "data": result,
            "calculated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Pricing calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast")
async def price_forecast(
        hotel_id: str,
        period_days: int = 30,
        include_competitors: bool = True
):
    """
    Прогноз цен на период
    """
    try:
        forecast_data = await generate_price_forecast(
            hotel_id, period_days, include_competitors
        )

        return {
            "hotel_id": hotel_id,
            "forecast_period_days": period_days,
            "forecast": forecast_data,
            "recommendations": generate_forecast_recommendations(forecast_data)
        }

    except Exception as e:
        logger.error(f"Forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_pricing_strategies():
    """
    Доступные стратегии ценообразования
    """
    return {
        "strategies": [
            {
                "id": "aggressive",
                "name": "Агрессивная",
                "description": "Захват доли рынка, цены ниже конкурентов",
                "best_for": ["новые отели", "низкий сезон", "повышение узнаваемости"]
            },
            {
                "id": "moderate",
                "name": "Умеренная",
                "description": "Баланс между заполняемостью и прибылью",
                "best_for": ["стабильный бизнес", "средний сезон"]
            },
            {
                "id": "conservative",
                "name": "Консервативная",
                "description": "Максимизация прибыли при сохранении заполняемости",
                "best_for": ["премиум сегмент", "высокий сезон"]
            },
            {
                "id": "premium",
                "name": "Премиальная",
                "description": "Позиционирование как премиум предложение",
                "best_for": ["люксовые отели", "уникальные локации"]
            }
        ]
    }


async def generate_price_forecast(hotel_id, period_days, include_competitors):
    """
    Генерация прогноза цен
    """
    # Здесь должна быть сложная логика прогнозирования
    # Пока возвращаем примерные данные

    forecast = []
    base_price = 5000  # Это должно быть из базы данных

    for day in range(period_days):
        date = datetime.now() + timedelta(days=day)

        # Простая модель сезонности
        if date.month in [6, 7, 8, 12]:
            season_factor = 1.3
        elif date.month in [1, 2, 11]:
            season_factor = 0.8
        else:
            season_factor = 1.0

        # Выходные дороже
        if date.weekday() >= 5:  # Суббота, воскресенье
            weekend_factor = 1.2
        else:
            weekend_factor = 1.0

        forecast_price = base_price * season_factor * weekend_factor

        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "predicted_price": round(forecast_price, 2),
            "recommended_min": round(forecast_price * 0.9, 2),
            "recommended_max": round(forecast_price * 1.1, 2),
            "confidence": 0.85 - (day * 0.01)  # Уверенность снижается со временем
        })

    return forecast


def generate_forecast_recommendations(forecast_data):
    """
    Генерация рекомендаций на основе прогноза
    """
    prices = [day["predicted_price"] for day in forecast_data]
    avg_price = np.mean(prices)
    max_price = max(prices)
    min_price = min(prices)

    recommendations = []

    if max_price / min_price > 1.5:
        recommendations.append(
            "Значительные колебания цен в периоде. "
            "Рекомендуется динамическое ценообразование."
        )

    if avg_price > 8000:
        recommendations.append(
            "Высокие средние цены. Проверьте конкурентоспособность."
        )

    return recommendations