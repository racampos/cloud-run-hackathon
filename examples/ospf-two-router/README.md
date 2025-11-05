# OSPF Two-Router Lab Example

An OSPF configuration lab with two routers for testing NetGenius.

## Topology

```
┌────────────┐ 10.0.12.0/30 ┌────────────┐
│     R1     │◄─────────────►│     R2     │
│ .1         │               │         .2 │
│            │               │            │
│ 192.168.1.0/24            192.168.2.0/24
│ (Network 1)               (Network 2)   │
└────────────┘               └────────────┘
```

## IP Addressing

| Device | Interface | IP Address | Network |
|--------|-----------|------------|---------|
| R1 | Gi0/0 | 192.168.1.1/24 | LAN 1 |
| R1 | Gi0/1 | 10.0.12.1/30 | P2P Link |
| R2 | Gi0/0 | 10.0.12.2/30 | P2P Link |
| R2 | Gi0/1 | 192.168.2.1/24 | LAN 2 |

## Learning Objectives

- Configure OSPF process on routers
- Configure OSPF network statements with correct area
- Verify OSPF neighbor adjacency
- Verify OSPF routes in routing table
- Test inter-LAN connectivity

## OSPF Configuration

- **Process ID:** 1
- **Area:** 0 (backbone area)
- **Networks:**
  - 192.168.1.0/24 in area 0
  - 10.0.12.0/30 in area 0
  - 192.168.2.0/24 in area 0

## Test Locally

```bash
cd ../../headless-runner
python main.py --payload-file ../examples/ospf-two-router/payload.json
```

## Expected Outcome

- OSPF neighbors establish adjacency (FULL state)
- Both routers learn routes via OSPF
- R1 can reach 192.168.2.0/24
- R2 can reach 192.168.1.0/24
- show ip ospf neighbor shows adjacency
- show ip route ospf shows learned routes
- Ping tests succeed between networks
