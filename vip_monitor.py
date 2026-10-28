"""
OF-RHM Live VIP Monitor — run in a separate terminal while demo is active.
No sudo needed. No Mininet. Just reads the events log in real-time.

Usage:
    python3 vip_monitor.py
"""

import time, json, pathlib, os

R='\033[91m'; G='\033[92m'; Y='\033[93m'; C='\033[96m'
BD='\033[1m'; RS='\033[0m'; B='\033[94m'; W='\033[97m'

EVENTS_LOG = pathlib.Path(__file__).parent / "outputs" / "events.jsonl"
REFRESH    = 2   # seconds

def fmt_ts(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))

def read_events():
    if not EVENTS_LOG.exists():
        return []
    evs = []
    for ln in EVENTS_LOG.read_text().splitlines():
        try:
            evs.append(json.loads(ln))
        except Exception:
            pass
    return evs

def render(evs):
    os.system("clear")
    print(f"{BD}{B}{'═'*58}{RS}")
    print(f"{BD}{B}  OF-RHM  |  Live VIP Monitor{RS}")
    print(f"{BD}{B}{'═'*58}{RS}\n")

    # Current VIP state
    mapping = {}
    for e in evs:
        if e["kind"] == "VIP_ASSIGN":
            mapping[e["real_ip"]] = e["vip"]
        elif e["kind"] == "ROTATION":
            mapping = e["new_mapping"]

    if mapping:
        print(f"  {BD}Active VIP Assignments{RS}")
        print(f"  {'─'*40}")
        for real, vip in sorted(mapping.items()):
            print(f"  {W}{real:<16}{RS}  →  {G}{vip}{RS}")
        print(f"  {'─'*40}\n")
    else:
        print(f"  {Y}No VIPs assigned yet — waiting for hosts to connect{RS}\n")

    # Last 12 events
    recent = evs[-12:]
    print(f"  {BD}Event Log  (latest {len(recent)} of {len(evs)}){RS}")
    print(f"  {'─'*56}")
    for e in recent:
        ts = fmt_ts(e["ts"])
        k  = e["kind"]
        if k == "VIP_ASSIGN":
            print(f"  {C}{ts}{RS}  VIP_ASSIGN    {e['real_ip']} → {G}{e['vip']}{RS}")
        elif k == "AI_DETECT":
            print(f"  {C}{ts}{RS}  {BD}{R}AI_DETECT{RS}    "
                  f"src={e['src']}  conf={e['confidence']*100:.0f}%  "
                  f"SYN={e['syn_rate']:.1f}/s")
        elif k == "ROTATION":
            n = len(e["new_mapping"])
            print(f"  {C}{ts}{RS}  {BD}{Y}ROTATION{RS}     "
                  f"{e['reason']}  ({n} VIPs)  {e['duration_ms']} ms")
        else:
            print(f"  {C}{ts}{RS}  {k}")
    print(f"  {'─'*56}")

    # Rotation count
    rot_count = sum(1 for e in evs if e["kind"] == "ROTATION")
    det_count = sum(1 for e in evs if e["kind"] == "AI_DETECT")
    print(f"\n  Rotations: {BD}{Y}{rot_count}{RS}   "
          f"AI detections: {BD}{R}{det_count}{RS}   "
          f"Refreshing every {REFRESH}s  (Ctrl+C to quit)\n")

try:
    while True:
        evs = read_events()
        render(evs)
        time.sleep(REFRESH)
except KeyboardInterrupt:
    print("\nMonitor stopped.")
