@echo off
cd /d "%~dp0"
echo Installing packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import streamlit,pandas,plotly,numpy,scipy; print('OK')"
echo Done.
pause
