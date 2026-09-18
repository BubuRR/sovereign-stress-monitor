# Sovereign Stress Monitor (SSM) v25.1
### Architect: Odin (Sergey, Ukraine)
### Token: TOKEN_F5B2C8E4A1D7396F

Sovereign Stress Monitor (SSM) is a production-grade, fault-tolerant, asynchronous early warning and risk triage engine written in pure Python. It completely eliminates institutional "baseline drift" and blind spots by processing live alternative macro data and low-level on-chain TRON smart contract telemetry.

## Features
- **Anti-Drift Baseline Shunt**: Locks pre-crisis metrics if high stress persists (`high_stress_duration >= 3`).
- **Low-Level HEX ABI Ingestion**: Direct parsing of TRC-20 `transfer` function inputs to compute robust transaction medians.
- **Logarithmic Visibility Penalty**: Dynamically scales stress vectors during API timeouts or data isolation.
- **Walk-Forward Validation**: Out-of-sample optimization using Youden's Index and F1-Score calibration.

## License
This project is open-source under the MIT License terms.
