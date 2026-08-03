pragma circom 2.1.9;

include "../../node_modules/circomlib/circuits/comparators.circom";
include "../../node_modules/circomlib/circuits/poseidon.circom";

// Select an element from a 5-element array using a 1-indexed group ID.
template Select5() {
    signal input arr[5];
    signal input idx;
    signal output out;

    component eq[5];
    signal onehot[5];

    for (var k = 0; k < 5; k++) {
        eq[k] = IsEqual();
        eq[k].in[0] <== idx;
        eq[k].in[1] <== k + 1;
        onehot[k] <== eq[k].out;
    }

    signal onehot_sum;
    onehot_sum <== onehot[0] + onehot[1] + onehot[2] + onehot[3] + onehot[4];
    onehot_sum === 1;

    signal acc[6];
    acc[0] <== 0;
    acc[1] <== acc[0] + onehot[0] * arr[0];
    acc[2] <== acc[1] + onehot[1] * arr[1];
    acc[3] <== acc[2] + onehot[2] * arr[2];
    acc[4] <== acc[3] + onehot[3] * arr[3];
    acc[5] <== acc[4] + onehot[4] * arr[4];

    out <== acc[5];
}

template CheckGroupId() {
    signal input id;

    component notZero = IsEqual();
    notZero.in[0] <== id;
    notZero.in[1] <== 0;
    notZero.out === 0;

    component inRange = LessThan(3);
    inRange.in[0] <== id;
    inRange.in[1] <== 6;
    inRange.out === 1;
}

// Rolling Poseidon commitment over:
//   domain tag, public metadata hash, private salt, private x_shifted[104].
//
// circomlib's Poseidon template supports up to 16 inputs in this version, so
// the 104-dimensional input is absorbed in fixed 16-input chunks.
template RollingInputCommitment(n) {
    signal input x_shifted[n];
    signal input metadata_hash;
    signal input salt;
    signal output out;

    var DOMAIN_STAGE35_INPUT = 350035;

    component first = Poseidon(16);
    first.inputs[0] <== DOMAIN_STAGE35_INPUT;
    first.inputs[1] <== metadata_hash;
    first.inputs[2] <== salt;
    for (var i = 0; i < 13; i++) {
        first.inputs[i + 3] <== x_shifted[i];
    }

    component chunk[7];
    for (var c = 0; c < 7; c++) {
        chunk[c] = Poseidon(16);
        if (c == 0) {
            chunk[c].inputs[0] <== first.out;
        } else {
            chunk[c].inputs[0] <== chunk[c - 1].out;
        }

        for (var j = 0; j < 15; j++) {
            var idx = 13 + c * 15 + j;
            if (idx < n) {
                chunk[c].inputs[j + 1] <== x_shifted[idx];
            } else {
                chunk[c].inputs[j + 1] <== 0;
            }
        }
    }

    out <== chunk[6].out;
}

