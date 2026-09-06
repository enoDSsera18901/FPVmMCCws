# Pair-2 deterministic software simulation evidence

This directory contains retained outputs from the repository's deterministic coordinator simulation. It demonstrates the controller state machine and is **not** PX4 SITL, Gazebo, ROS 2, RF, hardware, or flight evidence.

Reproduce from the repository root with:

```sh
make clean all test evidence
```

Evidence contract:

- frozen node identities are unique;
- both nodes are admitted and initially active;
- node 1 heartbeat degradation suppresses its outbound intent;
- loss of node 1 reassigns its task to healthy node 2;
- a returning node is quarantined;
- two heartbeats plus explicit recovery are required before node 1 is active;
- an active recovered node still suppresses intent until it has work assigned;
- task ownership remains with node 2 until explicit reconfiguration;
- no available replacement leaves work unassigned and intent suppressed.

`events.csv` is the deterministic state-transition log. `test-results.txt` records the known-answer test count. The live external-runtime gate is checked separately with `scripts/check_live_runtime.sh` and fails closed when any required runtime is absent.
