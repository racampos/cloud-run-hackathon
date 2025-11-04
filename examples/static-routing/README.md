# Static Routing Lab Example

A simple two-router static routing lab for testing NetGenius.

## Topology

```
┌────────────┐ 10.0.0.0/30 ┌────────────┐
│     R1     │◄────────────►│     R2     │
│ .1         │              │         .2 │
└────────────┘              └────────────┘
                                   │
                              192.168.2.0/24
                               (Loopback0)
```

## Learning Objectives

- Configure static routes
- Verify IP connectivity between routers
- Test reachability to remote networks

## Test Locally

```bash
cd ../../headless-runner
python main.py --payload-file ../examples/static-routing/payload.json
```

## Expected Outcome

- R1 can reach 192.168.2.0/24 via R2
- R2 has default route pointing to R1
- Both routers show proper routing tables
- Ping tests succeed
