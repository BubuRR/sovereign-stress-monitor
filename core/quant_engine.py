# ======================================================================
# SSM — Regime / stress engine v30.0 (honest MVP)
# ======================================================================
# Focus: structural-break aware composite from public market + on-chain
# signals. Not a sovereign AI oracle. Not a substitute for Aladdin.
# ======================================================================

import asyncio
import math
import json
import datetime
import urllib.request
import os
import sys
import traceback
import numpy as np
try:
    import ruptures as rpt
    HAS_RUPTURES = True
except ImportError:
    rpt = None
    HAS_RUPTURES = False
import scipy.stats as stats
from core.database import SovereignStressDB


class RollingOnchainBuffer:
    def __init__(self, max_size=500):
        self.max_size = max_size
        self.buffer = []

    def extend(self, new_values):
        self.buffer.extend(new_values)
        if len(self.buffer) > self.max_size:
            self.buffer = self.buffer[-self.max_size:]

    def get_trimmed_rolling_median(self, default_value):
        if not self.buffer:
            return default_value
        s = sorted(self.buffer)
        cutoff = max(1, int(len(s) * 0.05))
        if len(s) > 20:
            s = s[cutoff:-cutoff]
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    def get_size(self):
        return len(self.buffer)


class SovereignGlobalMonitorCore:
    def __init__(self, config_path="config/parameters.json"):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(root, config_path)
        self.cache_stale_cycles = 0
        self.high_stress_duration = {}  # per country
        self.reference_mode = "normal"
        self.pre_crisis_smh = 550.0
        self.pre_crisis_dbb = 25.0

        self.db = SovereignStressDB()
        self.onchain_buffer = RollingOnchainBuffer(max_size=500)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.weights = self.config.get(
            "WEIGHTS",
            {"w_smh": 0.40, "w_metals": 0.30, "w_flow": 0.20, "w_fiscal": 0.10},
        )

    async def _fetch_data_stream(self, symbol, fallback_val):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        poly_key = vault.get("POLYGON_IO_KEY", "")

        if poly_key and "PASTE" not in poly_key.upper():
            base = self.config["ENTERPRISE_DATA_GATEWAYS"]["POLYGON_IO_MACRO_FEED"].rstrip("/")
            url = f"{base}/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={poly_key}"
        else:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                f"?interval=1d&range=3mo"
            )

        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 SSM/30.0"},
            )
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8.0).read()
            )
            data = json.loads(raw.decode())

            if "results" in data:
                return [float(x["c"]) for x in data["results"]]

            result_list = data.get("chart", {}).get("result", [])
            if not result_list:
                return [fallback_val] * 50
            closes = (
                result_list[0]
                .get("indicators", {})
                .get("quote", [{}])[0]
                .get("close", [])
            )
            closes = [c for c in closes if c is not None]
            return closes if closes else [fallback_val] * 50
        except Exception:
            return [fallback_val] * 50

    async def _fetch_tron_usdt_stream(self):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        qn_key = vault.get("QUICKNODE_TRON_KEY", "")
        usdt = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        if qn_key and "PASTE" not in qn_key.upper():
            base = self.config["ENTERPRISE_DATA_GATEWAYS"]["QUICKNODE_TRON_RPC"].rstrip("/")
            url = f"{base}/{qn_key}"
        else:
            url = (
                f"https://api.trongrid.io/v1/contracts/{usdt}/events"
                f"?event_name=Transfer&only_confirmed=true&limit=50"
            )

        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            )
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8.0).read()
            )
            data = json.loads(raw.decode())
            values = []

            for event in data.get("data", []):
                try:
                    result = event.get("result", {})
                    raw_val = (
                        result.get("value")
                        or result.get("_value")
                        or result.get("amount")
                    )
                    if raw_val is None:
                        continue
                    amt = float(raw_val) / 1e6
                    if amt >= 100.0:
                        values.append(amt)
                except Exception:
                    continue

            # Legacy hex path (if payload shape differs)
            if not values:
                for tx in data.get("data", []):
                    try:
                        contracts = tx.get("raw_data", {}).get("contract", [])
                        if not contracts or not isinstance(contracts, list):
                            continue
                        block = contracts[0].get("parameter", {}).get("value", {})
                        hex_data = block.get("data", "")
                        if (
                            isinstance(hex_data, str)
                            and hex_data.startswith("a9059cbb")
                            and len(hex_data) >= 136
                        ):
                            amt = int(hex_data[-64:], 16) / 1e6
                            if amt >= 100.0:
                                values.append(amt)
                    except Exception:
                        continue
            return values
        except Exception:
            return []

    def _detect_change_points(self, history_data):
        if len(history_data) < 24:
            return False
        try:
            signal = np.array(history_data, dtype=float)
            if HAS_RUPTURES:
                algo = rpt.Pelt(model="rbf").fit(signal)
                result = algo.predict(pen=3.0)
                if len(result) > 1 and (len(history_data) - result[-2]) <= 5:
                    return True
                return False
            # Fallback: large recent move vs earlier window std
            mid = len(signal) // 2
            mu, sd = float(np.mean(signal[:mid])), float(np.std(signal[:mid])) + 1e-9
            recent = float(np.mean(signal[-5:]))
            return abs(recent - mu) / sd > 2.5
        except Exception:
            return False

    def _compute_z_score_stress(self, current, history, mode):
        if len(history) < 15:
            base = sum(history) / len(history) if history else current
            if mode == "dd":
                return min(max((base - current) / max(base, 1e-9) * 4.0, 0.0), 1.0)
            return min(max((current - base) / max(base, 1e-9) * 5.0, 0.0), 1.0)
        mean = float(np.mean(history))
        std = float(np.std(history)) + 1e-9
        z = (current - mean) / std
        cdf = stats.norm.cdf(z)
        if mode == "dd":
            return float(round(1.0 - cdf, 4))
        return float(round(cdf, 4))

    async def execute_monitoring_cycle(self, country_code="US", past_risk=50.0):
        defaults = self.config["GLOBAL_DEFAULTS"]
        profile = self.config["COUNTRY_PROFILES"].get(
            country_code, self.config["COUNTRY_PROFILES"]["US"]
        )
        params = {**defaults, **profile}

        smh_pool = await self._fetch_data_stream("SMH", params["SMH_50D_AVERAGE_NORM"])
        dbb_pool = await self._fetch_data_stream("DBB", params["DBB_50D_AVERAGE_NORM"])
        txs = await self._fetch_tron_usdt_stream()

        if txs:
            self.onchain_buffer.extend(txs)
            self.cache_stale_cycles = 0
            network_log = "FEED_OK"
        else:
            network_log = "FEED_DEGRADED"
            if self.onchain_buffer.get_size() == 0:
                self.cache_stale_cycles += 1

        current_smh = smh_pool[-1] if smh_pool else params["SMH_50D_AVERAGE_NORM"]
        current_dbb = dbb_pool[-1] if dbb_pool else params["DBB_50D_AVERAGE_NORM"]
        usdt_med = self.onchain_buffer.get_trimmed_rolling_median(
            params["HISTORICAL_MEDIAN_USDT"]
        )

        smh_break = self._detect_change_points(smh_pool)
        dbb_break = self._detect_change_points(dbb_pool)

        code = country_code.upper()
        hs_dur = self.high_stress_duration.get(code, 0)

        # Anti-drift: freeze pre-crisis baseline when break detected
        if smh_break or dbb_break or hs_dur >= 3:
            if hs_dur == 0:
                self.pre_crisis_smh = (
                    float(np.mean(smh_pool[-50:])) if len(smh_pool) >= 50 else current_smh
                )
                self.pre_crisis_dbb = (
                    float(np.mean(dbb_pool[-50:])) if len(dbb_pool) >= 50 else current_dbb
                )
            self.reference_mode = "pre_crisis"
        else:
            self.reference_mode = "normal"

        active_smh = (
            [self.pre_crisis_smh] * 50 if self.reference_mode == "pre_crisis" else smh_pool
        )
        active_dbb = (
            [self.pre_crisis_dbb] * 50 if self.reference_mode == "pre_crisis" else dbb_pool
        )

        res_bubble = self._compute_z_score_stress(current_smh, active_smh, "dd")
        res_material = self._compute_z_score_stress(current_dbb, active_dbb, "spike")

        base_usdt = max(params["HISTORICAL_MEDIAN_USDT"], 1e-9)
        res_crypto = min(
            max(0.12 + ((usdt_med - base_usdt) / base_usdt) * 0.25, 0.0), 0.40
        )

        material_deficit = max((1.0 - res_material) - params["GARAGE_BUFFER"], 0.0)
        if material_deficit > 0.6:
            material_deficit *= 2.0

        w = self.weights
        core = (
            res_bubble * float(w["w_smh"])
            + material_deficit * float(w["w_metals"])
            + res_crypto * float(w["w_flow"])
            + float(params["FISCAL_PRESSURE"]) * float(w["w_fiscal"])
        )
        financial = core * (1.0 + params["BASE_BLIND_SPOT"])
        kinetic = (params.get("DEMOGRAPHIC_SHRINKAGE", 0.0) * 0.45) - (
            params["BIOLOGICAL_BUFFER"] * 0.30
        )

        total_stress = financial + max(kinetic, 0.0) * 1.2 + (past_risk / 100.0) * 0.15
        if self.cache_stale_cycles > 0:
            total_stress += round(0.4 * math.log(self.cache_stale_cycles + 1), 3)

        risk_pct = round(
            (1.0 / (1.0 + math.exp(-total_stress * params["SIGMOID_STEEPNESS"]))) * 100.0,
            2,
        )

        if risk_pct >= params["ALERT_THRESHOLD"]:
            status = "CRITICAL"
            self.high_stress_duration[code] = hs_dur + 1
        elif risk_pct >= params["ELEVATED_THRESHOLD"]:
            status = "ELEVATED"
            self.high_stress_duration[code] = 0
        else:
            status = "NORMAL"
            self.high_stress_duration[code] = 0

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        self.db.write_triage_log(
            country=code,
            risk_pct=risk_pct,
            status_level=status,
            smh_price=float(current_smh),
            dbb_price=float(current_dbb),
            usdt_median=float(usdt_med),
        )

        return {
            "COUNTRY": code,
            "TIMESTAMP_UTC": ts,
            "RISK_PCT": risk_pct,
            "STATUS": status,
            "REGIME": self.reference_mode,
            "SMH": round(float(current_smh), 2),
            "DBB": round(float(current_dbb), 2),
            "USDT_MEDIAN": round(float(usdt_med), 2),
            "NETWORK": network_log,
            "CHANGE_POINT_SMH": bool(smh_break),
            "CHANGE_POINT_DBB": bool(dbb_break),
            "DRIVERS": {
                "tech_stress": round(res_bubble, 4),
                "materials_deficit": round(material_deficit, 4),
                "stablecoin_flow": round(res_crypto, 4),
                "fiscal": round(float(params["FISCAL_PRESSURE"]), 4),
            },
        }


