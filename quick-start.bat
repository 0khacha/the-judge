@echo off
REM Quick start script for The Judge (Windows)

echo.
echo The Judge - Quick Start
echo ==========================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed. Please install Python 3.9 or higher.
    exit /b 1
)

echo Found Python:
python --version
echo.

REM Check if in virtual environment
if not defined VIRTUAL_ENV (
    echo Not in a virtual environment. Creating one...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Virtual environment created and activated
    echo.
)

REM Install the package
echo Installing The Judge...
pip install -e ".[dev]" -q
echo The Judge installed
echo.

REM Run a quick test
echo Running quick verification...
judge --version
echo.

REM Show next steps
echo Setup complete!
echo.
echo Next steps:
echo   1. Run demo:       judge demo
echo   2. Verify code:    judge verify .
echo   3. Improve code:   judge improve .
echo   4. See help:       judge --help
echo.
echo Documentation:
echo   - Quick Start:     docs\QUICK_START.md
echo   - API Reference:   docs\API.md
echo   - Integration:     PLUGIN_GUIDE.md
echo.
echo Happy coding!
