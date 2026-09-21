# Run

## Windows (recommended)

1. Install Python from python.org — enable **Add to PATH**.
2. Unzip the project.
3. Double-click **`start.bat`**.
4. Open **http://localhost:8501** if the browser did not open itself.

Подробно по кликам: [HOWTO-WINDOWS.md](HOWTO-WINDOWS.md)

## Any OS (terminal)

```bash
pip install -r requirements.txt
python ssm_core.py
streamlit run interface/app.py --server.port 8501
```

## API

```bash
uvicorn api.main:app --port 8000
```

## Release tag

```bash
git tag v31.1
git push origin v31.1
```
