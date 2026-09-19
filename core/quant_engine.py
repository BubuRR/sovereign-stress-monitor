# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — ENTERPRISE QUANT ENGINE v28.7
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Date:      September 19, 2026
#
# STRICT CONTRACTS LIST INDEX FIX FOR PRODUCTION INTEGRATION
# EXPANDED GLOBAL COUNTRY MATRIX: US | UA | DE | GB | CN | PL | RU | IL
# ======================================================================

import asyncio
import math
import json
import datetime
import urllib.request
import os
import sys
import sqlite3
import traceback
import ruptures as rpt
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
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path)
        self.cache_stale_cycles = 0
        self.high_stress_duration = 0
        self.reference_mode = "normal"
        self.pre_crisis_smh = 550.0
        self.pre_crisis_dbb = 25.0
        
        self.db = SovereignStressDB()
        self.onchain_buffer = RollingOnchainBuffer(max_size=500)
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.weights = self.config.get("WEIGHTS", {"w_smh": 0.3913, "w_metals": 0.2609, "w_flow": 0.2174, "w_fiscal": 0.1304})

    async def _fetch_data_stream(self, symbol, fallback_val):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        poly_key = vault.get("POLYGON_IO_KEY", "")
        
        if poly_key and "PASTE" not in poly_key:
            url = f"{self.config['ENTERPRISE_DATA_GATEWAYS']['POLYGON_IO_MACRO_FEED']}/{symbol}/prev?apiKey={poly_key}"
        else:
            url = f"https://yahoo.com{symbol}?interval=1d&range=3mo"
            
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SSMCore/28.7"})
            raw = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=4.0).read())
            data = json.loads(raw.decode())
            
            if "results" in data:
                return [float(x["c"]) for x in data["results"]]
            else:
                result_list = data.get("chart", {}).get("result", [])
                if not result_list: return [fallback_val] * 50
                result = result_list[0]
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                closes = [c for c in closes if c is not None]
                return closes if closes else [fallback_val] * 50
        except Exception:
            return [fallback_val] * 50

    async def _fetch_tron_usdt_stream(self):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        qn_key = vault.get("QUICKNODE_TRON_KEY", "")
        
        if qn_key and "PASTE" not in qn_key:
            url = f"{self.config['ENTERPRISE_DATA_GATEWAYS']['QUICKNODE_TRON_RPC']}/{qn_key}"
        else:
            url = "https://trongrid.io"
            
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"})
            raw = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=4.0).read())
            data = json.loads(raw.decode())
            values = []
            for tx in data.get("data", []):
                try:
                    contracts = tx.get("raw_data", {}).get("contract", [])
                    if not contracts or not isinstance(contracts, list): continue
                    
                    # ИСПРАВЛЕННОЕ БЕЗОПАСНОЕ ИЗВЛЕЧЕНИЕ ИЗ МАССИВА CONTRACTS
                    target_contract = contracts[0]
                    value_block = target_contract.get("parameter", {}).get("value", {})
                    hex_data = value_block.get("data", "")
                    if isinstance(hex_data, str) and hex_data.startswith("a9059cbb") and len(hex_data) >= 136:
                        amt = int(hex_data[-64:], 16) / 1e6
                        if amt >= 100.0: values.append(amt)
                except Exception: continue
            return values
        except Exception: return []

    def _detect_change_points(self, history_data):
        if len(history_data) < 24: return False
        try:
            import numpy as np
            signal = np.array(history_data)
            algo = rpt.Pelt(model="rbf").fit(signal)
            result = algo.predict(pen=3.0)
            if len(result) > 1 and (len(history_data) - result[-2]) <= 5: return True
            return False
        except Exception: return False

    def _compute_z_score_stress(self, current, history, mode):
        if len(history) < 15:
            base = sum(history) / len(history) if history else current
            return min(max((base - current) / max(base, 1e-9) * 4.0, 0.0), 1.0) if mode == "dd" else min(max((current - base) / max(base, 1e-9) * 5.0, 0.0), 1.0)
        import numpy as np
        mean = np.mean(history)
        std = np.std(history) + 1e-9
        z_score = (current - mean) / std
        cdf_value = stats.norm.cdf(z_score)
        if mode == "dd": return float(round(1.0 - cdf_value, 4))
        return float(round(cdf_value, 4))

    async def execute_monitoring_cycle(self, country_code="US", past_risk=50.0):
        defaults = self.config["GLOBAL_DEFAULTS"]
        profile = self.config["COUNTRY_PROFILES"].get(country_code, self.config["COUNTRY_PROFILES"]["US"])
        params = {**defaults, **profile}
        
        smh_pool = await self._fetch_data_stream("SMH", params["SMH_50D_AVERAGE_NORM"])
        dbb_pool = await self._fetch_data_stream("DBB", params["DBB_50D_AVERAGE_NORM"])
        txs = await self._fetch_tron_usdt_stream()

        if txs:
            self.onchain_buffer.extend(txs)
            self.cache_stale_cycles = 0
            network_log = "COMMERCIAL_FEED_CONNECTED"
        else:
            network_log = "DEGRADED_FALLBACK_ACTIVE"
            if self.onchain_buffer.get_size() == 0: self.cache_stale_cycles += 1

        current_smh = smh_pool[-1] if smh_pool else params["SMH_50D_AVERAGE_NORM"]
        current_dbb = dbb_pool[-1] if dbb_pool else params["DBB_50D_AVERAGE_NORM"]
        usdt_med = self.onchain_buffer.get_trimmed_rolling_median(params["HISTORICAL_MEDIAN_USDT"])

        smh_break = self._detect_change_points(smh_pool)
        dbb_break = self._detect_change_points(dbb_pool)

        if smh_break or dbb_break or self.high_stress_duration >= 3:
            if self.high_stress_duration == 0:
                import numpy as np
                self.pre_crisis_smh = float(np.mean(smh_pool[-50:])) if len(smh_pool) >= 50 else current_smh
                self.pre_crisis_dbb = float(np.mean(dbb_pool[-50:])) if len(dbb_pool) >= 50 else current_dbb
            self.reference_mode = "pre_crisis"
        else:
            self.reference_mode = "normal"

        active_smh_history = [self.pre_crisis_smh] * 50 if self.reference_mode == "pre_crisis" else smh_pool
        active_dbb_history = [self.pre_crisis_dbb] * 50 if self.reference_mode == "pre_crisis" else dbb_pool

        res_bubble = self._compute_z_score_stress(current_smh, active_smh_history, "dd")
        res_material = self._compute_z_score_stress(current_dbb, active_dbb_history, "spike")
        
        base_usdt = max(params["HISTORICAL_MEDIAN_USDT"], 1e-9)
        res_crypto = min(max(0.12 + ((usdt_med - base_usdt) / base_usdt) * 0.25, 0.0), 0.40)
        
        material_deficit = max((1.0 - res_material) - params["GARAGE_BUFFER"], 0.0)
        if material_deficit > 0.6: material_deficit *= 2.0

        fiscal = params["FISCAL_PRESSURE"]
        w = self.weights
        
        core = (res_bubble * float(w["w_smh"]) + material_deficit * float(w["w_metals"]) + res_crypto * float(w["w_flow"]) + fiscal * float(w["w_fiscal"]))
        financial = core * (1.0 + params["BASE_BLIND_SPOT"])
        kinetic = (params.get("DEMOGRAPHIC_SHRINKAGE", 0.0) * 0.45) - (params["BIOLOGICAL_BUFFER"] * 0.30)
        
        total_stress = financial + max(kinetic, 0.0) * 1.2 + (past_risk / 100.0) * 0.2
        if self.cache_stale_cycles > 0: total_stress += round(0.4 * math.log(self.cache_stale_cycles + 1), 3)

        risk_pct = round((1.0 / (1.0 + math.exp(-total_stress * params["SIGMOID_STEEPNESS"]))) * 100.0, 2)
        
        if risk_pct >= params["ALERT_THRESHOLD"]: 
            status = "CRITICAL"
            self.high_stress_duration += 1
        elif risk_pct >= params["ELEVATED_THRESHOLD"]: 
            status = "ELEVATED"
            self.high_stress_duration = 0
        else: 
            status = "NORMAL"
            self.high_stress_duration = 0

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
