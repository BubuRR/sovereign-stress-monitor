@echo off
cd /d "%~dp0"
python ssm_core.py
python -m streamlit run interface/app.py --server.port 8501
pause
