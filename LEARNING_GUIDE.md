# 🧊 Vanishing Address — Complete Learning Guide

Welcome! This is a **Moving Target Defense (MTD)** system built on OpenFlow. Let me walk you through everything step-by-step.

---

## 📋 What is This Project?

Imagine you have servers with real IP addresses (10.0.0.1, 10.0.0.2, 10.0.0.3). An attacker can scan the network and find them. This project **constantly changes the IP addresses** so attackers can never find them. It's like a chameleon for networks! 🦎

**Key idea:** Your real IPs stay the same, but you "assign" temporary virtual IPs (VIPs) that change every 30 seconds. Attackers see moving targets.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  YOUR NETWORK                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  h1 (10.0.0.1) ─┐                                   │
│  h2 (10.0.0.2) ─┤── s1 (OVS Switch) ← 6653 ─┐      │
│  h3 (10.0.0.3) ─┤                             │      │
│  Attacker       ─┘                        Ryu       │
│  (10.0.0.99)                            Controller   │
│                                          (6653)      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Players:**
- **Hosts** (h1, h2, h3): Your real servers
- **Attacker** (10.0.0.99): The bad guy trying to scan
- **Switch (s1)**: An OpenFlow Switch (OVS — Open vSwitch)
- **Ryu Controller**: Manages the switch's behavior

**Flow:**
1. Ryu runs the MTD logic (assigning VIPs, rotating them)
2. Ryu tells the switch what to do via OpenFlow
3. When h1 sends a packet, the switch rewrites the source IP from 10.0.0.1 to a VIP (e.g., 172.16.42.99)
4. The attacker sees 172.16.42.99, not 10.0.0.1
5. Every 30 seconds, new VIPs are assigned → attacker loses track

---

## 📁 Files Explained

### 1️⃣ **requirements.txt** — Dependencies

```
ryu
eventlet==0.30.2
```

**What it does:** Lists Python libraries you need.
- **Ryu**: An OpenFlow controller framework (lets you write custom network logic)
- **Eventlet**: Async networking library (helps Ryu handle many connections)

**How to install:**
```bash
pip install -r requirements.txt
sudo apt install mininet openvswitch-switch nmap  # Linux packages
```

---

### 2️⃣ **topology.py** — Network Topology (The Plumbing)

**What it does:** Creates the virtual network with Mininet.

```python
def build():
    net = Mininet(...)  # Create a virtual network
    
    # Add a controller (Ryu)
    net.addController("c0", ip="127.0.0.1", port=6653)
    
    # Add an OpenFlow switch
    s1 = net.addSwitch("s1", protocols="OpenFlow13")
    
    # Add hosts (virtual machines)
    h1 = net.addHost("h1", ip="10.0.0.1/24")
    h2 = net.addHost("h2", ip="10.0.0.2/24")
    h3 = net.addHost("h3", ip="10.0.0.3/24")
    attacker = net.addHost("attacker", ip="10.0.0.99/24")
    
    # Wire them all to the switch
    for host in (h1, h2, h3, attacker):
        net.addLink(host, s1)
    
    return net
```

**Key Concepts:**
- **Mininet** = Virtual network on your computer (no real hardware needed!)
- **OpenFlow13** = The switch uses OpenFlow version 1.3 (standard protocol)
- **Port 6653** = The switch talks to the controller on this port

**How to run:**
```bash
sudo python3 topology.py
```

This starts a **CLI** where you can type commands like:
- `h1 ping h2` — Test connectivity
- `h1 ifconfig` — Check IP addresses
- `exit` — Quit

---

### 3️⃣ **demo.py** — Automated Demo (The Full Show)

**What it does:** Runs the entire MTD scenario without manual intervention.

**Step-by-step:**

```python
# Step 1: Start Mininet
net = build()
net.start()

# Step 2: Add routes (so hosts can reach the VIP subnet 172.16.0.0/16)
for h in hosts + [attacker]:
    h.cmd(f"ip route add 172.16.0.0/16 dev {interface}")

# Step 3: "Warm up" — ping to let the controller learn MAC addresses
for h in hosts:
    h.cmd("ping -c1 -W1 10.0.0.1 &")  # Background ping
time.sleep(3)

# Step 4: First Nmap scan (attacker tries to find targets)
out1 = attacker.cmd(f"nmap -sn 172.16.0.0/16")
# Output: "Nmap scan report for 172.16.XX.XX"
# Attacker sees VIP addresses! ✅

# Step 5: WAIT 35 seconds
# Behind the scenes: Controller rotates VIPs every 30 seconds
time.sleep(35)

# Step 6: Second Nmap scan (after rotation)
out2 = attacker.cmd(f"nmap -sn 172.16.0.0/16")
# Output: Different VIPs! "Nmap scan report for 172.16.YY.YY"

# Step 7: RESULT
if vips_round1 & vips_round2 == empty:
    print("✅ PASS: Zero overlap — MTD is working!")
else:
    print("❌ FAIL: Some IPs didn't rotate")
```

