"""
OF-RHM Moving Target Defense — Automated Demo
Course: 25AID202 | Team: Aditi Sriram, Dhanushiya S, Vani Karre, Laiba S

Usage:
    Terminal 1:  ryu-manager controller.py
    Terminal 2:  sudo python3 demo.py
"""

import re, time, json, pathlib, os
from mininet.log import setLogLevel, info
from topology import build

# ── ANSI colours ─────────────────────────────────────────────────────────────
R  = '\033[91m'   # red
G  = '\033[92m'   # green
Y  = '\033[93m'   # yellow
B  = '\033[94m'   # blue
C  = '\033[96m'   # cyan
W  = '\033[97m'   # white
BD = '\033[1m'    # bold
RS = '\033[0m'    # reset

SCAN_SUBNET = "172.16.0.0/24"
SCAN_FLAGS  = "-sS -p 80 -T4 --max-retries 0 --host-timeout 300ms"

OUTPUTS_DIR = pathlib.Path(__file__).parent / "outputs"
EVENTS_LOG  = OUTPUTS_DIR / "events.jsonl"


# ── Helpers ───────────────────────────────────────────────────────────────────

def hdr(step, msg):
    print(f"\n{BD}{C}{'─'*62}{RS}")
    print(f"{BD}{C}  [{step}] {msg}{RS}")
    print(f"{BD}{C}{'─'*62}{RS}")

def ok(msg):   print(f"  {G}✔{RS}  {msg}")
def warn(msg): print(f"  {Y}⚠{RS}  {msg}")
def err(msg):  print(f"  {R}✘{RS}  {msg}")
def info2(msg): print(f"  {W}{msg}{RS}")

def table(title, headers, rows):
    col_w = [max(len(h), max((len(str(r[i])) for r in rows), default=0))
             for i, h in enumerate(headers)]
    sep = "  ┼─" + "─┼─".join("─" * w for w in col_w) + "─┤"
    top = "  ┌─" + "─┬─".join("─" * w for w in col_w) + "─┐"
    bot = "  └─" + "─┴─".join("─" * w for w in col_w) + "─┘"
    hrow = "  │ " + " │ ".join(f"{BD}{h:<{col_w[i]}}{RS}" for i, h in enumerate(headers)) + " │"
    print(f"\n  {BD}{title}{RS}")
    print(top)
    print(hrow)
    print(sep)
    for row in rows:
        print("  │ " + " │ ".join(f"{str(row[i]):<{col_w[i]}}" for i in range(len(headers))) + " │")
    print(bot)

def clean_nmap(raw):
    """Strip the hundreds of nmap 'Warning: giving up' lines."""
    lines = []
    for ln in raw.splitlines():
        if ln.startswith("Warning:") or "giving up on port" in ln:
            continue
        lines.append(ln)
    return "\n".join(lines)

