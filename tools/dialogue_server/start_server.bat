@echo off
REM Запуск dialogue server на Windows.
REM Использование: double-click или из PowerShell.

setlocal

cd /d "%~dp0"

if not exist .venv\ (
    echo [!] .venv not found. Creating...
    py -m venv .venv || ^
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

if not exist .env (
    echo [!] .env not found — copying .env.example
    copy .env.example .env
)

echo.
echo Starting Firefly Dialogue Server on http://127.0.0.1:8765
echo Docs: http://127.0.0.1:8765/docs
echo Ctrl+C to stop.
echo.

python -m uvicorn server:app --host 127.0.0.1 --port 8765

endlocal
