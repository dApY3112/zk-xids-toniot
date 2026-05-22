# Compile script for Stage 3.4 - Exact SHAP Top-3
# Requires Circom 2.1.9. This mirrors the existing Stage 3 scripts and uses WSL
# when the thesis environment has the Rust Circom binary installed there.

Set-Location "C:\Paper\Masters thesis\stage3_zk"

Write-Host "============================================"
Write-Host "Compiling Exact SHAP Top-3 Circuit (Stage 3.4)"
Write-Host "============================================"

$ErrorActionPreference = "Stop"

$CIRCUIT_REL = "circuits\exact_shap_top3\exact_shap_top3.circom"
$OUT_REL = "circuits\exact_shap_top3\build"

Write-Host "Circuit: $CIRCUIT_REL"
Write-Host "Output: $OUT_REL"

New-Item -ItemType Directory -Force -Path $OUT_REL | Out-Null

Write-Host ""
Write-Host "[1/1] Compiling circuit with WSL Circom 2.1.9..."
wsl bash -c "cd '/mnt/c/Paper/Masters thesis/stage3_zk/circuits/exact_shap_top3' && /usr/local/bin/circom exact_shap_top3.circom -o build --r1cs --wasm --sym -l ../../node_modules"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Compilation failed"
    Write-Host "Make sure WSL has Circom 2.1.9 installed at /usr/local/bin/circom."
    exit 1
}

$r1csPath = "$OUT_REL\exact_shap_top3.r1cs"
$wasmPath = "$OUT_REL\exact_shap_top3_js\exact_shap_top3.wasm"

if (-not (Test-Path $r1csPath)) {
    Write-Host "ERROR: R1CS file not generated"
    exit 1
}

if (-not (Test-Path $wasmPath)) {
    Write-Host "ERROR: WASM file not generated"
    exit 1
}

Write-Host ""
Write-Host "Stage 3.4 compile complete."
Write-Host "Next:"
Write-Host "  python ""scripts/stage 3.4/01_prepare_input_stage34.py"" 1"
Write-Host "  python ""scripts/stage 3.4/03_witness_smoke_stage34.py"" 1"
