# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — ENTERPRISE DASHBOARD v28.1
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# ======================================================================

import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="Sovereign Stress Monitor v28.1", layout="wide", page_icon="📊")

st.title("🦅 Sovereign Stress Monitor (SSM) — Глобальная Панель Триажа Рисков")
st.markdown("### Разработчик: Architect Odin | Личный токен: `TOKEN_F5B2C8E4A1D7396F`")
st.write("---")

# Контур считывания сквозного паспорта угроз, сгенерированного роботом Actions
report_file = "ssm_unified_report.json"
csv_file = "ssm_historical_database.csv"

if os.path.exists(report_file):
    with open(report_file, "r", encoding="utf-8") as f:
        unified_data = json.load(f)
        
    st.sidebar.markdown(f"### 📡 Последнее обновление (UTC):\n`{unified_data.get('TIMESTAMP_UTC', 'Н/Д')}`")
    
    # 📈 ГРАФИК 1: Интерактивная тепловая гистограмма текущих рисков планеты по Юдену
    st.subheader("🔮 Текущий градиент системного хаоса по суверенным зонам")
    countries_data = unified_data.get("DATA_DYNAMIC_FEEDS", [])
    
    if countries_data:
        df_countries = pd.DataFrame(countries_data)
        fig_bar = px.bar(
            df_countries, x='COUNTRY', y='RISK_PCT', color='RISK_PCT', text='RISK_PCT',
            color_continuous_scale=px.colors.sequential.YlOrRd,
            labels={'RISK_PCT': 'Индекс Риска %', 'COUNTRY': 'Региональный контур'},
            title="Сравнительный анализ уязвимости макро-контуров"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Вывод детальных метрик по клику
        st.markdown("#### 📋 Живые метрики по контурам:")
        st.dataframe(df_countries[['COUNTRY', 'RISK_PCT', 'STATUS', 'SMH', 'DBB', 'USDT_MEDIAN', 'NETWORK']], use_container_width=True)

# 📉 ГРАФИК 2: Хронологические кривые нарастания стресса из базы данных
if os.path.exists(csv_file) and os.path.getsize(csv_file) > 100:
    st.subheader("📉 Временная шкала нелинейного излома макро-контуров (Историческая СУБД)")
    df_hist = pd.read_csv(csv_file)
    df_hist['Timestamp'] = pd.to_datetime(df_hist['Timestamp'])
    
    fig_line = px.line(
        df_hist, x='Timestamp', y='Risk_Pct', color='Country', markers=True,
        title="Динамика адаптации и привыкания к кризису (Режим Anti-Baseline Drift)"
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("💡 Исторические кривые будут отрисованы автоматически, как только база данных Actions накопит более 2-х тиков.")
