@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Move to script directory
cd /d "%~dp0"

echo ==============================================
echo   Hacktoberfest Project - Windows Setup
echo ==============================================

REM ------------------------------------------------
REM 1) Ensure Python (and pip) is installed
REM ------------------------------------------------
set "PY_CMD="
where python >nul 2>nul
if not errorlevel 1 set "PY_CMD=python"
if defined PY_CMD goto :have_python
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py"
:have_python

if defined PY_CMD goto :python_ready
echo Python not found. Attempting to install via winget...
where winget >nul 2>nul
if errorlevel 1 (
  echo winget not found. Please install Python manually from https://www.python.org/downloads/ and re-run.
  pause
  exit /b 1
)
winget install -e --id Python.Python --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo Failed to install Python via winget. Install Python manually and re-run.
  pause
  exit /b 1
)
REM Try to discover python again in this session
where python >nul 2>nul
if not errorlevel 1 set "PY_CMD=python"
if defined PY_CMD goto :python_ready
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py"

:python_ready

if not defined PY_CMD (
  echo Could not locate Python after installation. Close and reopen terminal, then re-run.
  pause
  exit /b 1
)

echo Using Python launcher: %PY_CMD%
%PY_CMD% --version

REM Ensure pip is available
%PY_CMD% -m pip --version >nul 2>nul
if errorlevel 1 (
  %PY_CMD% -m ensurepip --upgrade
)

REM ------------------------------------------------
REM 2) Ensure uv is installed
REM    Prefer official installer; falls back to pip if needed
REM ------------------------------------------------
set "UV_BIN="
where uv >nul 2>nul && set "UV_BIN=uv"
if defined UV_BIN goto :have_uv
echo uv not found. Installing uv (via official installer)...
powershell -NoProfile -Command "$env:PATH=\"$env:LOCALAPPDATA\Programs\uv\;$env:PATH\"; iex (irm https://astral.sh/uv/install.ps1)"
if errorlevel 1 (
  echo uv install script failed. Attempting install via pip...
  %PY_CMD% -m pip install --user uv
)
REM Put common user bin dirs on PATH for this session
set "PATH=%USERPROFILE%\.local\bin;%APPDATA%\Python\Scripts;%LOCALAPPDATA%\Programs\Python\Python39\Scripts;!PATH!"
where uv >nul 2>nul && set "UV_BIN=uv"
:have_uv

if not defined UV_BIN (
  echo Failed to install or locate uv. Add it to PATH or install manually: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

echo Using uv: %UV_BIN%
%UV_BIN% --version

REM ------------------------------------------------
REM 3) Create virtual environment and install dependencies
REM ------------------------------------------------
if exist .venv goto :venv_exists
echo Creating virtual environment with uv...
%UV_BIN% venv .venv
if errorlevel 1 (
  echo Failed to create venv with uv.
  pause
  exit /b 1
)
:venv_exists

call .venv\Scripts\activate
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

echo Syncing dependencies (pyproject.toml / uv.lock)...
%UV_BIN% sync
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

REM ------------------------------------------------
REM 4) Prepare directories and .env
REM ------------------------------------------------
if exist vector_db goto :skip_vec
mkdir vector_db
:skip_vec

if exist .env goto :skip_env
echo # Environment configuration> .env
echo # Add variables like API_KEY=your_key_here>> .env
:skip_env

REM ------------------------------------------------
REM 5) Run backend (run.py) then overlay (overlay.py)
REM    Start backend in a new window to keep it running.
REM ------------------------------------------------
echo Starting backend (run.py) in a new window...
start "Backend" cmd /c "".venv\Scripts\python.exe" run.py"
if errorlevel 1 echo Failed to start backend.

REM Small delay to allow backend to initialize
timeout /t 3 /nobreak >nul

echo Starting overlay (overlay.py)...
".venv\Scripts\python.exe" overlay.py

endlocal
exit /b 0

