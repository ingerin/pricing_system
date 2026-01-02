from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ВРЕМЕННО - убираем проблемные импорты
# from bs4 import BeautifulSoup
# import redis.asyncio as redis

class CompetitorData(BaseModel):
    service: str
    hotel_name: str
    price_per_night: float
    rating: float = 4.0
    reviews_count: int = 100
    occupancy: float = 0.7
    amenities: List[str] = []
    extracted_at: datetime = datetime.now()


@router.get("/")
async def get_competitors():
    """Базовый эндпоинт - возвращает тестовые данные"""
    return {
        "status": "ok",
        "data": [
            {
                "service": "mock",
                "hotel_name": "Test Hotel 1",
                "price_per_night": 5000.0,
                "rating": 4.5,
                "reviews_count": 128,
                "occupancy": 0.85,
                "amenities": ["Wi-Fi", "Breakfast"],
                "extracted_at": datetime.now().isoformat()
            },
            {
                "service": "mock",
                "hotel_name": "Test Hotel 2",
                "price_per_night": 5200.0,
                "rating": 4.3,
                "reviews_count": 95,
                "occupancy": 0.78,
                "amenities": ["Wi-Fi", "Pool"],
                "extracted_at": datetime.now().isoformat()
            }
        ]
    }


@router.post("/analyze")
async def analyze_competitors(
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        rooms: int = 1
):
    """Упрощенный анализ - без реального парсинга"""
    try:
        # Имитация задержки получения данных
        import asyncio
        await asyncio.sleep(0.1)

        return {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "competitors_found": 5,
            "average_price": 5300,
            "recommendation": "Your price is competitive"
        }

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend")
async def recommend_competitors(
        hotel_id: str,
        location: str,
        category: str
):
    """Рекомендация конкурентов"""
    return {
        "hotel_id": hotel_id,
        "recommended_competitors": [
            {
                "id": "comp_001",
                "name": f"Similar Hotel in {location}",
                "category": category,
                "similarity_score": 0.85
            }
        ]
    }