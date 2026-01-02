from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os

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


@app.get("/")
async def root():
    return {
        "message": "Hotel Dynamic Pricing API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "competitors": "/api/competitors",
            "pricing": "/api/pricing",
            "reports": "/api/reports",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# ПРОСТОЙ ВАРИАНТ - без импорта проблемных модулей
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

        return {
            "base_price": request.base_price,
            "final_price": round(final_price, 2),
            "factors": {
                "season": request.season_factor,
                "occupancy": request.occupancy_rate
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/summary")
async def get_report_summary(hotel_id: str, days: int = 7):
    """Упрощенный отчет"""
    return {
        "hotel_id": hotel_id,
        "period_days": days,
        "summary": {
            "average_price": 5500,
            "occupancy_rate": 0.78,
            "revenue": 1250000
        },
        "recommendations": [
            "Test recommendation 1",
            "Test recommendation 2"
        ]
    }


# ДЕЙСТВИТЕЛЬНО ВАЖНО для Vercel
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)