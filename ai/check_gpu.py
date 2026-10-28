"""
check_gpu.py — Verify GPU is visible to XGBoost before training.
Run this first:  python check_gpu.py
"""

import subprocess, sys, time
import numpy as np

# ── 1. NVIDIA driver ──────────────────────────────────────────────────────────
print("=" * 55)
print("  Step 1: NVIDIA driver")
print("=" * 55)
try:
    out = subprocess.check_output("nvidia-smi", shell=True, text=True,
                                  stderr=subprocess.STDOUT)
    for line in out.splitlines()[:10]:
        print(" ", line)
    print("  [OK] NVIDIA driver found\n")
except Exception:
    print("  [FAIL] nvidia-smi not found — install NVIDIA drivers first\n")
    sys.exit(1)

# ── 2. XGBoost version ───────────────────────────────────────────────────────
print("=" * 55)
print("  Step 2: XGBoost version")
print("=" * 55)
try:
    import xgboost as xgb
    print(f"  XGBoost version: {xgb.__version__}")
    major = int(xgb.__version__.split('.')[0])
    if major < 2:
        print("  [WARN] Version < 2.0 — upgrade for better GPU support:")
        print("         pip install --upgrade xgboost")
    else:
        print("  [OK] Version 2.0+ — GPU support bundled\n")
except ImportError:
    print("  [FAIL] xgboost not installed — run: pip install xgboost")
    sys.exit(1)

# ── 3. GPU training test ──────────────────────────────────────────────────────
print("=" * 55)
print("  Step 3: GPU training test (10 000 samples, 100 trees)")
print("=" * 55)

X = np.random.rand(10_000, 6).astype(np.float32)
y = (X[:, 0] + X[:, 2] > 1.0).astype(int)

# CPU timing
t0 = time.time()
cpu_model = xgb.XGBClassifier(
    n_estimators=100, max_depth=6,
    device='cpu', eval_metric='logloss',
    verbosity=0, random_state=42,
)
cpu_model.fit(X, y)
cpu_time = time.time() - t0
print(f"  CPU time: {cpu_time:.2f}s")

# GPU timing
try:
    t0 = time.time()
    gpu_model = xgb.XGBClassifier(
        n_estimators=100, max_depth=6,
        device='cuda', eval_metric='logloss',
        verbosity=0, random_state=42,
    )
    gpu_model.fit(X, y)
    gpu_time = time.time() - t0
    speedup = cpu_time / gpu_time if gpu_time > 0 else 0
    print(f"  GPU time: {gpu_time:.2f}s  ({speedup:.1f}x faster)")
    print(f"\n  [OK] GPU training works — your 4050 is being used")
    print(f"       Training scripts will use device='cuda'")
except Exception as e:
    print(f"\n  [FAIL] GPU training failed: {e}")
    print("  Likely fix: pip install --upgrade xgboost")
    print("  Training scripts will fall back to CPU automatically.")

print("\n" + "=" * 55)
