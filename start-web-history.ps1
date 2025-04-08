Start-Process "D:\Projects\web-history-manager\venv\Scripts\python.exe" `
  -ArgumentList "D:\Projects\web-history-manager\web-history-backend\app.py" `
  -WorkingDirectory "D:\Projects\web-history-manager\web-history-backend"

Start-Process -WorkingDirectory "D:\Projects\web-history-manager\web-history-frontend" "cmd.exe" -ArgumentList "/k npm start"
