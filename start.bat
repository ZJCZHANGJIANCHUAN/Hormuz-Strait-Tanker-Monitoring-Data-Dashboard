@echo off
echo ============================================
echo  霍尔木兹海峡油轮监测数据看板
echo  Hormuz Strait Oil Tanker Monitoring Dashboard
echo ============================================
echo.

echo [1/4] Starting backend server...
start "Backend" cmd /c "cd /d %~dp0backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo Backend started on http://localhost:8000

echo [2/4] Seeding initial data...
timeout /t 3 /nobreak >nul
cd /d %~dp0backend && python seed.py

echo [3/4] Starting frontend dev server...
start "Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"
echo Frontend started on http://localhost:5173

echo.
echo [4/4] Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo Dashboard is running!
echo Backend API: http://localhost:8000/docs
echo Frontend:   http://localhost:5173
echo.
pause
