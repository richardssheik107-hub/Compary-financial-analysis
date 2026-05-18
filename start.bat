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

echo.
echo Starting Dabaihua Financial Reports...
echo Open http://localhost:8501 if the browser does not open automatically.
python -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
