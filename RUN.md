# Run book

```bash
cd SSM-v30-CLEAN
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python ssm_core.py
uvicorn api.main:app --port 8000
# other terminal:
streamlit run interface/app.py --server.port 8501
```

Docker:

```bash
docker-compose up --build
```