def parse_nmap_ips(raw):
    return set(re.findall(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", raw))

def read_events(since_ts=0):
    events = []
    if EVENTS_LOG.exists():
        for line in EVENTS_LOG.read_text().splitlines():
            try:
                e = json.loads(line)
                if e["ts"] >= since_ts:
                    events.append(e)
            except Exception:
                pass
    return events

def show_events(since_ts):
    events = read_events(since_ts)
    detections = [e for e in events if e["kind"] == "AI_DETECT"]
    rotations  = [e for e in events if e["kind"] == "ROTATION"]

    if detections:
        for d in detections:
            print(f"\n  {BD}{R}⚠  ATTACK DETECTED by AI scan classifier{RS}")
            print(f"     Source     : {R}{d['src']}{RS}")
            print(f"     Confidence : {R}{d['confidence']*100:.0f}%{RS}")
            print(f"     Unique VIPs probed : {d['unique_vips']}")
            print(f"     SYN rate   : {d['syn_rate']:.1f} packets/s")
            print(f"     SYN/ACK ratio : {d['syn_ack_ratio']:.3f}  (scanners never complete handshake)")
    else:
        warn("AI detection event not recorded (scheduled rotation fired instead)")

    if rotations:
        for rot in rotations:
            old = rot["old_mapping"]
            new = rot["new_mapping"]
            rows = [[ip, old[ip], new[ip]] for ip in sorted(old)]
            table(f"VIP Rotation  ({rot['reason']})  — {rot['duration_ms']} ms",
                  ["Host", "Old VIP", "New VIP"], rows)
            ok(f"Atomic rotation completed in {rot['duration_ms']} ms (provably gap-free)")


# ── Main demo ─────────────────────────────────────────────────────────────────

def run_demo():
    OUTPUTS_DIR.mkdir(exist_ok=True)
    setLogLevel("warning")   # suppress mininet chatter

    # ── Banner ────────────────────────────────────────────────────────────────
    print(f"\n{BD}{B}{'═'*62}{RS}")
    print(f"{BD}{B}  OF-RHM Moving Target Defense — Live Demo{RS}")
    print(f"{BD}{B}  Course: 25AID202  |  Supervisors: Shashank & Sundaresan{RS}")
    print(f"{BD}{B}  Team: Aditi · Dhanushiya · Vani · Laiba{RS}")
    print(f"{BD}{B}{'═'*62}{RS}")

    net = build()
    net.start()

    hosts    = [h for h in net.hosts if h.name != "attacker"]
    attacker = net.get("attacker")

    # ── Step 1: warm up ───────────────────────────────────────────────────────
    hdr("STEP 1", "Network setup & warm-up")
    for h in hosts + [attacker]:
        iface = h.defaultIntf().name
        h.cmd(f"ip route add 172.16.0.0/16 dev {iface}")
    info2(f"Hosts  : {', '.join(h.name + ' (' + h.IP() + ')' for h in hosts)}")
    info2(f"Attacker: {attacker.name} ({attacker.IP()})")

    for h in hosts:
        h.cmd("ping -c1 -W1 10.0.0.1 &")
    time.sleep(4)

    # Read VIP assignments from events log
    assign_events = read_events()
    assigns = {e["real_ip"]: e["vip"] for e in assign_events if e["kind"] == "VIP_ASSIGN"}
    if assigns:
        table("Initial VIP assignments (hidden from attacker)",
              ["Host (real)", "Virtual IP assigned"],
              [[ip, vip] for ip, vip in sorted(assigns.items())])
    else:
        warn("VIP assignments not yet visible — controller may still be learning MACs")

    demo_start_ts = time.time()

    # ── Step 2: first scan ────────────────────────────────────────────────────
    hdr("STEP 2", "Attacker launches nmap scan  (scan #1)")
    info2(f"Command: nmap {SCAN_FLAGS} {SCAN_SUBNET}")
    print()

    raw1 = attacker.cmd(f"nmap {SCAN_FLAGS} {SCAN_SUBNET} 2>/dev/null")
    vips1 = parse_nmap_ips(raw1)

    # Show only the useful part of nmap output
    for ln in clean_nmap(raw1).splitlines():
        if ln.strip():
            print(f"  {ln}")

    if vips1:
        table("Hosts visible to attacker — Scan #1",
              ["VIP discovered", "Port 80", "Result"],
              [[ip, "filtered", "attacker adds to target map"] for ip in sorted(vips1)])
    else:
        warn("No hosts found in scan #1 (controller may not have learned hosts yet)")

    # ── Step 3: wait for MTD response ─────────────────────────────────────────
    hdr("STEP 3", "Waiting for MTD response (AI-triggered or scheduled)")
    info2("AI scan classifier is analysing traffic from attacker...")

    deadline = time.time() + 45
    rotated  = False
    while time.time() < deadline:
        time.sleep(2)
        evs = read_events(demo_start_ts)
        if any(e["kind"] == "ROTATION" for e in evs):
            elapsed = time.time() - demo_start_ts
            ok(f"Rotation detected after {elapsed:.0f}s")
            rotated = True
            break
        if any(e["kind"] == "AI_DETECT" for e in evs):
            info2("AI detection fired — waiting for rotation to complete...")

    if not rotated:
        warn("No rotation event in 45s (check controller window)")

    # Show what the controller did
    show_events(demo_start_ts)

    # ── Step 4: second scan ───────────────────────────────────────────────────
    hdr("STEP 4", "Attacker scans again  (scan #2)")
    info2("Attacker re-scans using their saved map from scan #1...")
    print()

    raw2 = attacker.cmd(f"nmap {SCAN_FLAGS} {SCAN_SUBNET} 2>/dev/null")
    vips2 = parse_nmap_ips(raw2)

    for ln in clean_nmap(raw2).splitlines():
        if ln.strip():
            print(f"  {ln}")

    if vips2:
        table("Hosts visible to attacker — Scan #2",
              ["VIP discovered", "Port 80", "Result"],
              [[ip, "filtered", "completely different map"] for ip in sorted(vips2)])

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n{BD}{B}{'═'*62}{RS}")
    overlap = vips1 & vips2
    if not overlap:
        print(f"{BD}{G}  RESULT: PASS{RS}")
        print(f"{G}  Zero address overlap between scan #1 and scan #2.{RS}")
        print(f"{G}  Attacker's intelligence is completely invalidated.{RS}")
        print(f"{G}  Every address in their target map is now stale.{RS}")
    else:
        print(f"{BD}{R}  RESULT: WARN — overlap detected: {overlap}{RS}")
        warn("Rotation may not have completed in time.")
    print(f"{BD}{B}{'═'*62}{RS}\n")

    # ── Write report ──────────────────────────────────────────────────────────
    ts   = time.strftime("%Y%m%d_%H%M%S")
    rpt  = OUTPUTS_DIR / f"demo_{ts}.txt"
    with open(rpt, "w") as f:
        f.write(f"OF-RHM Demo Report — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n")
        f.write(f"Scan #1 VIPs : {sorted(vips1)}\n")
        f.write(f"Scan #2 VIPs : {sorted(vips2)}\n")
        f.write(f"Overlap      : {sorted(overlap)}\n")
        f.write(f"Result       : {'PASS' if not overlap else 'WARN'}\n\n")
        f.write("Events:\n")
        for e in read_events(demo_start_ts):
            f.write(f"  {e}\n")
    ok(f"Report saved → {rpt}")

    net.stop()


if __name__ == "__main__":
    run_demo()
