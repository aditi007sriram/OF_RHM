"""
train_scan_detector.py — Train an XGBoost scan classifier (GPU-accelerated).

GPU-upgraded from the original Random Forest (50 trees, 2 000 samples).
Now trains on 50 000 samples with XGBoost using CUDA, falling back to CPU
automatically if no GPU is available.

Features per source IP (6, up from 4):
  n_unique_vips          : distinct VIPs this source has probed
  syn_rate               : SYN packets per second
  syn_ack_ratio          : SYN / (ACK + 1) — scanners never complete handshake
  elapsed                : seconds of observed activity
  inter_arrival_variance : variance of inter-packet gap (scanners = very regular)
  unique_vip_rate        : n_unique_vips / elapsed — normalised scan speed

Labels:  1 = scanner,  0 = normal user

Run on LAPTOP (with GPU).  Output: scan_detector.pkl  → transfer to Pi.
"""

import numpy as np
import joblib
import pathlib

_HAS_XGB = False  # force scikit-learn so .pkl loads on Pi without xgboost
from sklearn.ensemble import RandomForestClassifier

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

np.random.seed(42)
N = 20_000   # synthetic fallback size

REAL_CSV = pathlib.Path(__file__).parent / "real_features.csv"

# ─────────────────────────────────────────────────────────────────────────────
# Load real captured data if available, otherwise generate synthetic
# ─────────────────────────────────────────────────────────────────────────────

def load_real_data(csv_path):
    import csv as _csv
    rows = []
    with open(csv_path, newline="") as f:
        for row in _csv.DictReader(f):
            rows.append([float(row["n_unique_vips"]), float(row["syn_rate"]),
                         float(row["syn_ack_ratio"]), float(row["elapsed"]),
                         float(row["inter_arrival_variance"]),
                         float(row["unique_vip_rate"])])
    return np.array(rows)


def generate_scanner_samples(n):
    """
    nmap -sS behaviour with realistic noise:
    - ~10% of samples are 'slow' scanners (lower rate, some ACKs slip through)
    - Gaussian noise on all features
    """
    elapsed = np.random.uniform(0.5, 20.0, n)

    # Three archetypes — each has its own n_vips range:
    #   fast    (45%): subnet sweep, many VIPs, very regular timing
    #   slow    (25%): moderate sweep, fewer VIPs
    #   evasive (30%): focused/targeted scan, FEW VIPs like normal users, random timing
    roll    = np.random.random(n)
    fast    = roll < 0.45
    evasive = roll >= 0.70
    slow    = ~fast & ~evasive

    n_vips = np.where(fast,    np.random.randint(15, 50, n),
             np.where(slow,    np.random.randint(4,  18, n),
                               np.random.randint(1,   7, n)))  # evasive overlaps normal

    syn_rate = np.where(fast,    np.random.uniform(10.0, 80.0, n),
               np.where(slow,    np.random.uniform(0.5,   5.0, n),
                                 np.random.uniform(0.2,   5.0, n)))  # evasive overlaps

    syn_ack_ratio = np.where(fast,    np.random.uniform(0.0,  0.08, n),
                    np.where(slow,    np.random.uniform(0.05, 0.35, n),
                                      np.random.uniform(0.05, 0.65, n)))  # evasive overlaps

    iav = np.where(fast,    np.random.uniform(0.00005, 0.003, n),
          np.where(slow,    np.random.uniform(0.002,   0.08,  n),
                            np.random.uniform(0.05,    2.5,   n)))  # evasive overlaps normal

    X = np.column_stack([n_vips, syn_rate, syn_ack_ratio, elapsed, iav,
                         n_vips / (elapsed + 1e-6)])
    X += np.random.normal(0, 0.07, X.shape) * np.abs(X)
    return np.clip(X, 0, None)


