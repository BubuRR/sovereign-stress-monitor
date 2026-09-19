# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — ENTERPRISE SaaS BACKEND (main.py)
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Version:   28.7 (Production FastAPI Distribution Gateway)
# ======================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.database import SovereignStressDB
import os
import json
import sys

app = FastAPI(
    title="Sovereign Stress Monitor (SSM) Enterprise API",
    description="Промышленный асинхронный шлюз макроэкономического и ончейн-триажа рисков",
    version="28.7"
)

# Жесткая CORS-защита для беспрепятственного подключения Streamlit-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определение абсолютных путей репозитория
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")

try:
    # Инициализация моста к реляционной базе данных из Слоя В
    db_instance = SovereignStressDB()
except Exception as e:
    print(f"[FATAL API] Не удалось подключить СУБД: {e}", file=sys.stderr)
    db_instance = None

@app.get("/")
def read_root():
    """Эндпоинт верификации статуса и рантайм-чистоты сервера."""
    return {
        "status": "ONLINE",
        "platform": "Sovereign Stress Monitor (SSM)",
        "version": "28.7",
        "architect_token": "TOKEN_F5B2C8E4A1D7396F",
        "environment": "Production Monolith"
    }

@app.get("/api/v1/radar/composite")
def get_composite_radar_passport():
    """
    [TOWNSEND BROADCAST METHOD]
    Возвращает сквозной глобальный паспорт рисков из ssm_unified_report.json,
    сгенерированный беспилотным роботом Actions.
    """
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(
            status_code=404, 
            detail="Глобальный паспорт рисков ssm_unified_report.json еще не сформирован ядром."
        )
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Внутренний сбой чтения глобального паспорта: {str(e)}"
        )

@app.get("/api/v1/risk/{country_code}")
def get_country_historical_records(country_code: str, limit: int = 100):
    """
    [RELATIONAL DATA EXTRACTION]
    Извлекает из СУБД SQLite чистую хронологическую матрицу по конкретной стране.
    """
    code = country_code.upper().strip()
    if not db_instance:
        raise HTTPException(
            status_code=500, 
            detail="Комплаенс-блок: Реляционная СУБД SQLite недоступна в рантайме."
        )
        
    try:
        # Прямой вызов защищенного метода чтения из базы core/database.py
        logs = db_instance.fetch_historical_matrix(country=code, limit=limit)
        
        if not logs:
            raise HTTPException(
                status_code=404, 
                detail=f"Исторические записи по контуру {code} в СУБД отсутствуют."
            )
            
        return {
            "HEADER": "SSM_REGIONAL_LOG_EXTRACT",
            "COUNTRY": code,
            "RECORDS_COUNT": len(logs),
            "DATA": logs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Критический сбой извлечения строк СУБД: {str(e)}"
        )
