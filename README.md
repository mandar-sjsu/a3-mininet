# Networking Experiments with Mininet

## Experiment 1: IP Routing

### **Goal**
- Build an IPv4 routed Mininet topology:  
  `h1 — r1 — r2 — h3` with `h2` attached to `r1`, using `/24` subnets.  
- Enable IP forwarding on routers `r1` and `r2` to perform packet routing.  
- Configure static routes so that the following paths work:  
  - `h1 → h3`  
  - `h2 → h3`  
  - `h3 → h1`  
  - `h3 → h2`  
- Verify connectivity by running `ping -c 1` for each of the above and save results to `result1.txt`.  
- Record routing and ARP tables for verification.

### **Run Instructions**
```bash
sudo mn -c
sudo python3 exp1.py
```
Results and routing details will be automatically saved to result1.txt.

---

## Experiment 2: SDN (L2)


### **Goal**
- Create an **L2 (Layer 2) SDN topology**:  
  `h1 — s1 — s2 — h3`, with `h2` connected to `s1`.

- Use **Open vSwitch** in standalone mode (no controller).

- Save baseline connectivity results (`h1 → h3` and `h2 → h3`) to `result2.txt`.

- From another terminal, use `ovs-ofctl` to:
  - **Drop** all traffic arriving on `s1-eth2` (h2 link).
  - **Forward** all traffic arriving on `s1-eth1` (h1 link) to `s1-eth3` (link to s2).

- Re-run pings (`h1 → h3`, `h2 → h3`) and record results along with the flow table to `result2.txt`.

### **Run Instructions**
```bash
sudo mn -c
sudo python3 exp2.py
```

When prompted in another terminal execute:
```bash
sudo ovs-ofctl -O OpenFlow13 show s1
sudo ovs-ofctl -O OpenFlow13 add-flow s1 "in_port=2,actions=drop"
sudo ovs-ofctl -O OpenFlow13 add-flow s1 "in_port=1,actions=output:3"
```

Then return to the main terminal and press Enter to continue.
Final results, including ping outputs and flow tables will be saved to result2.txt.