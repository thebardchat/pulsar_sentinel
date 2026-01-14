@echo off
REM ============================================================================
REM PULSAR SENTINEL - Post-Quantum Security Framework
REM Windows Desktop Launcher
REM ============================================================================
REM
REM Place this file on your Desktop for one-click access to PULSAR SENTINEL
REM
REM Copyright (c) 2024 Angel Cloud - Patent Pending
REM ============================================================================

title PULSAR SENTINEL - Quantum-Safe Security

echo.
echo  ██████╗ ██╗   ██╗██╗     ███████╗ █████╗ ██████╗
echo  ██╔══██╗██║   ██║██║     ██╔════╝██╔══██╗██╔══██╗
echo  ██████╔╝██║   ██║██║     ███████╗███████║██████╔╝
echo  ██╔═══╝ ██║   ██║██║     ╚════██║██╔══██║██╔══██╗
echo  ██║     ╚██████╔╝███████╗███████║██║  ██║██║  ██║
echo  ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
echo.
echo  ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
echo  ██╔════╝██╔════╝████╗  ██║╚══════██║██║████╗  ██║██╔════╝██║
echo  ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
echo  ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
echo  ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
echo  ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
echo.
echo  Post-Quantum Cryptography Security Framework
echo  Protecting 800M Windows Users Against Quantum Threats
echo  ============================================================================
echo.

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [INFO] Found Python %PYVER%

REM Set working directory to script location
cd /d "%~dp0"

REM Check if we're in the pulsar_sentinel directory
if not exist "requirements.txt" (
    echo [ERROR] Please place this file in the pulsar_sentinel directory
    echo        or update the path below:
    echo.
    set /p SENTINEL_PATH="Enter PULSAR SENTINEL path: "
    cd /d "%SENTINEL_PATH%"
)

echo.
echo ============================================================================
echo                         PULSAR SENTINEL MENU
echo ============================================================================
echo.
echo  [1] Start PULSAR SENTINEL Server (Development Mode)
echo  [2] Start PULSAR SENTINEL Server (Production Mode)
echo  [3] Run Tests
echo  [4] Generate New Keys
echo  [5] Setup/Update Environment
echo  [6] Open API Documentation (Browser)
echo  [7] View Logs
echo  [8] Check System Status
echo  [9] Exit
echo.
echo ============================================================================
echo.

set /p CHOICE="Select option (1-9): "

if "%CHOICE%"=="1" goto :dev_server
if "%CHOICE%"=="2" goto :prod_server
if "%CHOICE%"=="3" goto :run_tests
if "%CHOICE%"=="4" goto :gen_keys
if "%CHOICE%"=="5" goto :setup_env
if "%CHOICE%"=="6" goto :open_docs
if "%CHOICE%"=="7" goto :view_logs
if "%CHOICE%"=="8" goto :check_status
if "%CHOICE%"=="9" goto :exit_app

echo [ERROR] Invalid option. Please select 1-9.
pause
goto :eof

:setup_env
echo.
echo [SETUP] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat
echo [SETUP] Installing dependencies...
pip install -r requirements.txt
echo.
echo [SUCCESS] Environment setup complete!
pause
goto :eof

:dev_server
echo.
echo [START] Starting PULSAR SENTINEL in Development Mode...
echo [INFO] API will be available at http://localhost:8000
echo [INFO] Press Ctrl+C to stop the server
echo.
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
pause
goto :eof

:prod_server
echo.
echo [START] Starting PULSAR SENTINEL in Production Mode...
echo [INFO] API will be available at http://localhost:8000
echo [INFO] Press Ctrl+C to stop the server
echo.
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4
pause
goto :eof

:run_tests
echo.
echo [TEST] Running PULSAR SENTINEL test suite...
echo.
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
pytest -v --tb=short
pause
goto :eof

:gen_keys
echo.
echo [KEYS] Generating cryptographic keys...
echo.
echo  [1] Generate Hybrid (ML-KEM + AES) Keys
echo  [2] Generate AES-256 Keys
echo  [3] Generate ECDSA Keys (Polygon)
echo  [4] Generate All Keys
echo.
set /p KEYTYPE="Select key type (1-4): "
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
if "%KEYTYPE%"=="1" python scripts\generate_keys.py --algorithm hybrid --output keys
if "%KEYTYPE%"=="2" python scripts\generate_keys.py --algorithm aes --output keys
if "%KEYTYPE%"=="3" python scripts\generate_keys.py --algorithm ecdsa --output keys
if "%KEYTYPE%"=="4" python scripts\generate_keys.py --algorithm all --output keys
pause
goto :eof

:open_docs
echo.
echo [DOCS] Opening API documentation in browser...
start http://localhost:8000/docs
goto :eof

:view_logs
echo.
echo [LOGS] Recent PULSAR SENTINEL logs:
echo ============================================================================
if exist "logs\pulsar_sentinel.log" (
    type logs\pulsar_sentinel.log | more
) else (
    echo No logs found. Start the server first.
)
pause
goto :eof

:check_status
echo.
echo [STATUS] Checking PULSAR SENTINEL status...
echo.
curl -s http://localhost:8000/api/v1/health 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Server is not running or not responding
) else (
    echo.
    echo [SUCCESS] Server is running!
)
echo.
pause
goto :eof

:exit_app
echo.
echo [EXIT] Thank you for using PULSAR SENTINEL
echo        "Build it once. Secure it forever."
echo.
exit /b 0
