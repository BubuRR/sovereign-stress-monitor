# ======================================================================
# SSM — FastAPI gateway
# ======================================================================
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.database import SovereignStressDB
import os
import json
import sys

app = FastAPI(
    title="Sovereign Stress Monitor API",
    description="Research regime / stress passport API (experimental)",
    version="30.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(BASE_DIR, "ssm_unified_report.json")

try:
    db_instance = SovereignStressDB()
except Exception as e:
    print(f"[FATAL API] DB unavailable: {e}", file=sys.stderr)
    db_instance = None


@app.get("/")
def read_root():
    return {
        "status": "ONLINE",
        "platform": "Sovereign Stress Monitor",
        "version": "30.0",
        "disclaimer": "Experimental research tool. Not investment advice.",
    }


@app.get("/api/v1/radar/composite")
def get_composite_radar_passport():
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(
            status_code=404,
            detail="Report not found. Run: python ssm_core.py",
        )
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/risk/{country_code}")
def get_country_historical_records(country_code: str, limit: int = 100):
    code = country_code.upper().strip()
    if not db_instance:
        raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        logs = db_instance.fetch_historical_matrix(country=code, limit=limit)
        if not logs:
            raise HTTPException(
                status_code=404,
                detail=f"No history for {code}. Run python ssm_core.py first.",
            )
        return {
            "COUNTRY": code,
            "RECORDS_COUNT": len(logs),
            "DATA": logs,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
