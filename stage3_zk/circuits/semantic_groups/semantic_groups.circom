pragma circom 2.1.9;

include "../../node_modules/circomlib/circuits/comparators.circom";

template SemanticGroups(n, nBits, B, maxAbsX, maxAbsW, nGroups) {
    // ========================================================================
    // INPUTS (all shifted to unsigned for safe comparisons)
    // ========================================================================
    signal input x_shifted[n];   // Private: x[i] + maxAbsX (non-negative)
    signal input w_shifted[n];   // Public: w[i] + maxAbsW (non-negative)
    signal input b_shifted;      // Public: b + B (non-negative)
    signal input y_hat;          // Public: prediction (0 or 1)
    signal input G[nGroups];     // Public: semantic group contributions (for verification)
    
    // ========================================================================
    // CONSTANTS & BOUNDS
    // ========================================================================
    // Hardcoded group mapping (from group_map.json: feature_index_to_group_id)
    // Groups: 1=Protocol, 2=Application, 3=ConnectionState, 4=Ports, 5=TrafficVolume
    var group_id[104] = [
        5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 5, 5, 1, 1, 1, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2
    ];
    
    // Contribution bounds: max_abs_c = max_abs_x * max_abs_w ~ 297270816 * 122130 ~ 3.63e13 ~ 2^45
    // Safe bound: Bc = 2^46 = 70368744177664
    var Bc = 70368744177664;
    var nBitsC = 47;  // To check c_offset in [0, 2*Bc) < 2^47
    
    // Group sum bound: max sum ~= n * max_abs_c ~ 104 * 3.63e13 ~ 3.78e15 ~ 2^52
    // Safe bound: BG = 2^53 = 9007199254740992
    var BG = 9007199254740992;
    var nBitsG = 54;  // To check G in [0, BG) < 2^54
    
    // ========================================================================
    // CONSTRAINT 1: y_hat must be binary (0 or 1)
    // ========================================================================
    y_hat * (y_hat - 1) === 0;
    
    // ========================================================================
    // CONSTRAINT 2: Range check for shifted inputs
    // ========================================================================
    component xRangeCheck[n];
    component wRangeCheck[n];
    
    for (var i = 0; i < n; i++) {
        // x_shifted in [0, 2*maxAbsX] → need 2*297270816+1 = 594541633 < 2^30
        xRangeCheck[i] = LessThan(30);
        xRangeCheck[i].in[0] <== x_shifted[i];
        xRangeCheck[i].in[1] <== 2 * maxAbsX + 1;
        xRangeCheck[i].out === 1;
        
        // w_shifted in [0, 2*maxAbsW] → need 2*122130+1 = 244261 < 2^19
        wRangeCheck[i] = LessThan(19);
        wRangeCheck[i].in[0] <== w_shifted[i];
        wRangeCheck[i].in[1] <== 2 * maxAbsW + 1;
        wRangeCheck[i].out === 1;
    }
    
    // b_shifted in [0, 2*B] → need 2*2^36+1 < 2^38
    component bRangeCheck = LessThan(38);
    bRangeCheck.in[0] <== b_shifted;
    bRangeCheck.in[1] <== 2 * B + 1;
    bRangeCheck.out === 1;
    
    // ========================================================================
    // CONSTRAINT 3: Recover signed values and compute contributions
    // ========================================================================
    signal x[n];
    signal w[n];
    signal b;
    signal c[n];  // Feature contributions: c[i] = w[i] * x[i]
    
    for (var i = 0; i < n; i++) {
        x[i] <== x_shifted[i] - maxAbsX;  // Recover x in [-maxAbsX, maxAbsX]
        w[i] <== w_shifted[i] - maxAbsW;  // Recover w in [-maxAbsW, maxAbsW]
        c[i] <== w[i] * x[i];              // BLOCK A: Feature contributions
    }
    
    b <== b_shifted - B;  // Recover b in [-B, B]
    
    // ========================================================================
    // CONSTRAINT 4: Compute score from contributions
    // ========================================================================
    signal partialSum[n+1];
    partialSum[0] <== 0;
    
    for (var i = 0; i < n; i++) {
        partialSum[i+1] <== partialSum[i] + c[i];
    }
    
    signal score;
    score <== partialSum[n] + b;
    
    // ========================================================================
    // CONSTRAINT 5: Score offset and bound check
    // ========================================================================
    signal score_offset;
    score_offset <== score + B;
    
    // Defensive bound check: score_offset in [0, 2*B) < 2^37
    // Use 38 bits to be safe (covers up to 2^38)
    component scoreBoundCheck = LessThan(38);
    scoreBoundCheck.in[0] <== score_offset;
    scoreBoundCheck.in[1] <== 2 * B + 1;
    scoreBoundCheck.out === 1;
    
    // ========================================================================
    // CONSTRAINT 6: Sign check (score >= 0 ?)
    // ========================================================================
    // score_offset < B means score < 0
    // nBits = 37 is tight for score_offset range [0, 2*B) where 2*B < 2^37
    component scoreSignCheck = LessThan(nBits);
    scoreSignCheck.in[0] <== score_offset;
    scoreSignCheck.in[1] <== B;
    
    signal pred;
    pred <== 1 - scoreSignCheck.out;  // pred = 1 if score >= 0
    
    // ========================================================================
    // CONSTRAINT 7: Predicted value must match y_hat
    // ========================================================================
    pred === y_hat;
    
    // ========================================================================
    // BLOCK B: Absolute value computation |c[i]| (DEFENDABLE)
    // ========================================================================
    signal a[n];     // Absolute values: a[i] = |c[i]|
    signal z[n];     // Sign bits: z[i] ∈ {0,1}
    signal c_offset[n];
    
    component cBoundCheck[n];
    component cSignCheck[n];
    
    for (var i = 0; i < n; i++) {
        // Offset contribution for safe comparison: c_offset = c + Bc
        c_offset[i] <== c[i] + Bc;
        
        // Range check: ensure c is within [-Bc, Bc) by checking c_offset in [0, 2*Bc)
        cBoundCheck[i] = LessThan(nBitsC);
        cBoundCheck[i].in[0] <== c_offset[i];
        cBoundCheck[i].in[1] <== 2 * Bc;
        cBoundCheck[i].out === 1;
        
        // Sign check: z = 1 if c < 0  <=> (c + Bc) < Bc
        cSignCheck[i] = LessThan(nBitsC);
        cSignCheck[i].in[0] <== c_offset[i];
        cSignCheck[i].in[1] <== Bc;
        z[i] <== cSignCheck[i].out;  // z is constrained to {0,1} by LessThan output

        
        // Compute absolute value: a = c if z=0, else -c
        // Formula: a = (1 - 2*z) * c
        // When z=0: a = c
        // When z=1: a = -c
        a[i] <== (1 - 2 * z[i]) * c[i];
        
        // Enforce a in [0, Bc) to prevent wrap (defensive check)
        // This ensures a is properly non-negative after abs operation
        // Note: a is guaranteed to be in [0, Bc) by construction:
        // - c is range-checked via cBoundCheck to be in [-Bc, Bc)
        // - z is binary (LessThan output)
        // - a = (1-2z)*c ensures a = |c|
        // Therefore, no additional bound check needed for a
    }
    
    // ========================================================================
    // BLOCK C: Semantic group aggregation (OPTIMIZED)
    // ========================================================================
    signal G_computed[nGroups];
    signal G_acc[nGroups][n+1];  // Accumulator for each group
    
    // Initialize accumulators to 0
    for (var g = 0; g < nGroups; g++) {
        G_acc[g][0] <== 0;
    }
    
    // Accumulate contributions: for each feature, add a[i] to its group
    for (var i = 0; i < n; i++) {
        for (var g = 0; g < nGroups; g++) {
            if (group_id[i] == g + 1) {  // group_id is 1-indexed
                G_acc[g][i+1] <== G_acc[g][i] + a[i];
            } else {
                G_acc[g][i+1] <== G_acc[g][i];
            }
        }
    }
    
    // Final group contributions with bound checks
    component GBoundCheck[nGroups];
    
    for (var g = 0; g < nGroups; g++) {
        G_computed[g] <== G_acc[g][n];
        
        // Bound check: ensure G doesn't wrap (defensive)
        GBoundCheck[g] = LessThan(nBitsG);
        GBoundCheck[g].in[0] <== G_computed[g];
        GBoundCheck[g].in[1] <== BG;
        GBoundCheck[g].out === 1;
        
        // Constraint: computed group contribution must match public input
        G_computed[g] === G[g];
    }
}

// Public: w_shifted[104], b_shifted, y_hat, G[5] | Private: x_shifted[104]
// maxAbsX = 297270816 (from bounds.json: max_abs_x_int)
// maxAbsW = 122130 (from bounds.json: max_abs_w_int)
// B = 2^36 = 68719476736
// nBits = 37 (for score sign check: score_offset < 2^37)
// nGroups = 5
component main {public [w_shifted, b_shifted, y_hat, G]} = SemanticGroups(104, 37, 68719476736, 297270816, 122130, 5);