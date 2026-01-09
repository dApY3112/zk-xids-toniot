pragma circom 2.1.9;

include "../../node_modules/circomlib/circuits/comparators.circom";

// Helper template: Select element from G array based on group ID (1-indexed)
// Helper template: Select element from G array based on group ID (1-indexed)
template Select5() {
    signal input arr[5];
    signal input idx;  // Group ID (1..5)
    signal output out;
    
    component eq[5];
    signal onehot[5];
    
    for (var k = 0; k < 5; k++) {
        eq[k] = IsEqual();
        eq[k].in[0] <== idx;
        eq[k].in[1] <== k + 1;  // Compare with 1,2,3,4,5
        onehot[k] <== eq[k].out;
    }
    
    // PATCH 1: Ensure exactly one match (defensive constraint)
    signal onehot_sum;
    onehot_sum <== onehot[0] + onehot[1] + onehot[2] + onehot[3] + onehot[4];
    onehot_sum === 1;
    
    // Compute output using accumulator to avoid non-quadratic constraint
    signal acc[6];
    acc[0] <== 0;
    acc[1] <== acc[0] + onehot[0] * arr[0];
    acc[2] <== acc[1] + onehot[1] * arr[1];
    acc[3] <== acc[2] + onehot[2] * arr[2];
    acc[4] <== acc[3] + onehot[3] * arr[3];
    acc[5] <== acc[4] + onehot[4] * arr[4];
    
    out <== acc[5];
}

// Helper template: Check group ID is in valid range {1..5}
template CheckGroupId() {
    signal input id;
    
    // id != 0
    component notZero = IsEqual();
    notZero.in[0] <== id;
    notZero.in[1] <== 0;
    notZero.out === 0;
    
    // id <= 5
    component inRange = LessThan(3);
    inRange.in[0] <== id;
    inRange.in[1] <== 6;
    inRange.out === 1;
}

