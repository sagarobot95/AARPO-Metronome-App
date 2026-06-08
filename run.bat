@echo off
REM Cross-platform launcher for Windows.
REM Creates a virtual environment on first run, installs dependencies, then starts.
setlocal
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"

where py >nul 2>nul && (set "PY=py") || (set "PY=python")

if not exist "%VENV%" (
    echo Setting up AARPO Metronome ^(first run^)...
    %PY% -m venv "%VENV%"
    call "%VENV%\Scripts\activate.bat"
    python -m pip install --upgrade pip >nul
    python -m pip install -r "%ROOT%requirements.txt"
) else (
    call "%VENV%\Scripts\activate.bat"
)

python -m aarpo_metronome
endlocal
