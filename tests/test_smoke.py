import os, json, ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_syntax():
    for rel in ["core/quant_engine.py", "core/ground_feeds.py", "core/database.py"]:
        ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())

def test_config_five_ground():
    cfg = json.load(open(os.path.join(ROOT, "config/parameters.json")))
    gs = cfg.get("GROUND_SIGNALS", {})
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

def test_ground_automator_without_keys():
    from core.ground_feeds import SovereignGroundAutomator
    import asyncio
    cfg = json.load(open(os.path.join(ROOT, "config/parameters.json")))
    eng = SovereignGroundAutomator(cfg)
    prior = cfg["LOCAL_PRIORS"]["UA"]
    pack = asyncio.get_event_loop().run_until_complete(eng.fetch_all("UA", prior))
    assert pack["GROUND_INDEX"] > 0.4  # must NOT collapse to 0 without keys
    assert pack["MODE"] in ("prior_baseline", "hybrid")

def test_db(tmp_path):
    from core.database import SovereignStressDB
    db = SovereignStressDB(db_name=str(tmp_path / "t.db"))
    assert db.write_triage_log("UA", 70, "CRITICAL", 1, 1, 1, 0.4, 0.7, 0.8, 0.3)
    assert db.fetch_historical_matrix("UA")


def test_ai_advisory_disabled_returns_none():
    from core.ai_advisory import SovereignAIAdvisory
    adv = SovereignAIAdvisory({"AI_ADVISORY": {"enabled": False}})
    assert adv.generate_brief({}) is None

def test_ai_advisory_enabled_without_key():
    from core.ai_advisory import SovereignAIAdvisory
    adv = SovereignAIAdvisory({
        "AI_ADVISORY": {"enabled": True},
        "ENTERPRISE_DATA_GATEWAYS": {"API_KEYS_VAULT": {"OPENAI_API_KEY": ""}},
    })
    out = adv.generate_brief({"DATA_DYNAMIC_FEEDS": []})
    assert out["status"] == "SKIPPED_NO_API_KEY"

def test_hard_baseline_land():
    from core.quant_engine import SovereignGlobalMonitorCore
    c = object.__new__(SovereignGlobalMonitorCore)
    c.defaults = {
        "HARD_BASELINE_SMH": 280.0, "HARD_BASELINE_DBB": 16.5, "DEFICIT_SOFT_CAP": 1.5,
        "LAND_CRITICAL": 0.7, "LAND_WATCH": 0.45, "GAP_ALARM_THRESHOLD": 0.25,
        "ASSUMED_DIGITAL_COVERAGE": 0.45, "CHRONIC_CRITICAL_S": 0.75, "CHRONIC_WATCH_S": 0.45,
    }
    phys = SovereignGlobalMonitorCore._hard_baseline_deficits(c, 590.0, 26.0)
    assert phys["MATERIALS_PHYSICAL_DEFICIT"] > 0.3
    land = SovereignGlobalMonitorCore._land_stress(c, 0.61, 0.64)
    assert abs(land - 0.64) < 1e-9


def test_groq_preset_defaults():
    from core.ai_advisory import SovereignAIAdvisory, PROVIDER_PRESETS
    assert "groq" in PROVIDER_PRESETS
    adv = SovereignAIAdvisory({"AI_ADVISORY": {"enabled": True, "provider": "groq"}})
    assert "groq.com" in adv.endpoint
    out = adv.generate_brief({"DATA_DYNAMIC_FEEDS": []})
    assert out["status"] == "SKIPPED_NO_API_KEY"