def generate_normal_samples(n):
    """
    Legitimate traffic — including scripted/automated tools and multi-server apps
    that overlap with evasive/slow scanners across all features.
    """
    elapsed = np.random.uniform(2.0, 120.0, n)

    # scripted/automated (25%): probe several servers, regular timing → overlaps evasive scanner
    # bursty (15%): momentary bursts
    # normal (60%): standard browsing
    roll          = np.random.random(n)
    scripted_mask = roll < 0.25
    bursty_mask   = (roll >= 0.25) & (roll < 0.40)

    n_vips = np.where(scripted_mask,
                      np.random.randint(3, 12, n),   # overlaps evasive & slow scanner
             np.where(bursty_mask,
                      np.random.randint(1, 6,  n),
                      np.random.randint(1, 4,  n)))

    syn_rate = np.where(scripted_mask,
                        np.random.uniform(0.5,  6.0, n),  # overlaps slow & evasive
               np.where(bursty_mask,
                        np.random.uniform(2.0,  8.0, n),
                        np.random.uniform(0.05, 1.5, n)))

    reset_mask    = np.random.random(n) < 0.12
    syn_ack_ratio = np.where(reset_mask,
                             np.random.uniform(0.1,  0.60, n),  # overlaps slow & evasive
                             np.random.uniform(0.55, 1.0,  n))

    iav = np.where(scripted_mask,
                   np.random.uniform(0.001, 0.20, n),   # overlaps slow & evasive scanner
                   np.random.uniform(0.05,  3.5,  n))

    X = np.column_stack([n_vips, syn_rate, syn_ack_ratio, elapsed, iav,
                         n_vips / (elapsed + 1e-6)])
    X += np.random.normal(0, 0.07, X.shape) * np.abs(X)
    return np.clip(X, 0, None)


if REAL_CSV.exists():
    print(f"[DATA] Loading real captured data from {REAL_CSV.name} …")
    import csv as _csv
    all_rows, all_labels = [], []
    with open(REAL_CSV, newline="") as f:
        for row in _csv.DictReader(f):
            all_rows.append([float(row["n_unique_vips"]), float(row["syn_rate"]),
                             float(row["syn_ack_ratio"]), float(row["elapsed"]),
                             float(row["inter_arrival_variance"]),
                             float(row["unique_vip_rate"])])
            all_labels.append(int(row["label"]))
    X_real = np.array(all_rows)
    y_real = np.array(all_labels)
    n_scan = int(y_real.sum()); n_norm = len(y_real) - n_scan
    print(f"  Real data: {n_scan} scanner + {n_norm} normal = {len(y_real)} total")
    # Augment with synthetic to balance and pad to at least 10k samples
    pad = max(0, 5000 - min(n_scan, n_norm))
    X_aug = np.vstack([generate_scanner_samples(pad), generate_normal_samples(pad)])
    y_aug = np.array([1]*pad + [0]*pad)
    X = np.vstack([X_real, X_aug])
    y = np.concatenate([y_real, y_aug])
    print(f"  After augmentation: {len(X)} total samples")
else:
    print("[DATA] real_features.csv not found — using synthetic data")
    print("       Run capture_training_data.py on Pi to get real data")
    X_scan   = generate_scanner_samples(N)
    X_normal = generate_normal_samples(N)
    X = np.vstack([X_scan, X_normal])
    y = np.array([1] * N + [0] * N)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


# ─────────────────────────────────────────────────────────────────────────────
# Train
# ─────────────────────────────────────────────────────────────────────────────

if _HAS_XGB:
    for device in ('cuda', 'cpu'):
        try:
            model = XGBClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                eval_metric='logloss', device=device, random_state=42,
            )
            model.fit(X_train, y_train)
            print(f"[{'GPU' if device == 'cuda' else 'CPU'}] XGBoost trained on {device.upper()}")
            break
        except Exception as e:
            if device == 'cuda':
                print(f"[GPU] CUDA unavailable ({e}) — retrying on CPU")
            else:
                raise
else:
    # scikit-learn fallback: all CPU cores, still fast on 50k samples
    model = RandomForestClassifier(
        n_estimators=100, max_depth=4, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)
    print("[CPU] Scikit-learn Random Forest trained (all cores, n_jobs=-1)")


# ─────────────────────────────────────────────────────────────────────────────
# Evaluate
# ─────────────────────────────────────────────────────────────────────────────

print("\nClassification Report (test set):")
print(classification_report(y_test, model.predict(X_test),
                            target_names=["Normal", "Scanner"]))

if _HAS_XGB:
    feature_names = ["n_unique_vips", "syn_rate", "syn_ack_ratio",
                     "elapsed", "inter_arrival_variance", "unique_vip_rate"]
    importances = model.feature_importances_
    print("Feature importances:")
    for name, imp in zip(feature_names, importances):
        print(f"  {name:<28} {imp:.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────

joblib.dump(model, "scan_detector.pkl")
print("\nSaved → scan_detector.pkl")
print("Transfer to Pi:  scp ai/scan_detector.pkl pi@10.176.30.10:~/CN_proj/ai/")
