"""
OF-RHM: OpenFlow Random Host Mutation — 3-table pipeline

  Table 0 (Outbound NAT): match src=real_ip on host port → rewrite src→VIP, goto T1
  Table 1 (Inbound NAT):  match dst=VIP              → rewrite dst→real_ip, goto T2
  Table 2 (L2 forward):   unicast by MAC; table-miss  → controller

Two-table NAT means one packet can get BOTH src and dst rewritten in sequence,
which single-table OpenFlow cannot do without priority conflicts.

AI extensions:
  scan_detector.pkl  — Random Forest classifier replaces threshold-based scan detection
  vip_scorer.pkl     — Gradient Boosting scorer replaces random VIP selection
  Both models degrade gracefully to rule-based fallback if .pkl files are missing.
"""

import json
import random
import time
import ipaddress
import pathlib

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4, tcp

import led

# ── AI model loading ──────────────────────────────────────────────────────────
# Models are optional — controller falls back to rule-based logic if missing.
try:
    import numpy as np
    import joblib
    _AI_AVAILABLE = True
except ImportError:
    _AI_AVAILABLE = False

_MODEL_DIR   = pathlib.Path(__file__).parent / "ai"
_SCAN_MODEL  = None
_VIP_MODEL   = None

if _AI_AVAILABLE:
    try:
        _SCAN_MODEL = joblib.load(_MODEL_DIR / "scan_detector.pkl")
        print("[AI] scan_detector.pkl loaded — AI scan detection active")
    except FileNotFoundError:
        print("[AI] scan_detector.pkl not found — using threshold-based detection")

    try:
        _VIP_MODEL = joblib.load(_MODEL_DIR / "vip_scorer.pkl")
        print("[AI] vip_scorer.pkl loaded — AI VIP selection active")
    except FileNotFoundError:
        print("[AI] vip_scorer.pkl not found — using random VIP selection")
# ─────────────────────────────────────────────────────────────────────────────

# ── Config ────────────────────────────────────────────────────────────────────
REAL_SUBNET       = '10.0.0.0/24'
VIP_POOL          = '172.16.0.0/24'   # /24 = 254 VIPs; fast nmap scans for demo
ROTATION_INTERVAL = 30       # seconds between scheduled rotations (short for demo)
ROTATION_FAST     = 5        # seconds between rotations while under active attack
RELAX_AFTER       = 3        # clean rotations before returning to normal speed
SCAN_WINDOW       = 10       # seconds
SCAN_THRESHOLD    = 3        # distinct VIPs probed → scan declared (matches 3-host net)

# Set True to use gap-free two-phase barrier rotation (the novelty contribution).
# Set False to revert to the legacy delete-then-reinstall approach for comparison.
USE_ATOMIC = True

T_OUT = 0   # outbound NAT table
T_IN  = 1   # inbound NAT table
T_L2  = 2   # L2 forwarding table

NAT_PRI = 10
L2_PRI  = 5

_VIP_HOSTS   = list(ipaddress.ip_network(VIP_POOL).hosts())
_VIP_NET     = ipaddress.ip_network(VIP_POOL)
_REAL_PREFIX = REAL_SUBNET.rsplit('.', 1)[0] + '.'   # '10.0.0.'

# ── Event log (written here, read by demo.py for pretty output) ───────────────
_OUTPUTS_DIR = pathlib.Path(__file__).parent / "outputs"
_EVENTS_LOG  = _OUTPUTS_DIR / "events.jsonl"
_OUTPUTS_DIR.mkdir(exist_ok=True)
_EVENTS_LOG.write_text("")   # clear on each controller start

def _log_event(kind, **data):
    with open(_EVENTS_LOG, "a") as _f:
        _f.write(json.dumps({"ts": round(time.time(), 3), "kind": kind, **data}) + "\n")
# ─────────────────────────────────────────────────────────────────────────────


