@echo off
title Kikis Auto Captions - server
cd /d "%~dp0"
start "Kikis Auto Captions - server" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
timeout /t 3 /nobreak >nul
start http://localhost:8001
