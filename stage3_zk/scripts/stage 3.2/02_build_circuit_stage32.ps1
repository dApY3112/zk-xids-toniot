# PowerShell Build Script for Stage 3.2 - Semantic Groups
Write-Host "============================================"
Write-Host "Building Semantic Groups Circuit (Stage 3.2)"
Write-Host "============================================"

$ErrorActionPreference = "Stop"

# Paths
$CIRCUIT_REL = "circuits\semantic_groups\semantic_groups.circom"
$OUT_REL = "circuits\semantic_groups\build"
$PTAU_REL = "circuits\semantic_groups\powersOfTau28_hez_final_15.ptau"

Write-Host "Circuit: $CIRCUIT_REL"
Write-Host "Output: $OUT_REL"

# Check ptau (download if needed)
if (-not (Test-Path $PTAU_REL)) {
    Write-Host ""
    Write-Host "Powers of Tau 15 not found. Downloading..."
    & powershell -ExecutionPolicy Bypass -File scripts/00_download_ptau15.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to download ptau"
        exit 1
    }
}

$ptauSize = (Get-Item $PTAU_REL).Length / 1MB
Write-Host "✅ Powers of Tau OK ($([math]::Round($ptauSize, 1)) MB)"

# Create output dir
New-Item -ItemType Directory -Force -Path $OUT_REL | Out-Null

# 1. Compile with WSL circom
Write-Host ""
Write-Host "[1/4] Compiling circuit with WSL circom..."
wsl bash -c "cd '/mnt/c/Paper/Masters thesis/stage3_zk/circuits/semantic_groups' && circom semantic_groups.circom -o build --r1cs --wasm --sym -l ../../node_modules"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Compilation failed"
    exit 1
}
Write-Host "✅ Circuit compiled"

# Verify outputs
$r1csPath = "$OUT_REL\semantic_groups.r1cs"
if (-not (Test-Path $r1csPath)) {
    Write-Host "❌ ERROR: R1CS file not generated"
    exit 1
}

# 2. Setup
Write-Host ""
Write-Host "[2/4] Running Groth16 setup..."
Write-Host "This may take 1-2 minutes for large circuits..."
Push-Location "$OUT_REL"
npx snarkjs groth16 setup semantic_groups.r1cs ..\powersOfTau28_hez_final_15.ptau semantic_groups_0000.zkey
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "❌ Setup failed"
    exit 1
}
Write-Host "✅ Setup complete"

# 3. Contribute
Write-Host ""
Write-Host "[3/4] Contributing to zkey..."
$entropy = -join ((65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object {[char]$_})
npx snarkjs zkey contribute semantic_groups_0000.zkey semantic_groups_final.zkey --name="Stage3.2-Groups" -v -e=$entropy
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "❌ Contribution failed"
    exit 1
}
Write-Host "✅ Contribution complete"

# 4. Export vk
Write-Host ""
Write-Host "[4/4] Exporting verification key..."
npx snarkjs zkey export verificationkey semantic_groups_final.zkey verification_key.json
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "❌ Export failed"
    exit 1
}
Write-Host "✅ Verification key exported"

Pop-Location

# Summary
Write-Host ""
Write-Host "============================================"
Write-Host "✅ Build complete!"
Write-Host "============================================"
Write-Host "Features: 104 (updated from 87)"
Write-Host "Constraints: ~21,500 non-linear + 2,100 linear (est. ~23,600 total)"
Write-Host "Next: python scripts/01_prepare_input_stage32.py 1"
