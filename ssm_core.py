# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — GLOBAL MULTI-COUNTRY MATRIX NODE v25.5
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Date:      September 19, 2026
#
# FULLY SELF-CONTAINED GLOBAL PRODUCTION RELEASE (PURE PYTHON)
# EXPANDED COUNTRY MATRIX: US | UA | DE | GB | CN | PL | RU | IL
# ======================================================================

import asyncio
import math
import json
import datetime
import urllib.request
import os

class RollingOnchainBuffer:
    def __init__(self, max_size=500):
        self.max_size = max_size
        self.buffer = []

    def extend(self, new_values):
        self.buffer.extend(new_values)
        if len(self.buffer) > self.max_size:
            self.buffer = self.buffer[-self.max_size:]

    def get_rolling_median(self, default_value):
        if not self.buffer:
            return default_value
        sorted_values = sorted(self.buffer)
        n = len(sorted_values)
        if n % 2 == 1:
            return sorted_values[n // 2]
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0

    def get_size(self):
        return len(self.buffer)


class SovereignGlobalMonitorV25_5:
    # 🏛️ РАСШИРЕННАЯ ИЕРАРХИЧЕСКАЯ МАТРИЦА СУВЕРЕННЫХ ПРОФИЛЕЙ СТРАН (v25.5)
    RAW_CONFIG = """
    {
      "GLOBAL_DEFAULTS": {
        "ALERT_THRESHOLD": 60.0,
        "BASE_BLIND_SPOT": 0.35,
        "BIOLOGICAL_BUFFER": 0.05,
        "SMH_50D_AVERAGE_NORM": 240.0,
        "DBB_50D_AVERAGE_NORM": 20.0
      },
      "COUNTRY_PROFILES": {
        "US": {
          "FISCAL_PRESSURE": 0.35,
          "GARAGE_BUFFER": 0.02,
          "DEMOGRAPHIC_SHRINKAGE": 0.01,
          "HISTORICAL_MEDIAN_USDT": 50000.0
        },
        "UA": {
          "FISCAL_PRESSURE": 0.515,
          "GARAGE_BUFFER": 0.15,
          "DEMOGRAPHIC_SHRINKAGE": 0.28,
          "HISTORICAL_MEDIAN_USDT": 5000.0
        },
        "DE": {
          "FISCAL_PRESSURE": 0.45,
          "GARAGE_BUFFER": 0.05,
          "DEMOGRAPHIC_SHRINKAGE": 0.04,
          "HISTORICAL_MEDIAN_USDT": 15000.0
        },
        "GB": {
          "FISCAL_PRESSURE": 0.43,
          "GARAGE_BUFFER": 0.04,
          "DEMOGRAPHIC_SHRINKAGE": 0.03,
          "HISTORICAL_MEDIAN_USDT": 25000.0
        },
        "CN": {
          "FISCAL_PRESSURE": 0.28,
          "GARAGE_BUFFER": 0.02,
          "DEMOGRAPHIC_SHRINKAGE": 0.08,
          "HISTORICAL_MEDIAN_USDT": 95000.0
        },
        "PL": {
          "FISCAL_PRESSURE": 0.41,
          "GARAGE_BUFFER": 0.10,
          "DEMOGRAPHIC_SHRINKAGE": 0.06,
          "HISTORICAL_MEDIAN_USDT": 12000.0
        },
        "RU": {
          "FISCAL_PRESSURE": 0.38,
          "GARAGE_BUFFER": 0.22,
          "DEMOGRAPHIC_SHRINKAGE": 0.18,
          "HISTORICAL_MEDIAN_USDT": 65000.0
        },
        "IL": {
          "FISCAL_PRESSURE": 0.46,
          "GARAGE_BUFFER": 0.08,
          "DEMOGRAPHIC_SHRINKAGE": 0.12,
          "HISTORICAL_MEDIAN_USDT": 20000.0
        }
      }
    }
    """

    def __init__(self):
        self.cache_stale_cycles = 0  
        self.high_stress_duration = 0  
        self.reference_mode = "normal"
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_file = os.path.join(current_dir, "ssm_historical_database.csv")
        
        self.global_config = json.loads(self.RAW_CONFIG)
        self.active_params = {}
        self.onchain_buffer = RollingOnchainBuffer(max_size=500)
        
        defaults = self.global_config.get("GLOBAL_DEFAULTS", {})
        self.pre_crisis_smh = defaults.get("SMH_50D_AVERAGE_NORM", 240.0)
        self.pre_crisis_dbb = defaults.get("DBB_50D_AVERAGE_NORM", 20.0)

    def _switch_country_context(self, country_code):
        defaults = self.global_config.get("GLOBAL_DEFAULTS", {})
        profiles = self.global_config.get("COUNTRY_PROFILES", {})
        target_profile = profiles.get(country_code, profiles.get("US", {}))
        self.active_params = {**defaults, **target_profile}

    def _calculate_visibility_penalty(self, stale_cycles):
        if stale_cycles == 0: return 0.0
        return round(0.4 * math.log(stale_cycles + 1), 3)

    async def _fetch_yahoo_chart(self, symbol: str, default_key: str):
        """Correct Yahoo Finance v8 chart endpoint."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (SSM_Monolith/25.3-FIXED)"}
            )
            res = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=3.5).read()
            )
            data = json.loads(res.decode("utf-8"))
            result_list = data.get("chart", {}).get("result", [])
            if not result_list:
                return self.active_params[default_key], f"YAHOO_{symbol}_EMPTY"

            result = result_list[0]  # FIXED: was treating list as dict
            closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            closes = [c for c in closes if c is not None]

            if len(closes) >= 1:
                return closes[-1], f"YAHOO_{symbol}_OK"
            return self.active_params[default_key], f"YAHOO_{symbol}_EMPTY"
        except Exception as e:
            return self.active_params[default_key], f"YAHOO_{symbol}_TIMEOUT:{type(e).__name__}"


    async def _fetch_trongrid_contract_stream(self):
        """Correct TronGrid transactions endpoint + hex ABI parse."""
        url = "https://api.trongrid.io/v1/contracts/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t/transactions"
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SSM_Monolith/25.5)", "Accept": "application/json"})
            res = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=3.5).read())
            data = json.loads(res.decode("utf-8"))
            tx_array = data.get("data", [])
            values = []
            for tx in tx_array:
                try:
                    contracts = tx.get("raw_data", {}).get("contract", [])
                    if not contracts: continue
                    value_block = contracts[0].get("parameter", {}).get("value", {})
                    hex_data = value_block.get("data", "")
                    if hex_data.startswith("a9059cbb") and len(hex_data) >= 136:
                        amount = int(hex_data[-64:], 16) / 1e6
                        if amount >= 100.0: values.append(amount)
                except Exception: continue
            return values
        except Exception:
            return []

     async def _fetch_tronscan_backup_stream(self):
        """Backup: Tronscan token stats (volume proxy, not individual txs)."""
        url = "https://apilist.tronscanapi.com/api/token_trc20?contract=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&limit=1"
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (SSM_Monolith/25.3-FIXED)"}
            )
            res = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=3.5).read()
            )
            data = json.loads(res.decode("utf-8"))
            tokens = data.get("trc20_tokens", [])
            if tokens:
                # volume24h is in USD; we don't convert it to individual tx sizes,
                # so this backup only confirms the endpoint is alive.
                # Return empty list so primary TronGrid remains the source of medians.
                return []
            return []
        except Exception:
            return []

    def _write_to_historical_csv(self, timestamp, country_code, risk_pct, status_level,
                                 current_smh, current_dbb, median_usdt):
        file_exists = os.path.exists(self.csv_file)
        try:
            with open(self.csv_file, "a", encoding="utf-8") as f:
                if not file_exists:
                    f.write("Timestamp,Country,Risk_Pct,Status_Level,SMH_Price,DBB_Price,USDT_Rolling_Median\n")
                f.write(
                    f"{timestamp},{country_code},{risk_pct},{status_level},"
                    f"{current_smh},{current_dbb},{round(median_usdt, 2)}\n"
                )
        except Exception:
            pass

    async def execute_monitoring_cycle(self, country_code="US", past_risk=60.0, kinetic_factor=0.0, network_storm=False):
        self._switch_country_context(country_code)
        
        tasks = [
            self._fetch_yahoo_chart("SMH", "SMH_50D_AVERAGE_NORM"),
            self._fetch_yahoo_chart("DBB", "DBB_50D_AVERAGE_NORM"),
            self._fetch_trongrid_contract_stream() if not network_storm else asyncio.sleep(0, result=[]),
            self._fetch_tronscan_backup_stream() if not network_storm else asyncio.sleep(0, result=[])
        ]

        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=5.0)
            (current_smh, status_b), (current_dbb, status_m), tg_values, ts_values = results
            if "TIMEOUT" in status_b and "TIMEOUT" in status_m: raise asyncio.TimeoutError

            live_incoming_tx = []
            if tg_values: live_incoming_tx.extend(tg_values)
            if ts_values: live_incoming_tx.extend(ts_values)

            if live_incoming_tx:
                self.onchain_buffer.extend(live_incoming_tx)
                self.cache_stale_cycles = 0
                status_onchain = f"VERIFIED_MULTI_STREAM_OK (buffer_n={self.onchain_buffer.get_size()})"
            else:
                status_onchain = "ONCHAIN_EMPTY_FIRST_TICK" if self.onchain_buffer.get_size() == 0 else "STREAM_TICK_EMPTY_RELYING_ON_ROLLING_WINDOW"

            use_dynamic, network_log = True, f"{status_b} | {status_m} | {status_onchain}"
        except asyncio.TimeoutError:
            self.cache_stale_cycles += 1
            current_smh, current_dbb = self.active_params["SMH_50D_AVERAGE_NORM"], self.active_params["DBB_50D_AVERAGE_NORM"]
            use_dynamic, network_log = False, f"TIMEOUT | GATEWAYS_DOWN_STALE_CYCLES={self.cache_stale_cycles}"

        live_median_usdt = self.onchain_buffer.get_rolling_median(
            self.active_params["HISTORICAL_MEDIAN_USDT"]
        )

        smh_avg = max(self.active_params["SMH_50D_AVERAGE_NORM"], 1e-9)
        dbb_avg = max(self.active_params["DBB_50D_AVERAGE_NORM"], 1e-9)
        base_usdt = max(self.active_params["HISTORICAL_MEDIAN_USDT"], 1e-9)

        baseline_smh = self.pre_crisis_smh if self.reference_mode == "pre_crisis" else smh_avg
        baseline_dbb = self.pre_crisis_dbb if self.reference_mode == "pre_crisis" else dbb_avg

        # Stress components (0..1)
        res_bubble = min(max((baseline_smh - current_smh) / baseline_smh * 5.0, 0.0), 1.0)
        res_material = min(max((current_dbb - baseline_dbb) / baseline_dbb * 5.0, 0.0), 1.0)

        deviation_usdt = (live_median_usdt - base_usdt) / base_usdt
        res_crypto = min(max(0.12 + deviation_usdt * 0.25, 0.0), 0.40)

        material_deficit = max((1.0 - res_material) - self.active_params["GARAGE_BUFFER"], 0.0)
        if material_deficit > 0.6:
            material_deficit *= 2.0

        fiscal_pressure = self.active_params["FISCAL_PRESSURE"]
        base_blind_spot = self.active_params["BASE_BLIND_SPOT"]
        demographic_shrinkage = self.active_params.get("DEMOGRAPHIC_SHRINKAGE", 0.0)
        biological_buffer = self.active_params.get("BIOLOGICAL_BUFFER", 0.05)

        total = res_bubble + material_deficit + res_crypto + fiscal_pressure
        if total <= 0:
            total = 1.0

        if use_dynamic:
            w_b = res_bubble / total
            w_m = material_deficit / total
            w_c = res_crypto / total
            w_f = fiscal_pressure / total
        else:
            w_b, w_m, w_c, w_f = 0.25, 0.45, 0.15, 0.15

        base_stress = (
            (res_bubble * w_b) ** 2 +
            (material_deficit * w_m) ** 2 +
            (res_crypto * w_c) ** 2 +
            (fiscal_pressure * w_f) ** 2
        ) ** 0.5

        financial = base_stress * (1.0 + base_blind_spot)
        kinetic = kinetic_factor + (demographic_shrinkage * 0.45) - (biological_buffer * 0.30)
        total_stress = financial + (kinetic * 1.2)
        total_stress += (past_risk / 100.0) * 0.5

        # visibility penalty for stale data
        total_stress += self._calculate_visibility_penalty(self.cache_stale_cycles)

        risk = 1.0 / (1.0 + math.exp(-total_stress * 2.5))
        risk_pct = round(risk * 100.0, 2)
        visibility = round(100.0 - risk_pct, 2)

        alert_threshold = self.active_params.get("ALERT_THRESHOLD", 60.0)
        if risk_pct >= alert_threshold:
            status_level = "CRITICAL"
            self.high_stress_duration += 1
        elif risk_pct >= alert_threshold * 0.75:
            status_level = "ELEVATED"
            self.high_stress_duration = 0
        else:
            status_level = "NORMAL"
            self.high_stress_duration = 0

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_to_historical_csv(
            timestamp, country_code, risk_pct, status_level,
            current_smh, current_dbb, live_median_usdt
        )

        result = {
            "HEADER": "SOVEREIGN_STRESS_MONITOR_V25_3_FIXED",
            "TIMESTAMP": timestamp,
            "COUNTRY": country_code,
            "RISK_PCT": risk_pct,
            "VISIBILITY_PCT": visibility,
            "STATUS": status_level,
            "NETWORK_LOG": network_log,
            "LIVE_METRICS": {
                "smh_price": round(current_smh, 2) if isinstance(current_smh, float) else current_smh,
                "dbb_price": round(current_dbb, 2) if isinstance(current_dbb, float) else current_dbb,
                "usdt_rolling_median": round(live_median_usdt, 2),
                "semiconductor_stress": round(res_bubble, 3),
                "metals_stress": round(res_material, 3),
                "crypto_component": round(res_crypto, 3),
                "material_deficit": round(material_deficit, 3),
                "fiscal_pressure": fiscal_pressure,
                "stale_cycles": self.cache_stale_cycles,
                "high_stress_duration": self.high_stress_duration
            }
        }
        return result


async def main():
    engine = SovereignGlobalMonitorV25_3()

    print("=" * 72)
    print("SSM v25.3-FIXED — LIVE TEST")
    print("=" * 72)

    for country in ["US", "UA", "DE"]:
        print(f"\n--- Country: {country} ---")
        report = await engine.execute_monitoring_cycle(country_code=country, past_risk=55.0)
        print(json.dumps(report, indent=2, ensure_ascii=False))

    print("\n" + "=" * 72)
    print("Forced network storm (TRON timeout simulation)")
    print("=" * 72)
    report_storm = await engine.execute_monitoring_cycle(
        country_code="US", past_risk=55.0, network_storm=True
    )
    print(json.dumps(report_storm, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
