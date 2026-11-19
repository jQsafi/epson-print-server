# PowerShell 1-Click Startup for Epson Print & Scan Gateway on Windows 11
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Epson L3110 All-in-One Gateway (Windows 11)" -ForegroundColor Cyan
Write-Host "  Python Hardware Engine + Node.js Web Dashboard" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Dependency Checks
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js is not installed or not in PATH." -ForegroundColor Red
    Exit 1
}

# 2. Install Packages
Write-Host "[*] Checking Python dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt --quiet

Write-Host "[*] Checking Node.js dependencies..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\web"
if (-not (Test-Path "node_modules")) {
    npm install --silent
}
Set-Location -Path $PSScriptRoot

# 3. Start Python Background Process
Write-Host "[*] Launching Python Hardware Engine & AirPrint..." -ForegroundColor Green
$pyProc = Start-Process python -ArgumentList "-m server.main" -WindowStyle Hidden -PassThru

# 4. Open Browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"

# 5. Run Node.js Server in Foreground
Write-Host "[*] Node.js Dashboard running at http://localhost:3000" -ForegroundColor Green
try {
    Set-Location -Path "$PSScriptRoot\web"
    node server.js
} finally {
    if ($pyProc -and -not $pyProc.HasExited) {
        Stop-Process -Id $pyProc.Id -Force -ErrorAction SilentlyContinue
    }
}
