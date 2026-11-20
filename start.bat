@echo off
TITLE Epson Print & Scan Server Gateway
COLOR 0A

:: Ensure user-installed runtimes are on PATH
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\NodeJS;%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"

echo ========================================================
echo   Epson All-in-One Gateway (Windows 11)
echo   Python Hardware Engine + Node.js Web Dashboard
echo ========================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org (Check 'Add to PATH').
    pause
    exit /b 1
)

:: 2. Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js LTS from nodejs.org.
    pause
    exit /b 1
)

:: 3. Install Python Dependencies
echo [*] Checking Python dependencies...
python -m pip install -r requirements.txt --quiet

:: 4. Install Node.js Dependencies
echo [*] Checking Node.js dependencies...
cd web
if not exist node_modules (
    call npm install --silent
)
cd ..

:: 5. Launch Python Hardware Engine (Port 5000 & AirPrint Port 631)
echo.
echo [*] Launching Python Hardware Engine & AirPrint...
start "Epson Python Engine" /min python -m server.main

:: 6. Launch Node.js Web Dashboard (Port 3000)
echo [*] Launching Node.js Web Dashboard on port 3000...
timeout /t 2 /nobreak >nul

:: Open browser automatically
start http://localhost:3000

cd web
node server.js
