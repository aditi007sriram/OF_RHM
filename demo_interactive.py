"""
OF-RHM Interactive Attacker Demo
Course: 25AID202

Three-terminal setup:
  Terminal 1:  ryu-manager controller.py
  Terminal 2:  sudo python3 demo_interactive.py   ← YOU ARE HERE
  Terminal 3:  python3 vip_monitor.py             (optional live feed)

You pick the attack. The system responds. Watch T1 for AI detection logs.
"""

import re, time, json, pathlib, os, sys
from mininet.log import setLogLevel
from topology import build

# ── ANSI colours ──────────────────────────────────────────────────────────────
R='\033[91m'; G='\033[92m'; Y='\033[93m'; C='\033[96m'
BD='\033[1m'; RS='\033[0m'; B='\033[94m'; W='\033[97m'

OUTPUTS_DIR = pathlib.Path(__file__).parent / "outputs"
EVENTS_LOG  = OUTPUTS_DIR / "events.jsonl"
SCAN_SUBNET = "172.16.0.0/24"


def cls():
    os.system("clear")

def banner():
    print(f"{BD}{B}{'═'*62}{RS}")
    print(f"{BD}{B}  OF-RHM  |  Moving Target Defense  |  Attacker Console{RS}")
    print(f"{BD}{B}  Course 25AID202  |  Ryu+Mininet on Raspberry Pi{RS}")
    print(f"{BD}{B}{'═'*62}{RS}\n")

def read_new_events(since_ts):
    evs = []
    if EVENTS_LOG.exists():
        for ln in EVENTS_LOG.read_text().splitlines():
            try:
                e = json.loads(ln)
                if e["ts"] > since_ts:
                    evs.append(e)
            except Exception:
                pass
    return evs

def current_vips():
    """Return latest VIP mapping from events log."""
    mapping = {}
    if EVENTS_LOG.exists():
        for ln in EVENTS_LOG.read_text().splitlines():
            try:
                e = json.loads(ln)
                if e["kind"] == "VIP_ASSIGN":
                    mapping[e["real_ip"]] = e["vip"]
                elif e["kind"] == "ROTATION":
                    mapping = e["new_mapping"]
            except Exception:
                pass
    return mapping

def show_current_vips(label="Current VIP assignments"):
    mapping = current_vips()
    if not mapping:
        print(f"  {Y}No VIP assignments yet (controller hasn't seen hosts){RS}\n")
        return
    print(f"  {BD}{label}{RS}")
    print(f"  {'─'*40}")
    for real, vip in sorted(mapping.items()):
        print(f"  {W}{real:<16}{RS} →  {G}{vip}{RS}")
    print(f"  {'─'*40}\n")

def clean_nmap(raw):
    return "\n".join(
        ln for ln in raw.splitlines()
        if not ln.startswith("Warning:") and "giving up" not in ln and ln.strip()
    )

