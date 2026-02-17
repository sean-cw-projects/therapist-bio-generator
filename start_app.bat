@echo off
REM Therapist Bio Generator Launcher
echo Starting Therapist Bio Generator...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if activation worked
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment
    echo Make sure venv exists in this directory
    pause
    exit /b 1
)

REM Run Streamlit app
echo Opening app in your browser...
echo Press Ctrl+C to stop the server
echo.
streamlit run app.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start app
    pause
)
