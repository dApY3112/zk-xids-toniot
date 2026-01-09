#!/bin/bash
set -e

echo "============================================"
echo "Stage 3.1 Setup - Inference Only Circuit"
echo "============================================"

cd "$(dirname "$0")/.."

# 1. Install Node.js dependencies
echo ""
echo "[1/3] Installing npm dependencies..."
npm install circomlib snarkjs circom

# 2. Download Powers of Tau (UPDATED LINK)
PTAU="circuits/inference_only/powersOfTau28_hez_final_12.ptau"
if [ ! -f "$PTAU" ]; then
    echo ""
    echo "[2/3] Downloading Powers of Tau (12)..."
    mkdir -p circuits/inference_only
    
    # NEW LINK: Use iden3 official GitHub release
    curl -L -o "$PTAU" \
        https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_12.ptau
    
    echo "✅ Downloaded: $PTAU"
else
    echo ""
    echo "[2/3] Powers of Tau already exists, skipping..."
fi

# 3. Create output directories
echo ""
echo "[3/3] Creating output directories..."
mkdir -p circuits/inference_only/build
mkdir -p outputs/proofs

echo ""
echo "============================================"
echo "✅ Setup complete!"
echo "============================================"
echo "Next step: Run 02_build_circuit.sh"