def parse_ips(raw):
    return set(re.findall(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", raw))

def wait_for_response(since_ts, timeout=45):
    """Poll events log until a ROTATION or AI_DETECT event appears."""
    deadline = time.time() + timeout
    detected = False
    print(f"  {C}Waiting for controller response", end="", flush=True)
    while time.time() < deadline:
        time.sleep(1.5)
        print(".", end="", flush=True)
        evs = read_new_events(since_ts)
        if any(e["kind"] == "AI_DETECT" for e in evs) and not detected:
            print(f"\n\n  {BD}{R}⚠  AI SCAN CLASSIFIER FIRED{RS}")
            detected = True
        if any(e["kind"] == "ROTATION" for e in evs):
            print(f"\n  {BD}{G}⚡ ROTATION COMPLETED{RS}\n")
            return evs
    print(f"\n  {Y}Timeout — scheduled rotation may have fired instead{RS}\n")
    return read_new_events(since_ts)

def show_response(evs, vips_before):
    detections = [e for e in evs if e["kind"] == "AI_DETECT"]
    rotations  = [e for e in evs if e["kind"] == "ROTATION"]

    if detections:
        d = detections[-1]
        print(f"  {BD}AI Detection Report{RS}")
        print(f"  {'─'*40}")
        print(f"  Source          : {R}{d['src']}{RS}")
        print(f"  Confidence      : {R}{d['confidence']*100:.0f}%{RS}  (threshold: 50%)")
        print(f"  Unique VIPs hit : {d['unique_vips']}")
        print(f"  SYN rate        : {d['syn_rate']:.1f} pkts/s")
        print(f"  SYN/ACK ratio   : {d['syn_ack_ratio']:.3f}  (0 = scanner, 1 = normal)")
        print(f"  {'─'*40}\n")
    else:
        print(f"  {Y}No AI_DETECT event — attack may not have crossed the threshold{RS}")
        print(f"  (slow stealth scan = realistic, may need more time)\n")

    if rotations:
        r = rotations[-1]
        old = r["old_mapping"]
        new = r["new_mapping"]
        print(f"  {BD}VIP Rotation  ({r['reason']})  — {r['duration_ms']} ms{RS}")
        print(f"  {'─'*50}")
        print(f"  {'Host':<16} {'Old VIP':<18} {'New VIP':<18}")
        print(f"  {'─'*50}")
        for ip in sorted(old):
            print(f"  {ip:<16} {R}{old[ip]:<18}{RS} {G}{new[ip]:<18}{RS}")
        print(f"  {'─'*50}")
        print(f"  {G}✔ Attacker's map is now completely stale{RS}\n")

        overlap = vips_before & set(new.values())
        if not overlap:
            print(f"  {BD}{G}RESULT: PASS — Zero overlap between old and new VIPs{RS}\n")
        else:
            print(f"  {Y}Overlap: {overlap} (partial rotation){RS}\n")
    else:
        print(f"  {Y}No rotation recorded in events log{RS}\n")


def run_attack(attacker, attack_type, since_ts):
    vips_before = set(current_vips().values())

    if attack_type == "1":
        print(f"\n  {BD}{R}[ATTACK] Fast TCP SYN scan — nmap -sS -T4{RS}")
        print(f"  This mimics an aggressive attacker mapping the network quickly.\n")
        raw = attacker.cmd(f"nmap -sS -p 80 -T4 --max-retries 0 --host-timeout 300ms {SCAN_SUBNET} 2>/dev/null")
        found = parse_ips(raw)
        print(f"  Attacker discovered: {sorted(found)}\n")

    elif attack_type == "2":
        print(f"\n  {BD}{Y}[ATTACK] Slow stealth scan — 1s delay between probes{RS}")
        print(f"  Attacker tries to fly under the radar with slow timing.\n")
        print(f"  {Y}(This will take ~60s — watch the controller window for partial detection){RS}\n")
        raw = attacker.cmd(f"nmap -sS -p 80 --scan-delay 1s --max-retries 0 {SCAN_SUBNET} 2>/dev/null")
        found = parse_ips(raw)
        print(f"  Attacker discovered: {sorted(found)}\n")

    elif attack_type == "3":
        print(f"\n  {BD}{Y}[ATTACK] Targeted probe — 3 known VIPs only{RS}")
        print(f"  Attacker already knows the VIPs and probes them directly.\n")
        vips = sorted(current_vips().values())[:3]
        if not vips:
            print(f"  {R}No VIPs known yet — run attack 1 first{RS}\n")
            return
        targets = " ".join(vips)
        raw = attacker.cmd(f"nmap -sS -p 80,443,22 -T4 {targets} 2>/dev/null")
        for ln in clean_nmap(raw).splitlines():
            if ln.strip():
                print(f"  {ln}")
        found = parse_ips(raw)
        print(f"\n  Attacker probed: {sorted(found)}\n")

    elif attack_type == "4":
        print(f"\n  {BD}{R}[ATTACK] hping3 SYN flood — 100 packets to first VIP{RS}")
        print(f"  Rapid-fire SYN packets — clearest signal for the AI classifier.\n")
        vips = sorted(current_vips().values())
        target = vips[0] if vips else "172.16.0.1"
        print(f"  Target: {R}{target}{RS}")
        attacker.cmd(f"hping3 -S -p 80 -c 100 --fast {target} 2>/dev/null &")
        time.sleep(3)
        attacker.cmd("pkill -f hping3 2>/dev/null; true")
        print(f"  Sent 100 SYN packets to {target}\n")

    elif attack_type == "5":
        print(f"\n  {BD}{C}[ATTACK] Port sweep — all common ports on known VIPs{RS}")
        print(f"  Attacker enumerates services after discovering hosts.\n")
        vips = sorted(current_vips().values())
        if not vips:
            print(f"  {R}No VIPs known — run attack 1 first{RS}\n")
            return
        target = vips[0]
        raw = attacker.cmd(f"nmap -sS -p 22,80,443,8080,3306,5432 -T4 {target} 2>/dev/null")
        for ln in clean_nmap(raw).splitlines():
            if ln.strip():
                print(f"  {ln}")
        print()

    elif attack_type == "6":
        print(f"\n  {BD}{W}[CUSTOM] Attacker shell — command runs from 10.0.0.99{RS}")
        print(f"  {C}Tip: use 172.16.0.0/24 as the target subnet{RS}")
        print(f"  {C}     e.g.  nmap -sS -p 80 172.16.0.0/24{RS}\n")
        cmd = input(f"  {BD}attacker@10.0.0.99 > {RS}").strip()
        if not cmd:
            return
        print()
        raw = attacker.cmd(f"{cmd} 2>/dev/null")
        for ln in clean_nmap(raw).splitlines():
            if ln.strip():
                print(f"  {ln}")
        print()

    else:
        return

    evs = wait_for_response(since_ts, timeout=40)
    show_response(evs, vips_before)


def run():
    OUTPUTS_DIR.mkdir(exist_ok=True)
    setLogLevel("warning")

    cls()
    banner()
    print(f"  Starting Mininet topology...\n")

    net = build()
    net.start()

    hosts    = [h for h in net.hosts if h.name != "attacker"]
    attacker = net.get("attacker")

    for h in hosts + [attacker]:
        h.cmd(f"ip route add 172.16.0.0/16 dev {h.defaultIntf().name}")

    print(f"  {G}Network up.{RS} Warming up (4s)...\n")
    for h in hosts:
        h.cmd("ping -c1 -W1 10.0.0.1 &")
    time.sleep(4)

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        cls()
        banner()
        show_current_vips()

        print(f"  {BD}Choose an attack to launch:{RS}\n")
        print(f"  {R}[1]{RS}  Fast SYN scan      (nmap -sS -T4)     — triggers AI immediately")
        print(f"  {Y}[2]{RS}  Slow stealth scan  (1s probe delay)   — tries to evade detection")
        print(f"  {Y}[3]{RS}  Targeted probe     (known VIPs only)  — post-recon follow-up")
        print(f"  {R}[4]{RS}  SYN flood          (hping3 100 pkts)  — clearest AI signal")
        print(f"  {C}[5]{RS}  Port sweep         (multi-port scan)  — service enumeration")
        print(f"  {W}[6]{RS}  {BD}Custom command{RS}     — type any command, runs from attacker host")
        print(f"  {W}[q]{RS}  Quit demo\n")

        choice = input(f"  {BD}Attack > {RS}").strip().lower()

        if choice == "q":
            print(f"\n  {G}Demo ended. Stopping Mininet...{RS}\n")
            break

        if choice not in ("1", "2", "3", "4", "5", "6"):
            continue

        since_ts = time.time()
        run_attack(attacker, choice, since_ts)

        input(f"\n  {C}Press Enter to return to attack menu...{RS}")

    net.stop()


if __name__ == "__main__":
    run()
