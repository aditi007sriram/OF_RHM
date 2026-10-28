"""
Mininet topology for OF-RHM demo.

  h1 (10.0.0.1) ─┐
  h2 (10.0.0.2) ─┤── s1 (OVS) ── Ryu controller (127.0.0.1:6653)
  h3 (10.0.0.3) ─┤
  attacker       ─┘  (10.0.0.99)

Run with:
    sudo python3 topology.py
"""

from mininet.net    import Mininet
from mininet.node   import RemoteController, OVSSwitch
from mininet.link   import TCLink
from mininet.cli    import CLI
from mininet.log    import setLogLevel, info


def build():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
    )

    info("*** Adding controller\n")
    net.addController("c0", ip="127.0.0.1", port=6653)

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1", protocols="OpenFlow13")

    info("*** Adding hosts\n")
    h1       = net.addHost("h1",       ip="10.0.0.1/24")
    h2       = net.addHost("h2",       ip="10.0.0.2/24")
    h3       = net.addHost("h3",       ip="10.0.0.3/24")
    attacker = net.addHost("attacker", ip="10.0.0.99/24")

    info("*** Wiring links\n")
    for host in (h1, h2, h3, attacker):
        net.addLink(host, s1)

    return net


if __name__ == "__main__":
    setLogLevel("info")
    net = build()
    net.start()

    info("\n*** Topology ready. Hosts:\n")
    for h in net.hosts:
        info(f"    {h.name:10s}  {h.IP()}\n")

    info("\n*** Type 'exit' to quit, or use the Mininet CLI.\n")
    CLI(net)
    net.stop()
