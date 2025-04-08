@echo off
REM Launch backend
start "" cmd /k "cd /d D:\Projects\web-history-manager\web-history-backend && D:\Projects\web-history-manager\venv\Scripts\python.exe app.py"

REM Launch frontend
cd /d "D:\Projects\web-history-manager\web-history-frontend"
start "" cmd /k "npm start"
