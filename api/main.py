from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.database import SovereignStressDB
import os, json, sys

app = FastAPI(title="SSM Hybrid Ground API", version="30.5")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "ssm_unified_report.json")
try:
    db = SovereignStressDB()
except Exception as e:
    print(e, file=sys.stderr)
    db = None

@app.get("/")
def root():
    return {
        "status": "ONLINE",
        "version": "30.5",
        "layers": ["OFFICIAL(G)", "STRUCTURAL(S)", "GROUND(x5)", "GAP", "ALARMS"],
        "disclaimer": "Hybrid radar. Ground proxies + priors. Not investment advice.",
    }

@app.get("/api/v1/radar/composite")
def composite():
    if not os.path.exists(REPORT):
        raise HTTPException(404, "Run python ssm_core.py first")
    return json.load(open(REPORT, encoding="utf-8"))

@app.get("/api/v1/risk/{country_code}")
def risk(country_code: str, limit: int = 100):
    if not db:
        raise HTTPException(500, "DB down")
    logs = db.fetch_historical_matrix(country_code, limit)
    if not logs:
        raise HTTPException(404, "No history")
    return {"COUNTRY": country_code.upper(), "DATA": logs}
