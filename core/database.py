# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — RELATIONAL DATABASE LAYER (database.py)
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Version:   28.0 (Hardened SQLite Production)
# ======================================================================

import sqlite3
import os
import sys
from datetime import datetime, timezone

class SovereignStressDB:
    def __init__(self, db_name="ssm_intelligence.db"):
        """Инициализация пути к базе данных в корневой директории проекта."""
        # База данных создается на один уровень выше папки core, в корне репозитория
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(os.path.dirname(self.current_dir), db_name)
        self._bootstrap_database()

    def _get_connection(self):
        """Безопасное транзакционное подключение к SQLite с таймаутом блокировок."""
        return sqlite3.connect(self.db_path, timeout=10.0)

    def _bootstrap_database(self):
        """Создание таблицы и индексов временных рядов при первом запуске."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Создание таблицы исторических логов стресса
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historical_stress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        country TEXT NOT NULL,
                        risk_pct REAL NOT NULL,
                        status_level TEXT NOT NULL,
                        smh_price REAL NOT NULL,
                        dbb_price REAL NOT NULL,
                        usdt_median REAL NOT NULL
                    )
                """)
                # Индексы для мгновенной выборки Оптимизатором по странам и датам
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_country_timestamp 
                    ON historical_stress (country, timestamp DESC)
                """)
                conn.commit()
        except Exception as e:
            print(f"[FATAL СУБД] Сбой инициализации базы данных: {e}", file=sys.stderr)
            sys.exit(1)

    def write_triage_log(self, country: str, risk_pct: float, status_level: str, 
                         smh_price: float, dbb_price: float, usdt_median: float):
        """
        Атомарная запись строки макро-разведки. 
        Полностью исключает повреждение файлов (Data Corruption).
        """
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO historical_stress (
                timestamp, country, risk_pct, status_level, smh_price, dbb_price, usdt_median
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(query, (
                    ts, country.upper().strip(), round(float(risk_pct), 2), 
                    status_level.strip(), round(float(smh_price), 2), 
                    round(float(dbb_price), 2), round(float(usdt_median), 2)
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"[WARN СУБД] Ошибка записи тика для {country}: {e}", file=sys.stderr)
            return False

    def fetch_historical_matrix(self, country: str, limit: int = 500):
        """Извлечение чистой хронологической матрицы для графиков и бэктестинга."""
        query = """
            SELECT timestamp, risk_pct, status_level, smh_price, dbb_price, usdt_median 
            FROM historical_stress 
            WHERE country = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (country.upper().strip(), limit))
                rows = cursor.fetchall()
            
            # Конвертация в структурированный список словарей (Clean JSON ready)
            return [
                {
                    "timestamp": r[0], "risk_pct": r[1], "status_level": r[2],
                    "smh_price": r[3], "dbb_price": r[4], "usdt_median": r[5]
                } for r in rows
            ]
        except Exception as e:
            print(f"[ERROR СУБД] Ошибка чтения истории {country}: {e}", file=sys.stderr)
            return []
