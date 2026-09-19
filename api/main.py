# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — ENTERPRISE SaaS BACKEND main.py
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# ======================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import json

app = FastAPI(
    title="Sovereign Stress Monitor (SSM) Enterprise API",
    description="SaaS API для сквозного макроэкономического и ончейн-триажа рисков",
    version="28.1"
)

# Настройка CORS-защиты для беспрепятственного подключения Streamlit-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "ssm_intelligence.db")
REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ssm_unified_report.json")

@app.get("/")
def read_root():
    return {
        "status": "ONLINE",
        "project": "Sovereign Stress Monitor (SSM)",
        "version": "28.1",
        "architect_token": "TOKEN_F5B2C8E4A1D7396F"
    }

@app.get("/api/v1/radar/composite")
def get_composite_passport():
    """Возвращает сквозной глобальный паспорт рисков из JSON-файла."""
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(status_code=404, detail="Единый паспорт рисков еще не сгенерирован ядром.")
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения СУБД: {str(e)}")

@app.get("/api/v1/risk/{country_code}")
def get_country_historical_logs(country_code: str):
    """Извлекает из реляционной СУБД SQLite полную историю стресса по конкретной стране."""
    code = country_code.upper()
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Реляционная база данных SQLite ssm_intelligence.db не найдена.")
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, risk_pct, status, smh_price, dbb_price, usdt_median 
            FROM historical_stress 
            WHERE country = ? 
            ORDER BY timestamp DESC
        """, (code,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"Записи по контуру страны {code} в СУБД отсутствуют.")
            
        logs = []
        for r in rows:
            logs.append({
                "timestamp": r[0], "risk_percentage": r[1], "status_level": r[2],
                "metrics": {"smh_price": r[3], "dbb_price": r[4], "usdt_median": r[5]}
            })
        return {"country": code, "records_count": len(logs), "historical_logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренний сбой сервера СУБД: {str(e)}")
