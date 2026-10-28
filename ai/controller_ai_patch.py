"""
controller_ai_patch.py — Shows exactly what to change in controller.py
to plug in the two AI models.

Copy these sections into controller.py replacing the originals.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1: Add at the top of controller.py, after existing imports
# ─────────────────────────────────────────────────────────────────────────────

import joblib
import numpy as np
import pathlib

_MODEL_DIR = pathlib.Path(__file__).parent

# Load models (fail gracefully — fall back to rule-based if model missing)
try:
    _SCAN_MODEL = joblib.load(_MODEL_DIR / "scan_detector.pkl")
    print("[AI] scan_detector.pkl loaded")
except FileNotFoundError:
    _SCAN_MODEL = None
    print("[AI] scan_detector.pkl not found — using rule-based detection")

try:
    _VIP_MODEL = joblib.load(_MODEL_DIR / "vip_scorer.pkl")
    print("[AI] vip_scorer.pkl loaded")
except FileNotFoundError:
    _VIP_MODEL = None
    print("[AI] vip_scorer.pkl not found — using random VIP selection")


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2: Add these new tracking structures to MTDController.__init__
# (add alongside self._scan_state = {})
# ─────────────────────────────────────────────────────────────────────────────

# In __init__, add:
self._src_syn_count  = {}   # src_ip → total SYN count
self._src_ack_count  = {}   # src_ip → total ACK count
self._probed_vips    = {}   # vip → probe_count (attacker intelligence)
self._vip_history    = []   # list of sets — each set = VIPs used in one rotation


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3: Replace _track_syn with AI-powered version
# ─────────────────────────────────────────────────────────────────────────────

def _track_syn(self, src_ip, dst_vip, is_syn=True, is_ack=False):
    """
    AI-powered scan detection.
    Extracts 4 features per source IP and runs Random Forest classifier.
    Falls back to threshold rule if model not loaded.
    """
    real_src = self.vip_to_real.get(src_ip, src_ip)
    now      = time.time()

    # Update per-source counters
    state = self._scan_state.setdefault(
        real_src, {'targets': set(), 'first_seen': now}
    )
    if now - state['first_seen'] > SCAN_WINDOW:
        state['targets']    = set()
        state['first_seen'] = now
        self._src_syn_count[real_src] = 0
        self._src_ack_count[real_src] = 0

    state['targets'].add(dst_vip)
    if is_syn:
        self._src_syn_count[real_src] = self._src_syn_count.get(real_src, 0) + 1
    if is_ack:
        self._src_ack_count[real_src] = self._src_ack_count.get(real_src, 0) + 1

    # Track which VIPs are being probed (for VIP generator)
    self._probed_vips[dst_vip] = self._probed_vips.get(dst_vip, 0) + 1

    # ── AI detection ──────────────────────────────────────────────────────
    elapsed       = max(now - state['first_seen'], 0.001)
    n_unique_vips = len(state['targets'])
    syn_count     = self._src_syn_count.get(real_src, 0)
    ack_count     = self._src_ack_count.get(real_src, 0)
    syn_rate      = syn_count / elapsed
    syn_ack_ratio = syn_count / (ack_count + 1)

    is_attack = False

    if _SCAN_MODEL is not None:
        features  = np.array([[n_unique_vips, syn_rate, syn_ack_ratio, elapsed]])
        prediction = _SCAN_MODEL.predict(features)[0]
        confidence = _SCAN_MODEL.predict_proba(features)[0][1]   # P(scanner)
        is_attack  = (prediction == 1)
        if is_attack:
            self.logger.warning(
                f"[AI-SCAN] {real_src} classified as SCANNER  "
                f"(confidence={confidence:.2f}, "
                f"unique_vips={n_unique_vips}, syn_rate={syn_rate:.1f}/s)"
            )
    else:
        # Fallback: original threshold rule
        is_attack = (n_unique_vips >= SCAN_THRESHOLD)
        if is_attack:
            self.logger.warning(
                f"[SCAN DETECTED] {real_src} → {n_unique_vips} VIPs in {SCAN_WINDOW}s"
            )

    if is_attack:
        del self._scan_state[real_src]
        led.pulse_attack()
        rotate_fn = self._rotate_atomic if USE_ATOMIC else self._rotate
        hub.spawn(rotate_fn, f"AI scan detection: {real_src}")


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 4: Replace _pick_vip_excluding with AI-powered version
# ─────────────────────────────────────────────────────────────────────────────

def _pick_vip_excluding(self, exclude_set):
    """
    AI-powered VIP selection.
    Scores each candidate VIP using the trained model and picks the best one.
    Falls back to random choice if model not loaded.
    """
    candidates = [
        str(h) for h in _VIP_HOSTS
        if str(h) not in exclude_set
    ]
    if not candidates:
        raise RuntimeError("VIP pool exhausted")

    if _VIP_MODEL is None:
        return random.choice(candidates)

    # Build feature matrix for all candidates
    rotation_count = len(self._vip_history)
    active_octets  = [
        int(v.split('.')[-1]) for v in self._used_vips
    ]

    features = []
    for vip in candidates:
        octet = int(vip.split('.')[-1])

        # How many rotations ago was this VIP last used?
        last_used_ago = rotation_count + 1   # default: never used
        for i, hist_set in enumerate(reversed(self._vip_history)):
            if vip in hist_set:
                last_used_ago = i
                break

        recently_used   = 1 if last_used_ago < 3 else 0
        recently_probed = 1 if vip in self._probed_vips else 0
        probe_count     = self._probed_vips.get(vip, 0)

        # Minimum distance (last octet) from any currently active VIP
        if active_octets:
            dist = min(abs(octet - a) for a in active_octets)
        else:
            dist = 128   # no active VIPs yet → neutral

        features.append([recently_used, recently_probed, probe_count,
                         last_used_ago, dist])

    feature_matrix = np.array(features)

    # Score each candidate (probability of being a "good" VIP)
    scores = _VIP_MODEL.predict_proba(feature_matrix)[:, 1]

    # Pick the highest-scoring candidate
    best_idx = int(np.argmax(scores))
    chosen   = candidates[best_idx]

    self.logger.info(
        f"  [AI-VIP] chose {chosen}  "
        f"(score={scores[best_idx]:.3f}, "
        f"probed={self._probed_vips.get(chosen,0)}, "
        f"dist={features[best_idx][4]})"
    )
    return chosen


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 5: Add one line at the END of _rotate_atomic (before led.pulse_mutation)
# Records this rotation's VIP set into history so the scorer can use it.
# ─────────────────────────────────────────────────────────────────────────────

# Add at end of _rotate_atomic, just before led.pulse_mutation():
self._vip_history.append(set(new_mapping.values()))
if len(self._vip_history) > 20:      # keep last 20 rotations only
    self._vip_history.pop(0)
