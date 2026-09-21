@echo off
cd /d "%~dp0"
echo Installing required packages (no ruptures)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: install failed
  pause
  exit /b 1
)
echo.
echo Checking streamlit...
python -c "import streamlit; print('streamlit OK', streamlit.__version__)"
python -c "import pandas, plotly, numpy, scipy; print('data stack OK')"
echo.
echo Done. Next: double-click start-simple.bat
echo Dashboard: http://localhost:8501
pause
