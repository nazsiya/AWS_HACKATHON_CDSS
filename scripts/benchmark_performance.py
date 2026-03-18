
import os
import time
import requests
import statistics
from datetime import datetime

# Usually running on localhost:8080 during dev
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")

def benchmark_endpoint(name, method, path, body=None):
    url = f"{BASE_URL}{path}"
    latencies = []
    print(f"Benchmarking {name} ({method} {path})...")
    
    for _ in range(5): # 5 iterations for averaging
        start = time.perf_counter()
        try:
            if method == "GET":
                resp = requests.get(url, timeout=10)
            elif method == "POST":
                resp = requests.post(url, json=body, timeout=10)
            
            end = time.perf_counter()
            if resp.status_code < 400:
                latencies.append(end - start)
        except Exception as e:
            print(f"  Error: {e}")
            
    if latencies:
        avg = statistics.mean(latencies)
        max_val = max(latencies)
        print(f"  Average: {avg:.3f}s | Max: {max_val:.3f}s")
        return avg, max_val
    else:
        print("  Failed to collect measurements.")
        return None, None

def run_benchmarks():
    results = {}
    
    # 1. Health Check (Infrastructure)
    results["Health"] = benchmark_endpoint("Health", "GET", "/health")
    
    # 2. Patient List (Common Query)
    results["Patient List"] = benchmark_endpoint("Patient List", "GET", "/api/v1/patients")
    
    # 3. Patient Detail (Heavier Query)
    # Using PT-1001 as a standard ID
    results["Patient Detail"] = benchmark_endpoint("Patient Detail", "GET", "/api/v1/patients/PT-1001")
    
    # 4. Terminology
    results["Terminology"] = benchmark_endpoint("Terminology", "GET", "/api/v1/terminology")

    print("\n--- [6.3] Performance Summary ---")
    all_pass = True
    for name, (avg, max_val) in results.items():
        if avg is not None:
            status = "PASS" if avg < 2.0 else "FAIL"
            if status == "FAIL": all_pass = False
            print(f"{name:15}: {avg:.3f}s average ({status})")
        else:
            print(f"{name:15}: ERROR")
            
    if all_pass:
        print("\nSUCCESS: All routine queries met sub-2-second target.")
    else:
        print("\nWARNING: Some queries exceeded performance targets.")

if __name__ == "__main__":
    run_benchmarks()
