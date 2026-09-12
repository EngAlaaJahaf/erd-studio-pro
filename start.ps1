# TESTR ERD Studio Pro - PowerShell Launcher
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  TESTR ERD Studio Pro - Standalone Application" -ForegroundColor White
Write-Host "  SQLite Database: data\app.db" -ForegroundColor Gray
Write-Host "  Backend Server: FastAPI (Port 8500)" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan

Start-Process "http://localhost:8500"
python server.py
