# PowerShell Build Script for Windows - WSL Circom Version
Write-Host "============================================"
Write-Host "Building Inference Only Circuit"
Write-Host "============================================"

$ErrorActionPreference = "Stop"

# Paths
$CIRCUIT_REL = "circuits\inference_only\inference_only.circom"
$OUT_REL = "circuits\inference_only\build"
$PTAU_REL = "circuits\inference_only\powersOfTau28_hez_final_12.ptau"

Write-Host "Circuit: $CIRCUIT_REL"
Write-Host "Output: $OUT_REL"

# Check ptau
if (-not (Test-Path $PTAU_REL)) {
    Write-Host "ERROR: Powers of Tau not found"
    exit 1
}

$ptauSize = (Get-Item $PTAU_REL).Length / 1MB
Write-Host "Powers of Tau OK ($([math]::Round($ptauSize, 1)) MB)"

# Create output dir
New-Item -ItemType Directory -Force -Path $OUT_REL | Out-Null

# 1. Compile with WSL circom
Write-Host ""
Write-Host "[1/4] Compiling circuit with WSL circom..."
wsl bash -c "cd '/mnt/c/Paper/Masters thesis/stage3_zk/circuits/inference_only' && circom inference_only.circom -o build --r1cs --wasm --sym -l ../../node_modules"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Compilation failed"
    exit 1
}
Write-Host "Circuit compiled"

# Verify outputs
$r1csPath = "$OUT_REL\inference_only.r1cs"
if (-not (Test-Path $r1csPath)) {
    Write-Host "ERROR: R1CS file not generated"
    exit 1
}

# 2. Setup
Write-Host ""
Write-Host "[2/4] Running Groth16 setup..."
Push-Location "$OUT_REL"
npx snarkjs groth16 setup inference_only.r1cs ..\powersOfTau28_hez_final_12.ptau inference_only_0000.zkey
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "Setup failed"
    exit 1
}
Write-Host "Setup complete"

# 3. Contribute
Write-Host ""
Write-Host "[3/4] Contributing to zkey..."
$entropy = -join ((65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object {[char]$_})
npx snarkjs zkey contribute inference_only_0000.zkey inference_only_final.zkey --name="Stage3.1-37bit" -v -e=$entropy
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "Contribution failed"
    exit 1
}
Write-Host "Contribution complete"

# 4. Export vk
Write-Host ""
Write-Host "[4/4] Exporting verification key..."
npx snarkjs zkey export verificationkey inference_only_final.zkey verification_key.json
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "Export failed"
    exit 1
}
Write-Host "Verification key exported"

Pop-Location

# Summary
Write-Host ""
Write-Host "============================================"
Write-Host "Build complete!"
Write-Host "============================================"
Write-Host "Next: python scripts/01_prepare_input.py 1"
