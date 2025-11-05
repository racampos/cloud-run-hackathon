# VLAN Basic Configuration Lab Example

A basic two-switch VLAN configuration lab for testing NetGenius.

## Topology

```
┌────────────┐ Trunk Link ┌────────────┐
│    SW1     │◄───────────►│    SW2     │
│ Gi0/3      │             │      Gi0/3 │
│            │             │            │
│ Gi0/1: V10 │             │ Gi0/1: V10 │
│ Gi0/2: V20 │             │ Gi0/2: V20 │
└────────────┘             └────────────┘
```

## VLANs

- **VLAN 10:** Sales
- **VLAN 20:** Engineering

## Learning Objectives

- Create VLANs on switches
- Assign switch ports to VLANs
- Configure trunk ports between switches
- Verify VLAN membership
- Test VLAN isolation

## Test Locally

```bash
cd ../../headless-runner
python main.py --payload-file ../examples/vlan-basic/payload.json
```

## Expected Outcome

- Both switches have VLAN 10 and VLAN 20 configured
- Gi0/1 on both switches is in VLAN 10 (access mode)
- Gi0/2 on both switches is in VLAN 20 (access mode)
- Gi0/3 on both switches is trunk mode
- show vlan brief shows correct VLAN assignments
- show interfaces trunk shows trunk port configuration
