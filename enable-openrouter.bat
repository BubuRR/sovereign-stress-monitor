@echo off
cd /d "%~dp0"
echo.
echo Set your key FIRST in this window:
echo   set OPENROUTER_API_KEY=sk-or-v1-...
echo.
echo Then this script runs the radar.
echo.
if "%OPENROUTER_API_KEY%"=="" if "%OPENAI_API_KEY%"=="" (
  echo ERROR: OPENROUTER_API_KEY is empty.
  echo Create key at https://openrouter.ai/keys
  pause
  exit /b 1
)
python ssm_core.py
echo.
echo Open dashboard? Running streamlit...
python -m streamlit run interface/app.py --server.port 8501
pause
