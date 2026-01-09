#!/bin/bash
set -e

SAMPLE_ID=${1:-1}

echo "============================================"
echo "Verifying ZK Proof (Sample $SAMPLE_ID)"
echo "============================================"

cd "$(dirname "$0")/../.."

VK="circuits/inference_only/build/verification_key.json"
PROOF="outputs/proofs/proof_sample_${SAMPLE_ID}.json"
PUBLIC="outputs/proofs/public_sample_${SAMPLE_ID}.json"

# Check files exist
if [ ! -f "$PROOF" ]; then
    echo "❌ ERROR: Proof not found at $PROOF"
    exit 1
fi

echo ""
echo "Verifying..."
START=$(date +%s%N)

npx snarkjs groth16 verify \
    "$VK" \
    "$PUBLIC" \
    "$PROOF"

VERIFY_TIME=$(( ($(date +%s%N) - START) / 1000000 ))

echo ""
echo "============================================"
echo "✅ Verification Complete!"
echo "============================================"
echo "Verify time: ${VERIFY_TIME}ms"
echo ""
echo "Result: VALID ✅"