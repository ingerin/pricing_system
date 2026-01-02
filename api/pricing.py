from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class Season(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    PEAK = "peak"


class PricingStrategy(str, Enum):
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    CONSERVATIVE = "conservative"


class PricingRequest(BaseModel):
    hotel_id: str
    base_price: float
    check_in: str
    check_out: str
    room_type: str = "standard"
    season: Season = Season.MID
    strategy: PricingStrategy = PricingStrategy.MODERATE
    occupancy: float = 0.7
    events: Optional[List[str]] = None


@router.post("/calculate")
async def calculate_price(request: PricingRequest):
    """Расчет оптимальной цены"""
    try:
        # Простая логика расчета
        price = request.base_price

        # Сезонные коэффициенты
        season_factors = {
            Season.LOW: 0.8,
            Season.MID: 1.0,
            Season.HIGH: 1.3,
            Season.PEAK: 1.6
        }
        price *= season_factors.get(request.season, 1.0)

        # Коэффициент стратегии
        strategy_factors = {
            PricingStrategy.AGGRESSIVE: 0.9,
            PricingStrategy.MODERATE: 1.0,
            PricingStrategy.CONSERVATIVE: 1.1
        }
        price *= strategy_factors.get(request.strategy, 1.0)

        # Корректировка по загрузке
        if request.occupancy > 0.8:
            price *= 1.15
        elif request.occupancy < 0.4:
            price *= 0.85

        # Округление
        price = round(price / 100) * 100

        return {
            "success": True,
            "hotel_id": request.hotel_id,
            "base_price": request.base_price,
            "final_price": price,
            "calculation_details": {
                "season_factor": season_factors.get(request.season),
                "strategy_factor": strategy_factors.get(request.strategy),
                "occupancy_adjustment": request.occupancy
            },
            "valid_until": (datetime.now() + timedelta(hours=6)).isoformat()
        }

    except Exception as e:
        logger.error(f"Pricing calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_price_forecast(
        hotel_id: str,
        days: int = 7
):
    """Прогноз цен"""
    base_price = 5000

    forecast = []
    for i in range(days):
        date = datetime.now() + timedelta(days=i)

        # Простая модель
        price = base_price

        # Выходные дороже
        if date.weekday() >= 5:
            price *= 1.2

        # Случайные колебания
        import random
        price *= random.uniform(0.95, 1.05)

        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "predicted_price": round(price, 2),
            "confidence": 0.8 - (i * 0.05)
        })

    return {
        "hotel_id": hotel_id,
        "forecast": forecast
    }