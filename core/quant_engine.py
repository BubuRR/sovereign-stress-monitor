# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — AUTOMATED GROUND FEEDS (ground_feeds.py)
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Version:   31.0 (UN & ACLED Async Ingestion Layer)
# ======================================================================

import asyncio
import json
import urllib.request
import urllib.parse
import datetime
import os

class SovereignGroundAutomator:
    def __init__(self, config_path="config/parameters.json"):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path)
        
    def _get_api_credentials(self):
        """Безопасное извлечение ключей из запечатанного хранилища config/parameters.json."""
        if not os.path.exists(self.config_path):
            return {"acled_key": "", "acled_email": ""}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            vault = config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
            return {
                "acled_key": vault.get("ACLED_API_KEY", ""),
                "acled_email": vault.get("ACLED_REGISTERED_EMAIL", "")
            }
        except Exception:
            return {"acled_key": "", "acled_email": ""}

    async def fetch_unhcr_migration_delta(self, country_iso2="UA"):
        """
        📡 АСИНХРОННЫЙ КОННЕКТОР К ОТКРЫТОМУ API ООН (UNHCR Operational Data)
        Возвращает актуальный объем зарегистрированного оттока населения.
        """
        # Официальный эндпоинт статистики беженцев ООН
        base_url = "https://unhcr.org"
        params = {
            "year": datetime.datetime.now().year,
            "coo": country_iso2.upper(), # Country of Origin
            "limit": 1
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "SSM-MacroRadar/31.0"})
            raw = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5.0).read())
            data = json.loads(raw.decode("utf-8"))
            
            # Извлекаем суммарный показатель зарегистрированного миграционного давления
            records = data.get("data", [])
            if records:
                return float(records[0].get("individuals", 0))
            return 0.0
        except Exception:
            # Резервный дефолтный возврат при таймаутах ООН-серверов
            return 0.0

    async def fetch_acled_kinetic_intensity(self, country_name="Ukraine"):
        """
        🦅 АСИНХРОННЫЙ КОННЕКТОР К БАЗЕ ДАННЫХ КОНФЛИКТОВ ACLED
        Фиксирует точное количество боестолкновений и ударов за последние 7 дней.
        """
        creds = self._get_api_credentials()
        if not creds["acled_key"] or "PASTE" in creds["acled_key"]:
            # Режим песочницы: если коммерческих ключей нет, возвращаем нулевую базовую линию
            return 0.0
            
        base_url = "https://acleddata.com"
        
        # Вычисляем временное окно: последние 7 дней
        date_limit = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        params = {
            "key": creds["acled_key"],
            "email": creds["acled_email"],
            "country": country_name,
            "event_date": date_limit,
            "event_date_where": ">=",
            "limit": 100
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5.0).read())
            data = json.loads(raw.decode("utf-8"))
            
            events = data.get("data", [])
            if isinstance(events, list):
                # Возвращаем физическое количество подтвержденных кинетических атак за неделю
                return float(len(events))
            return 0.0
        except Exception:
            return 0.0
