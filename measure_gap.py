#!/usr/bin/env python3
"""
measure_gap.py — Empirical proof that NAT atomic rotation eliminates packet loss.

Methodology
-----------
For each mode (LEGACY  USE_ATOMIC=False, ATOMIC  USE_ATOMIC=True):
  1. Patch controller.py's USE_ATOMIC constant
  2. Start ryu-manager as a subprocess
  3. Build and start the Mininet topology (topology.build())
  4. Warm-up: h1 ↔ h2 pings — controller learns MACs and assigns VIPs
  5. iperf3 UDP stream: server on h2, client on h1, 45 s @ 10 Mbps
     The scheduled VIP rotation fires at ~30 s (ROTATION_INTERVAL = 30 s)
  6. Parse iperf3 JSON for total packets sent / lost
  7. Restore controller.py and print side-by-side comparison table

Why 45 seconds?
  ROTATION_INTERVAL = 30 s.  Running for 45 s guarantees the rotation
  occurs well inside the measurement window regardless of startup jitter.

Expected output
---------------
  LEGACY  :  total_sent = 38000   total_lost = 42   (50 ms gap @ 10 Mbps)
  ATOMIC  :  total_sent = 38000   total_lost =  0   (barrier sync; gap = 0)
  VERDICT : PASS — atomic rotation provably eliminates the transition gap.

Usage
-----
    # Terminal 1 — do NOT start ryu-manager yourself; this script does it.
    sudo python3 measure_gap.py
"""

import json, os, pathlib, subprocess, sys, time

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = pathlib.Path(__file__).parent
CONTROLLER  = SCRIPT_DIR / "controller.py"

RYU_BOOT    = 4     # s  — wait after starting ryu-manager before touching Mininet
WARM_UP     = 6     # s  — ping warm-up so controller assigns VIPs before iperf3
IPERF_DUR   = 45    # s  — covers the 30 s scheduled rotation with margin
IPERF_BW    = "10M" # target UDP bandwidth (Mbps)
IPERF_INT   = "0.5" # per-interval reporting granularity (seconds)
IPERF_PORT  = 5201


# ─────────────────────────────────────────────────────────────────────────────
# controller.py patching
# ─────────────────────────────────────────────────────────────────────────────

def _patch_controller(atomic: bool):
    """Set USE_ATOMIC to the requested value in controller.py (in-place)."""
    text = CONTROLLER.read_text()
    want  = f"USE_ATOMIC = {atomic}"
    other = f"USE_ATOMIC = {not atomic}"
    if want in text:
        return  # already correct
    if other not in text:
        raise RuntimeError(
            f"Neither 'USE_ATOMIC = True' nor 'USE_ATOMIC = False' found in "
            f"{CONTROLLER}.  Cannot patch."
        )
    CONTROLLER.write_text(text.replace(other, want, 1))


# ─────────────────────────────────────────────────────────────────────────────
# Ryu lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────────

