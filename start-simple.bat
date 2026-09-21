@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python ssm_core.py
python -m streamlit run interface/app.py --server.port 8501
pause
