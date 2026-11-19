$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$testDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $testDir
$backend = Join-Path $root "deliverables\backend"
$frontend = Join-Path $root "deliverables\frontend"
$agentHost = Join-Path $root "deliverables\agent-host"
$reports = Join-Path $testDir "reports"
$startedServer = $null
$results = [ordered]@{}

New-Item -ItemType Directory -Path $reports -Force | Out-Null

function Invoke-Step {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "== $Name =="
    Push-Location $WorkingDirectory
    try {
        & $Action
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
        $results[$Name] = "passed"
    }
    finally {
        Pop-Location
    }
}

try {
    $health = $null
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
    }
    catch {
        $outLog = Join-Path $root "data\test-server.out.log"
        $errLog = Join-Path $root "data\test-server.err.log"
        $startedServer = Start-Process -FilePath "python" `
            -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
            -WorkingDirectory $backend `
            -WindowStyle Hidden `
            -RedirectStandardOutput $outLog `
            -RedirectStandardError $errLog `
            -PassThru
        for ($index = 0; $index -lt 30; $index++) {
            Start-Sleep -Milliseconds 500
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
                break
            }
            catch {
                continue
            }
        }
        if (-not $health) {
            throw "FastAPI did not become ready"
        }
    }

    Invoke-Step "backend-tests" $backend {
        python -m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80
    }
    Invoke-Step "agent-host-build" $agentHost {
        npm run build
    }
    Invoke-Step "frontend-build" $frontend {
        npm run build
    }
    Invoke-Step "browser-e2e" $root {
        node "$testDir\e2e\jagent.e2e.mjs"
    }

    $results["status"] = "passed"
    $exitCode = 0
}
catch {
    $results["status"] = "failed"
    $results["error"] = $_.Exception.Message
    $exitCode = 1
}
finally {
    if ($startedServer -and -not $startedServer.HasExited) {
        Stop-Process -Id $startedServer.Id -Force -ErrorAction SilentlyContinue
    }
    $results["finished_at"] = (Get-Date).ToString("o")
    $results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $reports "test-summary.json") -Encoding utf8
    Write-Host ""
    $results | ConvertTo-Json -Depth 6
}

exit $exitCode

