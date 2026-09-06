# Multi-Node Controller — V0.8.2 Preflight Engineering Gate

**Status:** historical preflight record; its source package was not committed and its test counts cannot be reproduced from this repository. Live PX4/Gazebo/ROS 2 integration has not been executed; not flight-ready.

> Repository audit, 2026-09-06: the commit carrying this document contained no controller source, test source, build files, launcher or evidence artifacts. The 37 C and 19 Python results below are therefore prior reported results, not independently reproducible evidence. The new repository-native pair-2 state-machine baseline is documented in `PAIR2_SOFTWARE_SIMULATION.md`.

## Previously reported baseline (source package unavailable here)

- 37/37 C tests pass under GCC.
- 37/37 C tests pass under Clang.
- 37/37 C tests pass under Clang AddressSanitizer + UndefinedBehaviorSanitizer.
- Sanitizer compile and link instrumentation was explicitly checked after correcting the CMake sanitizer option.
- 19/19 Python/tooling tests pass.
- deterministic staged node identity/configuration exists for pair-2 and later scale gates.
- live-SITL launcher is fail-closed and does not arm or switch flight modes.

## Pair-2 frozen identity

| Controller node | MAV_SYS_ID | PX4 instance | ROS/DDS namespace |
| --- | ---: | ---: | --- |
| 1 | 1 | 0 | `coord_001` |
| 2 | 2 | 1 | `coord_002` |

Identity drift is a gate failure.

## Current block

The available validation environment does not contain the required live runtime: PX4 SITL, ROS 2 and Micro XRCE-DDS Agent. Therefore no live pair-2 SITL result is claimed.

## Next gate

GitHub issue #1 is the authoritative execution gate: launch two PX4 SITL instances, retain exact runtime revisions and logs, execute a bounded coordinated simulated mission, inject communications degradation and node loss, verify quarantine/recovery/reconfiguration, and pass the evidence contract.

Do not move from this software baseline directly to coordinated physical free flight. The evidence ladder remains SITL -> simulated fault injection -> bench -> controlled/tethered physical testing -> progressively more complex flight testing.
