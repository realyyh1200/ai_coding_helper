@echo off
cd /d "%~dp0backend"
echo.
echo ===============================
echo     Start Backend Server
echo ===============================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: uv command not found
    echo Please install uv first: pip install uv
    pause
    exit /b 1
)

uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause