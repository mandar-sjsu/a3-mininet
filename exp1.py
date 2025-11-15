#!/usr/bin/env python
"""
Experiment 1: IP Routing with Mininet
Topology: 
 h1 -- r1 -- r2 -- h3
        |
        h2

Goal:
- Build an IP-routed Mininet topology as above.
- Enable IPv4 forwarding on r1 and r2 and assign per-interface IPs for all links.
- Configure static routes so that end-to-end connectivity works for:
    h1 → h3
    h2 → h3
    h3 → h1
    h3 → h2
- Verify reachability by ping tests and save all outputs to result1.txt.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI


class LinuxRouter(Node):
    """A Node with IP forwarding enabled to act as a router."""
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        # Enable basic forwarding (we'll further tune per-interface later)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


class NetworkTopo(Topo):
    """Custom topology for Experiment 1 with two routers and three hosts."""
    def build(self, **_opts):
        # Routers
        r1 = self.addNode('r1', cls=LinuxRouter)
        r2 = self.addNode('r2', cls=LinuxRouter)

        # Hosts with IPs + default routes
        h1 = self.addHost('h1', ip='10.0.0.3/24', defaultRoute='via 10.0.0.1')
        h2 = self.addHost('h2', ip='10.0.3.2/24', defaultRoute='via 10.0.3.4')
        h3 = self.addHost('h3', ip='10.0.2.2/24', defaultRoute='via 10.0.2.1')

        # h1 -- r1
        self.addLink(h1, r1,
                     intfName1='h1-eth0',
                     intfName2='r1-eth0',
                     params1={'ip': '10.0.0.3/24'},
                     params2={'ip': '10.0.0.1/24'})

        # r1 -- r2 (10.0.1.0/24)
        self.addLink(r1, r2,
                     intfName1='r1-eth1',
                     intfName2='r2-eth0',
                     params1={'ip': '10.0.1.1/24'},
                     params2={'ip': '10.0.1.2/24'})

        # r2 -- h3
        self.addLink(r2, h3,
                     intfName1='r2-eth1',
                     intfName2='h3-eth0',
                     params1={'ip': '10.0.2.1/24'},
                     params2={'ip': '10.0.2.2/24'})

        # h2 -- r1
        self.addLink(h2, r1,
                     intfName1='h2-eth0',
                     intfName2='r1-eth2',
                     params1={'ip': '10.0.3.2/24'},
                     params2={'ip': '10.0.3.4/24'})


def tune_router_sysctls(node):
    """Make the router's ARP/forwarding behavior deterministic for labs."""
    # Global
    node.cmd('sysctl -w net.ipv4.ip_forward=1')
    node.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0')
    node.cmd('sysctl -w net.ipv4.conf.default.rp_filter=0')
    node.cmd('sysctl -w net.ipv4.conf.all.proxy_arp=0')
    node.cmd('sysctl -w net.ipv4.conf.default.proxy_arp=0')
    node.cmd('sysctl -w net.ipv4.conf.all.arp_ignore=1')
    node.cmd('sysctl -w net.ipv4.conf.all.arp_announce=2')

    # Per-interface
    for intf in node.intfNames():
        node.cmd(f'sysctl -w net.ipv4.conf.{intf}.rp_filter=0')
        node.cmd(f'sysctl -w net.ipv4.conf.{intf}.proxy_arp=0')
        node.cmd(f'sysctl -w net.ipv4.conf.{intf}.arp_ignore=1')
        node.cmd(f'sysctl -w net.ipv4.conf.{intf}.arp_announce=2')


def configure_routes(net):
    """Configure static routes on routers for proper packet forwarding."""
    info('*** Configuring routes\n')
    r1, r2 = net.get('r1'), net.get('r2')

    # r1: reach 10.0.2.0/24 via r2 over r1-eth1
    r1.cmd('ip route replace 10.0.2.0/24 via 10.0.1.2 dev r1-eth1')
    info('r1: Added route to 10.0.2.0/24 via 10.0.1.2 dev r1-eth1\n')

    # r2: reach 10.0.0.0/24 and 10.0.3.0/24 via r1 over r2-eth0
    r2.cmd('ip route replace 10.0.0.0/24 via 10.0.1.1 dev r2-eth0')
    r2.cmd('ip route replace 10.0.3.0/24 via 10.0.1.1 dev r2-eth0')
    info('r2: Added routes to 10.0.0.0/24 and 10.0.3.0/24 via 10.0.1.1 dev r2-eth0\n')

    info('*** Routes configured successfully\n')


