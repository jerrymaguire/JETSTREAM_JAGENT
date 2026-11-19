$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "deliverables\backend"
$frontendDist = Join-Path $root "deliverables\frontend\dist"

if (-not (Test-Path -LiteralPath (Join-Path $frontendDist "index.html"))) {
    throw "前端尚未构建：请先在 deliverables\frontend 运行 npm install 和 npm run build"
}

$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Start-Process "http://127.0.0.1:8000"
    return
}

$outLog = Join-Path $root "data\server.out.log"
$errLog = Join-Path $root "data\server.err.log"
$process = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backend `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:8000"
Write-Host "AgentShow started. PID=$($process.Id)"
Write-Host "URL=http://127.0.0.1:8000"

