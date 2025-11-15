#!/usr/bin/env python3
"""
Experiment 2: SDN (L2)
Topology:
  h1 -- s1 -- s2 -- h3
         |
         h2

Goal:
- Start a pure L2 network (OVSKernelSwitch in standalone mode, no controller).
- Save baseline pings (h1->h3, h2->h3) to result2.txt.
- From another terminal, add OpenFlow rules on s1:
    * Drop everything that ARRIVES from s1-eth2 (h2 link).
    * Forward everything that ARRIVES from s1-eth1 (h1 link) to s1-eth3 (link to s2).
- Save s1's flows and post-rule pings to result2.txt.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.cli import CLI


class L2Topo(Topo):
    """Define the L2 topology with hosts h1–h3 and switches s1–s2."""
    def build(self):
        # Switches: OVS in standalone (L2) mode
        s1 = self.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')
        s2 = self.addSwitch('s2', cls=OVSKernelSwitch, failMode='standalone')

        # Hosts (same L2 subnet for simple pings)
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')

        # Links: h1-s1, h2-s1, s1-s2, s2-h3
        self.addLink(h1, s1)  # becomes s1-eth1
        self.addLink(h2, s1)  # becomes s1-eth2
        self.addLink(s1, s2)  # becomes s1-eth3 <-> s2-eth1
        self.addLink(s2, h3)  # becomes s2-eth2 <-> h3-eth0


def open_log(filename='result2.txt'):
    """Open a log file and return a write helper for logging experiment output."""
    f = open(filename, 'w')
    def W(s):
        f.write(s)
        f.flush()
    return f, W

def write_header(W):
    """Write the experiment header section to the log file."""
    W('Experiment 2: SDN (L2) Results\n')
    W('='*60 + '\n\n')

def show_ports_and_flows(switch, W, when='BEFORE adding flows'):
    """Record switch port configuration and flow table state using ovs-ofctl."""
    W(f'\nSwitch {switch.name} state {when}:\n')
    W('-'*60 + '\n')
    W('sudo ovs-ofctl show s1\n')
    W(switch.cmd('ovs-ofctl show s1') + '\n')
    W('sudo ovs-ofctl dump-flows s1\n')
    W(switch.cmd('ovs-ofctl dump-flows s1') + '\n')

def run_ping_pair(src, dst_ip, label, W):
    """Run a single ping test from one host to another and log the result."""
    W(f'{label} (ping -c 1):\n')
    W(src.cmd(f'ping -c 1 {dst_ip}') + '\n')

def baseline_pings(h1, h2, h3, W):
    """Execute baseline ping tests before installing OpenFlow rules."""
    W('Baseline connectivity (before adding flows):\n')
    W('-'*60 + '\n')
    run_ping_pair(h1, '10.0.0.3', 'h1 -> h3', W)
    run_ping_pair(h2, '10.0.0.3', 'h2 -> h3', W)

def post_rule_pings(h1, h2, h3, W):
    """Execute ping tests after OpenFlow rules are installed to verify behavior."""
    W('\nConnectivity AFTER adding flows to s1:\n')
    W('-'*60 + '\n')
    run_ping_pair(h1, '10.0.0.3', 'h1 -> h3', W)
    run_ping_pair(h2, '10.0.0.3', 'h2 -> h3', W)

def prompt_to_add_flows():
    """Pause execution and prompt the user to add OpenFlow rules from another terminal."""
    info('\n=== ACTION REQUIRED (in another terminal) ===\n')
    info('1) Inspect port numbers:\n')
    info('   sudo ovs-ofctl show s1\n\n')
    info('2) Add flows on s1:\n')
    info('   sudo ovs-ofctl add-flow s1 "in_port=2,actions=drop"\n')
    info('   sudo ovs-ofctl add-flow s1 "in_port=1,actions=output:3"\n\n')
    input('Press ENTER here after you have added the flows on s1...')

def record_commands_section(W):
    """Log the example ovs-ofctl commands used to configure flow rules on s1."""
    W('Commands used on s1:\n')
    W('sudo ovs-ofctl add-flow s1 "in_port=2,actions=drop"\n')
    W('sudo ovs-ofctl add-flow s1 "in_port=1,actions=output:3"\n')

def build_and_start_net():
    """Create and start the Mininet network using the defined L2 topology."""
    topo = L2Topo()
    # No controller; OVS standalone does L2 switching
    net = Mininet(topo=topo, controller=None, autoSetMacs=True, cleanup=True)
    net.start()
    info('*** Network started\n')
    h1, h2, h3 = net.get('h1', 'h2', 'h3')
    s1, s2 = net.get('s1', 's2')
    return net, (h1, h2, h3, s1, s2)

def run():
    """Run the full SDN L2 experiment workflow: build, test, record, and cleanup."""
    setLogLevel('info')
    net, (h1, h2, h3, s1, s2) = build_and_start_net()

    try:
        # Prepare log file
        f, W = open_log('result2.txt')
        write_header(W)

        # 1) Baseline tests (no custom flows)
        baseline_pings(h1, h2, h3, W)

        # 2) Show s1 ports & empty flow table
        show_ports_and_flows(s1, W, when='BEFORE adding flows')

        # 3) Pause and let user add flows from another terminal
        prompt_to_add_flows()

        # 4) Record flow table after user-added rules
        show_ports_and_flows(s1, W, when='AFTER adding flows')
        record_commands_section(W)

        # 5) Re-test connectivity after rules
        post_rule_pings(h1, h2, h3, W)

        f.close()
        info('\n*** All results saved to result2.txt\n')

        # CLI
        info('*** Starting CLI (type "exit" to quit)\n')
        CLI(net)

    finally:
        net.stop()
        info('*** Network stopped\n')


if __name__ == '__main__':
    run()
