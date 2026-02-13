@echo off
REM ============================================================================
REM PULSAR SENTINEL - Post-Quantum Security Framework
REM Windows Desktop Launcher v2.0
REM ============================================================================
REM
REM Place this file on your Desktop for one-click access to PULSAR SENTINEL
REM Double-click to launch the quantum-safe security portal
REM
REM Copyright (c) 2024 Angel Cloud Technologies - Patent Pending
REM ============================================================================

setlocal enabledelayedexpansion
title PULSAR SENTINEL - Quantum-Safe Security
color 0B

:main_banner
cls
echo.
echo  [36m██████╗ ██╗   ██╗██╗     ███████╗ █████╗ ██████╗[0m
echo  [36m██╔══██╗██║   ██║██║     ██╔════╝██╔══██╗██╔══██╗[0m
echo  [36m██████╔╝██║   ██║██║     ███████╗███████║██████╔╝[0m
echo  [36m██╔═══╝ ██║   ██║██║     ╚════██║██╔══██║██╔══██╗[0m
echo  [36m██║     ╚██████╔╝███████╗███████║██║  ██║██║  ██║[0m
echo  [36m╚═╝      ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝[0m
echo.
echo  [35m███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗[0m
echo  [35m██╔════╝██╔════╝████╗  ██║╚══════██║██║████╗  ██║██╔════╝██║[0m
echo  [35m███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║[0m
echo  [35m╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║[0m
echo  [35m███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗[0m
echo  [35m╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝[0m
echo.
echo  [33m============================================================[0m
echo  [33m  Post-Quantum Cryptography Security Framework v1.0[0m
echo  [33m  "Build it once. Secure it forever."[0m
echo  [33m============================================================[0m
echo.

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [91m  [X] ERROR: Python not found![0m
    echo      Please install Python 3.10+ from https://python.org
    echo      Make sure to check "Add Python to PATH" during install
    echo.
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [92m[OK][0m Python %PYVER% detected
echo.

REM Set working directory to script location
cd /d "%~dp0"

REM Check if requirements exist
if not exist "requirements.txt" (
    echo [91m  [X] ERROR: Not in PULSAR SENTINEL directory![0m
    echo      Please place this .bat file in the pulsar_sentinel folder
    echo.
    pause
    exit /b 1
)

:menu
echo.
echo  [96m============== MAIN MENU ==============[0m
echo.
echo   [1] [92mQUICK START[0m - Launch Everything
echo   [2] [93mStart Server Only[0m (Development)
echo   [3] [93mStart Server Only[0m (Production)
echo   [4] [96mOpen Web Portal[0m (Browser)
echo   [5] [95mMining Controls[0m
echo   [6] [94mSetup / Install[0m
echo   [7] [33mRun Tests[0m
echo   [8] [33mGenerate Keys[0m
echo   [9] [33mCheck Status[0m
echo  [10] [35mDiscord Bot[0m
echo   [0] [91mExit[0m
echo.
echo  [96m========================================[0m
echo.

set /p CHOICE="  Select option [0-10]: "

if "%CHOICE%"=="1" goto :quick_start
if "%CHOICE%"=="2" goto :dev_server
if "%CHOICE%"=="3" goto :prod_server
if "%CHOICE%"=="4" goto :open_portal
if "%CHOICE%"=="5" goto :mining_menu
if "%CHOICE%"=="6" goto :setup_menu
if "%CHOICE%"=="7" goto :run_tests
if "%CHOICE%"=="8" goto :gen_keys
if "%CHOICE%"=="9" goto :check_status
if "%CHOICE%"=="10" goto :discord_bot
if "%CHOICE%"=="0" goto :exit_app

echo.
echo  [91m[X] Invalid option. Please select 0-10.[0m
timeout /t 2 >nul
goto :menu

REM ============================================================================
REM QUICK START - One-Click Launch
REM ============================================================================
:quick_start
cls
echo.
echo  [92m============== QUICK START ==============[0m
echo.
echo  [93mInitializing PULSAR SENTINEL...[0m
echo.

REM Check/Create virtual environment
if not exist "venv" (
    echo  [*] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo  [91m[X] Failed to create venv[0m
        pause
        goto :menu
    )
)

REM Activate venv
echo  [*] Activating environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
pip show fastapi >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  [*] Installing dependencies (first time setup)...
    echo      This may take 2-3 minutes...
    pip install -r requirements.txt -q
    if %ERRORLEVEL% NEQ 0 (
        echo  [91m[X] Failed to install dependencies[0m
        pause
        goto :menu
    )
)

REM Check for .env file
if not exist ".env" (
    echo  [*] Creating configuration file...
    copy .env.template .env >nul 2>nul
)

echo.
echo  [92m[OK] Environment ready![0m
echo.
echo  [93mStarting PULSAR SENTINEL server...[0m
echo.
echo  [96m========================================[0m
echo    Server URL:    http://localhost:8000
echo    API Docs:      http://localhost:8000/docs
echo    Web Portal:    http://localhost:8000
echo  [96m========================================[0m
echo.
echo  [33m  Press Ctrl+C to stop the server[0m
echo.

REM Start browser after short delay
start /min cmd /c "timeout /t 3 >nul && start http://localhost:8000"

REM Start server
cd src
python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
cd ..
pause
goto :menu

REM ============================================================================
REM DEVELOPMENT SERVER
REM ============================================================================
:dev_server
cls
echo.
echo  [93m============== DEVELOPMENT SERVER ==============[0m
echo.
call :activate_env
echo.
echo  [93mStarting server in development mode (hot reload enabled)...[0m
echo.
echo  [96m  Server URL: http://localhost:8000[0m
echo  [96m  API Docs:   http://localhost:8000/docs[0m
echo.
echo  [33m  Press Ctrl+C to stop[0m
echo.
cd src
python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
cd ..
pause
goto :menu

REM ============================================================================
REM PRODUCTION SERVER
REM ============================================================================
:prod_server
cls
echo.
echo  [93m============== PRODUCTION SERVER ==============[0m
echo.
call :activate_env
echo.
echo  [93mStarting server in production mode (4 workers)...[0m
echo.
echo  [96m  Server URL: http://localhost:8000[0m
echo  [96m  Workers:    4[0m
echo.
echo  [33m  Press Ctrl+C to stop[0m
echo.
cd src
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4
cd ..
pause
goto :menu

REM ============================================================================
REM OPEN WEB PORTAL
REM ============================================================================
:open_portal
echo.
echo  [96m  Opening PULSAR SENTINEL Web Portal...[0m
start http://localhost:8000
timeout /t 1 >nul
goto :menu

REM ============================================================================
REM MINING MENU
REM ============================================================================
:mining_menu
cls
echo.
echo  [95m============== MINING CONTROLS ==============[0m
echo.
echo   [1] Start Mining (Default Settings)
echo   [2] Start Mining (High Performance)
echo   [3] Start Mining (Low Power)
echo   [4] Stop Mining
echo   [5] View Mining Stats
echo   [6] Configure Mining
echo   [0] Back to Main Menu
echo.
echo  [95m==============================================[0m
echo.

set /p MCHOICE="  Select option [0-6]: "

if "%MCHOICE%"=="1" goto :start_mining_default
if "%MCHOICE%"=="2" goto :start_mining_high
if "%MCHOICE%"=="3" goto :start_mining_low
if "%MCHOICE%"=="4" goto :stop_mining
if "%MCHOICE%"=="5" goto :mining_stats
if "%MCHOICE%"=="6" goto :configure_mining
if "%MCHOICE%"=="0" goto :menu

echo  [91m[X] Invalid option[0m
timeout /t 2 >nul
goto :mining_menu

:start_mining_default
echo.
echo  [95m  Starting mining with default settings...[0m
echo  [33m  Threads: 4  |  Intensity: 75%%[0m
echo.
echo  [93m  NOTE: Mining runs in the web portal.[0m
echo        Open http://localhost:8000/mining to control mining.
echo.
start http://localhost:8000/mining
pause
goto :mining_menu

:start_mining_high
echo.
echo  [95m  High performance mining settings configured.[0m
echo  [33m  Threads: 8  |  Intensity: 95%%[0m
echo.
echo  [91m  WARNING: This will use more CPU and power.[0m
echo.
start http://localhost:8000/mining
pause
goto :mining_menu

:start_mining_low
echo.
echo  [95m  Low power mining settings configured.[0m
echo  [33m  Threads: 2  |  Intensity: 50%%[0m
echo.
echo  [92m  Optimized for background operation.[0m
echo.
start http://localhost:8000/mining
pause
goto :mining_menu

:stop_mining
echo.
echo  [95m  Mining control is managed in the web portal.[0m
echo       Open http://localhost:8000/mining and click "Stop Mining"
echo.
start http://localhost:8000/mining
pause
goto :mining_menu

:mining_stats
echo.
echo  [95m  Opening mining statistics...[0m
start http://localhost:8000/mining
pause
goto :mining_menu

:configure_mining
echo.
echo  [95m  Mining configuration is managed in the web portal.[0m
echo       Open http://localhost:8000/mining to configure:
echo       - Worker name
echo       - Thread count
echo       - Mining intensity
echo       - Pool settings
echo.
start http://localhost:8000/mining
pause
goto :mining_menu

REM ============================================================================
REM SETUP MENU
REM ============================================================================
:setup_menu
cls
echo.
echo  [94m============== SETUP / INSTALL ==============[0m
echo.
echo   [1] Full Setup (Recommended)
echo   [2] Create Virtual Environment Only
echo   [3] Install Dependencies Only
echo   [4] Create Configuration File
echo   [5] Reset Everything
echo   [0] Back to Main Menu
echo.
echo  [94m==============================================[0m
echo.

set /p SCHOICE="  Select option [0-5]: "

if "%SCHOICE%"=="1" goto :full_setup
if "%SCHOICE%"=="2" goto :create_venv
if "%SCHOICE%"=="3" goto :install_deps
if "%SCHOICE%"=="4" goto :create_config
if "%SCHOICE%"=="5" goto :reset_all
if "%SCHOICE%"=="0" goto :menu

echo  [91m[X] Invalid option[0m
timeout /t 2 >nul
goto :setup_menu

:full_setup
echo.
echo  [94m  Running full setup...[0m
echo.

echo  [*] Step 1/4: Creating virtual environment...
if exist "venv" (
    echo      [Already exists - skipping]
) else (
    python -m venv venv
    echo      [92m[OK][0m
)

echo  [*] Step 2/4: Activating environment...
call venv\Scripts\activate.bat
echo      [92m[OK][0m

echo  [*] Step 3/4: Installing dependencies...
pip install -r requirements.txt -q
echo      [92m[OK][0m

echo  [*] Step 4/4: Creating configuration...
if exist ".env" (
    echo      [Already exists - skipping]
) else (
    copy .env.template .env >nul 2>nul
    echo      [92m[OK][0m
)

echo.
echo  [92m========================================[0m
echo  [92m  Setup complete! You can now run:[0m
echo  [92m  - Quick Start (Option 1)[0m
echo  [92m========================================[0m
echo.
pause
goto :setup_menu

:create_venv
echo.
echo  [94m  Creating virtual environment...[0m
python -m venv venv
echo  [92m  [OK] Virtual environment created[0m
pause
goto :setup_menu

:install_deps
echo.
echo  [94m  Installing dependencies...[0m
call :activate_env
pip install -r requirements.txt
echo  [92m  [OK] Dependencies installed[0m
pause
goto :setup_menu

:create_config
echo.
echo  [94m  Creating configuration file...[0m
if exist ".env" (
    echo  [33m  .env already exists. Overwrite? (Y/N)[0m
    set /p OVERWRITE="  "
    if /i "!OVERWRITE!"=="Y" (
        copy .env.template .env >nul
        echo  [92m  [OK] Configuration created[0m
    ) else (
        echo  [33m  Skipped[0m
    )
) else (
    copy .env.template .env >nul
    echo  [92m  [OK] Configuration created[0m
)
pause
goto :setup_menu

:reset_all
echo.
echo  [91m  WARNING: This will delete venv and .env[0m
echo  [91m  Are you sure? (Y/N)[0m
set /p CONFIRM="  "
if /i "!CONFIRM!"=="Y" (
    echo  [*] Removing virtual environment...
    rmdir /s /q venv 2>nul
    echo  [*] Removing configuration...
    del .env 2>nul
    echo  [92m  [OK] Reset complete[0m
) else (
    echo  [33m  Cancelled[0m
)
pause
goto :setup_menu

REM ============================================================================
REM RUN TESTS
REM ============================================================================
:run_tests
cls
echo.
echo  [33m============== TEST SUITE ==============[0m
echo.
call :activate_env
echo  [93m  Running PULSAR SENTINEL tests...[0m
echo.
pytest -v --tb=short tests/
echo.
pause
goto :menu

REM ============================================================================
REM GENERATE KEYS
REM ============================================================================
:gen_keys
cls
echo.
echo  [33m============== KEY GENERATION ==============[0m
echo.
echo   [1] Generate Hybrid Keys (ML-KEM + AES)
echo   [2] Generate AES-256 Keys
echo   [3] Generate ECDSA Keys (Polygon)
echo   [4] Generate All Keys
echo   [0] Back to Main Menu
echo.
echo  [33m==============================================[0m
echo.

set /p KCHOICE="  Select option [0-4]: "

call :activate_env

if "%KCHOICE%"=="1" (
    echo  [93m  Generating Hybrid keys...[0m
    python scripts\generate_keys.py --algorithm hybrid --output keys
)
if "%KCHOICE%"=="2" (
    echo  [93m  Generating AES-256 keys...[0m
    python scripts\generate_keys.py --algorithm aes --output keys
)
if "%KCHOICE%"=="3" (
    echo  [93m  Generating ECDSA keys...[0m
    python scripts\generate_keys.py --algorithm ecdsa --output keys
)
if "%KCHOICE%"=="4" (
    echo  [93m  Generating all keys...[0m
    python scripts\generate_keys.py --algorithm all --output keys
)
if "%KCHOICE%"=="0" goto :menu

echo.
pause
goto :menu

REM ============================================================================
REM CHECK STATUS
REM ============================================================================
:check_status
cls
echo.
echo  [33m============== SYSTEM STATUS ==============[0m
echo.

echo  [*] Checking server status...
curl -s http://localhost:8000/api/v1/health >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo      [91m[X] Server is NOT running[0m
) else (
    echo      [92m[OK] Server is running![0m
    echo.
    echo  [*] Fetching health data...
    curl -s http://localhost:8000/api/v1/health
)

echo.
echo  [*] Environment Check:
if exist "venv" (
    echo      [92m[OK] Virtual environment exists[0m
) else (
    echo      [91m[X] Virtual environment not found[0m
)

if exist ".env" (
    echo      [92m[OK] Configuration file exists[0m
) else (
    echo      [91m[X] Configuration file not found[0m
)

echo.
pause
goto :menu

REM ============================================================================
REM DISCORD BOT
REM ============================================================================
:discord_bot
cls
echo.
echo  [35m============== DISCORD BOT ==============[0m
echo.
call :activate_env
echo  [93m  Starting PULSAR SENTINEL Discord Bot...[0m
echo.
echo  [96m  Bot Commands: !help, !status, !pricing, !pts, !docs, !invite[0m
echo.
echo  [33m  Press Ctrl+C to stop the bot[0m
echo.
python scripts\run_discord_bot.py
pause
goto :menu

REM ============================================================================
REM EXIT
REM ============================================================================
:exit_app
cls
echo.
echo  [96m============================================[0m
echo.
echo    Thank you for using PULSAR SENTINEL
echo.
echo    "Build it once. Secure it forever."
echo.
echo  [96m============================================[0m
echo.
echo  [33m  Visit: https://github.com/angelcloud/pulsar-sentinel[0m
echo  [33m  Docs:  http://localhost:8000/docs[0m
echo.
timeout /t 3 >nul
exit /b 0

REM ============================================================================
REM HELPER FUNCTIONS
REM ============================================================================

:activate_env
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo  [91m[X] Virtual environment not found. Run Setup first.[0m
)
goto :eof
