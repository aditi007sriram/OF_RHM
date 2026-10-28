#!/usr/bin/env python3
"""
capture_training_data.py — Capture real Mininet traffic for model training.

Run on Raspberry Pi:
    sudo python3 capture_training_data.py

Output:
    real_features.csv   (transfer to Windows laptop for training)

What it does:
  1. Builds a Mininet topology with a simple learning switch (no Ryu needed)
  2. Phase 1 — SCANNER (label=1):
       attacker runs nmap -sS on 172.16.0.0/24 while tcpdump records its traffic
  3. Phase 2 — NORMAL (label=0):
       h1, h2, h3 exchange pings and iperf3 UDP bursts while tcpdump records
  4. Processes both pcap files with scapy, sliding a 10-second window over each
     source IP and extracting the 6 features the controller uses in _track_syn
  5. Writes real_features.csv — one row per (source, window)

Transfer to Windows:
    scp pi@10.176.30.10:~/CN_proj/ai/real_features.csv .
"""

import os, sys, time, csv, pathlib
import numpy as np

SCRIPT_DIR   = pathlib.Path(__file__).parent
OUT_CSV      = SCRIPT_DIR / "real_features.csv"
PCAP_SCANNER = "/tmp/scanner_capture.pcap"
PCAP_NORMAL  = "/tmp/normal_capture.pcap"

SCAN_WINDOW  = 10.0   # seconds — must match controller.py
SCAN_PHASE   = 45     # seconds to run nmap
NORMAL_PHASE = 60     # seconds to run normal traffic

# ─────────────────────────────────────────────────────────────────────────────
# Mininet topology (standalone — no ryu-manager required)
# ─────────────────────────────────────────────────────────────────────────────

def build_net():
    from mininet.net import Mininet
    from mininet.node import OVSKernelSwitch, DefaultController
    from mininet.log import setLogLevel
    setLogLevel("warning")

    net = Mininet(controller=DefaultController, switch=OVSKernelSwitch)
    net.addController("c0")
    s1       = net.addSwitch("s1")
    h1       = net.addHost("h1", ip="10.0.0.1/24")
    h2       = net.addHost("h2", ip="10.0.0.2/24")
    h3       = net.addHost("h3", ip="10.0.0.3/24")
    attacker = net.addHost("attacker", ip="10.0.0.99/24")
    for h in (h1, h2, h3, attacker):
        net.addLink(h, s1)
    net.start()
    # add VIP subnet route on all hosts so nmap can reach 172.16.0.x
    for h in net.hosts:
        h.cmd(f"ip route add 172.16.0.0/16 dev {h.defaultIntf().name} 2>/dev/null || true")
    return net


