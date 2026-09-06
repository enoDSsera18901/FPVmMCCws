# Pair-2 deterministic coordinator simulation

**Evidence level:** repository-native controller state-machine simulation only. This is not PX4 SITL, Gazebo, ROS 2, RF, hardware, airworthiness or flight-readiness evidence.

## Why this milestone was selected

The repository audit found that `main` contained only a README and a preflight note. The source and tests behind the note's reported 37 C and 19 Python tests had not been committed. Before external simulator integration can be meaningfully reproduced, the repository needs an inspectable coordinator state machine and an automated evidence contract.

## Configuration

The frozen identity mapping remains:

| Controller | MAV_SYS_ID | PX4 instance | ROS/DDS namespace |
| --- | ---: | ---: | --- |
| 1 | 1 | 0 | `coord_001` |
| 2 | 2 | 1 | `coord_002` |

The deterministic software harness uses a 500 ms degraded threshold and a 1000 ms lost threshold. These are test values, not validated real-RF or flight limits.

## Scenario

1. Discover and admit two uniquely identified nodes.
2. Assign task 101 to node 1 and task 102 to node 2.
3. Stop node 1 heartbeats while node 2 remains healthy.
4. At 500 ms heartbeat age, mark node 1 degraded and suppress its intent output.
5. At 1000 ms heartbeat age, mark node 1 lost and reassign task 101 to node 2.
6. When node 1 returns, quarantine it rather than immediately enabling output.
7. Require two fresh heartbeats and an explicit recovery action.
8. Keep the recovered node's intent suppressed while it has no assignment.
9. Preserve reassigned work on node 2 until an explicit reconfiguration action returns task 101 to node 1.

The known-answer tests also cover duplicate controller, MAVLink system, PX4 instance and ROS namespace identities; invalid timeout configuration; monotonic time rejection; invalid state changes; and loss with no healthy replacement. In the no-replacement case the task becomes unassigned and both nodes suppress intent.

## Reproduction

```sh
make clean all test sanitizers evidence
./scripts/check_live_runtime.sh
```

Expected local result in an environment without the external stack:

- 66/66 deterministic checks pass under GCC;
- 66/66 checks pass under GCC AddressSanitizer + UndefinedBehaviorSanitizer (leak detection disabled because the managed runner uses ptrace; this code owns no heap allocations);
- retained `events.csv` and `test-results.txt` regenerate without a diff;
- `check_live_runtime.sh` exits 2 and names every missing dependency.

## Remaining gate

Issue #1 remains open. A real pair-2 gate still requires compatible, revision-pinned PX4 SITL, Gazebo, ROS 2, `px4_msgs` and Micro XRCE-DDS Agent installations, a real bridge from coordinator intent to PX4 messages, vehicle-dynamics execution, external logs, measured loss/recovery timing, and evidence validation. The runtime probe only establishes whether required executables are present; it does not prove version compatibility.
