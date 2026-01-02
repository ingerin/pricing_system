import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime, timedelta
import json

# Конфигурация страницы
st.set_page_config(
    page_title="Hotel Pricing Dashboard",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .positive {
        color: #27ae60;
    }
    .negative {
        color: #e74c3c;
    }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.markdown('<h1 class="main-header">🏨 Система динамического ценообразования</h1>', unsafe_allow_html=True)

# Боковая панель
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2204/2204714.png", width=100)
    st.title("Настройки")

    hotel_id = st.selectbox(
        "Выберите отель",
        ["hotel_moscow_001", "hotel_spb_002", "hotel_sochi_003"]
    )

    report_period = st.selectbox(
        "Период анализа",
        ["7 дней", "30 дней", "90 дней", "Произвольный"]
    )

    if report_period == "Произвольный":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Начало", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Конец", datetime.now())

    st.divider()

    if st.button("🔄 Обновить данные", use_container_width=True):
        st.rerun()

# Основные метрики
st.subheader("📊 Ключевые показатели")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <h3>Средняя цена</h3>
        <h2>5,500 ₽</h2>
        <span class="positive">▲ 5.2%</span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <h3>Заполняемость</h3>
        <h2>78%</h2>
        <span class="positive">▲ 3.4%</span>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <h3>Выручка</h3>
        <h2>12.5M ₽</h2>
        <span class="positive">▲ 12.5%</span>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <h3>Доля рынка</h3>
        <h2>15.2%</h2>
        <span class="negative">▼ 0.8%</span>
    </div>
    """, unsafe_allow_html=True)

# Вкладки
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Ценообразование",
    "🏆 Конкуренты",
    "📋 Отчеты",
    "⚙️ Настройки"
])

with tab1:
    st.header("Анализ цен")

    col1, col2 = st.columns([2, 1])

    with col1:
        # График динамики цен
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.date_range(start='2024-01-01', periods=30, freq='D'),
            y=[5000, 5200, 4800, 5500, 5300, 5600, 5700] * 4 + [5500, 5200],
            mode='lines+markers',
            name='Наша цена',
            line=dict(color='#3498db', width=3)
        ))
        fig.add_trace(go.Scatter(
            x=pd.date_range(start='2024-01-01', periods=30, freq='D'),
            y=[4800, 5000, 4700, 5200, 5100, 5400, 5500] * 4 + [5300, 5000],
            mode='lines',
            name='Средняя по рынку',
            line=dict(color='#95a5a6', width=2, dash='dash')
        ))

        fig.update_layout(
            title="Динамика цен за 30 дней",
            xaxis_title="Дата",
            yaxis_title="Цена (RUB)",
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Калькулятор цены")

        base_price = st.number_input("Базовая цена", value=5000, step=100)
        season = st.selectbox("Сезон", ["Низкий", "Средний", "Высокий", "Пиковый"])
        occupancy = st.slider("Заполняемость", 0.0, 1.0, 0.78)
        strategy = st.selectbox("Стратегия",
                                ["Агрессивная", "Умеренная", "Консервативная", "Премиальная"])

        if st.button("Рассчитать", use_container_width=True):
            # Здесь будет вызов API
            st.success(f"Рекомендуемая цена: **6,200 ₽**")

            with st.expander("Детали расчета"):
                st.write("""
                - Базовая цена: 5,000 ₽
                - Коэффициент сезона: 1.3x
                - Коэффициент заполняемости: 1.1x
                - Стратегия: 1.15x
                - Итого: 5,000 × 1.3 × 1.1 × 1.15 = 6,197 ₽
                """)

with tab2:
    st.header("Анализ конкурентов")

    # Таблица конкурентов
    competitor_data = pd.DataFrame({
        "Отель": ["Luxury Hotel", "Business Inn", "City Center", "Comfort Stay", "Premium Suites"],
        "Цена": [6200, 4800, 5500, 5200, 7500],
        "Рейтинг": [4.8, 4.2, 4.5, 4.3, 4.9],
        "Отзывы": [1280, 560, 890, 670, 1500],
        "Заполняемость": [0.85, 0.72, 0.78, 0.75, 0.92]
    })

    st.dataframe(
        competitor_data,
        use_container_width=True,
        column_config={
            "Цена": st.column_config.NumberColumn(format="%d ₽"),
            "Рейтинг": st.column_config.NumberColumn(format="%.1f ⭐"),
            "Заполняемость": st.column_config.ProgressColumn(format="%.0f%%")
        }
    )

    # Рекомендации
    st.subheader("Рекомендации")
    st.info("""
    🎯 **Топ-3 рекомендации:**
    1. Снизить цену на 5% в будние дни для повышения конкурентоспособности
    2. Добавить пакет "Завтрак + парковка" за 800 ₽
    3. Мониторить акции конкурента "Business Inn"
    """)

with tab3:
    st.header("Генерация отчетов")

    col1, col2 = st.columns(2)

    with col1:
        st.selectbox("Тип отчета",
                     ["Анализ ценообразования", "Анализ конкурентов", "Финансовый отчет"])

        st.date_input("Начало периода", datetime.now() - timedelta(days=30))
        st.date_input("Конец периода", datetime.now())

        include_charts = st.checkbox("Включить графики", value=True)
        language = st.radio("Язык отчета", ["Русский", "Английский"])

    with col2:
        st.subheader("Предпросмотр")
        st.image("https://via.placeholder.com/400x500.png?text=PDF+Report+Preview",
                 caption="Предварительный просмотр отчета")

    if st.button("📥 Сгенерировать PDF отчет", use_container_width=True, type="primary"):
        # Здесь будет вызов API генерации PDF
        st.success("Отчет успешно сгенерирован!")
        st.download_button(
            label="Скачать отчет",
            data=open("sample_report.pdf", "rb").read() if os.path.exists("sample_report.pdf") else b"",
            file_name=f"report_{hotel_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

with tab4:
    st.header("Настройки системы")

    with st.form("settings_form"):
        st.subheader("Настройки ценообразования")

        col1, col2 = st.columns(2)

        with col1:
            min_price = st.number_input("Минимальная цена", value=3000, step=100)
            max_price = st.number_input("Максимальная цена", value=10000, step=100)
            price_step = st.number_input("Шаг изменения цены", value=100, step=10)

        with col2:
            update_frequency = st.selectbox(
                "Частота обновления цен",
                ["Каждый час", "Каждые 3 часа", "Каждые 6 часов", "Раз в день"]
            )
            auto_adjust = st.checkbox("Автоматическая корректировка цен", value=True)
            notifications = st.checkbox("Уведомления о изменениях", value=True)

        st.subheader("Источники данных")

        data_sources = st.multiselect(
            "Платформы для отслеживания",
            ["Booking.com", "Airbnb", "Ostrovok.ru", "TripAdvisor", "Яндекс.Путешествия"],
            default=["Booking.com", "Ostrovok.ru"]
        )

        st.subheader("Уведомления")

        email = st.text_input("Email для уведомлений", value="admin@hotel.com")
        telegram_token = st.text_input("Telegram Bot Token", type="password")

        submitted = st.form_submit_button("Сохранить настройки")

        if submitted:
            st.success("Настройки успешно сохранены!")

# Нижний колонтитул
st.divider()
st.caption(f"© 2024 Hotel Pricing System | Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")