async def run_all():
    """Orchestrate one cycle for all configured countries; write JSON passport."""
    core = SovereignGlobalMonitorCore()
    countries = list(core.config.get("COUNTRY_PROFILES", {}).keys()) or [
        "US",
        "UA",
        "DE",
        "GB",
        "CN",
        "PL",
        "RU",
        "IL",
    ]

    feeds = []
    for code in countries:
        try:
            hist = core.db.fetch_historical_matrix(country=code, limit=1)
            past = hist[0]["risk_pct"] if hist else 50.0
            result = await core.execute_monitoring_cycle(country_code=code, past_risk=past)
            feeds.append(result)
            print(
                f"[SSM] {code}: {result['RISK_PCT']}% {result['STATUS']} "
                f"regime={result['REGIME']} net={result['NETWORK']}",
                flush=True,
            )
        except Exception as exc:
            print(f"[SSM ERROR] {code}: {exc}", file=sys.stderr)
            traceback.print_exc()

    report = {
        "HEADER": "SSM_REGIME_PASSPORT",
        "VERSION": "30.0",
        "DISCLAIMER": (
            "Experimental research tool. Not investment advice. "
            "Composite score is heuristic; validate before any decision use."
        ),
        "TIMESTAMP_UTC": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "WEIGHTS": core.weights,
        "DATA_DYNAMIC_FEEDS": feeds,
        "COUNTRIES_PROCESSED": len(feeds),
    }

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "ssm_unified_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[SSM] Report → {path}", flush=True)
    return report
