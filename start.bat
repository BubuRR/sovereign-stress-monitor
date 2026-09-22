@echo off
cd /d "%~dp0"
title SSM v32
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found.
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
python ssm_core.py
echo Open http://localhost:8501
python -m streamlit run interface/app.py --server.port 8501
pause
