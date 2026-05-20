@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -3 -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
set "APP_PORT=8502"

echo.
echo Starting Dabaihua Financial Reports...
echo Open http://localhost:%APP_PORT% if the browser does not open automatically.
python -m streamlit run app.py --server.port %APP_PORT% --server.headless true --browser.gatherUsageStats false
