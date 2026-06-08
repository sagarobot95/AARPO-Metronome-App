@echo off
REM Cross-platform launcher for Windows.
REM Creates a virtual environment on first run, installs dependencies, then starts.
setlocal
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"

where py >nul 2>nul && (set "PY=py") || (set "PY=python")

set "NEED=1"
if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" -c "import textual, pygame, PIL, textual_image" >nul 2>nul && set "NEED=0"
)

if "%NEED%"=="1" (
    echo Setting up AARPO Metronome ^(first run on this machine^)...
    %PY% -m venv "%VENV%"
    call "%VENV%\Scripts\activate.bat"
    python -m pip install --upgrade pip >nul
    python -m pip install -r "%ROOT%requirements.txt"
) else (
    call "%VENV%\Scripts\activate.bat"
)

python -m aarpo_metronome
endlocal
