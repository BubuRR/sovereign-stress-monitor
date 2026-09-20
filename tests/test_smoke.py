"""Smoke tests — run from project root: pytest -q"""
import os
import json
import ast
import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_quant_engine_syntax():
    path = os.path.join(ROOT, "core", "quant_engine.py")
    src = open(path, encoding="utf-8").read()
    ast.parse(src)
    assert "async def run_all" in src
    assert "async def execute_monitoring_cycle" in src


def test_database_roundtrip(tmp_path, monkeypatch):
    # Point DB to temp dir by patching after import is tricky; use isolated name
    import core.database as dbmod

    db = dbmod.SovereignStressDB(db_name=str(tmp_path / "test.db"))
    ok = db.write_triage_log("US", 61.5, "ELEVATED", 500.0, 25.0, 1000.0)
    assert ok is True
    rows = db.fetch_historical_matrix("US", limit=5)
    assert len(rows) >= 1
    assert rows[0]["status_level"] == "ELEVATED"
    assert rows[0]["risk_pct"] == 61.5


def test_parameters_json():
    path = os.path.join(ROOT, "config", "parameters.json")
    cfg = json.load(open(path, encoding="utf-8"))
    assert "WEIGHTS" in cfg
    assert "COUNTRY_PROFILES" in cfg
    assert "US" in cfg["COUNTRY_PROFILES"]


def test_import_run_all():
    from core.quant_engine import run_all, SovereignGlobalMonitorCore

    assert callable(run_all)
    assert SovereignGlobalMonitorCore is not None
