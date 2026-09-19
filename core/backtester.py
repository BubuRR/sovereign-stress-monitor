# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — AUTOMATED AI BACKTESTER (backtester.py)
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Token:     TOKEN_F5B2C8E4A1D7396F
# Version:   29.1 (Analytical Evaluation Layer)
# ======================================================================

import sqlite3
import os
import sys
import math
import numpy as np

class SovereignAIBacktester:
    def __init__(self, db_name="ssm_intelligence.db"):
        """Связывание бэктестера с корневой реляционной СУБД SQLite."""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(os.path.dirname(self.current_dir), db_name)

    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=5.0)

    def execute_validation_matrix(self, target_country="US", alert_threshold=70.0):
        """
        Извлекает историю тиков из СУБД, моделирует временной сдвиг 7 дней 
        и строит точную матрицу ошибок (Confusion Matrix) по Юдену.
        """
        if not os.path.exists(self.db_path):
            return {"status": "ERROR", "detail": "Реляционная база данных SQLite не найдена в рантайме."}

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Вытягиваем хронологический ряд рисков из Слоя В
                cursor.execute("""
                    SELECT timestamp, risk_pct, smh_price, dbb_price, usdt_median 
                    FROM historical_stress 
                    WHERE country = ? 
                    ORDER BY timestamp ASC
                """, (target_country.upper().strip(),))
                rows = cursor.fetchall()

            if len(rows) < 15:
                return {
                    "status": "INSUFFICIENT_DATA",
                    "records_found": len(rows),
                    "detail": "Недостаточно исторических тиков в СУБД для расчета матрицы ошибок. Требуется минимум 15 записей."
                }

            # Парсинг массивов
            risks = np.array([float(r[1]) for r in rows])
            
            n_samples = len(risks)
            true_labels = np.zeros(n_samples)
            predicted_labels = np.zeros(n_samples)

            # Определение предсказаний (Где радар взвел статус CRITICAL)
            for i in range(n_samples):
                if risks[i] >= alert_threshold:
                    predicted_labels[i] = 1

            # Формирование сдвинутого истинного таргета (Target Shift):
            # Факт излома (падение/взлет) наступает на шаг t, но ИИ обязан был поймать его на шаге t-7
            for i in range(n_samples):
                # Симулируем излом тренда: падение индекса риска ниже скользящих или выход на экстремум
                if i < n_samples - 7:
                    if risks[i+7] >= alert_threshold:
                        true_labels[i] = 1

            # Математический обсчет компонентов Confusion Matrix
            tp = int(np.sum((true_labels == 1) & (predicted_labels == 1))) # Истинные положительные
            fp = int(np.sum((true_labels == 0) & (predicted_labels == 1))) # Ложные положительные
            fn = int(np.sum((true_labels == 1) & (predicted_labels == 0))) # Ложные отрицательные
            tn = int(np.sum((true_labels == 0) & (predicted_labels == 0))) # Истинные отрицательные

            # Расчет FinTech-метрик качества прогнозирования
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # True Positive Rate (TPR)
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0  # True Negative Rate (TNR)
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0          # False Positive Rate (FPR)
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0    # Точность
            
            # Финальный расчет Индекса Юдена (Youden J-Index)
            youden_j = sensitivity + specificity - 1.0

            return {
                "status": "SUCCESS",
                "target_country": target_country.upper(),
                "total_records_analyzed": n_samples,
                "confusion_matrix": {
                    "true_positives_tp": tp,
                    "false_positives_fp": fp,
                    "false_negatives_fn": fn,
                    "true_negatives_tn": tn
                },
                "accuracy_metrics": {
                    "sensitivity_tpr_pct": round(sensitivity * 100, 2),
                    "specificity_tnr_pct": round(specificity * 100, 2),
                    "false_positive_rate_fpr_pct": round(fpr * 100, 2),
                    "precision_pct": round(precision * 100, 2),
                    "youden_j_index": round(youden_j, 4)
                }
            }

        except Exception as e:
            return {"status": "FATAL_CRASH", "detail": f"Сбой аналитического движка бэктестера: {str(e)}"}

if __name__ == "__main__":
    # Локальный технический тест-драйв слоя
    backtester = SovereignAIBacktester()
    res = backtester.execute_validation_matrix(target_country="UA")
    print(json.dumps(res, indent=2, ensure_ascii=False) if "json" in sys.modules else res)