def _start_ryu() -> subprocess.Popen:
    proc = subprocess.Popen(
        ["ryu-manager", str(CONTROLLER), "--ofp-tcp-listen-port", "6653"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(RYU_BOOT)
    if proc.poll() is not None:
        raise RuntimeError(
            f"ryu-manager exited immediately (rc={proc.returncode}).  "
            f"Is ryu installed?  Try: pip install ryu"
        )
    return proc


def _stop_ryu(proc: subprocess.Popen):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ─────────────────────────────────────────────────────────────────────────────
# iperf3 JSON parser
# ─────────────────────────────────────────────────────────────────────────────

def _parse_iperf3_json(raw: str, label: str) -> dict:
    """
    Extract total packets sent and total packets lost from iperf3 JSON output.

    iperf3 UDP JSON layout (relevant paths):
      end.sum_received.packets        — total datagrams received by server
      end.sum_received.lost_packets   — total lost (missing from server)
      end.sum_sent.packets            — total datagrams sent by client
      end.sum.packets / end.sum.lost_packets  — fallback in older iperf3
    """
    base = {"label": label, "total_sent": 0, "total_lost": 0, "error": None}

    if not raw.strip():
        base["error"] = "empty output"
        return base

    # Strip any Mininet prompt noise that may appear before the JSON
    start = raw.find("{")
    if start < 0:
        base["error"] = "no JSON found in output"
        return base

    try:
        data = json.loads(raw[start:])
    except json.JSONDecodeError as exc:
        # Sometimes iperf3 is still flushing when we read; try to find complete JSON
        try:
            end = raw.rindex("}")
            data = json.loads(raw[start : end + 1])
        except (ValueError, json.JSONDecodeError):
            base["error"] = f"JSON parse failed: {exc}"
            return base

    end_block = data.get("end", {})

    # Prefer sum_received (receiver-side stats, includes loss) over sum (may be sender-only)
    for key in ("sum_received", "sum"):
        s = end_block.get(key, {})
        if "lost_packets" in s:
            base["total_sent"] = s.get("packets", 0)
            base["total_lost"] = s.get("lost_packets", 0)
            return base

    # Last resort: check streams array for UDP sub-object
    for stream in end_block.get("streams", []):
        udp = stream.get("udp", {})
        if "lost_packets" in udp:
            base["total_sent"] = udp.get("packets", 0)
            base["total_lost"] = udp.get("lost_packets", 0)
            return base

    base["error"] = "lost_packets field not found — iperf3 may be non-UDP or too old"
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Single experiment
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(atomic: bool) -> dict:
    label    = "ATOMIC" if atomic else "LEGACY"
    out_file = pathlib.Path(f"/tmp/iperf3_{label}.json")

    print(f"\n{'━' * 62}")
    print(f"  Experiment: {label}  (USE_ATOMIC = {atomic})")
    print(f"{'━' * 62}")

    _patch_controller(atomic)

    ryu = _start_ryu()
    print(f"  [+] ryu-manager started  (pid {ryu.pid})")

    # Import Mininet here so the module-level import doesn't block non-root runs
    from mininet.log import setLogLevel
    setLogLevel("warning")
    from topology import build

    net = build()
    net.start()
    h1 = net.get("h1")
    h2 = net.get("h2")
    print("  [+] Mininet topology ready  (h1=10.0.0.1, h2=10.0.0.2, s1)")

    # Every host needs a route to the VIP subnet so NAT'd traffic is reachable
    for h in net.hosts:
        h.cmd(
            f"ip route add 172.16.0.0/16 dev {h.defaultIntf().name} 2>/dev/null"
            f" || ip route replace 172.16.0.0/16 dev {h.defaultIntf().name}"
        )

    # Warm-up: bidirectional pings so the controller sees both h1 and h2,
    # installs their VIP mappings, and populates the L2 forwarding table.
    print(f"  [+] Warm-up ({WARM_UP} s) — controller learning MACs + assigning VIPs …")
    h1.cmd("ping -c 5 -i 0.5 10.0.0.2 > /dev/null 2>&1 &")
    h2.cmd("ping -c 5 -i 0.5 10.0.0.1 > /dev/null 2>&1 &")
    time.sleep(WARM_UP)

    # ─────────────────────────────────────────────────────────────────────── #
    # iperf3 UDP test
    #   Server: h2 daemon (-D), writing to /tmp for reference
    #   Client: h1 background, JSON output redirected to out_file
    # ─────────────────────────────────────────────────────────────────────── #
    h2.cmd(
        f"iperf3 -s -p {IPERF_PORT} -D "
        f"--logfile /tmp/iperf3_{label}_server.log 2>/dev/null"
    )
    time.sleep(0.4)   # let server bind

    h1.cmd(
        f"iperf3 -c 10.0.0.2 -p {IPERF_PORT} "
        f"-u -b {IPERF_BW} -t {IPERF_DUR} -i {IPERF_INT} -J "
        f"> {out_file} 2>&1 &"
    )

    print(
        f"  [+] iperf3 UDP running  ({IPERF_DUR} s @ {IPERF_BW})  "
        f"— rotation fires at ~30 s …"
    )
    # Block until the iperf3 test completes, plus a small buffer for JSON flush
    time.sleep(IPERF_DUR + 4)

    # Tidy up iperf3 processes (they should have exited by now, but be safe)
    h1.cmd("pkill -f 'iperf3 -c' 2>/dev/null; true")
    h2.cmd("pkill -f 'iperf3 -s' 2>/dev/null; true")
    time.sleep(0.5)

    # Read JSON output (written directly to host filesystem by the Mininet host)
    try:
        raw = out_file.read_text()
    except FileNotFoundError:
        raw = ""

    net.stop()
    _stop_ryu(ryu)
    print(f"  [+] Mininet and Ryu stopped")

    result = _parse_iperf3_json(raw, label)

    # Surface parse errors immediately
    if result.get("error"):
        print(f"  [!] Parser warning: {result['error']}")

    sent = result["total_sent"]
    lost = result["total_lost"]
    pct  = (lost / sent * 100) if sent else 0.0
    print(f"  [=] Packets sent={sent}  lost={lost}  ({pct:.2f}%)")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Final report
# ─────────────────────────────────────────────────────────────────────────────

def print_report(results: list):
    print(f"\n{'━' * 62}")
    print("  OF-RHM  ·  NAT Rotation Packet-Loss Measurement")
    print(f"{'━' * 62}\n")

    print(f"  {'Mode':<10}  {'Pkts sent':>11}  {'Pkts lost':>11}  {'Loss %':>8}")
    print(f"  {'-'*10}  {'-'*11}  {'-'*11}  {'-'*8}")

    for r in results:
        sent = r["total_sent"]
        lost = r["total_lost"]
        pct  = (lost / sent * 100) if sent else 0.0
        print(f"  {r['label']:<10}  {sent:>11}  {lost:>11}  {pct:>7.2f}%")

    print()

    legacy = next((r for r in results if r["label"] == "LEGACY"), {})
    atomic = next((r for r in results if r["label"] == "ATOMIC"), {})
    l_lost = legacy.get("total_lost", -1)
    a_lost = atomic.get("total_lost", -1)

    if a_lost == 0 and l_lost > 0:
        print("  VERDICT  ✓ PASS")
        print(f"  Legacy rotation  : {l_lost} packets dropped (transition gap confirmed)")
        print(f"  Atomic rotation  : 0 packets dropped (OpenFlow barrier eliminates gap)")
        print(f"\n  NAT atomicity claim is empirically verified.")
    elif a_lost == 0 and l_lost == 0:
        print("  VERDICT  ⚠ INCONCLUSIVE")
        print("  No loss in either mode — VIP rotation may not have fired.")
        print("  Tip: shorten ROTATION_INTERVAL in controller.py (e.g. 10 s)")
        print("       and re-run, or trigger manually with an nmap SYN scan.")
    elif a_lost > 0 and l_lost > 0 and a_lost < l_lost:
        print("  VERDICT  ⚠ PARTIAL IMPROVEMENT")
        print(f"  Atomic reduced loss {l_lost} → {a_lost} but did not reach zero.")
        print("  Check barrier event handler; ensure OFPBarrierReply is firing.")
    else:
        print(f"  VERDICT  ✗ UNEXPECTED  (legacy={l_lost}, atomic={a_lost})")
        print("  Inspect controller logs and iperf3 output in /tmp/.")

    print(f"\n{'━' * 62}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit(
            "ERROR: This script requires root privileges (Mininet uses Linux namespaces).\n"
            "       Run:  sudo python3 measure_gap.py"
        )

    if not CONTROLLER.exists():
        sys.exit(f"ERROR: {CONTROLLER} not found.  Run from the CN_proj directory.")

    # Snapshot the original controller so we can always restore it
    original_text = CONTROLLER.read_text()

    results = []
    try:
        results.append(run_experiment(atomic=False))   # baseline: legacy rotation
        time.sleep(2)                                   # brief cooldown between runs
        results.append(run_experiment(atomic=True))    # proof:    atomic rotation
    except KeyboardInterrupt:
        print("\n  [!] Interrupted by user")
    except Exception as exc:
        print(f"\n  [!] Fatal error: {exc}")
        import traceback; traceback.print_exc()
    finally:
        # Always restore controller.py regardless of how we exit
        CONTROLLER.write_text(original_text)
        print("[+] controller.py restored to original state (USE_ATOMIC preserved)")

    if results:
        print_report(results)
    else:
        print("No results collected — check errors above.")
