# Pair-2 PX4 / ROS 2 SITL host contract

State: **preflight contract only; no live SITL pass is claimed by this file.**

## Frozen host baseline

- Ubuntu 24.04 LTS.
- ROS 2 Jazzy LTS.
- Gazebo Harmonic as installed/supported by the PX4 Ubuntu toolchain.
- Micro XRCE-DDS Agent v2.4.3 when using PX4's default DDS v2 client with ROS 2 Jazzy.
- Exact PX4-Autopilot and `px4_msgs` git SHAs must be captured in the evidence pack; evidence runs must not rely on floating `main` references.

## Pair-2 identity

`integration/sitl/pair2_identity.json` is normative for the first live gate. It explicitly namespaces both vehicles to remove the upstream instance-0 namespace special case:

| node | PX4 instance | MAV_SYS_ID | UXRCE_DDS_KEY | PX4_UXRCE_DDS_NS |
|---:|---:|---:|---:|---|
| 1 | 0 | 1 | 1 | `coord_001` |
| 2 | 1 | 2 | 2 | `coord_002` |

Run `python3 tools/verify_pair2_identity.py` before launch. Any identity drift is a gate failure.

## Safety boundary

The coordination layer has no authority to arm aircraft or change PX4 flight mode. Trajectory/setpoint output remains conditional on the local supervisor safety gate. Live evidence must demonstrate suppression on the injected degraded condition before recovery/re-entry is accepted.

## Live evidence required to close the gate

1. Exact PX4, `px4_msgs`, ROS distribution, Gazebo and Micro XRCE-DDS Agent versions.
2. Process map proving two distinct PX4 instances and the identity table above.
3. ROS 2 topic inventory proving per-node namespaces are isolated.
4. Coordinated mission timeline.
5. Injected communications degradation/failure timeline.
6. Supervisor transition showing output suppression / DEGRADED response.
7. Recovery or node replacement/reconfiguration evidence.
8. PX4 logs and controller logs retained together.
9. Explicit result JSON: PASS or FAIL against frozen criteria.

Only live runtime evidence closes the gate. Static validation or a successful launcher does not.
