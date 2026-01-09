const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

async function benchmarkProving(nRuns = 100) {
    const times = [];
    const wasmPath = path.join("circuits", "semantic_groups", "build", "semantic_groups_js", "semantic_groups.wasm");
    const zkeyPath = path.join("circuits", "semantic_groups", "build", "semantic_groups_final.zkey");
    const inputPath = path.join("circuits", "semantic_groups", "build", "input_sample_1.json");
    
    const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
    
    console.log(`Benchmarking Stage 3.2 proof generation (${nRuns} runs)...`);
    
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
    const vkeyPath = path.join("circuits", "semantic_groups", "build", "verification_key.json");
    const proofPath = path.join("outputs", "proofs", "proof_stage32_sample_1.json");
    const publicPath = path.join("outputs", "proofs", "public_stage32_sample_1.json");
    
    const vkey = JSON.parse(fs.readFileSync(vkeyPath, "utf8"));
    const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
    const publicSignals = JSON.parse(fs.readFileSync(publicPath, "utf8"));
    
    console.log(`\nBenchmarking Stage 3.2 verification (${nRuns} runs)...`);
    
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
    console.log("Starting Stage 3.2 benchmark...\n");
    
    const proveTimes = await benchmarkProving(100);
    const verifyTimes = await benchmarkVerification(100);
    
    const results = {
        stage: "3.2_semantic_groups",
        circuit: "semantic_groups",
        n_features: 104,
        n_groups: 5,
        n_runs: 100,
        constraints: {
            non_linear: 21500,
            linear: 2100,
            total: 23600
        },
        proof_generation: calculateStats(proveTimes),
        verification: calculateStats(verifyTimes)
    };
    
    // Save
    const outputDir = path.join("outputs", "proofs");
    fs.writeFileSync(
        path.join(outputDir, "benchmark_stage32.json"), 
        JSON.stringify(results, null, 2)
    );
    
    // Compare with Stage 3.1
    let stage31Data = null;
    try {
        stage31Data = JSON.parse(fs.readFileSync(
            path.join(outputDir, "benchmark_optimized.json"), 
            "utf8"
        ));
    } catch (e) {
        // Stage 3.1 benchmark not available
    }
    
    console.log("\n" + "=".repeat(60));
    console.log("STAGE 3.2 BENCHMARK RESULTS");
    console.log("=".repeat(60));
    console.log(`Proof Generation (mean): ${results.proof_generation.mean_ms.toFixed(2)}ms`);
    console.log(`Verification (mean):     ${results.verification.mean_ms.toFixed(2)}ms`);
    console.log(`Constraints:             ${results.constraints.total.toLocaleString()}`);
    
    if (stage31Data) {
        const overhead_prove = results.proof_generation.mean_ms - stage31Data.proof_generation.mean_ms;
        const overhead_pct = (overhead_prove / stage31Data.proof_generation.mean_ms * 100).toFixed(1);
        
        console.log("\n" + "=".repeat(60));
        console.log("COMPARISON: Stage 3.2 vs Stage 3.1");
        console.log("=".repeat(60));
        console.log(`Stage 3.1 proving:  ${stage31Data.proof_generation.mean_ms.toFixed(2)}ms`);
        console.log(`Stage 3.2 proving:  ${results.proof_generation.mean_ms.toFixed(2)}ms`);
        console.log(`Overhead:           +${overhead_prove.toFixed(2)}ms (+${overhead_pct}%)`);
        console.log(`\nAdded features:     Semantic group aggregation (5 groups)`);
    }
    
    console.log(`\nResults saved to: outputs/proofs/benchmark_stage32.json`);
}

main().catch(console.error);