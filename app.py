# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — ENTERPRISE PRODUCTION DASHBOARD v29.2
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
#
# CLEAN READ-ONLY UI // ZERO INGESTION IMPACT // PLOTLY INTERACTIVE
# ======================================================================

import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# Настройка конфигурации страницы в стиле минимализма Кремниевой долины
st.set_page_config(page_title="SSM Predictive Radar v29.2", layout="wide", page_icon="🦅")

st.title("🦅 Sovereign Stress Monitor (SSM) — Глобальная Панель Триажа Рисков")
st.markdown("### Разработчик: Architect Odin | Суверенный токен: `TOKEN_F5B2C8E4A1D7396F`")
st.write("---")

# Определение абсолютных путей к изолированным слоям хранения данных
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "ssm_intelligence.db")
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")

def load_historical_time_series():
    """Безопасное Read-Only извлечение истории из СУБД без влияния на поток ядра."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT timestamp, country, risk_pct, status_level AS status 
            FROM historical_stress 
            ORDER BY timestamp ASC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# 📡 СЛОЙ ОТОБРАЖЕНИЯ ЖИВЫХ ПРОГНОЗОВ ИИ
if os.path.exists(REPORT_PATH):
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            unified_data = json.load(f)
            
        st.sidebar.markdown(f"### 📡 Последний тик (UTC):\n`{unified_data.get('TIMESTAMP_UTC', 'Н/Д')}`")
        
        # Вывод текущей активной матрицы весов Юдена
        weights = unified_data.get("WEIGHTS", {})
        st.sidebar.markdown("### 📊 Матрица Оптимизации Юдена:")
        for k, v in weights.items():
            st.sidebar.write(f"**{k}:** `{v}`")
            
        feeds = unified_data.get("DATA_DYNAMIC_FEEDS", [])
        if feeds:
            df_countries = pd.DataFrame(feeds)
            
            # РАЗДЕЛ А: ИНДИКАТОРЫ ВЫСШЕГО УРОВНЯ (МЕТРИКИ КРАХА ИИ)
            st.subheader("🔮 Опережающие ИИ-Прогнозы Вероятности Системных Сдвигов (7 дней)")
            
            # Выводим топ-контуры по уровню угрозы через удобные карточки (Metrics)
            cols = st.columns(len(df_countries))
            for idx, row in df_countries.iterrows():
                with cols[idx]:
                    country = row['COUNTRY']
                    prob = float(row['AI_CRASH_PROBABILITY_PCT'])
                    status = row['STATUS']
                    
                    # Цветовой маркер в зависимости от уровня угрозы
                    if status == "CRITICAL": delta_color = "inverse"
                    elif status == "ELEVATED": delta_color = "off"
                    else: delta_color = "normal"
                    
                    st.metric(
                        label=f"🌍 Контур {country}",
                        value=f"{prob}%",
                        delta=status,
                        delta_color=delta_color
                    )
            
            st.write("---")
            
            # 📈 ГРАФИК 1: Интерактивная тепловая гистограмма текущих рисков
            st.subheader("📊 Текущий градиент совокупного стресса по макро-рукавам")
            fig_bar = px.bar(
                df_countries, x='COUNTRY', y='RISK_PCT', color='RISK_PCT', text='RISK_PCT',
                color_continuous_scale=px.colors.sequential.OrRd,
                labels={'RISK_PCT': 'Индекс Совокупного Риска %', 'COUNTRY': 'Суверенная Зона'},
                template="plotly_dark"
            )
            fig_bar.update_layout(yaxis_range=[0, 100], height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Журнал параметров под графиком
            with st.expander("🔎 Просмотреть детальный лог текущих параметров фидов данных (Raw JSON-Feed)"):
                st.dataframe(df_countries[['COUNTRY', 'RISK_PCT', 'AI_CRASH_PROBABILITY_PCT', 'STATUS', 'FED_GPR_INDEX', 'SMH', 'DBB', 'USDT_MEDIAN', 'NETWORK']], use_container_width=True)

    except Exception as e:
        st.sidebar.error(f"Ошибка парсинга паспорта рисков: {e}")
else:
    st.info("💡 Ожидание генерации ssm_unified_report.json беспилотным предиктивным ядром...")

# 📉 СЛОЙ ОТОБРАЖЕНИЯ ИСТОРИЧЕСКИХ КРИВЫХ ИЗ СУБД SQLite
df_hist = load_historical_time_series()
if not df_hist.empty and len(df_hist) > 1:
    st.write("---")
    st.subheader("📉 Динамика излома макро-контуров во времени (Временные ряды СУБД)")
    df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
    
    fig_line = px.line(
        df_hist, x='timestamp', y='risk_pct', color='country', markers=True,
        labels={'risk_pct': 'Индекс Риска %', 'timestamp': 'Временная шкала UTC'},
        template="plotly_dark"
    )
    fig_line.update_layout(height=500)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.write("---")
    st.info("💡 Кривые таймлайна будут построены автоматически, как только СУБД SQLite накопит исторические тики от робота Actions.")
