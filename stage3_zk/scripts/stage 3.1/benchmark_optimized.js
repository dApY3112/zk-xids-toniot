// benchmark_optimized.js - FIXED
const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

async function benchmarkProving(nRuns = 100) {
    const times = [];
    const wasmPath = path.join("circuits", "inference_only", "build", "inference_only_js", "inference_only.wasm");
    const zkeyPath = path.join("circuits", "inference_only", "build", "inference_only_final.zkey");
    const inputPath = path.join("circuits", "inference_only", "build", "input_sample_1.json");
    
    const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
    
    console.log(`Benchmarking proof generation (${nRuns} runs)...`);
    
    for (let i = 0; i < nRuns; i++) {
        const start = Date.now();
        
        // Generate proof (includes witness calculation internally)
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
    const vkeyPath = path.join("circuits", "inference_only", "build", "verification_key.json");
    const proofPath = path.join("outputs", "proofs", "proof_sample_1.json");
    const publicPath = path.join("outputs", "proofs", "public_sample_1.json");
    
    const vkey = JSON.parse(fs.readFileSync(vkeyPath, "utf8"));
    const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
    const publicSignals = JSON.parse(fs.readFileSync(publicPath, "utf8"));
    
    console.log(`\nBenchmarking verification (${nRuns} runs)...`);
    
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
    console.log("Starting optimized benchmark...\n");
    
    const proveTimes = await benchmarkProving(100);
    const verifyTimes = await benchmarkVerification(100);
    
    const results = {
        circuit: "inference_only",
        n_features: 104,
        n_runs: 100,
        proof_generation: calculateStats(proveTimes),
        verification: calculateStats(verifyTimes)
    };
    
    // Ensure output directory exists
    const outputDir = path.join("outputs", "proofs");
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }
    
    fs.writeFileSync(
        path.join(outputDir, "benchmark_optimized.json"), 
        JSON.stringify(results, null, 2)
    );
    
    console.log("\n" + "=".repeat(50));
    console.log("OPTIMIZED BENCHMARK RESULTS");
    console.log("=".repeat(50));
    console.log(`Proof Generation (mean): ${results.proof_generation.mean_ms.toFixed(2)}ms`);
    console.log(`Verification (mean):     ${results.verification.mean_ms.toFixed(2)}ms`);
    console.log(`\nResults saved to: outputs/proofs/benchmark_optimized.json`);
}

main().catch(console.error);