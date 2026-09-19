# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — PREDICTIVE ML ENGINE v29.1 FIXED
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
#
# INTEGRATED FED GPR PARSER // RANDOM FOREST PREDICTOR // DATASET SHIFT
# COMPLETED: execute_monitoring_cycle + run_all + fixed Yahoo/Tron URLs
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
import ruptures as rpt
import scipy.stats as stats
from sklearn.ensemble import RandomForestClassifier
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
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path
        )
        self.cache_stale_cycles = 0
        self.high_stress_duration = {}
        self.reference_mode = "normal"
        self.pre_crisis_smh = 550.0
        self.pre_crisis_dbb = 25.0

        self.db = SovereignStressDB()
        self.onchain_buffer = RollingOnchainBuffer(max_size=500)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.weights = self.config.get(
            "WEIGHTS",
            {"w_smh": 0.3913, "w_metals": 0.2609, "w_flow": 0.2174, "w_fiscal": 0.1304},
        )

        self.model = RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=42
        )
        self.model_trained = False

    async def _fetch_fed_gpr_index(self):
        """Async parser for geopolitical risk index (fallback-safe)."""
        url = self.config.get("MACRO_RESEARCH_FEEDS", {}).get(
            "FED_GPR_INDEX_URL", "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.csv"
        )
        # Prefer a known public CSV if config points to a non-data page
        if "geopoliticalriskindex.com" in url and "csv" not in url.lower():
            url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.csv"
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 SSMCore/29.1"},
            )
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8.0).read()
            )
            lines = raw.decode("utf-8", errors="ignore").split("\n")
            valid_raws = [l.split(",") for l in lines if l and "," in l]
            if len(valid_raws) > 1:
                last_row = valid_raws[-1]
                for cell in reversed(last_row):
                    try:
                        return float(cell.strip())
                    except ValueError:
                        continue
            return 100.0
        except Exception:
            return 100.0

    async def _fetch_data_stream(self, symbol, fallback_val):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        poly_key = vault.get("POLYGON_IO_KEY", "")

        if poly_key and "PASTE" not in poly_key:
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
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SSMCore/29.1"},
            )
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8.0).read()
            )
            data = json.loads(raw.decode())

            if "results" in data:
                return [float(x["c"]) for x in data["results"]]
            result_list = data.get("chart", {}).get("result", [])
            if not result_list or not isinstance(result_list, list):
                return [fallback_val] * 50
            result = result_list[0]
            closes = (
                result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            )
            closes = [c for c in closes if c is not None]
            return closes if closes else [fallback_val] * 50
        except Exception:
            return [fallback_val] * 50

    async def _fetch_tron_usdt_stream(self):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        qn_key = vault.get("QUICKNODE_TRON_KEY", "")
        usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        if qn_key and "PASTE" not in qn_key:
            base = self.config["ENTERPRISE_DATA_GATEWAYS"]["QUICKNODE_TRON_RPC"].rstrip("/")
            url = f"{base}/{qn_key}"
        else:
            url = (
                f"https://api.trongrid.io/v1/contracts/{usdt_contract}/events"
                f"?event_name=Transfer&only_confirmed=true&limit=50"
            )

        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                },
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

            if not values:
                for tx in data.get("data", []):
                    try:
                        contracts = tx.get("raw_data", {}).get("contract", [])
                        if not contracts or not isinstance(contracts, list):
                            continue
                        target_contract = contracts[0]
                        value_block = target_contract.get("parameter", {}).get("value", {})
                        hex_data = value_block.get("data", "")
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
            algo = rpt.Pelt(model="rbf").fit(signal)
            result = algo.predict(pen=3.0)
            if len(result) > 1 and (len(history_data) - result[-2]) <= 5:
                return True
            return False
        except Exception:
            return False

    def _train_prediction_engine(self, fed_gpr, current_smh, current_dbb, usdt_med):
        try:
            np.random.seed(42)
            n_samples = 200
            h_gpr = np.random.normal(fed_gpr, 20, n_samples)
            h_smh = np.random.normal(current_smh, 15, n_samples)
            h_dbb = np.random.normal(current_dbb, 2, n_samples)
            h_usdt = np.random.normal(usdt_med, max(usdt_med * 0.1, 1.0), n_samples)
            X_train = np.column_stack([h_gpr, h_smh, h_dbb, h_usdt])
            Y_train = np.zeros(n_samples)
            for i in range(n_samples):
                if (
                    h_gpr[i] > 180.0
                    or h_smh[i] < (current_smh * 0.92)
                    or h_usdt[i] < (usdt_med * 0.7)
                ):
                    Y_train[max(0, i - 7)] = 1
            self.model.fit(X_train, Y_train)
            self.model_trained = True
        except Exception:
            self.model_trained = False

    def _compute_z_score_stress(self, current, history, mode):
        if len(history) < 15:
            base = sum(history) / len(history) if history else current
            if mode == "dd":
                return min(max((base - current) / max(base, 1e-9) * 4.0, 0.0), 1.0)
            return min(max((current - base) / max(base, 1e-9) * 5.0, 0.0), 1.0)
        mean = np.mean(history)
        std = np.std(history) + 1e-9
        z_score = (current - mean) / std
        cdf_value = stats.norm.cdf(z_score)
        if mode == "dd":
            return float(round(1.0 - cdf_value, 4))
        return float(round(cdf_value, 4))

    async def execute_monitoring_cycle(self, country_code="US", past_risk=50.0):
        defaults = self.config["GLOBAL_DEFAULTS"]
        profile = self.config["COUNTRY_PROFILES"].get(
            country_code, self.config["COUNTRY_PROFILES"]["US"]
        )
        params = {**defaults, **profile}

        smh_pool = await self._fetch_data_stream("SMH", params["SMH_50D_AVERAGE_NORM"])
        dbb_pool = await self._fetch_data_stream("DBB", params["DBB_50D_AVERAGE_NORM"])
        txs = await self._fetch_tron_usdt_stream()
        fed_gpr = await self._fetch_fed_gpr_index()

        if txs:
            self.onchain_buffer.extend(txs)
            self.cache_stale_cycles = 0
            network_log = "COMMERCIAL_FEED_CONNECTED"
        else:
            network_log = "DEGRADED_FALLBACK_ACTIVE"
            if self.onchain_buffer.get_size() == 0:
                self.cache_stale_cycles += 1

        current_smh = smh_pool[-1] if smh_pool else params["SMH_50D_AVERAGE_NORM"]
        current_dbb = dbb_pool[-1] if dbb_pool else params["DBB_50D_AVERAGE_NORM"]
        usdt_med = self.onchain_buffer.get_trimmed_rolling_median(
            params["HISTORICAL_MEDIAN_USDT"]
        )

        if not self.model_trained:
            self._train_prediction_engine(fed_gpr, current_smh, current_dbb, usdt_med)

        ai_crash_prob = 0.0
        if self.model_trained:
            try:
                X_live = np.array([[fed_gpr, current_smh, current_dbb, usdt_med]])
                proba = self.model.predict_proba(X_live)[0]
                # class 1 = crash / structural break
                ai_crash_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])
            except Exception:
                ai_crash_prob = 0.0

        smh_break = self._detect_change_points(smh_pool)
        dbb_break = self._detect_change_points(dbb_pool)

        code = country_code.upper()
        hs_dur = self.high_stress_duration.get(code, 0)

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

        active_smh_history = (
            [self.pre_crisis_smh] * 50 if self.reference_mode == "pre_crisis" else smh_pool
        )
        active_dbb_history = (
            [self.pre_crisis_dbb] * 50 if self.reference_mode == "pre_crisis" else dbb_pool
        )

        res_bubble = self._compute_z_score_stress(current_smh, active_smh_history, "dd")
        res_material = self._compute_z_score_stress(
            current_dbb, active_dbb_history, "spike"
        )

        base_usdt = max(params["HISTORICAL_MEDIAN_USDT"], 1e-9)
        res_crypto = min(
            max(0.12 + ((usdt_med - base_usdt) / base_usdt) * 0.25, 0.0), 0.40
        )

        material_deficit = max((1.0 - res_material) - params["GARAGE_BUFFER"], 0.0)
        if material_deficit > 0.6:
            material_deficit *= 2.0

        fiscal = params["FISCAL_PRESSURE"]
        w = self.weights

        core = (
            res_bubble * float(w["w_smh"])
            + material_deficit * float(w["w_metals"])
            + res_crypto * float(w["w_flow"])
            + fiscal * float(w["w_fiscal"])
        )
        financial = core * (1.0 + params["BASE_BLIND_SPOT"])
        kinetic = (params.get("DEMOGRAPHIC_SHRINKAGE", 0.0) * 0.45) - (
            params["BIOLOGICAL_BUFFER"] * 0.30
        )

        # Blend classical stress with ML crash probability
        total_stress = (
            financial
            + max(kinetic, 0.0) * 1.2
            + (past_risk / 100.0) * 0.2
            + ai_crash_prob * 0.35
        )
        if self.cache_stale_cycles > 0:
            total_stress += round(0.4 * math.log(self.cache_stale_cycles + 1), 3)

        # Mild GPR contribution
        if fed_gpr > 150:
            total_stress += min((fed_gpr - 150) / 200.0, 0.25)

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
            country=country_code,
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
            "SMH": round(float(current_smh), 2),
            "DBB": round(float(current_dbb), 2),
            "USDT_MEDIAN": round(float(usdt_med), 2),
            "FED_GPR": round(float(fed_gpr), 2),
            "AI_CRASH_PROB": round(ai_crash_prob, 4),
            "NETWORK": network_log,
            "REFERENCE_MODE": self.reference_mode,
            "CHANGE_POINT_SMH": smh_break,
            "CHANGE_POINT_DBB": dbb_break,
        }


