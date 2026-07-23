$PORT = 7861
$APP_FILE = "space_agent_v2.py"

Write-Host "=== Space Agent Service Manager ===" -ForegroundColor Cyan

# 1. Check and stop existing process on the port
$portConnection = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue

if ($portConnection) {
    $portProcess = $portConnection | Select-Object -ExpandProperty OwningProcess -Unique
    Write-Host "Existing process found on port $PORT (PID: $portProcess). Stopping..." -ForegroundColor Yellow
    Stop-Process -Id $portProcess -Force
    Start-Sleep -Seconds 2
    Write-Host "Process stopped." -ForegroundColor Green
} else {
    Write-Host "No active process found on port $PORT." -ForegroundColor Gray
}

# 2. Start Streamlit application
Write-Host "Launching Space Agent Dashboard on port $PORT..." -ForegroundColor Cyan
Start-Process -FilePath "streamlit" -ArgumentList "run $APP_FILE --server.port $PORT --server.headless true" -WindowStyle Hidden

Start-Sleep -Seconds 3

# 3. Output Confirmation
Write-Host "----------------------------------------------------" -ForegroundColor Gray
Write-Host "Space Agent Started Successfully!" -ForegroundColor Green
Write-Host "Access Dashboard at: http://localhost:$PORT" -ForegroundColor Yellow
Write-Host "----------------------------------------------------" -ForegroundColor Gray