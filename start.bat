@echo off
cd /d "%~dp0"
echo Instalando dependencias (si hace falta)...
python -m pip install -r requirements.txt
echo.
echo Levantando TCG Trade en http://localhost:8085
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8085"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8085
pause