def configure_arp(net):
    """Configure static ARP entries (for deterministic lab outputs)."""
    info('*** Configuring static ARP entries\n')

    h1, h2, h3 = net.get('h1', 'h2', 'h3')
    r1, r2 = net.get('r1', 'r2')

    # MACs
    h1_mac = h1.intf('h1-eth0').MAC()
    h2_mac = h2.intf('h2-eth0').MAC()
    h3_mac = h3.intf('h3-eth0').MAC()
    r1_eth0_mac = r1.intf('r1-eth0').MAC()
    r1_eth1_mac = r1.intf('r1-eth1').MAC()
    r1_eth2_mac = r1.intf('r1-eth2').MAC()
    r2_eth0_mac = r2.intf('r2-eth0').MAC()
    r2_eth1_mac = r2.intf('r2-eth1').MAC()

    # Clean slate neighbor state
    for n in (r1, r2):
        for intf in n.intfNames():
            n.cmd(f'ip neigh flush dev {intf}')

    # Hosts: pin default gateway ARP (bind to their interface)
    h1.cmd(f'ip neigh replace 10.0.0.1 lladdr {r1_eth0_mac} dev h1-eth0 nud permanent')
    info('h1: pinned gateway 10.0.0.1\n')

    h2.cmd(f'ip neigh replace 10.0.3.4 lladdr {r1_eth2_mac} dev h2-eth0 nud permanent')
    info('h2: pinned gateway 10.0.3.4\n')

    h3.cmd(f'ip neigh replace 10.0.2.1 lladdr {r2_eth1_mac} dev h3-eth0 nud permanent')
    info('h3: pinned gateway 10.0.2.1\n')

    # Routers: pin ONLY directly-attached hosts and NEXT-HOPS, on the right iface
    # r1 neighbors
    r1.cmd(f'ip neigh replace 10.0.0.3 lladdr {h1_mac} dev r1-eth0 nud permanent')
    r1.cmd(f'ip neigh replace 10.0.3.2 lladdr {h2_mac} dev r1-eth2 nud permanent')
    r1.cmd(f'ip neigh replace 10.0.1.2 lladdr {r2_eth0_mac} dev r1-eth1 nud permanent')
    info('r1: pinned h1, h2, and next-hop r2 on correct ifaces\n')

    # r2 neighbors
    r2.cmd(f'ip neigh replace 10.0.2.2 lladdr {h3_mac} dev r2-eth1 nud permanent')
    r2.cmd(f'ip neigh replace 10.0.1.1 lladdr {r1_eth1_mac} dev r2-eth0 nud permanent')
    info('r2: pinned h3 and next-hop r1 on correct ifaces\n')

    info('*** ARP entries configured successfully\n')


def run_ping_tests(net, output_file='result1.txt'):
    """Execute ping tests and save results to file."""
    info('*** Running ping tests\n')

    h1, h2, h3 = net.get('h1'), net.get('h2'), net.get('h3')

    with open(output_file, 'w') as f:
        f.write("Experiment 1: IP Routing - Ping Test Results\n")
        f.write("=" * 60 + "\n\n")

        # Test 1: h1 to h3
        f.write("Test 1: h1 (10.0.0.3) to h3 (10.0.2.2)\n")
        f.write("-" * 60 + "\n")
        f.write(h1.cmd('ping -c 1 10.0.2.2') + "\n")

        # Test 2: h2 to h3
        f.write("\nTest 2: h2 (10.0.3.2) to h3 (10.0.2.2)\n")
        f.write("-" * 60 + "\n")
        f.write(h2.cmd('ping -c 1 10.0.2.2') + "\n")

        # Test 3: h3 to h1
        f.write("\nTest 3: h3 (10.0.2.2) to h1 (10.0.0.3)\n")
        f.write("-" * 60 + "\n")
        f.write(h3.cmd('ping -c 1 10.0.0.3') + "\n")

        # Test 4: h3 to h2
        f.write("\nTest 4: h3 (10.0.2.2) to h2 (10.0.3.2)\n")
        f.write("-" * 60 + "\n")
        f.write(h3.cmd('ping -c 1 10.0.3.2') + "\n")

        # Routing tables
        f.write("\n" + "=" * 60 + "\n")
        f.write("Routing Tables\n")
        f.write("=" * 60 + "\n\n")
        f.write("Router r1 routing table:\n")
        f.write("-" * 60 + "\n")
        f.write(net.get('r1').cmd('route -n') + "\n")

        f.write("\nRouter r2 routing table:\n")
        f.write("-" * 60 + "\n")
        f.write(net.get('r2').cmd('route -n') + "\n")

        # ARP tables
        f.write("\n" + "=" * 60 + "\n")
        f.write("ARP Tables\n")
        f.write("=" * 60 + "\n\n")
        for host in ['h1', 'h2', 'h3', 'r1', 'r2']:
            f.write(f"{host} ARP table:\n")
            f.write("-" * 60 + "\n")
            f.write(net.get(host).cmd('arp -n') + "\n\n")

    info(f'*** Ping test results saved to {output_file}\n')

    with open(output_file, 'r') as f:
        print(f.read())


def run():
    """Create network, configure routes, run tests, and start CLI."""
    setLogLevel('info')
    topo = NetworkTopo()
    net = Mininet(topo=topo, controller=None, waitConnected=True)

    try:
        net.start()
        info('*** Network started\n')

        # === 1) Tune sysctls per router & per interface ===
        r1, r2 = net.get('r1', 'r2')
        tune_router_sysctls(r1)
        tune_router_sysctls(r2)
        info('*** Tuned sysctls on r1/r2\n')

        # === 2) Flush neighbor tables after tuning ===
        for n in (r1, r2):
            for intf in n.intfNames():
                n.cmd(f'ip neigh flush dev {intf}')

        # === 3) Add routes ===
        configure_routes(net)

        # === 4) Pin ARP neighbors ===
        configure_arp(net)

        # === 5) Tests & CLI ===
        run_ping_tests(net)
        info('*** Starting CLI (type "exit" to quit)\n')
        CLI(net)
    finally:
        net.stop()
        info('*** Network stopped\n')


if __name__ == '__main__':
    run()
