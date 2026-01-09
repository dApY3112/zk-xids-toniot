const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

// Navigate to project root
process.chdir(path.join(__dirname, '..', '..'));

async function benchmarkProving(nRuns = 100) {
    const times = [];
    const wasmPath = path.join("circuits", "top3_explanation", "build", "top3_explanation_js", "top3_explanation.wasm");
    const zkeyPath = path.join("circuits", "top3_explanation", "build", "top3_explanation_final.zkey");
    const inputPath = path.join("circuits", "top3_explanation", "build", "input_sample_1.json");
    
    const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
    
    console.log(`Benchmarking Stage 3.3 proof generation (${nRuns} runs)...`);
    
    for (let i = 0; i < nRuns; i++) {
        const start = Date.now();
        
        const { proof, publicSignals } = await snarkjs.groth16.fullProve(
            input, 
            wasmPath, 
            zkeyPath
        );
        
        const elapsed = Date.now() - start;
        times.push(elapsed);
        
        if ((i + 1) % 10 === 0) {
            console.log(`  Progress: ${i+1}/${nRuns}`);
        }
    }
    
    return times;
}

async function benchmarkVerification(nRuns = 100) {
    const times = [];
    const vkeyPath = path.join("circuits", "top3_explanation", "build", "verification_key.json");
    const proofPath = path.join("outputs", "proofs", "proof_stage33_sample_1.json");
    const publicPath = path.join("outputs", "proofs", "public_stage33_sample_1.json");
    
    const vkey = JSON.parse(fs.readFileSync(vkeyPath, "utf8"));
    const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
    const publicSignals = JSON.parse(fs.readFileSync(publicPath, "utf8"));
    
    console.log(`\nBenchmarking Stage 3.3 verification (${nRuns} runs)...`);
    
    for (let i = 0; i < nRuns; i++) {
        const start = Date.now();
        
        const res = await snarkjs.groth16.verify(vkey, publicSignals, proof);
        
        const elapsed = Date.now() - start;
        times.push(elapsed);
        
        if ((i + 1) % 10 === 0) {
            console.log(`  Progress: ${i+1}/${nRuns}`);
        }
    }
    
    return times;
}

function calculateStats(arr) {
    const sorted = [...arr].sort((a, b) => a - b);
    const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
    const variance = arr.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / arr.length;
    
    return {
        mean_ms: mean,
        median_ms: sorted[Math.floor(sorted.length / 2)],
        min_ms: Math.min(...arr),
        max_ms: Math.max(...arr),
        stdev_ms: Math.sqrt(variance)
    };
}

async function main() {
    console.log("Starting Stage 3.3 benchmark...\n");
    
    const proveTimes = await benchmarkProving(100);
    const verifyTimes = await benchmarkVerification(100);
    
    const results = {
        stage: "3.3_top3_explanation",
        circuit: "top3_explanation",
        n_features: 104,
        n_top: 3,
        n_runs: 100,
        constraints: {
            non_linear: 26000,  // Estimated for 104 features
            linear: 2500,
            total: 28500
        },
        proof_generation: calculateStats(proveTimes),
        verification: calculateStats(verifyTimes)
    };
    
    // Save
    const outputDir = path.join("outputs", "proofs");
    fs.writeFileSync(
        path.join(outputDir, "benchmark_stage33.json"), 
        JSON.stringify(results, null, 2)
    );
    
    // Load Stage 3.1 and 3.2 for comparison
    let stage31, stage32;
    try {
        stage31 = JSON.parse(fs.readFileSync(path.join(outputDir, "benchmark_optimized.json"), "utf8"));
        stage32 = JSON.parse(fs.readFileSync(path.join(outputDir, "benchmark_stage32.json"), "utf8"));
    } catch (e) {}
    
    console.log("\n" + "=".repeat(60));
    console.log("STAGE 3.3 BENCHMARK RESULTS");
    console.log("=".repeat(60));
    console.log(`Proof Generation (mean): ${results.proof_generation.mean_ms.toFixed(2)}ms`);
    console.log(`Verification (mean):     ${results.verification.mean_ms.toFixed(2)}ms`);
    
    if (stage31 && stage32) {
        console.log("\n" + "=".repeat(60));
        console.log("COMPARISON: All Stages");
        console.log("=".repeat(60));
        console.log(`Stage 3.1 (Inference):       ${stage31.proof_generation.mean_ms.toFixed(2)}ms`);
        console.log(`Stage 3.2 (+ Groups):        ${stage32.proof_generation.mean_ms.toFixed(2)}ms`);
        console.log(`Stage 3.3 (+ Top-3):         ${results.proof_generation.mean_ms.toFixed(2)}ms`);
        
        const overhead32 = ((stage32.proof_generation.mean_ms / stage31.proof_generation.mean_ms - 1) * 100).toFixed(1);
        const overhead33 = ((results.proof_generation.mean_ms / stage31.proof_generation.mean_ms - 1) * 100).toFixed(1);
        
        console.log(`\nOverhead 3.2 vs 3.1:         +${overhead32}%`);
        console.log(`Overhead 3.3 vs 3.1:         +${overhead33}%`);
    }
    
    console.log(`\nResults saved to: outputs/proofs/benchmark_stage33.json`);
}

main().catch(console.error);