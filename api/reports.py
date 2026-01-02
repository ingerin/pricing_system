from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ReportRequest(BaseModel):
    hotel_id: str
    period_start: str
    period_end: str
    format: str = "json"  # временно только JSON


@router.get("/")
async def get_report_types():
    """Доступные типы отчетов"""
    return {
        "available_reports": [
            {"id": "summary", "name": "Сводный отчет", "format": "json"},
            {"id": "competitors", "name": "Анализ конкурентов", "format": "json"},
            {"id": "pricing", "name": "Анализ ценообразования", "format": "json"}
        ]
    }


@router.post("/generate")
async def generate_report(request: ReportRequest):
    """Генерация отчета"""
    try:
        # Генерация тестового отчета
        report_data = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "hotel_id": request.hotel_id,
            "period": {
                "start": request.period_start,
                "end": request.period_end
            },
            "generated_at": datetime.now().isoformat(),
            "data": {
                "revenue_summary": {
                    "total": 1250000,
                    "average_per_day": 45000,
                    "growth": 0.125
                },
                "occupancy": {
                    "average": 0.78,
                    "best_day": "2024-01-15",
                    "worst_day": "2024-01-10"
                },
                "competitors": {
                    "count": 12,
                    "average_price": 5200,
                    "our_position": 3
                }
            },
            "recommendations": [
                "Рассмотрите повышение цены на выходные",
                "Добавьте пакетные предложения",
                "Мониторьте акции конкурентов"
            ]
        }

        if request.format == "json":
            return report_data
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Format {request.format} not supported yet. Use 'json'"
            )

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard(hotel_id: str):
    """Дашборд с аналитикой"""
    return {
        "hotel_id": hotel_id,
        "metrics": {
            "current_price": 5500,
            "market_average": 5200,
            "occupancy_rate": 0.78,
            "revenue_today": 125000,
            "competitors_monitored": 12
        },
        "charts": {
            "price_trend": "https://via.placeholder.com/600x300.png?text=Price+Trend",
            "occupancy_chart": "https://via.placeholder.com/600x300.png?text=Occupancy+Chart"
        }
    }