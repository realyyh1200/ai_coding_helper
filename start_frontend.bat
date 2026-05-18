@echo off
cd /d "%~dp0frontend"
echo.
echo ===============================
echo     Start Frontend Server
echo ===============================
echo.

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm command not found
    echo Please install Node.js first
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

npm run dev
pause