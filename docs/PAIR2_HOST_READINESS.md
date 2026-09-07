# Pair-2 host readiness

This is a fail-closed **preflight check**, not simulation evidence.

Run after installing the frozen host stack and checking out the exact source revisions:

```bash
export MICRO_XRCE_DDS_AGENT_VERSION=2.4.3
python3 tools/check_sitl_host.py \
  --px4-root /path/to/PX4-Autopilot \
  --px4-msgs-root /path/to/px4_msgs \
  --json evidence/host-readiness.json
```

`PASS` requires Ubuntu 24.04, ROS 2 Jazzy, `git`, `ros2`, `colcon`, `gz` and `MicroXRCEAgent`, the frozen Agent version, clean exact git revisions, every bridge-used PX4 message field, and byte-matching bridge-used PX4/`px4_msgs` definitions.

For this first pair-2 gate, message translation is intentionally not enabled. PX4 now supports message translation for differing definitions, but introducing it would add another integration variable before the basic two-node path is proven.

When Gazebo is the ROS time source, use the PX4-recommended ROS/Gazebo bridge setup (`ros-jazzy-ros-gzharmonic`), set ROS nodes to `use_sim_time=true`, and disable PX4 uXRCE-DDS time synchronization (`UXRCE_DDS_SYNCT=0`) so there is one simulation time authority.

A host `PASS` only permits the live gate to start. Closing Gate #1 still requires the two-node mission, fault injection, output-suppression, recovery/reconfiguration, and retained PX4/controller logs defined in `PAIR2_SITL_HOST_CONTRACT.md`.
