# Sovereign Stress Monitor — запуск

```bash
cd SSM-v29.1-FIXED
pip install -r requirements.txt
python ssm_core.py
```

API:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
# http://localhost:8000/
# http://localhost:8000/api/v1/radar/composite
# http://localhost:8000/api/v1/risk/US
# http://localhost:8000/api/v1/backtest/US
```

Dashboard:
```bash
streamlit run interface/app.py --server.port 8501
```

Docker:
```bash
docker-compose up --build
```
