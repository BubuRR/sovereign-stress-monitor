import streamlit as st
import pandas as pd
import json, os, sqlite3
import plotly.express as px

st.set_page_config(page_title="SSM v30.5 Hybrid", layout="wide", page_icon="📡")
st.title("SSM v30.5 — Official vs Ground (hybrid radar)")
st.caption(
    "See official/market (G), structural (S) and five ground signals side by side. "
    "GAP = when markets look calm while land/structural load is high. Not investment advice."
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB, REPORT = os.path.join(ROOT, "ssm_intelligence.db"), os.path.join(ROOT, "ssm_unified_report.json")

if os.path.exists(REPORT):
    data = json.load(open(REPORT, encoding="utf-8"))
    st.sidebar.write(f"**v{data.get('VERSION')}** | `{data.get('TIMESTAMP_UTC')}`")
    st.sidebar.write(f"Digital coverage assumption: **{data.get('ASSUMED_DIGITAL_COVERAGE')}**")
    feeds = data.get("DATA_DYNAMIC_FEEDS", [])
    if feeds:
        rows = []
        for f in feeds:
            rows.append({
                "COUNTRY": f["COUNTRY"],
                "DISPLAY": f["DISPLAY_SCORE"],
                "G_official": f["OFFICIAL"]["GLOBAL_REGIME_SCORE"],
                "S_structural": f["STRUCTURAL"]["LOCAL_STRUCTURAL_SCORE"],
                "GROUND": f["GROUND"]["GROUND_INDEX"],
                "GAP": f["COMPARISON"]["GAP_SCORE"],
                "STATUS": f["STATUS"],
                "ALARMS": ", ".join(f["COMPARISON"]["ALARM_CODES"]) or "—",
            })
        df = pd.DataFrame(rows)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Official G vs Ground index")
            m = df.melt(id_vars=["COUNTRY"], value_vars=["G_official", "GROUND"], var_name="layer", value_name="score")
            st.plotly_chart(px.bar(m, x="COUNTRY", y="score", color="layer", barmode="group", range_y=[0, 100]), use_container_width=True)
        with c2:
            st.subheader("GAP (alternative − official)")
            st.plotly_chart(px.bar(df, x="COUNTRY", y="GAP", color="GAP", color_continuous_scale="Reds", range_y=[0, 100]), use_container_width=True)
        st.subheader("Passport table")
        st.dataframe(df, use_container_width=True)
        # expand one country ground detail
        pick = st.selectbox("Ground signals detail", df["COUNTRY"].tolist())
        detail = next(x for x in feeds if x["COUNTRY"] == pick)
        gsig = detail["GROUND"]["SIGNALS"]
        st.write({k: v for k, v in gsig.items()})
        if detail["COMPARISON"]["ALARM_ACTIVE"]:
            st.error("ALARMS: " + ", ".join(detail["COMPARISON"]["ALARM_CODES"]))
        st.info(detail["COMPARISON"]["WHY"])
else:
    st.info("Run: python ssm_core.py")
