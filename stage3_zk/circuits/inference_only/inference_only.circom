pragma circom 2.1.9;

include "../../node_modules/circomlib/circuits/comparators.circom";

template InferenceOnly(n, nBits, B, maxAbsX) {
    signal input x_shifted[n]; // Private: x[i] + maxAbsX (non-negative)
    signal input w[n];         // Public: model weights  
    signal input b;            // Public: model bias
    signal input y_hat;        // Public: prediction
    
    // Constraint 1: y_hat must be binary (0 or 1)
    y_hat * (y_hat - 1) === 0;
    
    // Constraint 2: Range check for shifted inputs
    // Ensure x_shifted[i] in [0, 2*maxAbsX] (covers x in [-maxAbsX, maxAbsX])
    component xRangeCheck[n];
    
    for (var i = 0; i < n; i++) {
        xRangeCheck[i] = LessThan(30); // 2^30 = 1,073,741,824 > 2*maxAbsX = 594,541,632
        xRangeCheck[i].in[0] <== x_shifted[i];
        xRangeCheck[i].in[1] <== 2 * maxAbsX + 1; // Inclusive: x_shifted <= 2*maxAbsX
        xRangeCheck[i].out === 1;
    }
    
    // Constraint 3: Recover signed x[i] and compute score = w^T x + b
    signal x[n];
    signal partialSum[n+1];
    partialSum[0] <== 0;
    
    for (var i = 0; i < n; i++) {
        x[i] <== x_shifted[i] - maxAbsX; // Recover signed value
        partialSum[i+1] <== partialSum[i] + w[i] * x[i];
    }
    
    signal score;
    score <== partialSum[n] + b;
    
    // Constraint 4: Offset score to non-negative range
    signal score_offset;
    score_offset <== score + B;
    
    // Constraint 5: Defensive bound check (0 <= score_offset < 2*B)
    component boundCheck = LessThan(38);
    boundCheck.in[0] <== score_offset;
    boundCheck.in[1] <== 2 * B;
    boundCheck.out === 1;
    
    // Constraint 6: Sign check (score >= 0 ?)
    component lt = LessThan(nBits);
    lt.in[0] <== score_offset;
    lt.in[1] <== B;
    
    signal pred;
    pred <== 1 - lt.out;
    
    // Constraint 7: Predicted value must match y_hat
    pred === y_hat;
}

// Public: w[104], b, y_hat | Private: x_shifted[104]
// maxAbsX = 297270816 (from bounds.json: max_abs_x_int)
component main {public [w, b, y_hat]} = InferenceOnly(104, 37, 68719476736, 297270816);
