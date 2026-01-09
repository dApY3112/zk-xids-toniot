# Download Powers of Tau 15 for Stage 3.2
Write-Host "============================================"
Write-Host "Downloading Powers of Tau 15"
Write-Host "============================================"

$ErrorActionPreference = "Stop"

$PTAU_PATH = "circuits\semantic_groups\powersOfTau28_hez_final_15.ptau"

if (Test-Path $PTAU_PATH) {
    $size = (Get-Item $PTAU_PATH).Length / 1MB
    Write-Host "✅ Powers of Tau 15 already exists ($([math]::Round($size, 1)) MB)"
    exit 0
}

Write-Host ""
Write-Host "Downloading from Hermez ceremony..."
Write-Host "URL: https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_15.ptau"
Write-Host "Size: ~49 MB"
Write-Host ""

New-Item -ItemType Directory -Force -Path "circuits\semantic_groups" | Out-Null

# Download using curl (built-in Windows 10+)
curl.exe -L -o $PTAU_PATH "https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_15.ptau"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Download failed"
    exit 1
}

$size = (Get-Item $PTAU_PATH).Length / 1MB
Write-Host ""
Write-Host "✅ Downloaded: $PTAU_PATH ($([math]::Round($size, 1)) MB)"