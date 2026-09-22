# SSM Streamlit dashboard v32.4 — hybrid layers + optional narrative advisory
import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="SSM Hybrid Radar v32.4", layout="wide", page_icon="📡")
st.title("SSM — Sovereign Stress Monitor v32.4")
st.caption(
    "G = market/official · S = structural priors · Ground = land proxies · "
    "LAND = max(S, Ground) · GAP = divergence. Optional AI is advisory only — not investment advice."
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "ssm_unified_report.json")

if not os.path.exists(REPORT):
    st.warning("No report yet. Run: python ssm_core.py")
    st.stop()

with open(REPORT, encoding="utf-8") as f:
    data = json.load(f)

st.sidebar.markdown(f"**v{data.get('VERSION')}**")
st.sidebar.write(data.get("TIMESTAMP_UTC", ""))
st.sidebar.write(f"AI_MODE: **{data.get('AI_MODE', 'off')}**")

feeds = data.get("DATA_DYNAMIC_FEEDS") or []
if not feeds:
    st.info("Empty feeds.")
    st.stop()

rows = []
for f in feeds:
    rows.append(
        {
            "COUNTRY": f.get("COUNTRY"),
            "R": f.get("DISPLAY_SCORE"),
            "STATUS": f.get("STATUS"),
            "G": (f.get("OFFICIAL") or {}).get("GLOBAL_REGIME_SCORE"),
            "S": (f.get("STRUCTURAL") or {}).get("LOCAL_STRUCTURAL_SCORE"),
            "GROUND": (f.get("GROUND") or {}).get("GROUND_INDEX"),
            "LAND": (f.get("LAND") or {}).get("LAND_STRESS")
            or (f.get("COMPARISON") or {}).get("LAND_STRESS"),
            "GAP": (f.get("COMPARISON") or {}).get("GAP_SCORE"),
            "ALARMS": ", ".join((f.get("COMPARISON") or {}).get("ALARM_CODES") or []) or "—",
        }
    )
df = pd.DataFrame(rows)

# Metrics row
cols = st.columns(min(4, len(df)))
for i, r in df.iterrows():
    if i >= 4:
        break
    with cols[i]:
        st.metric(r["COUNTRY"], f"{r['R']}%", r["STATUS"])

c1, c2 = st.columns(2)
with c1:
    st.subheader("G vs LAND vs Ground")
    m = df.melt(
        id_vars=["COUNTRY"],
        value_vars=[c for c in ("G", "LAND", "GROUND") if c in df.columns],
        var_name="layer",
        value_name="score",
    )
    st.plotly_chart(
        px.bar(m, x="COUNTRY", y="score", color="layer", barmode="group", range_y=[0, 100]),
        use_container_width=True,
    )
with c2:
    st.subheader("GAP")
    st.plotly_chart(
        px.bar(df, x="COUNTRY", y="GAP", color="GAP", color_continuous_scale="Reds", range_y=[0, 100]),
        use_container_width=True,
    )

st.subheader("Passport")
st.dataframe(df, use_container_width=True)

pick = st.selectbox("Country detail", df["COUNTRY"].tolist())
detail = next(x for x in feeds if x.get("COUNTRY") == pick)
st.write((detail.get("GROUND") or {}).get("SIGNALS", {}))
alarms = (detail.get("COMPARISON") or {}).get("ALARM_CODES") or []
if alarms:
    st.error("ALARMS: " + ", ".join(alarms))
why = (detail.get("COMPARISON") or {}).get("WHY")
if why:
    st.info(why)

# --- AI / Narrative decompilation panel ---
st.divider()
st.subheader("AI Advisory / Narrative decompilation")
ai = data.get("AI_ADVISORY")
st.caption(
    "Optional LLM commentary. Does **not** change G/S/Ground/LAND/Gap. Not investment advice."
)
if not ai:
    st.info(
        "AI off or no key. Core radar is fine. "
        "Set OPENROUTER_API_KEY and AI_ADVISORY.enabled=true (see HOWTO-OPENROUTER.md)."
    )
elif isinstance(ai, dict) and ai.get("ai_narrative_brief"):
    lag = ai.get("narrative_lag_triggered")
    if lag or ai.get("status") == "NARRATIVE_LAG_DECOMPILED":
        st.error(
            "NARRATIVE_LAG pressure detected by math "
            f"(max GAP={ai.get('max_gap_observed')}, "
            f"threshold={ai.get('gap_threshold')}, "
            f"countries={ai.get('hot_countries')}). "
            "Text below is AI hypothesis only."
        )
    else:
        st.success(f"Routine brief (status={ai.get('status')})")
    st.markdown(ai["ai_narrative_brief"])
    st.caption(
        f"role={ai.get('role')} · provider={ai.get('provider')} · "
        f"model={ai.get('model')} · {ai.get('timestamp_utc')}"
    )
    st.caption(ai.get("disclaimer") or "")
else:
    st.warning(str(ai))