**What's nmap?**
```bash
nmap -sn 172.16.0.0/16
```
- `-sn` = "ping sweep" (send ARP pings to find alive hosts)
- Attacker is looking for targets in the VIP subnet
- Normally, same IPs appear every time
- **With MTD:** Different IPs every 30 seconds!

**How to run:**
```bash
# Terminal 1: Start the Ryu controller
ryu-manager controller.py

# Terminal 2: Run the demo
sudo python3 demo.py
```

---

### 4️⃣ **ui.html** — Web Dashboard (The Visual)

**What it does:** Beautiful real-time dashboard showing everything happening.

#### **Layout:**
- **Left panel**: Countdown timer, LED indicators, buttons
- **Center**: Network diagram (switch, hosts, attacker) with animated packets
- **Right panel**: Event log, flow table

#### **Key Components:**

**A) Countdown Timer**
```javascript
const ROT_MS = 30000;  // 30 seconds
const S.nextRot = Date.now() + ROT_MS;  // When's the next rotation?
```
Shows "30s" → "29s" → ... → "0s" → ROTATE! 🔄

**B) Network Diagram (SVG)**
```html
<g id="nh1" transform="translate(108,114)">
  <!-- h1 host box -->
  <text id="v1">—</text>  <!-- Current VIP -->
</g>
```
SVG draws boxes for hosts, links, the switch. When rotation happens, VIPs animate like this:
```
172.16.42.99 ← Random
172.16.88.77 ← Random
172.16.15.22 ← Settles here
```

**C) Animated Packets**
```javascript
function spawnPkt(key, color, speed) {
    S.pkts.push({
        x1: link.x1, y1: link.y1,  // Start point
        x2: link.x2, y2: link.y2,  // End point
        t: 0, sp: speed,            // Progress + speed
        c: color,                   // Color (blue=legit, red=attack)
    });
}
```
Packets fly across the network diagram. Colors:
- 🔵 **Blue**: Legitimate traffic (host-to-host)
- 🟠 **Amber**: Burst after rotation
- 🔴 **Red**: Attacker scan
- 🟣 **Purple**: Controller commands

**D) Event Log**
```javascript
log('rot', '↻', '[ROTATE] Scheduled — 30 s interval');
log('sc',  '⚠', '[SCAN DETECTED] 10.0.0.99 → 3 VIPs in <10s');
log('lrn', '🟢', '10.0.0.1 learned · VIP 172.16.42.99');
```
Shows everything that happens (rotations, scans, host learning).

**E) Flow Table**
```
Match dst (VIP)  →  Rewrite to (Real IP)
172.16.42.99     →  10.0.0.1
172.16.88.77     →  10.0.0.2
172.16.15.22     →  10.0.0.3
```
When a packet arrives with destination VIP, it gets rewritten to the real IP.

#### **JavaScript State Machine:**
```javascript
const S = {
  paused: false,
  rotN: 0,          // Number of rotations
  scN: 0,           // Number of scans detected
  hosts: {
    h1: { vip: null, real: '10.0.0.1' },
    h2: { vip: null, real: '10.0.0.2' },
    ...
  },
  usedV: new Set(), // VIPs we've already assigned
};
```

#### **Main Loop:**
```javascript
function loop(now) {
  requestAnimationFrame(loop);  // 60 FPS
  
  if (Date.now() >= S.nextRot) rotate();  // Time to rotate?
  tickPkts(dt);                           // Update packets
  drawBG(dt);                             // Draw canvas (snow effect)
  refreshStats();                         // Update counters
}
```

**How to open:**
Just open `ui.html` in a browser. It starts with a **simulation** (no real controller needed).
To connect to real Ryu: Controller must send SSE (Server-Sent Events) to `http://127.0.0.1:8080/mtd/events`

---

## 🔄 How MTD Works (The Logic)

### **Lifecycle of a Packet:**

**Real IP Outgoing (Host → Internet):**
```
h1 sends: SRC=10.0.0.1  DST=8.8.8.8
          ↓ [Switch processes with T_OUT table]
          SRC=172.16.42.99  DST=8.8.8.8  ← VIP replaces real IP
          ↓
Internet thinks h1 is at 172.16.42.99
```

