@echo off
cd /d "%~dp0"
echo Running data cycle...
python ssm_core.py
echo.
echo Starting dashboard at http://localhost:8501
python -m streamlit run interface/app.py --server.port 8501
pause