async def run_all():
    """Master entry-point for ssm_core.py and GitHub Actions."""
    core = SovereignGlobalMonitorCore()
    countries = list(core.config.get("COUNTRY_PROFILES", {}).keys())
    if not countries:
        countries = ["US", "UA", "DE", "GB", "CN", "PL", "RU", "IL"]

    feeds = []
    for code in countries:
        try:
            hist = core.db.fetch_historical_matrix(country=code, limit=1)
            past = hist[0]["risk_pct"] if hist else 50.0
            result = await core.execute_monitoring_cycle(
                country_code=code, past_risk=past
            )
            feeds.append(result)
            print(
                f"[SSM] {code}: risk={result['RISK_PCT']}% status={result['STATUS']} "
                f"ai={result['AI_CRASH_PROB']} net={result['NETWORK']}",
                flush=True,
            )
        except Exception as exc:
            print(f"[SSM ERROR] {code}: {exc}", file=sys.stderr)
            traceback.print_exc()

    report = {
        "HEADER": "SSM_UNIFIED_RISK_PASSPORT",
        "VERSION": "29.1",
        "ARCHITECT_TOKEN": "TOKEN_F5B2C8E4A1D7396F",
        "TIMESTAMP_UTC": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "WEIGHTS": core.weights,
        "DATA_DYNAMIC_FEEDS": feeds,
        "COUNTRIES_PROCESSED": len(feeds),
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(base_dir, "ssm_unified_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[SSM] Unified report written → {report_path}", flush=True)
    return report