**Response Incoming (Internet → Host):**
```
Packet arrives: SRC=8.8.8.8  DST=172.16.42.99 (the VIP)
                ↓ [Switch processes with T_IN table]
                SRC=8.8.8.8  DST=10.0.0.1 (real IP)
                ↓
h1 receives it normally
```

### **VIP Rotation (What Changes Every 30 Seconds):**

**Before Rotation (Age 0-30s):**
```
h1 VIP = 172.16.42.99
h2 VIP = 172.16.88.77
h3 VIP = 172.16.15.22
```

**At 30s Mark — ROTATE!**
```
Random number generator picks new VIPs:
h1 VIP = 172.16.61.8   ← CHANGED!
h2 VIP = 172.16.200.44 ← CHANGED!
h3 VIP = 172.16.9.123  ← CHANGED!
```

All the old ones are discarded. Attacker's scan results are now useless!

### **Attack Detection:**

If attacker sends 3+ probe packets to different VIPs within 10 seconds:
```python
if vip_probes_in_10s >= 3:
    # DETECTED! Initiate emergency rotation
    rotate("Emergency — scan from 10.0.0.99")
```

---

## 🚀 Running Everything (Step-by-Step)

### **Option 1: Just the Dashboard (No Real Network)**
```bash
# Just open ui.html in Chrome/Firefox
# It runs a built-in simulation
open ui.html
```

### **Option 2: Full Real Demo**
```bash
# Terminal 1: Start Ryu controller (from CN_proj folder)
ryu-manager controller.py

# Wait for: "running app(s) ['mtd_app']"

# Terminal 2: Run automated demo
sudo python3 demo.py
```

**Output:**
```
───────────────────────────────────────────────────
  Step 1: adding VIP routes and warming up
───────────────────────────────────────────────────

───────────────────────────────────────────────────
  Step 2: attacker runs Nmap (scan #1 — before rotation)
───────────────────────────────────────────────────
Nmap scan report for 172.16.42.99
Nmap scan report for 172.16.88.77
Nmap scan report for 172.16.15.22
  Addresses visible to attacker: {172.16.42.99, 172.16.88.77, 172.16.15.22}

───────────────────────────────────────────────────
  Step 3: waiting 35 s for scheduled rotation…
───────────────────────────────────────────────────

───────────────────────────────────────────────────
  Step 4: attacker runs Nmap again (scan #2 — after rotation)
───────────────────────────────────────────────────
Nmap scan report for 172.16.61.8
Nmap scan report for 172.16.200.44
Nmap scan report for 172.16.9.123
  Addresses visible to attacker: {172.16.61.8, 172.16.200.44, 172.16.9.123}

───────────────────────────────────────────────────
  Result
───────────────────────────────────────────────────
PASS  Zero address overlap between scans — MTD is working!
```

---

## 🎓 Key Concepts to Understand

### **1. OpenFlow**
A standard protocol where a controller (Ryu) tells a switch (s1) what to do:
- "When you see packet X, do Y"
- All forwarding logic lives on the controller, not the switch
- Switch = dumb, Controller = smart

### **2. Virtual IPs (VIPs)**
- Not real IP addresses on any interface
- Generated randomly: `172.16.0.0/16` = 172.16.1.1 to 172.16.254.254
- Stored only in the controller's memory
- When rotation happens, old ones disappear forever

### **3. Flow Tables**
- **T_OUT**: "When sending TO the internet, rewrite SRC to VIP"
- **T_IN**: "When receiving FROM the internet, rewrite DST back to real IP"
- **T_L2**: "Forward to the right port"

### **4. Mininet**
- Creates virtual hosts, switches, links on your computer
- Each host is a Linux network namespace
- Can run real tools (ping, nmap, iperf) inside

### **5. Ryu**
- OpenFlow controller framework (Python library)
- Listens on port 6653 for switch connections
- Implements the MTD logic (VIP assignment, rotation)

---

## 💻 What Each Tool Does

| Tool | What It Is | Example |
|------|-----------|---------|
| **Mininet** | Virtual network simulator | `sudo python3 topology.py` → creates virtual network |
| **Ryu** | OpenFlow controller | `ryu-manager controller.py` → runs MTD logic |
| **OVS** (Open vSwitch) | OpenFlow switch | Runs inside Mininet, follows Ryu's commands |
| **Nmap** | Network scanner | `nmap -sn 172.16.0.0/16` → finds alive hosts |
| **OpenFlow 1.3** | Protocol | Switch ↔ Controller communication |

