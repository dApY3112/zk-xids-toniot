#!/bin/bash
set -e

SAMPLE_ID=${1:-1}

echo "============================================"
echo "Generating ZK Proof Stage 3.2 (Sample $SAMPLE_ID)"
echo "============================================"

cd "$(dirname "$0")/../.."

OUT="circuits/semantic_groups/build"
WASM="$OUT/semantic_groups_js/semantic_groups.wasm"
ZKEY="$OUT/semantic_groups_final.zkey"
INPUT="$OUT/input_sample_${SAMPLE_ID}.json"
WITNESS="$OUT/witness.wtns"
PROOF="outputs/proofs/proof_stage32_sample_${SAMPLE_ID}.json"
PUBLIC="outputs/proofs/public_stage32_sample_${SAMPLE_ID}.json"

# Check input exists
if [ ! -f "$INPUT" ]; then
    echo "❌ ERROR: Input not found at $INPUT"
    echo "Run: python scripts/01_prepare_input_stage32.py $SAMPLE_ID"
    exit 1
fi

# 1. Generate witness
echo ""
echo "[1/2] Generating witness..."
START=$(date +%s%N)

node "$OUT/semantic_groups_js/generate_witness.js" \
    "$WASM" \
    "$INPUT" \
    "$WITNESS"

WITNESS_TIME=$(( ($(date +%s%N) - START) / 1000000 ))
echo "✅ Witness generated (${WITNESS_TIME}ms)"

# 2. Generate proof
echo ""
echo "[2/2] Generating proof..."
START=$(date +%s%N)

npx snarkjs groth16 prove \
    "$ZKEY" \
    "$WITNESS" \
    "$PROOF" \
    "$PUBLIC"

PROOF_TIME=$(( ($(date +%s%N) - START) / 1000000 ))
PROOF_SIZE=$(stat -f%z "$PROOF" 2>/dev/null || stat -c%s "$PROOF")

echo "✅ Proof generated (${PROOF_TIME}ms)"

# Summary
echo ""
echo "============================================"
echo "✅ Proof Generation Complete!"
echo "============================================"
echo "Witness time: ${WITNESS_TIME}ms"
echo "Proof time:   ${PROOF_TIME}ms"
echo "Proof size:   ${PROOF_SIZE} bytes"
echo ""
echo "Outputs:"
echo "  - $PROOF"
echo "  - $PUBLIC"
echo ""
echo "Next: wsl bash scripts/04_verify_proof_stage32.sh $SAMPLE_ID"