# ─────────────────────────────────────────────────────────────────────────────
# Feature extraction from a pcap file
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(pcap_path: str, label: int) -> list[dict]:
    """
    Slide a SCAN_WINDOW over the pcap and emit one feature-row per
    (source IP, window start) that contains at least 3 TCP SYN packets.

    Features (must match _track_syn in controller.py):
      n_unique_vips, syn_rate, syn_ack_ratio, elapsed,
      inter_arrival_variance, unique_vip_rate
    """
    from scapy.all import rdpcap, TCP

    try:
        packets = rdpcap(pcap_path)
    except Exception as e:
        print(f"  [!] Cannot read {pcap_path}: {e}")
        return []

    # Group packets by source IP
    by_src: dict[str, list] = {}
    for pkt in packets:
        if not pkt.haslayer("IP") or not pkt.haslayer("TCP"):
            continue
        src = pkt["IP"].src
        by_src.setdefault(src, []).append(pkt)

    rows = []
    for src, pkts in by_src.items():
        pkts.sort(key=lambda p: float(p.time))
        times     = [float(p.time) for p in pkts]
        t_start   = times[0]
        t_end     = times[-1]

        # Slide the window
        win_start = t_start
        while win_start < t_end:
            win_end = win_start + SCAN_WINDOW
            win_pkts = [p for p, t in zip(pkts, times)
                        if win_start <= t < win_end]
            if len(win_pkts) < 3:
                win_start += SCAN_WINDOW / 2
                continue

            tcp_pkts   = [p for p in win_pkts if p.haslayer(TCP)]
            syn_pkts   = [p for p in tcp_pkts if p[TCP].flags & 0x02]
            ack_pkts   = [p for p in tcp_pkts if p[TCP].flags & 0x10]
            targets    = {p["IP"].dst for p in win_pkts}

            elapsed         = max(win_end - win_start, 0.001)
            syn_count       = len(syn_pkts)
            ack_count       = len(ack_pkts)
            n_unique_vips   = len(targets)
            syn_rate        = syn_count / elapsed
            syn_ack_ratio   = syn_count / (ack_count + 1)
            unique_vip_rate = n_unique_vips / elapsed

            # inter-arrival variance (machine-paced scanners = very regular)
            win_times = sorted(float(p.time) for p in win_pkts)
            if len(win_times) >= 3:
                gaps = [win_times[i+1] - win_times[i]
                        for i in range(len(win_times) - 1)]
                iav  = float(np.var(gaps))
            else:
                iav = 1.0

            rows.append({
                "n_unique_vips":         n_unique_vips,
                "syn_rate":              syn_rate,
                "syn_ack_ratio":         syn_ack_ratio,
                "elapsed":               elapsed,
                "inter_arrival_variance": iav,
                "unique_vip_rate":       unique_vip_rate,
                "label":                 label,
            })
            win_start += SCAN_WINDOW / 2   # 50% overlap for more samples

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if os.geteuid() != 0:
        sys.exit("Run with sudo: sudo python3 capture_training_data.py")

    print("\n[capture] Building Mininet topology …")
    net = build_net()
    h1 = net.get("h1"); h2 = net.get("h2"); h3 = net.get("h3")
    attacker = net.get("attacker")

    # warm-up: let OVS learning switch populate its MAC table
    print("[capture] Warming up (5s) …")
    h1.cmd("ping -c 5 -i 0.5 10.0.0.2 > /dev/null 2>&1")
    h2.cmd("ping -c 5 -i 0.5 10.0.0.3 > /dev/null 2>&1")
    time.sleep(5)

    # ── Phase 1: scanner traffic ──────────────────────────────────────────────
    print(f"\n[Phase 1] Scanner — nmap SYN scan for {SCAN_PHASE}s …")
    attacker.cmd(f"tcpdump -i attacker-eth0 -w {PCAP_SCANNER} tcp &")
    time.sleep(0.5)
    # nmap SYN scan of the VIP subnet (--max-retries 0 = fast, like real attacker)
    attacker.cmd(
        f"nmap -sS -p 80 --max-retries 0 -T4 172.16.0.0/24 "
        f"> /dev/null 2>&1 &"
    )
    time.sleep(SCAN_PHASE)
    attacker.cmd("pkill -f nmap 2>/dev/null; pkill -f tcpdump 2>/dev/null; true")
    time.sleep(1)
    print(f"  pcap saved → {PCAP_SCANNER}")

    # ── Phase 2: normal traffic ───────────────────────────────────────────────
    print(f"\n[Phase 2] Normal traffic for {NORMAL_PHASE}s …")
    h1.cmd(f"tcpdump -i h1-eth0 -w {PCAP_NORMAL} tcp &")
    h2.cmd(f"tcpdump -i h2-eth0 -w {PCAP_NORMAL.replace('.pcap','_h2.pcap')} tcp &")
    time.sleep(0.5)
    # Mix of ping bursts and iperf3 TCP (normal browsing simulation)
    h1.cmd("iperf3 -s -D 2>/dev/null")
    h2.cmd("iperf3 -s -D 2>/dev/null")
    time.sleep(0.5)
    for _ in range(NORMAL_PHASE // 5):
        h2.cmd("iperf3 -c 10.0.0.1 -t 3 > /dev/null 2>&1 &")
        h3.cmd("ping -c 10 -i 0.3 10.0.0.2 > /dev/null 2>&1 &")
        h1.cmd("ping -c 10 -i 0.3 10.0.0.3 > /dev/null 2>&1 &")
        time.sleep(5)
    h1.cmd("pkill -f tcpdump 2>/dev/null; pkill -f iperf3 2>/dev/null; true")
    h2.cmd("pkill -f tcpdump 2>/dev/null; pkill -f iperf3 2>/dev/null; true")
    time.sleep(1)
    print(f"  pcap saved → {PCAP_NORMAL}")

    net.stop()
    print("\n[capture] Mininet stopped. Extracting features …")

    # ── Feature extraction ────────────────────────────────────────────────────
    scanner_rows = extract_features(PCAP_SCANNER, label=1)
    normal_rows  = extract_features(PCAP_NORMAL,  label=0)
    # also grab h2's capture for more normal samples
    normal_rows += extract_features(PCAP_NORMAL.replace('.pcap','_h2.pcap'), label=0)

    print(f"  Scanner samples : {len(scanner_rows)}")
    print(f"  Normal samples  : {len(normal_rows)}")

    if not scanner_rows and not normal_rows:
        print("[!] No samples extracted — check pcap files in /tmp/")
        sys.exit(1)

    all_rows = scanner_rows + normal_rows

    fieldnames = ["n_unique_vips", "syn_rate", "syn_ack_ratio", "elapsed",
                  "inter_arrival_variance", "unique_vip_rate", "label"]
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n[capture] Saved {len(all_rows)} rows → {OUT_CSV}")
    print("Transfer to Windows:")
    print(f"  scp pi@10.176.30.10:{OUT_CSV} .")
    print("Then retrain:  py -3.12 train_scan_detector.py")


if __name__ == "__main__":
    main()
