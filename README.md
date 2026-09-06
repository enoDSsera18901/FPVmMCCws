# FPV Multi-Node Coordination Controller

Engineering repository for the multi-node FPV coordination/controller architecture.

The controller is intentionally separated from airframe design. It manages configuration identity, node discovery/admission, assignment, supervision, mission coordination, replacement/reconfiguration, bounded intent generation, and simulation/verification evidence while leaving local flight stability and motor control to the aircraft autopilot.

Current engineering gate: validated portable software baseline -> live PX4/Gazebo/ROS 2 two-node SITL evidence -> fault injection -> progressive scale testing.

This repository is **not evidence of flight readiness**. Physical testing remains gated after SITL, simulated fault injection, bench and controlled test stages.

## Reproducible repository baseline

The committed minimal coordinator simulator makes the pair-2 state-machine claims reproducible without external flight middleware:

```sh
make clean all test evidence
```

It verifies deterministic identity, discovery/admission, assignment, heartbeat degradation, output suppression, loss, fail-closed reassignment, quarantine, recovery and explicit reconfiguration. Retained outputs are in `evidence/pair2-software-sim/`.

This test harness does not emulate vehicle dynamics or prove PX4 integration. Check whether the external integration gate can run with:

```sh
./scripts/check_live_runtime.sh
```

The check exits with status 2 if PX4 SITL, Gazebo, ROS 2 or Micro XRCE-DDS Agent is missing. It never arms a vehicle or changes a flight mode.
