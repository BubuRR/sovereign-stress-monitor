@echo off
chcp 65001 >nul
cd /d "%~dp0"
title SSM - Sovereign Stress Monitor

echo.
echo ========================================
echo   SSM - запуск панели
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ОШИБКА] Python не найден.
  echo Установите Python 3.11+ с https://www.python.org/downloads/
  echo При установке отметьте: "Add python.exe to PATH"
  pause
  exit /b 1
)

echo [1/3] Установка зависимостей (первый раз может занять 1-3 мин)...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [ОШИБКА] pip install не удался
  pause
  exit /b 1
)

echo [2/3] Сбор данных (ssm_core.py)...
python ssm_core.py
if errorlevel 1 (
  echo [ПРЕДУПРЕЖДЕНИЕ] Цикл завершился с ошибкой — панель всё равно откроем, если есть старый отчёт.
)

echo [3/3] Открываем панель Streamlit...
echo.
echo   В браузере должна открыться страница.
echo   Если нет — сами откройте:  http://localhost:8501
echo.
echo   Чтобы ОСТАНОВИТЬ панель: закройте это окно или Ctrl+C
echo.

python -m streamlit run interface/app.py --server.port 8501 --server.headless false
pause
