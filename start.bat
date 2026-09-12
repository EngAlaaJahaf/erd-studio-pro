@echo off
title TESTR ERD Studio Pro Server
cd /d "%~dp0"
echo ========================================================
echo   TESTR ERD Studio Pro - Standalone Application
echo   SQLite Database: data\app.db
echo   Backend Server: FastAPI / Uvicorn (Port 8500)
echo ========================================================
echo.
echo Starting backend server and launching browser...

start http://localhost:8500
python server.py

pause