template ExactShapTop3(n, nBits, B, maxAbsX, maxAbsW, nGroups) {
    signal input x_shifted[n];      // Private: x_int[i] + maxAbsX
    signal input w_shifted[n];      // Public: w_int[i] + maxAbsW
    signal input b_shifted;         // Public: b_int + B
    signal input metadata_hash;      // Public: event/log metadata commitment preimage hash
    signal input salt;               // Private: per-event commitment salt
    signal input y_hat;             // Public prediction
    signal input top3_ids[3];       // Public top-3 semantic groups by abs(Exact SHAP)
    signal input other2_ids[2];     // Private remaining group IDs
    signal output input_commitment;  // Public output: Poseidon commitment to metadata, salt, and x_shifted

    var group_id[104] = [
        5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 5, 5, 1, 1, 1, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2
    ];

    // x_ref_int = round(training_mean_processed * Sx), generated in
    // stage3_zk/artifacts/exact_shap_reference.json.
    var x_ref_int[104] = [
        0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 54, 60536, 4946, 49586,
        1, 0, 0, 4618, 45, 0, 1, 0, 0, 0, 1, 10099, 0, 19, 0, 0,
        0, 0, 0, 0, 0, 0, 1, 22, 0, 1123, 0, 20, 2165, 17108, 636,
        988, 65, 53, 14517, 6226, 102, 7219, 14781, 145, 1531, 31,
        0, 0, 65467, 38, 68, 65468, 65468, 10, 0, 0, 54, 0, 1, 1,
        1, 65463, 71, 1, 0, 65463, 0, 0, 0, 0, 1, 71, 0, 3, 65527,
        2, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 91, 4105, 1982, 0, 69
    ];

    // Conservative bound from exact_shap_reference.json:
    // max_abs_phi_int <= 82150463534784 < 2^47.
    var BPhi = 140737488355328; // 2^47
    var nBitsPhi = 49;

    component inputCommitment = RollingInputCommitment(n);
    for (var i = 0; i < n; i++) {
        inputCommitment.x_shifted[i] <== x_shifted[i];
    }
    inputCommitment.metadata_hash <== metadata_hash;
    inputCommitment.salt <== salt;
    input_commitment <== inputCommitment.out;

    y_hat * (y_hat - 1) === 0;

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

    signal partialSum[n + 1];
    partialSum[0] <== 0;

    for (var i = 0; i < n; i++) {
        partialSum[i + 1] <== partialSum[i] + c[i];
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

    // Closed-form semantic-group Exact SHAP for LR score:
    // phi_g_int = sum_{i in group g} w_int[i] * (x_int[i] - x_ref_int[i]).
    signal phi_term[n];
    signal phi_acc[nGroups][n + 1];
    signal Phi[nGroups];
    signal absPhi[nGroups];
    signal phi_offset[nGroups];
    signal phi_sign[nGroups];

    for (var g = 0; g < nGroups; g++) {
        phi_acc[g][0] <== 0;
    }

    for (var i = 0; i < n; i++) {
        phi_term[i] <== w[i] * (x[i] - x_ref_int[i]);
        for (var g = 0; g < nGroups; g++) {
            if (group_id[i] == g + 1) {
                phi_acc[g][i + 1] <== phi_acc[g][i] + phi_term[i];
            } else {
                phi_acc[g][i + 1] <== phi_acc[g][i];
            }
        }
    }

    component phiBoundCheck[nGroups];
    component phiSignCheck[nGroups];
    component absPhiBoundCheck[nGroups];

    for (var g = 0; g < nGroups; g++) {
        Phi[g] <== phi_acc[g][n];
        phi_offset[g] <== Phi[g] + BPhi;

        phiBoundCheck[g] = LessThan(nBitsPhi);
        phiBoundCheck[g].in[0] <== phi_offset[g];
        phiBoundCheck[g].in[1] <== 2 * BPhi;
        phiBoundCheck[g].out === 1;

        phiSignCheck[g] = LessThan(nBitsPhi);
        phiSignCheck[g].in[0] <== phi_offset[g];
        phiSignCheck[g].in[1] <== BPhi;
        phi_sign[g] <== phiSignCheck[g].out;
        phi_sign[g] * (phi_sign[g] - 1) === 0;

        absPhi[g] <== (1 - 2 * phi_sign[g]) * Phi[g];

        absPhiBoundCheck[g] = LessThan(nBitsPhi);
        absPhiBoundCheck[g].in[0] <== absPhi[g];
        absPhiBoundCheck[g].in[1] <== BPhi;
        absPhiBoundCheck[g].out === 1;
    }

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

    signal all_ids[5];
    all_ids[0] <== top3_ids[0];
    all_ids[1] <== top3_ids[1];
    all_ids[2] <== top3_ids[2];
    all_ids[3] <== other2_ids[0];
    all_ids[4] <== other2_ids[1];

    component neq[10];
    var k = 0;

    for (var i = 0; i < 5; i++) {
        for (var j = i + 1; j < 5; j++) {
            neq[k] = IsEqual();
            neq[k].in[0] <== all_ids[i];
            neq[k].in[1] <== all_ids[j];
            neq[k].out === 0;
            k++;
        }
    }

    signal sum_ids;
    signal sumsq_ids;

    sum_ids <== all_ids[0] + all_ids[1] + all_ids[2] + all_ids[3] + all_ids[4];
    sum_ids === 15;

    signal sq[5];
    sq[0] <== all_ids[0] * all_ids[0];
    sq[1] <== all_ids[1] * all_ids[1];
    sq[2] <== all_ids[2] * all_ids[2];
    sq[3] <== all_ids[3] * all_ids[3];
    sq[4] <== all_ids[4] * all_ids[4];

    sumsq_ids <== sq[0] + sq[1] + sq[2] + sq[3] + sq[4];
    sumsq_ids === 55;

    signal mappedAbsPhi[5];
    component sel[5];

    for (var idx = 0; idx < 5; idx++) {
        sel[idx] = Select5();
        sel[idx].arr <== absPhi;
        sel[idx].idx <== all_ids[idx];
        mappedAbsPhi[idx] <== sel[idx].out;
    }

    component mappedBoundCheck[5];
    for (var idx = 0; idx < 5; idx++) {
        mappedBoundCheck[idx] = LessThan(nBitsPhi);
        mappedBoundCheck[idx].in[0] <== mappedAbsPhi[idx];
        mappedBoundCheck[idx].in[1] <== BPhi;
        mappedBoundCheck[idx].out === 1;
    }

    component dominance[6];
    var dom_idx = 0;

    for (var t = 0; t < 3; t++) {
        for (var o = 3; o < 5; o++) {
            dominance[dom_idx] = LessThan(nBitsPhi);
            dominance[dom_idx].in[0] <== mappedAbsPhi[t];
            dominance[dom_idx].in[1] <== mappedAbsPhi[o];
            dominance[dom_idx].out === 0;
            dom_idx++;
        }
    }

    component order01 = LessThan(nBitsPhi);
    order01.in[0] <== mappedAbsPhi[0];
    order01.in[1] <== mappedAbsPhi[1];
    order01.out === 0;

    component order12 = LessThan(nBitsPhi);
    order12.in[0] <== mappedAbsPhi[1];
    order12.in[1] <== mappedAbsPhi[2];
    order12.out === 0;
}

// Public: input_commitment output, w_shifted[104], b_shifted, metadata_hash, y_hat, top3_ids[3]
// Private: x_shifted[104], salt, other2_ids[2]
component main {public [w_shifted, b_shifted, metadata_hash, y_hat, top3_ids]} =
    ExactShapTop3(104, 37, 68719476736, 297270816, 122130, 5);
