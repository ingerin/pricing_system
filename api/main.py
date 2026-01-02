from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
    return {"message": "Hotel Dynamic Pricing API", "status": "operational"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Подключаем другие модули
from api.competitors import router as competitors_router
from api.pricing import router as pricing_router
from api.reports import router as reports_router

app.include_router(competitors_router, prefix="/api/competitors", tags=["competitors"])
app.include_router(pricing_router, prefix="/api/pricing", tags=["pricing"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])