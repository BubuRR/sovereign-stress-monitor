# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — INTERACTIVE DASHBOARD v29.0
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# ======================================================================

import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import plotly.express as px

st.set_page_config(page_title="Sovereign Stress Monitor v29.0", layout="wide", page_icon="🦅")

st.title("🦅 Sovereign Stress Monitor (SSM) — Предиктивная Панель Триажа Рисков")
st.markdown("### Разработчик: Architect Odin | Личный токен: `TOKEN_F5B2C8E4A1D7396F`")
st.write("---")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "core", "ssm_intelligence.db")
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")

def load_historical_data_from_sqlite():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT timestamp, country, risk_pct, status_level AS status FROM historical_stress ORDER BY timestamp ASC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

if os.path.exists(REPORT_PATH):
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            unified_data = json.load(f)
            
        st.sidebar.markdown(f"### 📡 Последнее обновление (UTC):\n`{unified_data.get('TIMESTAMP_UTC', 'Н/Д')}`")
        
        weights = unified_data.get("WEIGHTS", {})
        st.sidebar.markdown("### 📊 Матрица оптимизации Юдена:")
        for k, v in weights.items():
            st.sidebar.write(f"**{k}:** `{v}`")
            
        st.subheader("🔮 Предиктивный градиент ИИ-прогнозов вероятности краха (Опережение 7 дней)")
        feeds = unified_data.get("DATA_DYNAMIC_FEEDS", [])
        
        if feeds:
            df_countries = pd.DataFrame(feeds)
            
            # 📈 ГРАФИК 1: Показываем вероятность излома, рассчитанную RandomForest
            fig_bar = px.bar(
                df_countries, x='COUNTRY', y='AI_CRASH_PROBABILITY_PCT', color='AI_CRASH_PROBABILITY_PCT', text='AI_CRASH_PROBABILITY_PCT',
                color_continuous_scale=px.colors.sequential.OrRd,
                labels={'AI_CRASH_PROBABILITY_PCT': 'Вероятность Краха % (ИИ Прогноз)', 'COUNTRY': 'Региональный контур'},
                title="Опережающий ИИ-анализ каскадных сдвигов рынков"
            )
            fig_bar.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("#### 📋 Журнал параметров и индекс ФРС США (GPR):")
            st.dataframe(df_countries[['COUNTRY', 'RISK_PCT', 'AI_CRASH_PROBABILITY_PCT', 'STATUS', 'FED_GPR_INDEX', 'SMH', 'DBB', 'USDT_MEDIAN']], use_container_width=True)
    except Exception as e:
        st.sidebar.error(f"Ошибка парсинга паспорта рисков: {e}")
else:
    st.info("💡 Ожидание генерации отчетов ИИ-ядра...")

df_hist = load_historical_data_from_sqlite()
if not df_hist.empty and len(df_hist) > 1:
    st.write("---")
    st.subheader("📉 Временная шкала макро-стресса")
    df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
    
    fig_line = px.line(
        df_hist, x='timestamp', y='risk_pct', color='country', markers=True,
        title="Динамика адаптации контуров (Прямой лог из СУБД SQLite)"
    )
    st.plotly_chart(fig_line, use_container_width=True)
