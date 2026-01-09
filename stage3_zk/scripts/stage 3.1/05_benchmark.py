#!/usr/bin/env python3
"""
Benchmark proof generation/verification (100 runs) - Windows version
"""

import subprocess
import time
import json
import statistics
import sys
import os

def benchmark_proof_generation(n_runs=100):
    """Benchmark proof generation"""
    
    print(f"Benchmarking proof generation ({n_runs} runs)...")
    times = []
    
    for i in range(n_runs):
        start = time.time()
        # Use WSL bash for proof generation
        subprocess.run([
            "wsl", "bash", "-c",
            f"cd '/mnt/c/Paper/Masters thesis/stage3_zk' && "
            f"node circuits/inference_only/build/inference_only_js/generate_witness.js "
            f"circuits/inference_only/build/inference_only_js/inference_only.wasm "
            f"circuits/inference_only/build/input_sample_1.json "
            f"circuits/inference_only/build/witness.wtns && "
            f"npx snarkjs groth16 prove "
            f"circuits/inference_only/build/inference_only_final.zkey "
            f"circuits/inference_only/build/witness.wtns "
            f"outputs/proofs/proof_sample_1.json "
            f"outputs/proofs/public_sample_1.json"
        ], capture_output=True, check=True)
        elapsed = (time.time() - start) * 1000  # ms
        times.append(elapsed)
        
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{n_runs}")
    
    return times

def benchmark_verification(n_runs=100):
    """Benchmark verification"""
    
    print(f"\nBenchmarking verification ({n_runs} runs)...")
    times = []
    
    for i in range(n_runs):
        start = time.time()
        subprocess.run([
            "wsl", "bash", "-c",
            f"cd '/mnt/c/Paper/Masters thesis/stage3_zk' && "
            f"npx snarkjs groth16 verify "
            f"circuits/inference_only/build/verification_key.json "
            f"outputs/proofs/public_sample_1.json "
            f"outputs/proofs/proof_sample_1.json"
        ], capture_output=True, check=True)
        elapsed = (time.time() - start) * 1000  # ms
        times.append(elapsed)
        
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{n_runs}")
    
    return times

if __name__ == "__main__":
    # Generate proof once first
    print("Preparing...")
    subprocess.run(["python", "scripts/01_prepare_input.py", "1"], check=True)
    
    print("Generating initial proof...")
    subprocess.run([
        "wsl", "bash", "-c",
        f"cd '/mnt/c/Paper/Masters thesis/stage3_zk' && "
        f"node circuits/inference_only/build/inference_only_js/generate_witness.js "
        f"circuits/inference_only/build/inference_only_js/inference_only.wasm "
        f"circuits/inference_only/build/input_sample_1.json "
        f"circuits/inference_only/build/witness.wtns && "
        f"npx snarkjs groth16 prove "
        f"circuits/inference_only/build/inference_only_final.zkey "
        f"circuits/inference_only/build/witness.wtns "
        f"outputs/proofs/proof_sample_1.json "
        f"outputs/proofs/public_sample_1.json"
    ], check=True)
    
    print("✅ Setup complete\n")
    
    # Benchmark
    prove_times = benchmark_proof_generation(100)
    verify_times = benchmark_verification(100)
    
    # Calculate stats
    results = {
        "circuit": "inference_only",
        "n_features": 104,
        "n_runs": 100,
        "proof_generation": {
            "mean_ms": statistics.mean(prove_times),
            "median_ms": statistics.median(prove_times),
            "stdev_ms": statistics.stdev(prove_times),
            "min_ms": min(prove_times),
            "max_ms": max(prove_times)
        },
        "verification": {
            "mean_ms": statistics.mean(verify_times),
            "median_ms": statistics.median(verify_times),
            "stdev_ms": statistics.stdev(verify_times),
            "min_ms": min(verify_times),
            "max_ms": max(verify_times)
        }
    }
    
    # Save results
    os.makedirs("outputs/proofs", exist_ok=True)
    with open("outputs/proofs/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    print(f"Proof Generation (mean): {results['proof_generation']['mean_ms']:.2f}ms")
    print(f"Verification (mean):     {results['verification']['mean_ms']:.2f}ms")
    print(f"\nResults saved to: outputs/proofs/benchmark_results.json")