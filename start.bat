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

python --version
echo.

echo [1/3] Installing packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: pip install failed.
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
echo Open browser: http://localhost:8501
echo Stop: close this window or Ctrl+C
echo.

python -m streamlit run interface/app.py --server.port 8501
pause