template Top3Explanation(n, nBits, B, maxAbsX, maxAbsW, nGroups) {
    // ========================================================================
    // INPUTS
    // ========================================================================
    signal input x_shifted[n];      // Private: x[i] + maxAbsX
    signal input w_shifted[n];      // Public: w[i] + maxAbsW
    signal input b_shifted;         // Public: b + B
    signal input y_hat;             // Public: prediction (0 or 1)
    signal input top3_ids[3];       // Public: top-3 group IDs (e.g., [2,3,1])
    signal input other2_ids[2];     // Private: remaining 2 group IDs
    
    // ========================================================================
    // CONSTANTS & BOUNDS
    // ========================================================================
    var group_id[104] = [
        5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 5, 5, 1, 1, 1, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2
    ];
    
    var Bc = 70368744177664;  // 2^46
    var nBitsC = 47;
    var BG = 9007199254740992;  // 2^53
    var nBitsG = 54;
    
    // ========================================================================
    // CONSTRAINT 1: y_hat must be binary
    // ========================================================================
    y_hat * (y_hat - 1) === 0;
    
    // ========================================================================
    // CONSTRAINT 2: Range check for shifted inputs
    // ========================================================================
    component xRangeCheck[n];
    component wRangeCheck[n];
    
    for (var i = 0; i < n; i++) {
        xRangeCheck[i] = LessThan(30);
        xRangeCheck[i].in[0] <== x_shifted[i];
        xRangeCheck[i].in[1] <== 2 * maxAbsX + 1;
        xRangeCheck[i].out === 1;
        
        wRangeCheck[i] = LessThan(19);
        wRangeCheck[i].in[0] <== w_shifted[i];
        wRangeCheck[i].in[1] <== 2 * maxAbsW + 1;
        wRangeCheck[i].out === 1;
    }
    
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
    signal c[n];
    
    for (var i = 0; i < n; i++) {
        x[i] <== x_shifted[i] - maxAbsX;
        w[i] <== w_shifted[i] - maxAbsW;
        c[i] <== w[i] * x[i];
    }
    
    b <== b_shifted - B;
    
    // ========================================================================
    // CONSTRAINT 4: Compute score and verify prediction
    // ========================================================================
    signal partialSum[n+1];
    partialSum[0] <== 0;
    
    for (var i = 0; i < n; i++) {
        partialSum[i+1] <== partialSum[i] + c[i];
    }
    
    signal score;
    score <== partialSum[n] + b;
    
    signal score_offset;
    score_offset <== score + B;
    
    component scoreBoundCheck = LessThan(38);
    scoreBoundCheck.in[0] <== score_offset;
    scoreBoundCheck.in[1] <== 2 * B;
    scoreBoundCheck.out === 1;
    
    component scoreSignCheck = LessThan(nBits);
    scoreSignCheck.in[0] <== score_offset;
    scoreSignCheck.in[1] <== B;
    
    signal pred;
    pred <== 1 - scoreSignCheck.out;
    pred === y_hat;
    
    // ========================================================================
    // BLOCK B: Absolute value computation
    // ========================================================================
    signal a[n];
    signal z[n];
    signal c_offset[n];
    
    component cBoundCheck[n];
    component cSignCheck[n];
    
    for (var i = 0; i < n; i++) {
        c_offset[i] <== c[i] + Bc;
        
        cBoundCheck[i] = LessThan(nBitsC);
        cBoundCheck[i].in[0] <== c_offset[i];
        cBoundCheck[i].in[1] <== 2 * Bc;
        cBoundCheck[i].out === 1;
        
        cSignCheck[i] = LessThan(nBitsC);
        cSignCheck[i].in[0] <== c_offset[i];
        cSignCheck[i].in[1] <== Bc;
        z[i] <== cSignCheck[i].out;
        z[i] * (z[i] - 1) === 0;  // Defensive: ensure z is binary
        
        a[i] <== (1 - 2 * z[i]) * c[i];
    }
    
    // ========================================================================
    // BLOCK C: Semantic group aggregation (INTERNAL - NOT PUBLIC)
    // ========================================================================
    signal G[nGroups];
    signal G_acc[nGroups][n+1];
    
    for (var g = 0; g < nGroups; g++) {
        G_acc[g][0] <== 0;
    }
    
    for (var i = 0; i < n; i++) {
        for (var g = 0; g < nGroups; g++) {
            if (group_id[i] == g + 1) {
                G_acc[g][i+1] <== G_acc[g][i] + a[i];
            } else {
                G_acc[g][i+1] <== G_acc[g][i];
            }
        }
    }
    
    component GBoundCheck[nGroups];
    
    for (var g = 0; g < nGroups; g++) {
        G[g] <== G_acc[g][n];
        
        GBoundCheck[g] = LessThan(nBitsG);
        GBoundCheck[g].in[0] <== G[g];
        GBoundCheck[g].in[1] <== BG;
        GBoundCheck[g].out === 1;
    }
    
    // ========================================================================
    // BLOCK D: TOP-3 EXPLANATION VERIFICATION (CORE OF STAGE 3.3)
    // ========================================================================
    
    // Step 1: Range check all group IDs are in {1..5}
    component checkTop3[3];
    component checkOther2[2];
    
    for (var i = 0; i < 3; i++) {
        checkTop3[i] = CheckGroupId();
        checkTop3[i].id <== top3_ids[i];
    }
    
    for (var i = 0; i < 2; i++) {
        checkOther2[i] = CheckGroupId();
        checkOther2[i].id <== other2_ids[i];
    }
    
    // Step 2: All-distinct constraint using IsEqual (10 pairs)
    signal all_ids[5];
    all_ids[0] <== top3_ids[0];
    all_ids[1] <== top3_ids[1];
    all_ids[2] <== top3_ids[2];
    all_ids[3] <== other2_ids[0];
    all_ids[4] <== other2_ids[1];
    
    component neq[10];
    var k = 0;
    
    for (var i = 0; i < 5; i++) {
        for (var j = i+1; j < 5; j++) {
            neq[k] = IsEqual();
            neq[k].in[0] <== all_ids[i];
            neq[k].in[1] <== all_ids[j];
            neq[k].out === 0;  // Must be different
            k++;
        }
    }
    
    // Step 3: Permutation constraint (sum and sum-of-squares)
    signal sum_ids;
    signal sumsq_ids;
    
    sum_ids <== all_ids[0] + all_ids[1] + all_ids[2] + all_ids[3] + all_ids[4];
    sum_ids === 15;  // 1+2+3+4+5 = 15
    
    // Compute sum of squares step by step to avoid non-quadratic constraint
    signal sq[5];
    sq[0] <== all_ids[0] * all_ids[0];
    sq[1] <== all_ids[1] * all_ids[1];
    sq[2] <== all_ids[2] * all_ids[2];
    sq[3] <== all_ids[3] * all_ids[3];
    sq[4] <== all_ids[4] * all_ids[4];
    
    sumsq_ids <== sq[0] + sq[1] + sq[2] + sq[3] + sq[4];
    sumsq_ids === 55;  // 1²+2²+3²+4²+5² = 55
    
    // Step 4: Map group IDs to G values using Select5
    signal G_mapped[5];
    component sel[5];
    
    for (var idx = 0; idx < 5; idx++) {
        sel[idx] = Select5();
        sel[idx].arr <== G;
        sel[idx].idx <== all_ids[idx];
        G_mapped[idx] <== sel[idx].out;
    }
    
    // PATCH 2: Defensive bound check for mapped values (optional but formal)
    component gmBoundCheck[5];
    for (var idx = 0; idx < 5; idx++) {
        gmBoundCheck[idx] = LessThan(nBitsG);
        gmBoundCheck[idx].in[0] <== G_mapped[idx];
        gmBoundCheck[idx].in[1] <== BG;
        gmBoundCheck[idx].out === 1;
    }
    
    // Step 5: Dominance constraint - top3 >= others
    // G_mapped[0..2] are top3, G_mapped[3..4] are others
    // Use LessThan to check: A >= B <=> NOT(A < B)
    component dominance[6];  // 3 × 2 = 6 comparisons
    var dom_idx = 0;
    
    for (var t = 0; t < 3; t++) {
        for (var o = 3; o < 5; o++) {
            dominance[dom_idx] = LessThan(nBitsG);
            dominance[dom_idx].in[0] <== G_mapped[t];
            dominance[dom_idx].in[1] <== G_mapped[o];
            dominance[dom_idx].out === 0;  // NOT less than => greater or equal
            dom_idx++;
        }
    }
    
    // Step 6: Ordering constraint (deterministic top-3)
    // G[top3[0]] >= G[top3[1]] >= G[top3[2]]
    // Note: Ties are allowed (non-strict inequality). If G values are equal,
    // any valid permutation satisfying dominance is accepted. This is defendable
    // as "deterministic up to equivalence class of tied groups".
    component order01 = LessThan(nBitsG);
    order01.in[0] <== G_mapped[0];
    order01.in[1] <== G_mapped[1];
    order01.out === 0;  // G0 >= G1
    
    component order12 = LessThan(nBitsG);
    order12.in[0] <== G_mapped[1];
    order12.in[1] <== G_mapped[2];
    order12.out === 0;  // G1 >= G2
}

// Public: w_shifted[104], b_shifted, y_hat, top3_ids[3]
// Private: x_shifted[104], other2_ids[2]
component main {public [w_shifted, b_shifted, y_hat, top3_ids]} = 
    Top3Explanation(104, 37, 68719476736, 297270816, 122130, 5);