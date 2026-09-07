# ROS 2 / PX4 live transport workspace — v0.8.3-pre-SITL

This workspace contains the concrete transport binding and remains separate from the dependency-free controller core.

Packages:
- `coordination_msgs` — intent, supervisor gate, and normalized vehicle-state messages.
- `coordination_px4_bridge` — per-node ROS 2 bridge to PX4 uXRCE-DDS topics.

The bridge:
- subscribes to PX4 `VehicleLocalPosition`, `VehicleStatus`, and `FailsafeFlags`;
- republishes normalized NED vehicle state into the coordination namespace;
- publishes `OffboardControlMode` at the configured rate when external control is requested;
- publishes `TrajectorySetpoint` only when the supervisor permits intent, intent/state are fresh, local navigation is healthy, and PX4 v1.17 reports `NAVIGATION_STATE_OFFBOARD`;
- never arms the aircraft and never commands a mode switch.

Typical build in the frozen ROS 2 Jazzy + PX4 v1.17 `px4_msgs` environment:

```sh
cd integration/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

Example node 1:

```sh
ros2 run coordination_px4_bridge coordination_px4_bridge --ros-args \
  -r __ns:=/coord_001 \
  -p node_id:=1 \
  -p px4_namespace:=coord_001
```

PX4's ROS 2 publisher QoS is best-effort rather than ROS 2's default reliable policy, so the bridge explicitly uses compatible best-effort QoS for PX4 topics.

## PX4 v1.17 stable compatibility

The first live pair-2 gate is frozen to PX4 v1.17.0 and the matching `px4_msgs` v1.17.0 release.

PX4 v1.17 stable does not expose the later `VehicleStatus.accepts_offboard_setpoints` field. For this first gate the bridge derives `accepts_offboard_setpoints` strictly as `nav_state == NAVIGATION_STATE_OFFBOARD`. It does not infer acceptance from `can_set_nav_states_mask`, because that mask expresses mode selectability rather than whether the current mode accepts trajectory setpoints.

PX4 v1.17 stable also does not expose the later `FailsafeFlags.gnss_lost` field. The normalized coordination state therefore reports `global_position_invalid` directly and does not relabel it as GNSS loss.

This workspace still requires compilation against the frozen Jazzy/v1.17 environment before pair-2 SITL can start.
