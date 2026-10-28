"""
train_vip_generator.py — Train an XGBoost VIP scorer (GPU-accelerated).

GPU-upgraded from the original Gradient Boosting (40 trees, 3 000 samples).
Now trains on 60 000 samples with XGBoost using CUDA, falling back to CPU
automatically if no GPU is available.

Features per VIP candidate (5, unchanged):
  recently_used      : 1 if used in last 3 rotations
  recently_probed    : 1 if attacker sent SYN to this VIP recently
  probe_count        : how many times attacker has probed this VIP
  last_used_ago      : rotations since this VIP was last used (0 = current)
  distance_from_used : min last-octet distance from any currently active VIP

Label:  1 = good VIP to pick,  0 = bad VIP to pick

Run on LAPTOP (with GPU).  Output: vip_scorer.pkl  → transfer to Pi.
"""

import numpy as np
import joblib

_HAS_XGB = False  # force scikit-learn so .pkl loads on Pi without xgboost
from sklearn.ensemble import RandomForestClassifier

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

np.random.seed(7)
N = 60_000   # 20× more data — trains in seconds on GPU


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic training data
# ─────────────────────────────────────────────────────────────────────────────

def generate_good_vip_samples(n):
    """
    A good VIP: not recently used, never probed, far from active addresses.
    ~20% are ambiguous edge cases that overlap with bad VIP ranges.
    """
    recently_used   = (np.random.random(n) < 0.12).astype(float)  # 12% recently used
    recently_probed = (np.random.random(n) < 0.10).astype(float)  # 10% lightly probed
    probe_count     = np.where(recently_probed,
                                np.random.randint(1, 5, n).astype(float),  # overlaps bad
                                np.zeros(n))
    last_used_ago   = np.where(recently_used,
                                np.random.randint(2, 7, n).astype(float),  # overlaps bad
                                np.random.randint(5, 30, n).astype(float))
    # 15% of good VIPs are moderately close — not all far VIPs are safe
    close_mask = np.random.random(n) < 0.15
    distance   = np.where(close_mask,
                           np.random.randint(15, 50, n).astype(float),  # overlaps bad
                           np.random.randint(50, 200, n).astype(float))
    return np.column_stack([recently_used, recently_probed, probe_count,
                            last_used_ago, distance])


def generate_bad_vip_samples(n):
    """
    A bad VIP: recently used OR probed, close to active addresses.
    ~20% are ambiguous — bad by one metric only, fine on others.
    """
    recently_used   = (np.random.random(n) < 0.55).astype(float)
    recently_probed = (np.random.random(n) < 0.50).astype(float)
    # ensure at least one bad flag per sample
    neither = (recently_used == 0) & (recently_probed == 0)
    recently_used[neither] = 1
    # probe_count overlaps with good (some bad VIPs have low probe counts)
    probe_count   = np.random.randint(0, 10, n).astype(float)
    # last_used_ago overlaps with good (some bad VIPs were used a few rotations ago)
    last_used_ago = np.random.randint(0, 8, n).astype(float)
    # 20% of bad VIPs have moderate distance — overlap with some good VIPs
    far_mask  = np.random.random(n) < 0.20
    distance  = np.where(far_mask,
                          np.random.randint(30, 70, n).astype(float),  # ambiguous range
                          np.random.randint(0, 35, n).astype(float))
    return np.column_stack([recently_used, recently_probed, probe_count,
                            last_used_ago, distance])


X_good = generate_good_vip_samples(N)
X_bad  = generate_bad_vip_samples(N)

X = np.vstack([X_good, X_bad])
y = np.array([1] * N + [0] * N)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=7, stratify=y
)


# ─────────────────────────────────────────────────────────────────────────────
# Train
# ─────────────────────────────────────────────────────────────────────────────

if _HAS_XGB:
    for device in ('cuda', 'cpu'):
        try:
            model = XGBClassifier(
                n_estimators=80, max_depth=4, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                eval_metric='logloss', device=device, random_state=7,
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
    model = RandomForestClassifier(
        n_estimators=80, max_depth=4, random_state=7, n_jobs=-1
    )
    model.fit(X_train, y_train)
    print("[CPU] Scikit-learn RandomForest trained (all cores)")


# ─────────────────────────────────────────────────────────────────────────────
# Evaluate
# ─────────────────────────────────────────────────────────────────────────────

print("\nClassification Report (test set):")
print(classification_report(y_test, model.predict(X_test),
                            target_names=["Bad VIP", "Good VIP"]))

if _HAS_XGB:
    feature_names = ["recently_used", "recently_probed", "probe_count",
                     "last_used_ago", "distance_from_used"]
    importances = model.feature_importances_
    print("Feature importances:")
    for name, imp in zip(feature_names, importances):
        print(f"  {name:<25} {imp:.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────

joblib.dump(model, "vip_scorer.pkl")
print("\nSaved → vip_scorer.pkl")
print("Transfer to Pi:  scp ai/vip_scorer.pkl pi@10.176.30.10:~/CN_proj/ai/")