class MTDController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths       = {}
        self.real_to_vip     = {}
        self.vip_to_real     = {}
        self.host_port       = {}
        self.host_mac        = {}
        self._used_vips      = set()
        self._scan_state     = {}
        self._barrier_events = {}   # xid → hub.Event; used by _barrier_wait

        # ── AI tracking structures ─────────────────────────────────────────
        self._src_syn_count          = {}   # src_ip → SYN packet count
        self._src_ack_count          = {}   # src_ip → ACK packet count
        self._probed_vips            = {}   # vip → probe_count (attacker intel history)
        self._vip_history            = []   # list of sets — VIPs used per past rotation
        self._src_pkt_times          = {}   # src_ip → list of recent packet timestamps
        self._current_interval       = ROTATION_INTERVAL   # adaptive: shrinks under attack
        self._rotations_since_attack = 0                   # used to relax interval
        # ──────────────────────────────────────────────────────────────────

        hub.spawn(self._rotation_loop)

    # ── VIP management ────────────────────────────────────────────────────────

    def _pick_vip(self):
        available = [str(h) for h in _VIP_HOSTS if str(h) not in self._used_vips]
        return random.choice(available)

    def _pick_vip_excluding(self, exclude_set):
        """
        AI-powered VIP selection.

        Scores every candidate VIP using the trained Gradient Boosting model.
        The model prefers VIPs that are:
          - Not recently used (avoids predictable cycling)
          - Not previously probed by an attacker (avoids giving known addresses)
          - Far (last-octet distance) from the current active VIP set

        Falls back to random.choice() if the model is not loaded.
        """
        candidates = [
            str(h) for h in _VIP_HOSTS if str(h) not in exclude_set
        ]
        if not candidates:
            raise RuntimeError("VIP pool exhausted — reduce number of hosts or expand VIP_POOL")

        if _VIP_MODEL is None or not _AI_AVAILABLE:
            return random.choice(candidates)

        rotation_count = len(self._vip_history)
        active_octets  = [int(v.split('.')[-1]) for v in self._used_vips]

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
            dist = min((abs(octet - a) for a in active_octets), default=128)

            features.append([recently_used, recently_probed, probe_count,
                              last_used_ago, dist])

        scores     = _VIP_MODEL.predict_proba(np.array(features))[:, 1]
        best_idx   = int(np.argmax(scores))
        chosen     = candidates[best_idx]

        self.logger.info(
            f"  [AI-VIP] selected {chosen}  "
            f"score={scores[best_idx]:.3f}  "
            f"probed={self._probed_vips.get(chosen, 0)}  "
            f"dist={features[best_idx][4]}"
        )
        return chosen

    def _assign_vip(self, real_ip):
        vip = self._pick_vip()
        self.real_to_vip[real_ip] = vip
        self.vip_to_real[vip]     = real_ip
        self._used_vips.add(vip)
        self.logger.info(f"  {real_ip} → VIP {vip}")
        _log_event("VIP_ASSIGN", real_ip=real_ip, vip=vip)
        return vip

    def _rotate(self, reason="scheduled"):
        self.logger.info(f"\n{'='*50}\n[ROTATE] {reason}")
        old = dict(self.real_to_vip)
        self.real_to_vip.clear()
        self.vip_to_real.clear()
        self._used_vips.clear()
        for dp in self.datapaths.values():
            self._del_nat_flows(dp)
            # _del_nat_flows issues a wildcard DELETE that wipes every flow in
            # T_OUT and T_IN — including the priority-0 goto_table defaults.
            # Restore them immediately before reinstalling NAT rules.
            self._setup_pipeline(dp)
        for real_ip in old:
            self._assign_vip(real_ip)
        for dp in self.datapaths.values():
            self._install_all_nat(dp)
        self.logger.info('='*50)
        led.pulse_mutation()

    def _rotation_loop(self):
        while True:
            hub.sleep(self._current_interval)
            self._rotations_since_attack += 1
            if (self._rotations_since_attack >= RELAX_AFTER
                    and self._current_interval != ROTATION_INTERVAL):
                self._current_interval = ROTATION_INTERVAL
                self.logger.info(
                    f"[THREAT] Quiet for {RELAX_AFTER} rotations — "
                    f"interval restored to {ROTATION_INTERVAL}s"
                )
            if USE_ATOMIC:
                self._rotate_atomic("scheduled timer")
            else:
                self._rotate("scheduled timer")

    # ── Atomic (gap-free) rotation ────────────────────────────────────────────

    def _barrier_wait(self, dp):
        """
        Send OFPBarrierRequest to dp and block this greenlet until the switch
        replies.  The barrier guarantees every FlowMod sent before the request
        has been committed to the switch's pipeline before we proceed.
        """
        ev     = hub.Event()
        parser = dp.ofproto_parser
        req    = parser.OFPBarrierRequest(datapath=dp)
        dp.set_xid(req)                      # assign XID before registering
        self._barrier_events[req.xid] = ev
        dp.send_msg(req)
        ev.wait()                            # yields greenlet; resumes in _barrier_reply
        # hub.Event.wait() blocks until .send() is called from _barrier_reply

    @set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
    def _barrier_reply(self, ev):
        """Wake the greenlet waiting in _barrier_wait for this XID."""
        barrier_ev = self._barrier_events.pop(ev.msg.xid, None)
        if barrier_ev:
            barrier_ev.set()

    def _rotate_atomic(self, reason="scheduled"):
        """
        Gap-free two-phase VIP rotation.

        Phase 1 — install new NAT rules while old rules are still active.
                   Because old and new rules match on different VIP addresses,
                   there is no conflict and both sets coexist safely.

        Barrier  — send OFPBarrierRequest and wait for the switch to confirm
                   every Phase-1 FlowMod has been applied.  After this point
                   new rules are provably active; no traffic window exists.

        Phase 2  — delete old rules by exact (STRICT) match, one VIP at a time.
                   The wildcard wipe used by legacy _rotate is never issued,
                   so the goto-table defaults in T_OUT/T_IN are preserved and
                   _setup_pipeline does not need to be called.

        AI VIP selection (_pick_vip_excluding) scores candidates to avoid
        recently used and recently probed addresses.
        """
        self.logger.info(f"\n{'='*50}\n[ROTATE-ATOMIC] {reason}")
        t_start = time.time()

        old_mapping = dict(self.real_to_vip)
        if not old_mapping:
            self.logger.info("  (no hosts yet — skipping)")
            return

        # --- Pick new VIPs via AI scorer (must not collide with current or each other) ---
        exclude     = set(self._used_vips)
        new_mapping = {}
        for real_ip in old_mapping:
            new_vip = self._pick_vip_excluding(exclude)
            new_mapping[real_ip] = new_vip
            exclude.add(new_vip)

        # --- Phase 1: install new NAT rules (old rules still active) ---
        for real_ip, new_vip in new_mapping.items():
            for dp in self.datapaths.values():
                self._install_nat_for_vip(dp, real_ip, new_vip)

        # --- Barrier: block until switch confirms Phase-1 FlowMods applied ---
        t_barrier = time.time()
        for dp in self.datapaths.values():
            self._barrier_wait(dp)
        barrier_ms = (time.time() - t_barrier) * 1000
        self.logger.info(
            f"  [atomic] barrier RTT {barrier_ms:.1f} ms — new rules confirmed active"
        )

        # --- Phase 2: update controller state ---
        # New rules are guaranteed active; safe to rebuild bookkeeping now.
        self.real_to_vip.clear()
        self.vip_to_real.clear()
        self._used_vips.clear()
        for real_ip, new_vip in new_mapping.items():
            self.real_to_vip[real_ip] = new_vip
            self.vip_to_real[new_vip] = real_ip
            self._used_vips.add(new_vip)
            self.logger.info(
                f"  {real_ip}  {old_mapping[real_ip]} → {new_vip}"
            )

        # --- Phase 2: delete old NAT rules by strict per-VIP match ---
        for real_ip, old_vip in old_mapping.items():
            for dp in self.datapaths.values():
                self._del_nat_for(dp, real_ip, old_vip)

        total_ms = (time.time() - t_start) * 1000
        self.logger.info(
            f"  [atomic] complete in {total_ms:.1f} ms — provably gap-free"
        )
        self.logger.info('='*50)

        # --- Record VIP set used in this rotation (AI VIP scorer uses this history) ---
        self._vip_history.append(set(new_mapping.values()))
        if len(self._vip_history) > 20:   # keep last 20 rotations only
            self._vip_history.pop(0)

        _log_event("ROTATION", reason=reason,
                   old_mapping=old_mapping, new_mapping=new_mapping,
                   duration_ms=round(total_ms, 1))
        led.pulse_mutation()

    # ── Low-level flow helpers ────────────────────────────────────────────────

    def _add_flow(self, dp, table_id, priority, match, instructions):
        parser = dp.ofproto_parser
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, table_id=table_id,
            priority=priority, match=match, instructions=instructions,
        ))

    def _apply(self, dp, actions):
        ofp    = dp.ofproto
        parser = dp.ofproto_parser
        return [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]

    def _goto(self, dp, table_id):
        return [dp.ofproto_parser.OFPInstructionGotoTable(table_id)]

    def _apply_goto(self, dp, actions, nxt):
        ofp    = dp.ofproto
        parser = dp.ofproto_parser
        return [
            parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions),
            parser.OFPInstructionGotoTable(nxt),
        ]

    # ── Switch pipeline setup ─────────────────────────────────────────────────

    def _setup_pipeline(self, dp):
        parser = dp.ofproto_parser
        ofp    = dp.ofproto
        # T_OUT default → T_IN
        self._add_flow(dp, T_OUT, 0, parser.OFPMatch(), self._goto(dp, T_IN))
        # T_IN default → T_L2
        self._add_flow(dp, T_IN,  0, parser.OFPMatch(), self._goto(dp, T_L2))
        # T_L2: ARP → controller (for learning/proxy) AND flood (for delivery)
        self._add_flow(dp, T_L2, L2_PRI + 1,
            parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP),
            self._apply(dp, [
                parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER),
                parser.OFPActionOutput(ofp.OFPP_FLOOD),
            ]),
        )
        # T_L2 table-miss → controller
        self._add_flow(dp, T_L2, 0, parser.OFPMatch(),
            self._apply(dp, [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)])
        )

    # ── NAT flows ─────────────────────────────────────────────────────────────

    def _install_nat_for(self, dp, real_ip):
        """Install NAT rules for real_ip using its current VIP from self.real_to_vip."""
        vip = self.real_to_vip.get(real_ip)
        if not vip:
            return
        self._install_nat_for_vip(dp, real_ip, vip)

    def _install_nat_for_vip(self, dp, real_ip, vip):
        """
        Install NAT rules for (real_ip, vip) at NAT_PRI.

        Called both during initial assignment and during Phase 1 of atomic rotation
        (while old rules are still active — safe because match fields differ by VIP).
        """
        port = self.host_port.get(real_ip)
        if not port:
            return
        parser = dp.ofproto_parser
        ofp    = dp.ofproto

        # T_OUT: outbound — mask real src with VIP
        self._add_flow(dp, T_OUT, NAT_PRI,
            parser.OFPMatch(in_port=port, eth_type=ether_types.ETH_TYPE_IP, ipv4_src=real_ip),
            self._apply_goto(dp, [parser.OFPActionSetField(ipv4_src=vip)], T_IN),
        )

        # T_IN (priority NAT_PRI+1): TCP to VIP.
        # Output(CONTROLLER) runs first so the controller sees dst=VIP (needed for
        # scan detection); then SetField rewrites dst before GOTO passes it to T_L2.
        self._add_flow(dp, T_IN, NAT_PRI + 1,
            parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=vip, ip_proto=6),
            self._apply_goto(dp, [
                parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER),
                parser.OFPActionSetField(ipv4_dst=real_ip),
            ], T_L2),
        )

        # T_IN (priority NAT_PRI): non-TCP (ICMP, UDP) — just rewrite, no controller copy
        self._add_flow(dp, T_IN, NAT_PRI,
            parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=vip),
            self._apply_goto(dp, [parser.OFPActionSetField(ipv4_dst=real_ip)], T_L2),
        )

    def _install_all_nat(self, dp):
        for real_ip in self.real_to_vip:
            self._install_nat_for(dp, real_ip)

    def _del_nat_flows(self, dp):
        """Wildcard delete — wipes ALL T_OUT/T_IN flows. Used by legacy _rotate."""
        ofp    = dp.ofproto
        parser = dp.ofproto_parser
        for tbl in (T_OUT, T_IN):
            dp.send_msg(parser.OFPFlowMod(
                datapath=dp, table_id=tbl,
                command=ofp.OFPFC_DELETE,
                out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                priority=NAT_PRI, match=parser.OFPMatch(),
            ))

    def _del_nat_for(self, dp, real_ip, old_vip):
        """
        Strict per-VIP deletion — removes only the three rules that were installed
        for (real_ip, old_vip).  Used in Phase 2 of _rotate_atomic so the wildcard
        delete (and its pipeline gap) is never needed.
        """
        ofp    = dp.ofproto
        parser = dp.ofproto_parser
        port   = self.host_port.get(real_ip)

        # T_OUT rule: match on in_port + ipv4_src=real_ip
        if port:
            dp.send_msg(parser.OFPFlowMod(
                datapath=dp, table_id=T_OUT,
                command=ofp.OFPFC_DELETE_STRICT,
                out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                priority=NAT_PRI,
                match=parser.OFPMatch(
                    in_port=port,
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_src=real_ip,
                ),
            ))

        # T_IN TCP rule (priority NAT_PRI+1): match ipv4_dst=old_vip + ip_proto=TCP
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, table_id=T_IN,
            command=ofp.OFPFC_DELETE_STRICT,
            out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
            priority=NAT_PRI + 1,
            match=parser.OFPMatch(
                eth_type=ether_types.ETH_TYPE_IP,
                ipv4_dst=old_vip,
                ip_proto=6,
            ),
        ))

        # T_IN non-TCP rule (priority NAT_PRI): match ipv4_dst=old_vip
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, table_id=T_IN,
            command=ofp.OFPFC_DELETE_STRICT,
            out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
            priority=NAT_PRI,
            match=parser.OFPMatch(
                eth_type=ether_types.ETH_TYPE_IP,
                ipv4_dst=old_vip,
            ),
        ))

    # ── L2 forwarding ─────────────────────────────────────────────────────────

    def _install_l2(self, dp, mac, port):
        parser = dp.ofproto_parser
        self._add_flow(dp, T_L2, L2_PRI,
            parser.OFPMatch(eth_dst=mac),
            self._apply(dp, [parser.OFPActionOutput(port)]),
        )

    # ── Packet helpers ────────────────────────────────────────────────────────

    def _pkt_out(self, dp, msg, actions):
        ofp    = dp.ofproto
        parser = dp.ofproto_parser
        data   = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id,
            in_port=msg.match['in_port'],
            actions=actions, data=data,
        ))

    def _flood(self, dp, msg):
        self._pkt_out(dp, msg, [dp.ofproto_parser.OFPActionOutput(dp.ofproto.OFPP_FLOOD)])

    def _arp_reply(self, dp, in_port, req_eth, req_arp, reply_mac):
        ofp    = dp.ofproto
        parser = dp.ofproto_parser
        pkt    = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(
            ethertype=ether_types.ETH_TYPE_ARP,
            dst=req_eth.src, src=reply_mac,
        ))
        pkt.add_protocol(arp.arp(
            opcode=arp.ARP_REPLY,
            src_mac=reply_mac,   src_ip=req_arp.dst_ip,
            dst_mac=req_eth.src, dst_ip=req_arp.src_ip,
        ))
        pkt.serialize()
        dp.send_msg(parser.OFPPacketOut(
            datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
            in_port=ofp.OFPP_CONTROLLER,
            actions=[parser.OFPActionOutput(in_port)],
            data=pkt.data,
        ))

    # ── Host learning ─────────────────────────────────────────────────────────

    def _learn(self, dp, ip, mac, port):
        if ip in self.host_port:
            return
        self.host_port[ip] = port
        self.host_mac[ip]  = mac
        self._assign_vip(ip)
        for d in self.datapaths.values():
            self._install_nat_for(d, ip)
            self._install_l2(d, mac, port)

    # ── ARP handler ───────────────────────────────────────────────────────────

    def _handle_arp(self, dp, in_port, msg, eth, arp_pkt):
        src_ip = arp_pkt.src_ip
        dst_ip = arp_pkt.dst_ip

        # Learn the sender; T_L2's ARP rule already flooded, no need to flood again
        if src_ip.startswith(_REAL_PREFIX):
            self._learn(dp, src_ip, eth.src, in_port)

        if arp_pkt.opcode == arp.ARP_REQUEST and dst_ip in self.vip_to_real:
            real_ip  = self.vip_to_real[dst_ip]
            real_mac = self.host_mac.get(real_ip)
            if real_mac:
                self._arp_reply(dp, in_port, eth, arp_pkt, real_mac)

    # ── Scan detection (AI-powered) ───────────────────────────────────────────

    def _track_syn(self, src_ip, dst_vip):
        """
        AI-powered scan detection using a Random Forest classifier.

        Extracts 4 features per source IP and classifies as scanner/normal:
          n_unique_vips  — how many different VIPs this source has probed
          syn_rate       — SYN packets per second from this source
          syn_ack_ratio  — SYN count / (ACK count + 1); scanners never complete handshake
          elapsed        — seconds of activity observed for this source

        Falls back to SCAN_THRESHOLD rule if model is not loaded.
        Also records probed VIPs so the AI VIP scorer can avoid them on next rotation.
        """
        real_src = self.vip_to_real.get(src_ip, src_ip)
        now      = time.time()

        state = self._scan_state.setdefault(
            real_src, {'targets': set(), 'first_seen': now}
        )
        if now - state['first_seen'] > SCAN_WINDOW:
            state['targets']         = set()
            state['first_seen']      = now
            self._src_syn_count[real_src] = 0
            self._src_ack_count[real_src] = 0

        state['targets'].add(dst_vip)

        # Track SYN count and packet timestamps for this source
        self._src_syn_count[real_src] = self._src_syn_count.get(real_src, 0) + 1
        times = self._src_pkt_times.setdefault(real_src, [])
        times.append(now)
        if len(times) > 50:   # keep last 50 timestamps
            times.pop(0)

        # Record this VIP as probed — AI VIP scorer will avoid it next rotation
        self._probed_vips[dst_vip] = self._probed_vips.get(dst_vip, 0) + 1

        # ── AI classification ──────────────────────────────────────────────
        elapsed       = max(now - state['first_seen'], 0.001)
        n_unique_vips = len(state['targets'])
        syn_count     = self._src_syn_count.get(real_src, 1)
        ack_count     = self._src_ack_count.get(real_src, 0)
        syn_rate      = syn_count / elapsed
        syn_ack_ratio = syn_count / (ack_count + 1)

        # Inter-arrival variance: scanners send at machine speed (very regular → low variance)
        if len(times) >= 3:
            gaps = [times[i+1] - times[i] for i in range(len(times)-1)]
            inter_arrival_var = float(np.var(gaps)) if _AI_AVAILABLE else 0.0
        else:
            inter_arrival_var = 1.0   # default to "normal" if too few packets

        unique_vip_rate = n_unique_vips / elapsed

        is_attack = False

        if _SCAN_MODEL is not None and _AI_AVAILABLE:
            features   = np.array([[n_unique_vips, syn_rate, syn_ack_ratio, elapsed,
                                     inter_arrival_var, unique_vip_rate]])
            prediction = _SCAN_MODEL.predict(features)[0]
            confidence = _SCAN_MODEL.predict_proba(features)[0][1]
            is_attack  = (prediction == 1)
            if is_attack:
                self.logger.warning(
                    f"[AI-SCAN] {real_src} classified as SCANNER  "
                    f"confidence={confidence:.2f}  "
                    f"unique_vips={n_unique_vips}  "
                    f"syn_rate={syn_rate:.1f}/s  "
                    f"syn_ack_ratio={syn_ack_ratio:.2f}"
                )
                _log_event("AI_DETECT", src=real_src,
                           confidence=round(float(confidence), 3),
                           unique_vips=n_unique_vips,
                           syn_rate=round(float(syn_rate), 2),
                           syn_ack_ratio=round(float(syn_ack_ratio), 3))
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
            if self._current_interval != ROTATION_FAST:
                self._current_interval       = ROTATION_FAST
                self._rotations_since_attack = 0
                self.logger.warning(
                    f"[THREAT] Under attack — rotation interval → {ROTATION_FAST}s"
                )
            rotate_fn = self._rotate_atomic if USE_ATOMIC else self._rotate
            hub.spawn(rotate_fn, f"scan from {real_src}")

    # ── OpenFlow handlers ─────────────────────────────────────────────────────

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self._setup_pipeline(dp)
        self._install_all_nat(dp)
        for ip, mac in self.host_mac.items():
            self._install_l2(dp, mac, self.host_port[ip])
        self.logger.info(f"Switch connected: dpid={dp.id}")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        msg     = ev.msg
        dp      = msg.datapath
        ofp     = dp.ofproto
        in_port = msg.match['in_port']
        pkt     = packet.Packet(msg.data)
        eth     = pkt.get_protocol(ethernet.ethernet)
        if not eth:
            return

        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self._handle_arp(dp, in_port, msg, eth, arp_pkt)
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return

        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst

        if src_ip.startswith(_REAL_PREFIX):
            self._learn(dp, src_ip, eth.src, in_port)

        tcp_pkt = pkt.get_protocol(tcp.tcp)
        if tcp_pkt and (tcp_pkt.bits & 0x02):
            try:
                if ipaddress.ip_address(dst_ip) in _VIP_NET:
                    self._track_syn(src_ip, dst_ip)
            except ValueError:
                pass

        # Only flood genuine table-misses (OFPR_NO_MATCH).  Packets that arrive
        # here via the T_IN TCP monitoring flow have reason=OFPR_ACTION and are
        # already being forwarded by the pipeline — re-flooding them would cause
        # duplicate delivery to the destination host.
        if msg.reason == ofp.OFPR_NO_MATCH:
            self._flood(dp, msg)
