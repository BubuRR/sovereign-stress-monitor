# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — INTERACTIVE DASHBOARD (app.py)
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Version:   28.4 (Production Streamlit Visualization Node)
# ======================================================================

import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import plotly.express as px

st.set_page_config(
    page_title="Sovereign Stress Monitor v28.4", layout="wide", page_icon="📊"
)

st.title("🦅 Sovereign Stress Monitor (SSM) — Панель Триажа Рисков")
st.markdown("### Разработчик: Architect Odin | Личный токен: `TOKEN_F5B2C8E4A1D7396F`")
st.write("---")

# Absolute paths: DB lives in project root (same place database.py creates it)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "ssm_intelligence.db")
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")


def load_historical_data_from_sqlite():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        # Match table & column names from core/database.py
        df = pd.read_sql_query(
            "SELECT timestamp, country, risk_pct, status_level AS status "
            "FROM historical_stress ORDER BY timestamp ASC",
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# 🏛️ UPPER LAYER: live composite passport
if os.path.exists(REPORT_PATH):
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            unified_data = json.load(f)

        st.sidebar.markdown(
            f"### 📡 Последнее обновление (UTC):\n`{unified_data.get('TIMESTAMP_UTC', 'Н/Д')}`"
        )

        weights = unified_data.get("WEIGHTS", {})
        st.sidebar.markdown("### 📊 Откалиброванные веса Юдена:")
        for k, v in weights.items():
            st.sidebar.write(f"**{k}:** `{v}`")

        st.subheader("🔮 Текущий градиент системного стресса по суверенным зонам")
        feeds = unified_data.get("DATA_DYNAMIC_FEEDS", [])

        if feeds:
            df_countries = pd.DataFrame(feeds)
            fig_bar = px.bar(
                df_countries,
                x="COUNTRY",
                y="RISK_PCT",
                color="RISK_PCT",
                text="RISK_PCT",
                color_continuous_scale=px.colors.sequential.YlOrRd,
                labels={"RISK_PCT": "Индекс Риска %", "COUNTRY": "Региональный контур"},
                title="Сравнительный анализ уязвимости макро-контуров",
            )
            fig_bar.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("#### 📋 Журнал текущих параметров:")
            cols = [
                c
                for c in [
                    "COUNTRY",
                    "RISK_PCT",
                    "STATUS",
                    "SMH",
                    "DBB",
                    "USDT_MEDIAN",
                    "NETWORK",
                ]
                if c in df_countries.columns
            ]
            st.dataframe(df_countries[cols], use_container_width=True)
    except Exception as e:
        st.sidebar.error(f"Ошибка парсинга паспорта рисков: {e}")
else:
    st.info(
        "💡 Ожидание генерации ssm_unified_report.json беспилотным роботом Actions..."
    )

# 📉 Historical curves from SQLite
df_hist = load_historical_data_from_sqlite()
if not df_hist.empty and len(df_hist) > 1:
    st.write("---")
    st.subheader("📉 Временная шкала макро-стресса (Режим Anti-Baseline Drift)")
    df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])

    fig_line = px.line(
        df_hist,
        x="timestamp",
        y="risk_pct",
        color="country",
        markers=True,
        labels={"risk_pct": "Индекс Риска %", "timestamp": "Временная метка"},
        title="Динамика адаптации контуров (Прямой лог из СУБД SQLite)",
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.write("---")
    st.info(
        "💡 Кривые временных рядов будут построены автоматически, "
        "как только СУБД SQLite накопит более 2-х исторических тиков."
    )
