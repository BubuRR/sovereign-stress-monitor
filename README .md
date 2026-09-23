# Sovereign Stress Monitor (SSM) v32.4 🛰️💼

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OSINT](https://img.shields.io/badge/Sector-Financial%20OSINT-orange.svg)](#-an-osint-approach-to-macro-risk)
[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-red.svg)](https://streamlit.io/)

**Release line: v32.4-SYNC** — Hybrid G/S/Ground/LAND Quantitative Risk & Early-Warning Framework.

> ⚠️ **Research Tool Notice:** This is an open-source macroeconomic stress radar designed for institutional research and risk modeling. This is **not investment advice** and is not a financial product.

---

## 📡 An OSINT Approach to Macro Risk

Traditional financial platforms often suffer from **Narrative Lag (NARRATIVE_LAG)** — a dangerous systemic blind spot where speculative stock markets trade at record highs on hype, entirely detached from raw material shortages, supply chain blockages, and geopolitical friction on the ground.

**Sovereign Stress Monitor (SSM)** bypasses official public relations and corporate spin by leveraging pure **OSINT (Open-Source Intelligence)** and **GEOINT (Geospatial Intelligence)** methodologies. It constantly confronts the official speculative market layer with real-time, unmanipulated physical ground-truth data.

---

## 🏗️ Core Architecture & Methodology

SSM processes data across distinct mathematical layers for each country profile:

*   **Official G (Market Regime):** Tracks official global market proxies, liquidity, and speculative tech equity layers (e.g., semiconductor index `SMH`, industrial metals `DBB`, USD-liquidity proxies).
*   **Structural S (Priors):** Versioned, deep macro structural pressures that markets tend to ignore over long horizons (fiscal deficits, systemic debt, catastrophic demographic decay).
*   **Ground (Live Proxies):** Active data slots evaluating five real-world signals: `conflict`, `food`, `migration`, `mortality`, and `physical` (via live geospatial supply-chain probes like `gdacs_probe`).
*   **LAND Layer:** Defined mathematically as:
    $$\text{LAND} = \max(\text{S}, \text{Ground})$$
    This enforces the true material and structural load, refusing to mask risks even if local equity markets look entirely calm.
*   **The GAP (Divergence Indicator):** The defining metric of the framework:
    $$\text{GAP} = \text{LAND} - \text{G}$$
    A high positive GAP explicitly signals a severe decoupling—where Wall Street is partying, but the physical foundations are cracking.
*   **Composite Risk (R):** The final aggregated safety score combining max-based math with non-linear ground friction escalations.

### 🤖 Optional AI Advisory Layer
Once the core mathematical matrices are sealed, SSM activates an optional **AI Advisory module (`core/ai_advisory.py`)** powered by **OpenRouter** or **Groq**. The LLM performs a cold narrative decompilation to translate index numbers into a pragmatic, cynical macro warning. **Crucial:** The AI layer acts strictly as a secondary consultant — it cannot alter the objective G, S, Land, or GAP scores.

---

## 📂 Project Layout

*   `ssm_core.py` — Application orchestration entry point.
*   `core/quant_engine.py` — Core mathematical engine & cross-layer divergence algorithms.
*   `core/ground_feeds.py` — Live OSINT automator, RSS connectors, and geospatial probe engines.
*   `core/ai_advisory.py` — LLM text-decoupling module (OpenRouter/Groq).
*   `core/database.py` — SQLite localized data persistence layer (`ssm_intelligence.db`).
*   `config/parameters.json` — Static calibration parameters, weight distribution, and structural priors.
*   `interface/app.py` — Interactive **Streamlit** user control panel.
*   `api/main.py` — Outbound headless **FastAPI** integration layer.

---

## 🚀 Quick Start (Windows Setup)

### Automated Launch (Recommended)
1. Ensure **Python 3.10+** is installed on your OS and checked with **"Add to PATH"**.
2. Clone or extract the project archive.
3. Double-click **`install.bat`** (downloads dependencies, sets up local SQLite storage).
4. Double-click **`start-simple.bat`** (launches the automated data collectors and UI).
5. Open your web browser and navigate to: **`http://localhost:8501`**

### Manual CLI Execution
```bash
# 1. Install required framework dependencies
python -m pip install -r requirements.txt

# 2. Run the quantitative database compilation
python ssm_core.py

# 3. Fire up the frontend dashboard
python -m streamlit run interface/app.py --server.port 8501
```
*No paid API keys are required for the hard baseline configuration (utilizes open web paths, public RSS feeds, and versioned parameters).*

---

## 🔑 Activating Advanced Live Upgrades

### 1. Live AI Advisor (Groq / OpenRouter)
To allow the AI advisor to decompile the narrative, supply your private environment keys:
1. Create a `.env` file in the root folder.
2. Provide your API secret:
   ```env
   OPENROUTER_API_KEY="your_openrouter_key_here"
   ```
3. Set `"enabled": true` under the `AI_ADVISORY` section inside `config/parameters.json`.

### 2. Live Ground Feeds (ACLED Research Upgrades)
To bypass static prior defaults (`prior_only`) for the live conflict tracking loops, insert your institutional ACLED research credentials into your local environment profile as specified in `HOWTO-OPENROUTER.md`.

---

## 🛠️ Calibration & Hard Baseline
To prevent the model from adapting to systemic decay over short rolling windows, SSM locks performance targets using fixed anchors (`HARD_BASELINE_SMH` / `HARD_BASELINE_DBB`) located in the global defaults. This ensures physical material deficits are weighed against absolute macro stability benchmarks rather than temporary market stabilization.

---
**Developed by BubuRR** | *Garbage in $\rightarrow$ garbage out. Know your metrics, monitor the GAP.*
