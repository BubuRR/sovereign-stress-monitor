# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — ENTERPRISE SaaS BACKEND (main.py)
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Version:   29.2 (FastAPI Distribution Gateway + Live Backtester API)
# ======================================================================

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from core.database import SovereignStressDB
from core.backtester import SovereignAIBacktester
import os
import json
import sys

app = FastAPI(
    title="Sovereign Stress Monitor (SSM) Enterprise API",
    description="Промышленный асинхронный шлюз макроэкономического триажа и ИИ-бэктестинга рисков",
    version="29.2"
)

# Асинхронный CORS-мост для защиты фронтенд-интерфейсов от блокировок браузерами
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определение абсолютной файловой структуры репозитория
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")

try:
    # Инициализация мостов к реляционным и аналитическим модулям Слоя В
    db_instance = SovereignStressDB()
    backtester_instance = SovereignAIBacktester()
except Exception as e:
    print(f"[FATAL API] Критический сбой инициализации инфраструктурных мостов: {e}", file=sys.stderr)
    db_instance = None
    backtester_instance = None

@app.get("/")
def read_root():
    """Эндпоинт верификации статуса и рантайм-чистоты сервера."""
    return {
        "status": "ONLINE",
        "platform": "Sovereign Stress Monitor (SSM)",
        "version": "29.2",
        "architect_token": "TOKEN_F5B2C8E4A1D7396F",
        "environment": "Production Predictive Monolith"
    }

@app.get("/api/v1/radar/composite")
def get_composite_radar_passport():
    """
    [TOWNSEND BROADCAST METHOD]
    Возвращает сквозной глобальный паспорт рисков из ssm_unified_report.json,
    содержащий ИИ-вероятности краха контуров.
    """
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(
            status_code=404, 
            detail="Глобальный паспорт рисков ssm_unified_report.json еще не сформирован предиктивным ядром."
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

@app.get("/api/v1/backtest/{country_code}")
def get_automated_ai_backtest_matrix(
    country_code: str, 
    threshold: float = Query(70.0, description="Порог отсечения для фиксации сигнала паники (CRITICAL)")
):
    """
    [AUTOMATED QUANT VALIDATION]
    Запускает движок бэктестинга по накопленным логам СУБД SQLite.
    Вычисляет Confusion Matrix, точную чувствительность и Индекс Юдена.
    """
    code = country_code.upper().strip()
    if not backtester_instance:
        raise HTTPException(
            status_code=500, 
            detail="Комплаенс-блок: Движок бэктестинга когнитивной матрицы недоступен."
        )

    try:
        # Прямой вызов математического метода валидации из core/backtester.py
        result = backtester_instance.execute_validation_matrix(target_country=code, alert_threshold=threshold)
        
        if result.get("status") == "ERROR":
            raise HTTPException(status_code=404, detail=result.get("detail"))
        elif result.get("status") == "INSUFFICIENT_DATA":
            raise HTTPException(status_code=422, detail=result.get("detail"))
        elif result.get("status") == "FATAL_CRASH":
            raise HTTPException(status_code=500, detail=result.get("detail"))
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Фатальный сбой обработки предиктивной матрицы ИИ: {str(e)}"
        )
