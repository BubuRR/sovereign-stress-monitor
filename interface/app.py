# ======================================================================
# SSM — Streamlit dashboard
# ======================================================================
import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import plotly.express as px

st.set_page_config(
    page_title="SSM Regime Monitor v30",
    layout="wide",
    page_icon="📊",
)

st.title("Sovereign Stress Monitor — Regime panel")
st.caption(
    "Experimental research tool. Composite scores are heuristic — not investment advice."
)
st.write("---")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "ssm_intelligence.db")
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")


def load_historical_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            """
            SELECT timestamp, country, risk_pct, status_level AS status
            FROM historical_stress
            ORDER BY timestamp ASC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


if os.path.exists(REPORT_PATH):
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            unified = json.load(f)

        st.sidebar.markdown(
            f"**Last update (UTC)**  \n`{unified.get('TIMESTAMP_UTC', 'n/a')}`"
        )
        st.sidebar.markdown(f"**Version** `{unified.get('VERSION', 'n/a')}`")
        for k, v in unified.get("WEIGHTS", {}).items():
            st.sidebar.write(f"{k}: `{v}`")

        feeds = unified.get("DATA_DYNAMIC_FEEDS", [])
        if feeds:
            df = pd.DataFrame(feeds)
            st.subheader("Current composite by contour")
            fig = px.bar(
                df,
                x="COUNTRY",
                y="RISK_PCT",
                color="RISK_PCT",
                text="RISK_PCT",
                color_continuous_scale=px.colors.sequential.YlOrRd,
                title="Heuristic stress index (0–100)",
            )
            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

            cols = [
                c
                for c in [
                    "COUNTRY",
                    "RISK_PCT",
                    "STATUS",
                    "REGIME",
                    "SMH",
                    "DBB",
                    "USDT_MEDIAN",
                    "NETWORK",
                ]
                if c in df.columns
            ]
            st.dataframe(df[cols], use_container_width=True)
    except Exception as e:
        st.sidebar.error(f"Report parse error: {e}")
else:
    st.info("No report yet. Run: `python ssm_core.py`")

df_hist = load_historical_data()
if not df_hist.empty and len(df_hist) > 1:
    st.write("---")
    st.subheader("Historical series (SQLite)")
    df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
    fig2 = px.line(
        df_hist,
        x="timestamp",
        y="risk_pct",
        color="country",
        markers=True,
        title="Stored ticks",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.write("---")
    st.info("History charts appear after 2+ ticks are stored in SQLite.")
