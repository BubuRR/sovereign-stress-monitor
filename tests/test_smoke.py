import os, json, ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_syntax():
    for rel in ["core/quant_engine.py", "core/ground_feeds.py", "core/database.py"]:
        ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())

def test_config_five_ground():
    cfg = json.load(open(os.path.join(ROOT, "config/parameters.json")))
    gs = cfg["GROUND_SIGNALS"]
    for k in ["conflict", "food", "migration", "mortality", "physical"]:
        assert k in gs

def test_structural_and_gap_logic():
    from core.quant_engine import SovereignGlobalMonitorCore
    c = object.__new__(SovereignGlobalMonitorCore)
    c.mix = {"alpha_fiscal": 0.5, "beta_demographic": 0.35, "gamma_buffer": 0.15}
    c.defaults = {
        "STRUCTURAL_LAMBDA": 2.5,
        "CHRONIC_CRITICAL_S": 0.75,
        "CHRONIC_WATCH_S": 0.45,
        "GAP_ALARM_THRESHOLD": 0.25,
        "ASSUMED_DIGITAL_COVERAGE": 0.45,
    }
    c.composite_mode = "max"
    S = SovereignGlobalMonitorCore._structural_S(
        c, {"fiscal_pressure": 0.515, "demographic_squeeze": 0.28, "buffer_gap": 0.15}
    )
    assert S > 0.55
    gap = SovereignGlobalMonitorCore._gap_and_alarms(c, G=0.40, S=0.70, ground=0.80)
    assert gap["GAP_SCORE"] > 25
    assert gap["ALARM_ACTIVE"]
    assert "GROUND_DIVERGENCE" in gap["ALARM_CODES"] or "NARRATIVE_LAG" in gap["ALARM_CODES"]

def test_db(tmp_path):
    from core.database import SovereignStressDB
    db = SovereignStressDB(db_name=str(tmp_path / "t.db"))
    assert db.write_triage_log("UA", 70, "CRITICAL", 1, 1, 1, 0.4, 0.7, 0.8, 0.3)
    assert db.fetch_historical_matrix("UA")
