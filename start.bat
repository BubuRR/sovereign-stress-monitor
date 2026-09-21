@echo off
setlocal
cd /d "%~dp0"
title SSM Dashboard

echo.
echo ========================================
echo   SSM - Sovereign Stress Monitor
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found.
  echo Install from https://www.python.org/downloads/
  echo Enable: Add python.exe to PATH
  pause
  exit /b 1
)

echo Python found:
python --version
echo.

echo [1/3] Installing packages - please wait...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: pip install failed.
  echo Try manually:
  echo   python -m pip install streamlit pandas plotly fastapi
  pause
  exit /b 1
)

echo.
echo [2/3] Collecting data...
python ssm_core.py
if errorlevel 1 (
  echo WARNING: data cycle had errors. Dashboard may use old report.
)

echo.
echo [3/3] Starting dashboard...
echo Open in browser: http://localhost:8501
echo To stop: close this window or press Ctrl+C
echo.

python -m streamlit run interface/app.py --server.port 8501
if errorlevel 1 (
  echo.
  echo ERROR: streamlit failed to start.
  echo Run this command manually:
  echo   python -m pip install streamlit
  echo   python -m streamlit run interface/app.py --server.port 8501
)

echo.
pause
