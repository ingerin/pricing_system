from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib import colors
import base64
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ReportRequest(BaseModel):
    hotel_id: str
    period_start: str
    period_end: str
    report_type: str = "pricing_analysis"
    include_charts: bool = True
    language: str = "ru"


@router.post("/generate")
async def generate_report(request: ReportRequest):
    """
    Генерация PDF отчета с анализом ценообразования
    """
    try:
        # Сбор данных для отчета
        report_data = await collect_report_data(
            request.hotel_id,
            request.period_start,
            request.period_end
        )

        # Генерация PDF
        if request.report_type == "pricing_analysis":
            pdf_content = await generate_pricing_pdf(
                report_data,
                request.include_charts,
                request.language
            )
        elif request.report_type == "competitor_analysis":
            pdf_content = await generate_competitor_pdf(
                report_data,
                request.include_charts
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown report type")

        # Возврат PDF
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{request.hotel_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_report_dashboard(
        hotel_id: str,
        period_days: int = 30
):
    """
    Веб-дашборд с отчетностью
    """
    try:
        # Сбор данных
        data = await collect_dashboard_data(hotel_id, period_days)

        # Генерация графиков
        charts = await generate_dashboard_charts(data)

        return {
            "hotel_id": hotel_id,
            "period": f"last_{period_days}_days",
            "summary": data.get("summary", {}),
            "charts": charts,
            "recommendations": data.get("recommendations", []),
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def collect_report_data(hotel_id, period_start, period_end):
    """
    Сбор данных для отчета
    """
    # Здесь должна быть реальная логика сбора данных
    # Пока возвращаем тестовые данные

    return {
        "hotel_info": {
            "id": hotel_id,
            "name": "Luxury Hotel Moscow",
            "location": "Moscow, City Center",
            "category": "4-star",
            "rooms": 150
        },
        "period": {
            "start": period_start,
            "end": period_end
        },
        "pricing_data": {
            "average_price": 5500,
            "min_price": 4500,
            "max_price": 7500,
            "occupancy_rate": 0.78,
            "revenue": 12500000
        },
        "competitor_data": {
            "total_competitors": 12,
            "average_market_price": 5200,
            "market_share": 0.15,
            "position": 3
        },
        "recommendations": [
            "Increase prices on weekends by 15%",
            "Add package deals for business travelers",
            "Monitor competitor X special offers"
        ]
    }


async def generate_pricing_pdf(data, include_charts, language="ru"):
    """
    Генерация PDF отчета по ценообразованию
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []

    styles = getSampleStyleSheet()

    # Стили
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#2c3e50')
    )

    normal_style = styles['Normal']

    # Заголовок
    story.append(Paragraph("Отчет по ценообразованию", title_style))
    story.append(Spacer(1, 20))

    # Информация об отеле
    story.append(Paragraph("Информация об отеле", heading_style))
    hotel_info = data["hotel_info"]
    story.append(Paragraph(f"Отель: {hotel_info['name']}", normal_style))
    story.append(Paragraph(f"Локация: {hotel_info['location']}", normal_style))
    story.append(Paragraph(f"Категория: {hotel_info['category']}", normal_style))
    story.append(Spacer(1, 15))

    # Период отчета
    story.append(Paragraph("Период анализа", heading_style))
    period = data["period"]
    story.append(Paragraph(f"С: {period['start']}", normal_style))
    story.append(Paragraph(f"По: {period['end']}", normal_style))
    story.append(Spacer(1, 15))

    # Данные по ценам
    story.append(Paragraph("Анализ цен", heading_style))
    pricing = data["pricing_data"]

    pricing_table_data = [
        ["Показатель", "Значение", "Изменение"],
        ["Средняя цена", f"{pricing['average_price']} RUB", "+5.2%"],
        ["Минимальная цена", f"{pricing['min_price']} RUB", "-2.1%"],
        ["Максимальная цена", f"{pricing['max_price']} RUB", "+8.7%"],
        ["Заполняемость", f"{pricing['occupancy_rate'] * 100:.1f}%", "+3.4%"],
        ["Выручка", f"{pricing['revenue']:,} RUB", "+12.5%"]
    ]

    pricing_table = Table(pricing_table_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
    pricing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(pricing_table)
    story.append(Spacer(1, 20))

    # Анализ конкурентов
    story.append(Paragraph("Рыночная позиция", heading_style))
    competitor_data = data["competitor_data"]

    comp_table_data = [
        ["Показатель", "Значение"],
        ["Всего конкурентов", competitor_data["total_competitors"]],
        ["Средняя рыночная цена", f"{competitor_data['average_market_price']} RUB"],
        ["Доля рынка", f"{competitor_data['market_share'] * 100:.1f}%"],
        ["Позиция на рынке", f"{competitor_data['position']} место"]
    ]

    comp_table = Table(comp_table_data, colWidths=[3 * inch, 2 * inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(comp_table)
    story.append(Spacer(1, 20))

    # Рекомендации
    story.append(Paragraph("Рекомендации", heading_style))
    for i, recommendation in enumerate(data["recommendations"], 1):
        story.append(Paragraph(f"{i}. {recommendation}", normal_style))
        story.append(Spacer(1, 5))

    # Время генерации
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        f"Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey)
    ))

    # Сборка PDF
    doc.build(story)
    buffer.seek(0)

    return buffer.getvalue()


async def generate_competitor_pdf(data, include_charts):
    """
    Генерация PDF отчета по конкурентам
    """
    # Аналогичная реализация для отчета по конкурентам
    pass


async def collect_dashboard_data(hotel_id, period_days):
    """
    Сбор данных для дашборда
    """
    # Реальная логика сбора данных
    return {
        "summary": {
            "revenue": {"current": 12500000, "change": 0.125},
            "occupancy": {"current": 0.78, "change": 0.034},
            "adr": {"current": 5500, "change": 0.052},
            "revpar": {"current": 4290, "change": 0.089}
        },
        "trends": {
            "prices": [5000, 5200, 4800, 5500, 5300, 5600, 5700],
            "occupancy": [0.7, 0.72, 0.68, 0.75, 0.78, 0.8, 0.76]
        },
        "recommendations": [
            "Optimize weekend pricing",
            "Add early booking discounts",
            "Monitor competitor promotions"
        ]
    }


async def generate_dashboard_charts(data):
    """
    Генерация графиков для дашборда
    """
    charts = {}

    # График динамики цен
    fig_prices = go.Figure()
    fig_prices.add_trace(go.Scatter(
        y=data["trends"]["prices"],
        mode='lines+markers',
        name='Средняя цена',
        line=dict(color='#3498db', width=3)
    ))
    fig_prices.update_layout(
        title="Динамика цен",
        xaxis_title="Дни",
        yaxis_title="Цена (RUB)",
        template="plotly_white"
    )

    charts["price_trend"] = pio.to_json(fig_prices)

    # График заполняемости
    fig_occupancy = go.Figure()
    fig_occupancy.add_trace(go.Bar(
        y=data["trends"]["occupancy"],
        name='Заполняемость',
        marker_color='#2ecc71'
    ))
    fig_occupancy.update_layout(
        title="Заполняемость номеров",
        xaxis_title="Дни",
        yaxis_title="Заполняемость (%)",
        yaxis_tickformat=".0%",
        template="plotly_white"
    )

    charts["occupancy_trend"] = pio.to_json(fig_occupancy)

    return charts