---

## 🧠 Brain Exercise: Trace a Packet

**Scenario:** h1 (10.0.0.1) sends ping to h2 (10.0.0.2)

**1. h1 creates the packet:**
```
SRC = 10.0.0.1
DST = 10.0.0.2
ICMP ECHO request
```

**2. h1 sends it out its interface:**
```
Physical link: h1-eth0 → s1-eth1 (the switch)
```

**3. Switch receives it on port 1:**
```
Table T_OUT (outgoing):
  Match: SRC = 10.0.0.1
  Action: Rewrite SRC to VIP 172.16.42.99
```
Packet becomes:
```
SRC = 172.16.42.99
DST = 10.0.0.2
```

**4. Switch forwards to port 2 (h2):**
```
Table T_L2 (forwarding):
  Match: Everything
  Action: Forward to all ports except ingress
```

**5. h2 receives it on h2-eth0:**
```
SRC = 172.16.42.99
DST = 10.0.0.2
```

**6. h2 responds:**
```
SRC = 10.0.0.2
DST = 172.16.42.99 (the attacker's VIP!)
```

**7. Switch receives h2's response on port 2:**
```
Table T_IN (incoming):
  Match: DST = 172.16.42.99
  Action: Rewrite DST to 10.0.0.1 (h1's real IP)
```
Packet becomes:
```
SRC = 10.0.0.2
DST = 10.0.0.1
```

**8. h1 receives the response:**
```
Echo reply from 10.0.0.2 ✅
Ping successful!
```

---

## 🔍 Debugging Tips

**Check if Ryu is running:**
```bash
ps aux | grep ryu-manager
```

**Check if switch is connected:**
```bash
ryu-manager controller.py  # Look for "registered LLDP packet in"
```

**Test connectivity in Mininet CLI:**
```
mininet> h1 ping -c1 h2
PING 10.0.0.2 from 10.0.0.1
64 bytes from 10.0.0.2 icmp_seq=0 ttl=64 time=0.123 ms
```

**Check switch flows:**
```bash
# Inside Mininet CLI:
mininet> s1 ovs-ofctl dump-flows s1
```

**Monitor nmap timing:**
```bash
# Inside Mininet (terminal 2 during demo):
mininet> attacker nmap -sn -T5 --min-rate 2000 172.16.0.0/16
```

---

## 🎯 What to Experiment With

1. **Change rotation interval:** Edit `ROT_MS = 30000` → try 15000 (15 seconds)
2. **Change VIP subnet:** Edit `172.16.0.0/16` → try `192.168.10.0/16`
3. **Add more hosts:** In topology.py, add `h4 = net.addHost("h4", ip="10.0.0.4/24")`
4. **Change nmap timing:** Edit `SCAN_FLAGS` in demo.py
5. **Add a real attacker:** Replace `attacker.cmd(nmap)` with actual malicious code

---

## 📖 Recommended Reading Order

1. **First:** Understand the problem (MTD exists because...)
2. **Second:** Read topology.py (what's the network?)
3. **Third:** Read ui.html JavaScript (what happens visually?)
4. **Fourth:** Run demo.py (see it in action)
5. **Fifth:** Modify controller.py (the real MTD logic)

---

## ❓ FAQ

**Q: Why is it called "Vanishing Address"?**
A: The IP addresses vanish (change) every 30 seconds! Like magic.

**Q: Can a real attacker get past this?**
A: Harder than finding a static IP, but attackers can:
- Flood with many packets to hit any VIP
- Learn the rotation interval (30s)
- Use side-channel attacks
- Monitor control traffic

**Q: Why 172.16.0.0/16?**
A: That's a private IP range (like 10.0.0.0/8 or 192.168.0.0/16). Won't conflict with real internet IPs.

**Q: What if a VIP accidentally matches the real IP?**
A: The `randVIP()` function checks `while(S.usedV.has(v))` to avoid duplicates.

**Q: Can I run this on a Raspberry Pi?**
A: Yes! See requirements.txt: "Run on Ubuntu/Debian or Raspberry Pi OS"

---

## 🏆 You Now Know...

✅ What Moving Target Defense is  
✅ How OpenFlow controls network behavior  
✅ How to build a virtual network with Mininet  
✅ How VIPs protect real servers  
✅ How to trace a packet through the system  
✅ How to run and debug the project  

**Next step:** Open `ui.html` and run `demo.py` side-by-side. Watch the magic happen! 🪄

---

**Questions?** Look for "controller.py" in the project — that's the brain of the MTD system!
